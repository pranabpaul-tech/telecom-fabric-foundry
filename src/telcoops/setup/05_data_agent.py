#!/usr/bin/env python
"""Create, update and publish the Fabric Data Agent over the telecom KQL database.

    python src/telcoops/setup/05_data_agent.py --apply     # create or update the agent, then publish it
    python src/telcoops/setup/05_data_agent.py --show      # print the live definition's part paths
    python src/telcoops/setup/05_data_agent.py --dry-run   # build the parts locally and print their paths

Inputs: artifacts/data-agent/instructions.md (the agent's instructions), artifacts/data-agent/examples.json
(question / KQL pairs). The data source is the KQL database from state.json['eventhouse'].

"Publishing" through the definition API means writing the same configuration under Files/Config/published/
together with Files/Config/publish_info.json (see the Data Agent item definition article).
Run as the operator: the agent answers with the identity of whoever asks, so the people who use it need
access to the workspace and the KQL database.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from telcoops.common.auth import assert_delegated_identity  # noqa: E402
from telcoops.common.config import StateStore, get_settings  # noqa: E402
from telcoops.common.fabric_client import FabricClient, decode_definition_part  # noqa: E402
from telcoops.common.logging_setup import setup_logging  # noqa: E402

logger = setup_logging(__name__)

ART = Path(__file__).resolve().parents[3] / "artifacts" / "data-agent"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition"
DATA_AGENT_SCHEMA = f"{SCHEMA}/dataAgent/2.1.0/schema.json"
STAGE_SCHEMA = f"{SCHEMA}/stageConfiguration/1.0.0/schema.json"
DATASOURCE_SCHEMA = f"{SCHEMA}/dataSource/1.0.0/schema.json"
FEWSHOTS_SCHEMA = f"{SCHEMA}/fewShots/1.0.0/schema.json"
PUBLISH_SCHEMA = f"{SCHEMA}/publishInfo/1.0.0/schema.json"

TABLES = ["cdr_raw", "towers", "mv_drops_5m"]


def part(path: str, obj: dict) -> dict:
    payload = base64.b64encode(json.dumps(obj, indent=2).encode("utf-8")).decode("ascii")
    return {"path": path, "payload": payload, "payloadType": "InlineBase64"}


def build_parts(workspace_id: str, kql_db_id: str, kql_db_name: str, agent_description: str, publish: bool) -> list[dict]:
    instructions = (ART / "instructions.md").read_text(encoding="utf-8").strip()
    examples = json.loads((ART / "examples.json").read_text(encoding="utf-8"))
    source_dir = f"kusto-{kql_db_name}"
    datasource = {
        "$schema": DATASOURCE_SCHEMA,
        "artifactId": kql_db_id,
        "workspaceId": workspace_id,
        "displayName": kql_db_name,
        "type": "kusto",
        "userDescription": "Live synthetic call data records: calls per tower and region, drop rates, quality.",
        "dataSourceInstructions": "Use mv_drops_5m and the functions drop_rate_by_region, worst_towers, "
                                  "region_alert_candidates and silent_towers for rates; use cdr_raw only for single calls.",
        "elements": [
            {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"telco/{t}")), "display_name": t, "type": "kusto.table",
             "is_selected": True} for t in TABLES
        ],
    }
    fewshots = {
        "$schema": FEWSHOTS_SCHEMA,
        "fewShots": [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, ex["question"])), "question": ex["question"],
                      "query": ex["query"]} for ex in examples],
    }
    stage = {"$schema": STAGE_SCHEMA, "aiInstructions": instructions}

    parts = [part("Files/Config/data_agent.json", {"$schema": DATA_AGENT_SCHEMA})]
    for stage_name in (["draft", "published"] if publish else ["draft"]):
        base = f"Files/Config/{stage_name}"
        parts += [part(f"{base}/stage_config.json", stage),
                  part(f"{base}/{source_dir}/datasource.json", datasource),
                  part(f"{base}/{source_dir}/fewshots.json", fewshots)]
    if publish:
        parts.append(part("Files/Config/publish_info.json", {"$schema": PUBLISH_SCHEMA, "description": agent_description}))
    return parts


def find_agent(client: FabricClient, workspace_id: str, name: str) -> str | None:
    items = client.request("GET", f"/workspaces/{workspace_id}/items?type=DataAgent").json().get("value", [])
    match = next((i for i in items if i["displayName"] == name), None)
    return match["id"] if match else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    for flag in ("apply", "show", "dry_run"):
        mode.add_argument(f"--{flag.replace('_', '-')}", action="store_true")
    parser.add_argument("--draft-only", action="store_true", help="do not publish")
    parser.add_argument("--skip-identity-check", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    state = StateStore()
    eh = state.require("eventhouse", "kqlDatabaseId", "kqlDatabaseName")
    workspace_id = state.require("workspace", "workspaceId")["workspaceId"]
    description = "Telecom CDR data agent: drop rates, worst towers, quality trends and call mix (synthetic data)."

    if args.dry_run:
        for p in build_parts(workspace_id, eh["kqlDatabaseId"], eh["kqlDatabaseName"], description, not args.draft_only):
            print(p["path"], len(base64.b64decode(p["payload"])), "bytes")
        return

    if not args.skip_identity_check:
        assert_delegated_identity()
    client = FabricClient()
    agent_id = (state.get("data_agent") or {}).get("dataAgentId") or find_agent(client, workspace_id, settings.data_agent_name)

    if args.show:
        if not agent_id:
            sys.exit("no data agent yet")
        result = client.call("POST", f"/workspaces/{workspace_id}/dataAgents/{agent_id}/getDefinition")
        for p in result.get("definition", {}).get("parts", []):
            print(p["path"])
            if p["path"].endswith("datasource.json"):
                print(json.dumps(decode_definition_part(p), indent=1)[:1500])
        return

    parts = build_parts(workspace_id, eh["kqlDatabaseId"], eh["kqlDatabaseName"], description, not args.draft_only)
    if agent_id:
        logger.info("Updating Data Agent %s...", agent_id)
        client.call("POST", f"/workspaces/{workspace_id}/dataAgents/{agent_id}/updateDefinition",
                    {"definition": {"parts": parts}})
    else:
        logger.info("Creating Data Agent '%s'...", settings.data_agent_name)
        created = client.call("POST", f"/workspaces/{workspace_id}/dataAgents", {
            "displayName": settings.data_agent_name, "description": description,
            "definition": {"parts": parts}})
        agent_id = created["id"]
    state.merge("data_agent", {"dataAgentId": agent_id, "dataAgentName": settings.data_agent_name,
                               "published": not args.draft_only, "workspaceId": workspace_id})
    logger.info("Done. dataAgentId=%s published=%s", agent_id, not args.draft_only)


if __name__ == "__main__":
    main()
