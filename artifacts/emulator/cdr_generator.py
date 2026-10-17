"""Tower-aware CDR generator with a spike mode.

This file is the single source for the generator logic. It is imported by the offline tests and
inlined (by src/telcoops/setup/02_patch_emulator.py) into the Jumpstart emulator notebook, which
runs in Fabric with only the standard library. Keep it standard-library only and free of top-level
side effects.

Differences from the Jumpstart's generate_cdr():
  - every record carries tower_id and region, picked from the TOWERS table (weighted traffic), and
    the tower's own latitude / longitude with a little jitter instead of a random point
  - spike mode: for one region and a time window, the Dropped share is raised (default 25%)
Everything else (field names, 1-10 quality, Failed duration 0, ...) is unchanged so the Jumpstart
dashboard keeps working.
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

CALL_TYPES = ["Voice", "Video", "Data"]
STATUS_OPTIONS = ["Completed", "Failed", "Dropped"]
BASELINE_WEIGHTS = (0.85, 0.08, 0.07)  # Completed, Failed, Dropped: the Jumpstart default
SPIKE_FAILED_SHARE = 0.08

# Filled in by the notebook patcher from artifacts/seed/towers.csv:
# (tower_id, region, lat, lon, traffic_weight)
TOWERS: list[tuple[str, str, float, float, float]] = []


def status_weights(region: str, now: datetime, spike: dict | None) -> tuple[float, float, float]:
    """(Completed, Failed, Dropped) weights for a call in `region` at `now`.

    `spike` is None, or {"region": str, "drop_rate": float, "start": datetime, "end": datetime}.
    """
    if spike and spike.get("region") and region == spike["region"] and spike["start"] <= now < spike["end"]:
        dropped = float(spike["drop_rate"])
        return (round(1.0 - dropped - SPIKE_FAILED_SHARE, 6), SPIKE_FAILED_SHARE, dropped)
    return BASELINE_WEIGHTS


def make_spike(region: str, drop_rate: float, start_offset_min: float, minutes: float,
               run_start: datetime | None = None) -> dict | None:
    """Build the spike window, relative to the start of the run. Empty region means no spike."""
    if not region:
        return None
    if not 0.0 < drop_rate < 0.92:
        raise ValueError("drop_rate must be between 0 and 0.92 (Failed keeps 8%)")
    run_start = run_start or datetime.now(timezone.utc)
    start = run_start + timedelta(minutes=start_offset_min)
    return {"region": region, "drop_rate": drop_rate, "start": start, "end": start + timedelta(minutes=minutes)}


def pick_tower(rng: random.Random, towers=None):
    towers = towers if towers is not None else TOWERS
    if not towers:
        raise RuntimeError("TOWERS is empty: the notebook patcher did not inline towers.csv")
    return rng.choices(towers, weights=[t[4] for t in towers], k=1)[0]


def generate_cdr(rng: random.Random | None = None, now: datetime | None = None,
                 spike: dict | None = None, towers=None) -> dict:
    """One call data record, as a dict ready for json.dumps()."""
    rng = rng or random
    now = now or datetime.now(timezone.utc)
    tower_id, region, lat, lon, _weight = pick_tower(rng, towers)

    duration_seconds = rng.randint(5, 3600)
    call_start = now
    status = rng.choices(STATUS_OPTIONS, weights=status_weights(region, now, spike), k=1)[0]

    if status == "Failed":
        duration_seconds = 0
    elif status == "Dropped":
        duration_seconds = rng.randint(5, duration_seconds // 2) if duration_seconds > 10 else duration_seconds
    call_end = call_start + timedelta(seconds=duration_seconds)

    if status == "Dropped":
        call_quality = rng.randint(1, 5)
    elif status == "Failed":
        call_quality = rng.randint(1, 3)
    else:
        call_quality = rng.randint(1, 10)

    return {
        "call_id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
        "subscriber_id": f"SUB-{rng.randint(100000, 999999)}",
        "call_start_time": call_start.isoformat().replace("+00:00", "Z"),
        "call_end_time": call_end.isoformat().replace("+00:00", "Z"),
        "duration_seconds": duration_seconds,
        "call_type": rng.choice(CALL_TYPES),
        "status": status,
        "tower_latitude": round(lat + rng.uniform(-0.01, 0.01), 6),
        "tower_longitude": round(lon + rng.uniform(-0.01, 0.01), 6),
        "call_quality": call_quality,
        "tower_id": tower_id,
        "region": region,
    }
