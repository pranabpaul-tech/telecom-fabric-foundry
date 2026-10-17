#!/usr/bin/env python
"""One-line status of the last emulator job and the row counts in the Eventhouse.

    python scripts/emulator_status.py            # status + counts
    python scripts/emulator_status.py --cancel   # cancel the last job (stops the stream and the cost)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telcoops.common.config import StateStore  # noqa: E402
from telcoops.common.fabric_client import FabricClient  # noqa: E402
from telcoops.common.kusto_client import EventhouseKustoClient  # noqa: E402


def main() -> None:
    state = StateStore()
    ws = state.require("workspace", "workspaceId")["workspaceId"]
    em = state.require("emulator", "notebookId")
    eh = state.require("eventhouse", "queryServiceUri", "kqlDatabaseName")
    job_id = em.get("lastJobId", "")
    fc = FabricClient()

    if "--cancel" in sys.argv:
        if not job_id:
            sys.exit("no job id recorded")
        fc.request("POST", f"/workspaces/{ws}/items/{em['notebookId']}/jobs/instances/{job_id}/cancel", {})
        print("cancel requested")
        return

    status, started, err = "n/a", "", ""
    if job_id:
        job = fc.request("GET", f"/workspaces/{ws}/items/{em['notebookId']}/jobs/instances/{job_id}").json()
        status, started = job.get("status"), (job.get("startTimeUtc") or "")[:19]
        err = (job.get("failureReason") or {}).get("message", "")

    counts = "n/a"
    try:
        c = EventhouseKustoClient(eh["queryServiceUri"], eh["kqlDatabaseName"])
        rows = c.query_to_dicts(
            "cdr_raw | summarize total = count(), last_5m = countif(call_start_time > ago(5m)), "
            "with_tower = countif(isnotempty(tower_id)), newest = max(call_start_time)")
        counts = ", ".join(f"{k}={v}" for k, v in rows[0].items())
        c.close()
    except Exception as exc:  # noqa: BLE001
        counts = f"kql error: {str(exc)[:100]}"
    print(f"job={status} started={started} | cdr_raw: {counts}" + (f" | ERROR: {err[:200]}" if err else ""))


if __name__ == "__main__":
    main()
