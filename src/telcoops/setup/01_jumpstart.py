#!/usr/bin/env python
"""Create the Fabric workspace on the F8 capacity, install the Telecom CDR Jumpstart unchanged, and
record every item ID in state.json.

Run from the local machine (not the jumpbox), signed in with `az login` as the operator who will
later create the Operations Agent. Steps are idempotent: a re-run reuses the workspace and skips
the install when the Jumpstart items already exist.

    python src/telcoops/setup/01_jumpstart.py
    python src/telcoops/setup/01_jumpstart.py --skip-install     # only (re)capture IDs

The Jumpstart needs Python 3.10-3.13, so the installer runs in its own .venv-js (created with
`py -3.13` if missing).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from telcoops.common.auth import assert_delegated_identity  # noqa: E402
from telcoops.common.config import StateStore, get_settings  # noqa: E402
from telcoops.common.fabric_client import FabricClient  # noqa: E402
from telcoops.common.logging_setup import setup_logging  # noqa: E402

logger = setup_logging(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
VENV_JS = REPO_ROOT / ".venv-js"
EXPECTED_TYPES = {"Notebook", "Eventstream", "Eventhouse", "KQLDatabase", "KQLDashboard"}


def resolve_capacity_guid(client: FabricClient, display_name: str) -> str:
    """assignToCapacity wants Fabric's own capacity GUID, not the ARM resource ID."""
    capacities = client.request("GET", "/capacities").json().get("value", [])
    match = next((c for c in capacities if c.get("displayName") == display_name), None)
    if match is None:
        raise RuntimeError(f"No Fabric capacity with displayName '{display_name}' is visible to this identity. "
                           f"Visible: {[c.get('displayName') for c in capacities]}. "
                           "Is the capacity active, and is the operator a capacity admin?")
    if match.get("state") not in (None, "Active"):
        raise RuntimeError(f"Capacity '{display_name}' is {match.get('state')}, not Active. Resume it first.")
    return match["id"]


def ensure_workspace(client: FabricClient, state: StateStore, name: str, capacity_name: str) -> str:
    existing = state.get("workspace") or {}
    workspace_id = existing.get("workspaceId")
    if workspace_id:
        try:
            client.request("GET", f"/workspaces/{workspace_id}")
            logger.info("Workspace %s from state.json still exists.", workspace_id)
        except Exception:  # noqa: BLE001
            logger.warning("Recorded workspace no longer resolves; looking it up by name.")
            workspace_id = None
    if not workspace_id:
        found = [w for w in client.request("GET", "/workspaces").json().get("value", []) if w.get("displayName") == name]
        if found:
            workspace_id = found[0]["id"]
            logger.info("Found existing workspace '%s' (%s).", name, workspace_id)
        else:
            workspace_id = client.call("POST", "/workspaces", {
                "displayName": name,
                "description": "Telecom NOC Copilot: real-time call data records, alerting and conversational triage.",
            })["id"]
            logger.info("Created workspace '%s' (%s).", name, workspace_id)
        # Persist now: if the capacity assignment below fails, a re-run must reuse this workspace.
        state.merge("workspace", {"workspaceId": workspace_id, "workspaceName": name})

    capacity_guid = resolve_capacity_guid(client, capacity_name)
    ws = client.request("GET", f"/workspaces/{workspace_id}").json()
    if ws.get("capacityId") != capacity_guid:
        logger.info("Assigning workspace to capacity %s (%s)...", capacity_name, capacity_guid)
        client.call("POST", f"/workspaces/{workspace_id}/assignToCapacity", {"capacityId": capacity_guid})
    state.merge("workspace", {"workspaceId": workspace_id, "workspaceName": name,
                              "capacityId": capacity_guid, "capacityAssigned": True})
    return workspace_id


def list_items(client: FabricClient, workspace_id: str) -> list[dict]:
    return client.request("GET", f"/workspaces/{workspace_id}/items").json().get("value", [])


def ensure_install_venv() -> Path:
    py = VENV_JS / "Scripts" / "python.exe"
    if not py.exists():
        launcher = shutil.which("py")
        if launcher is None:
            raise RuntimeError("Python launcher `py` not found; install Python 3.13 (the Jumpstart needs 3.10-3.13).")
        logger.info("Creating %s with Python 3.13...", VENV_JS)
        subprocess.run([launcher, "-3.13", "-m", "venv", str(VENV_JS)], check=True)
        subprocess.run([str(py), "-m", "pip", "install", "-q", "fabric-jumpstart"], check=True)
    return py


def install_jumpstart(workspace_id: str, jumpstart_name: str) -> None:
    py = ensure_install_venv()
    code = (f"import fabric_jumpstart as j; j.install({jumpstart_name!r}, workspace_id={workspace_id!r}, unattended=True)")
    env = {**__import__("os").environ, "FABRIC_JUMPSTART_TOKEN_CREDENTIAL": "AzureCliCredential"}
    logger.info("Installing Jumpstart '%s' (about 2 minutes)...", jumpstart_name)
    result = subprocess.run([str(py), "-c", code], env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Jumpstart install failed (exit {result.returncode}). See the output above.")


def capture(client: FabricClient, state: StateStore, workspace_id: str, settings) -> None:
    items = list_items(client, workspace_id)
    by_type: dict[str, list[dict]] = {}
    for it in items:
        by_type.setdefault(it["type"], []).append(it)
    logger.info("Workspace items: %s", {t: [i["displayName"] for i in v] for t, v in by_type.items()})
    missing = EXPECTED_TYPES - by_type.keys()
    if missing:
        raise RuntimeError(f"Jumpstart items missing in the workspace: {sorted(missing)}")

    def pick(item_type: str, name: str) -> dict:
        found = [i for i in by_type[item_type] if i["displayName"] == name]
        if not found:
            raise RuntimeError(f"No {item_type} named '{name}'; found {[i['displayName'] for i in by_type[item_type]]}. "
                               "Update the names in common/config.py to match the installed Jumpstart.")
        return found[0]

    notebook = pick("Notebook", settings.emulator_notebook_name)
    stream = pick("Eventstream", settings.eventstream_name)
    eventhouse = pick("Eventhouse", settings.eventhouse_name)
    kql_db = pick("KQLDatabase", settings.kql_database_name)
    dashboard = by_type["KQLDashboard"][0]

    db = client.request("GET", f"/workspaces/{workspace_id}/kqlDatabases/{kql_db['id']}").json()["properties"]
    state.merge("eventhouse", {
        "eventhouseId": eventhouse["id"], "eventhouseName": eventhouse["displayName"],
        "kqlDatabaseId": kql_db["id"], "kqlDatabaseName": kql_db["displayName"],
        "queryServiceUri": db["queryServiceUri"], "ingestionServiceUri": db.get("ingestionServiceUri", ""),
    })
    state.merge("emulator", {
        "notebookId": notebook["id"], "notebookName": notebook["displayName"],
        "eventstreamId": stream["id"], "eventstreamName": stream["displayName"],
        "dashboardId": dashboard["id"], "dashboardName": dashboard["displayName"],
    })
    logger.info("state.json updated (eventhouse, emulator).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-install", action="store_true", help="do not install the Jumpstart; only capture IDs")
    parser.add_argument("--skip-identity-check", action="store_true")
    args = parser.parse_args()

    if not args.skip_identity_check:
        assert_delegated_identity()
    settings = get_settings()
    state = StateStore()
    client = FabricClient()

    workspace_id = ensure_workspace(client, state, settings.workspace_name, settings.fabric_capacity_name)

    names = {i["displayName"] for i in list_items(client, workspace_id)}
    if not args.skip_install:
        if settings.emulator_notebook_name in names and settings.eventhouse_name in names:
            logger.info("Jumpstart items already present; skipping the install.")
        else:
            install_jumpstart(workspace_id, settings.jumpstart_name)

    capture(client, state, workspace_id, settings)
    logger.info("Done. Next: python scripts/emulator_status.py, then 02_patch_emulator.py --capture.")


if __name__ == "__main__":
    main()
