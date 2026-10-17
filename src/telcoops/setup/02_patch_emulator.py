#!/usr/bin/env python
"""Capture, patch or restore the Jumpstart emulator notebook.

    python src/telcoops/setup/02_patch_emulator.py --capture   # save the original to artifacts/emulator/original/
    python src/telcoops/setup/02_patch_emulator.py --apply     # push the tower-aware, spike-capable version
    python src/telcoops/setup/02_patch_emulator.py --restore   # push the saved original back
    python src/telcoops/setup/02_patch_emulator.py --show      # print the patched source, change nothing

--apply captures the original first if there is no backup yet. The backup lives in
artifacts/emulator/original/ (git-ignored: it is the Jumpstart authors' notebook, not ours).
The patch itself is in notebook_patch.py (unit-tested offline).
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from telcoops.common.auth import assert_delegated_identity  # noqa: E402
from telcoops.common.config import StateStore  # noqa: E402
from telcoops.common.fabric_client import FabricClient  # noqa: E402
from telcoops.common.logging_setup import setup_logging  # noqa: E402

logger = setup_logging(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATOR = REPO_ROOT / "artifacts" / "emulator" / "cdr_generator.py"
TOWERS_CSV = REPO_ROOT / "artifacts" / "seed" / "towers.csv"
BACKUP_DIR = REPO_ROOT / "artifacts" / "emulator" / "original"
CONTENT_PATH = "notebook-content.py"


def _patch_module():
    spec = importlib.util.spec_from_file_location("notebook_patch", Path(__file__).with_name("notebook_patch.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_definition(client: FabricClient, workspace_id: str, notebook_id: str) -> list[dict]:
    result = client.call("POST", f"/workspaces/{workspace_id}/notebooks/{notebook_id}/getDefinition")
    return result.get("definition", {}).get("parts", [])


def content_of(parts: list[dict]) -> str:
    part = next((p for p in parts if p["path"] == CONTENT_PATH), None)
    if part is None:
        raise RuntimeError(f"definition has no '{CONTENT_PATH}' part; parts: {[p['path'] for p in parts]}. "
                           "The notebook may be in ipynb format: request fabricGitSource.")
    return base64.b64decode(part["payload"]).decode("utf-8")


def push_content(client: FabricClient, workspace_id: str, notebook_id: str, parts: list[dict], new_source: str) -> None:
    new_parts = []
    for p in parts:
        if p["path"] == CONTENT_PATH:
            p = {**p, "payload": base64.b64encode(new_source.encode("utf-8")).decode("ascii"), "payloadType": "InlineBase64"}
        new_parts.append(p)
    client.call("POST", f"/workspaces/{workspace_id}/notebooks/{notebook_id}/updateDefinition",
                {"definition": {"parts": new_parts}})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ("capture", "apply", "restore", "show"):
        group.add_argument(f"--{flag}", action="store_true")
    parser.add_argument("--skip-identity-check", action="store_true")
    args = parser.parse_args()

    patch = _patch_module()
    original_file = BACKUP_DIR / CONTENT_PATH
    generator_source = GENERATOR.read_text(encoding="utf-8")

    if args.show:
        if not original_file.exists():
            sys.exit("No backup yet: run --capture first.")
        print(patch.patch_notebook_source(original_file.read_text(encoding="utf-8"), generator_source, TOWERS_CSV))
        return

    if not args.skip_identity_check:
        assert_delegated_identity()
    state = StateStore()
    workspace_id = state.require("workspace", "workspaceId")["workspaceId"]
    notebook_id = state.require("emulator", "notebookId")["notebookId"]
    client = FabricClient()

    parts = get_definition(client, workspace_id, notebook_id)
    live = content_of(parts)

    if args.capture or (args.apply and not original_file.exists()):
        if patch.is_patched(live):
            sys.exit("The live notebook is already patched and there is no backup of the original. "
                     "Reinstall the Jumpstart item, or recreate artifacts/emulator/original/notebook-content.py.")
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        original_file.write_text(live, encoding="utf-8")
        logger.info("Saved the original notebook to %s", original_file)
        if args.capture:
            return

    if args.apply:
        source = live if not patch.is_patched(live) else original_file.read_text(encoding="utf-8")
        patched = patch.patch_notebook_source(source, generator_source, TOWERS_CSV)
        push_content(client, workspace_id, notebook_id, parts, patched)
        state.merge("emulator", {"patched": True})
        logger.info("Patched notebook pushed (parameters: spike_region, spike_drop_rate, spike_start_offset_min, "
                    "spike_minutes, run_minutes, records_per_second).")
    elif args.restore:
        if not original_file.exists():
            sys.exit("No backup to restore.")
        push_content(client, workspace_id, notebook_id, parts, original_file.read_text(encoding="utf-8"))
        state.merge("emulator", {"patched": False})
        logger.info("Original notebook restored.")


if __name__ == "__main__":
    main()
