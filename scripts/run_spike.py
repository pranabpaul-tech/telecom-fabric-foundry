#!/usr/bin/env python
"""Start the patched emulator notebook as a Fabric job, optionally with a drop-rate spike.

    python scripts/run_spike.py --steady --run-minutes 30
    python scripts/run_spike.py --region Gauteng --minutes 10 --run-minutes 30
    python scripts/run_spike.py --region Gauteng --drop-rate 0.25 --offset 5 --minutes 10

The emulator always runs as a bounded job (`run_minutes`), never open-ended, because the F8 capacity
bills while it is active. Parameters are the ones in the notebook's PARAMETERS cell. The job id is
saved to state.json['emulator']['lastJobId'] for scripts/emulator_status.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telcoops.common.config import StateStore  # noqa: E402
from telcoops.common.fabric_client import FabricClient  # noqa: E402


def param(value, kind: str) -> dict:
    return {"value": value, "type": kind}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--region", default="", help="province to spike, e.g. Gauteng (empty = steady state)")
    p.add_argument("--steady", action="store_true", help="no spike (same as an empty --region)")
    p.add_argument("--drop-rate", type=float, default=0.25, help="Dropped share inside the spike (default 0.25)")
    p.add_argument("--offset", type=float, default=0, help="minutes after the run starts when the spike begins")
    p.add_argument("--minutes", type=float, default=10, help="spike length in minutes (default 10)")
    p.add_argument("--run-minutes", type=float, default=30, help="total run length in minutes (default 30)")
    p.add_argument("--rps", type=int, default=5, help="records per second (default 5, as in the Jumpstart)")
    args = p.parse_args()

    region = "" if args.steady else args.region
    if region and args.offset + args.minutes > args.run_minutes:
        sys.exit(f"The spike ends at minute {args.offset + args.minutes:g}, after the run ends ({args.run_minutes:g}). "
                 "Raise --run-minutes.")

    state = StateStore()
    workspace_id = state.require("workspace", "workspaceId")["workspaceId"]
    notebook_id = state.require("emulator", "notebookId")["notebookId"]
    if not (state.get("emulator") or {}).get("patched"):
        print("warning: the emulator notebook is not patched (02_patch_emulator.py --apply); spike parameters are ignored.",
              file=sys.stderr)

    body = {"executionData": {"parameters": {
        "spike_region": param(region, "string"),
        "spike_drop_rate": param(args.drop_rate, "float"),
        "spike_start_offset_min": param(args.offset, "float"),
        "spike_minutes": param(args.minutes, "float"),
        "run_minutes": param(args.run_minutes, "float"),
        "records_per_second": param(args.rps, "int"),
        "_inlineInstallationEnabled": param(True, "bool"),
    }}}
    client = FabricClient()
    resp = client.request("POST", f"/workspaces/{workspace_id}/items/{notebook_id}/jobs/instances?jobType=RunNotebook", body)
    location = resp.headers.get("Location", "")
    job_id = location.rstrip("/").split("/")[-1] if location else ""
    state.merge("emulator", {"lastJobId": job_id, "lastJobRegion": region or "(steady)"})
    print(f"started job {job_id or '(id not returned)'}: "
          + (f"spike {region} {args.drop_rate:.0%} for {args.minutes:g} min starting at +{args.offset:g} min, " if region else "steady state, ")
          + f"run {args.run_minutes:g} min at {args.rps}/s")


if __name__ == "__main__":
    main()
