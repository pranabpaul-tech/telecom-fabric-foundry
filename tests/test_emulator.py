"""Offline tests for the tower-aware CDR generator (artifacts/emulator/cdr_generator.py)."""
from __future__ import annotations

import csv
import importlib.util
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_generator():
    spec = importlib.util.spec_from_file_location("cdr_generator", ROOT / "artifacts/emulator/cdr_generator.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = _load_generator()


@pytest.fixture(scope="module")
def towers():
    rows = list(csv.DictReader((ROOT / "artifacts/seed/towers.csv").open(encoding="utf-8")))
    return [(r["tower_id"], r["region"], float(r["lat"]), float(r["lon"]), float(r["traffic_weight"])) for r in rows]


def _sample(n, towers, spike=None, seed=1, now=None):
    rng = random.Random(seed)
    now = now or datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)
    return [gen.generate_cdr(rng, now, spike, towers) for _ in range(n)]


def test_record_has_jumpstart_fields_plus_tower_and_region(towers):
    rec = _sample(1, towers)[0]
    for field in ("call_id", "subscriber_id", "call_start_time", "call_end_time", "duration_seconds", "call_type",
                  "status", "tower_latitude", "tower_longitude", "call_quality", "tower_id", "region"):
        assert field in rec
    assert rec["call_start_time"].endswith("Z")


def test_every_tower_id_is_in_the_seed_and_region_matches(towers):
    by_id = {t[0]: t for t in towers}
    for rec in _sample(3000, towers):
        assert rec["tower_id"] in by_id
        assert rec["region"] == by_id[rec["tower_id"]][1]
        assert abs(rec["tower_latitude"] - by_id[rec["tower_id"]][2]) <= 0.011
        assert abs(rec["tower_longitude"] - by_id[rec["tower_id"]][3]) <= 0.011


def test_baseline_mix_is_85_8_7(towers):
    counts = Counter(r["status"] for r in _sample(20000, towers))
    n = sum(counts.values())
    assert counts["Completed"] / n == pytest.approx(0.85, abs=0.015)
    assert counts["Failed"] / n == pytest.approx(0.08, abs=0.015)
    assert counts["Dropped"] / n == pytest.approx(0.07, abs=0.015)


def test_gauteng_carries_a_large_share_so_the_50_call_rule_can_fire(towers):
    recs = _sample(20000, towers)
    share = sum(r["region"] == "Gauteng" for r in recs) / len(recs)
    assert 0.30 < share < 0.45
    # 5 calls/s => 1500 calls per 5 minutes; Gauteng must clear the 50-call minimum with room to spare
    assert share * 1500 > 300


def test_spike_raises_drops_only_in_region_and_window(towers):
    now = datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)
    spike = gen.make_spike("Gauteng", 0.25, 0, 10, run_start=now)
    inside = _sample(20000, towers, spike, seed=2, now=now + timedelta(minutes=5))
    gp = [r for r in inside if r["region"] == "Gauteng"]
    other = [r for r in inside if r["region"] != "Gauteng"]
    assert sum(r["status"] == "Dropped" for r in gp) / len(gp) == pytest.approx(0.25, abs=0.02)
    assert sum(r["status"] == "Dropped" for r in other) / len(other) == pytest.approx(0.07, abs=0.015)

    after = _sample(20000, towers, spike, seed=3, now=now + timedelta(minutes=11))
    gp_after = [r for r in after if r["region"] == "Gauteng"]
    assert sum(r["status"] == "Dropped" for r in gp_after) / len(gp_after) == pytest.approx(0.07, abs=0.015)


def test_spike_window_is_half_open_and_offset_is_applied():
    now = datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)
    spike = gen.make_spike("Gauteng", 0.25, 5, 10, run_start=now)
    assert gen.status_weights("Gauteng", now + timedelta(minutes=4, seconds=59), spike) == gen.BASELINE_WEIGHTS
    assert gen.status_weights("Gauteng", now + timedelta(minutes=5), spike)[2] == 0.25
    assert gen.status_weights("Gauteng", now + timedelta(minutes=15), spike) == gen.BASELINE_WEIGHTS


def test_no_spike_when_region_is_empty_and_bad_rates_are_rejected():
    assert gen.make_spike("", 0.25, 0, 10) is None
    with pytest.raises(ValueError):
        gen.make_spike("Gauteng", 0.95, 0, 10)


def test_failed_calls_have_zero_duration_and_dropped_are_low_quality(towers):
    for rec in _sample(5000, towers):
        if rec["status"] == "Failed":
            assert rec["duration_seconds"] == 0 and rec["call_quality"] <= 3
        if rec["status"] == "Dropped":
            assert rec["call_quality"] <= 5
