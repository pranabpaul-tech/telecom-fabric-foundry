"""Offline checks on the KQL files and the schema applier (no Azure needed)."""
from __future__ import annotations

import csv
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_applier():
    spec = importlib.util.spec_from_file_location("kql_schema", ROOT / "src/telcoops/setup/03_kql_schema.py")
    # the applier imports telcoops.common.*; make that importable without installing the package
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


kql = _load_applier()


def _all_statements():
    out = []
    for path in kql.kql_files():
        out += [(path.name, s) for s in kql.parse_kql_statements(path.read_text(encoding="utf-8"))]
    return out


def test_files_are_ordered_and_every_statement_is_a_dot_command():
    assert [p.name for p in kql.kql_files()] == [
        "010_cdr_raw.kql", "020_towers.kql", "030_mv_drops_5m.kql", "035_mv_region_5m.kql", "040_functions.kql"]
    for name, s in _all_statements():
        assert s.startswith("."), f"{name}: {s[:60]}"


def test_expected_objects_are_created():
    text = "\n".join(s for _, s in _all_statements())
    for needle in [".create-merge table cdr_raw", "ingestion json mapping 'cdr_raw_mapping'",
                   ".create-merge table towers", "materialized-view with (backfill = true) mv_drops_5m", "mv_region_5m on table cdr_raw",
                   "drop_rate_by_region(", "worst_towers(", "region_alert_candidates(", "silent_towers("]:
        assert needle in text, needle


def test_mapping_lists_all_twelve_columns_including_tower_id_and_region():
    stmt = next(s for _, s in _all_statements() if "ingestion json mapping" in s)
    cols = re.findall(r'"column":"(\w+)"', stmt)
    assert len(cols) == 12 and {"tower_id", "region"} <= set(cols)
    assert cols[:10] == ["call_id", "subscriber_id", "call_start_time", "call_end_time", "duration_seconds",
                         "call_type", "status", "tower_latitude", "tower_longitude", "call_quality"]


def test_no_reserved_word_used_as_a_column_name():
    text = "\n".join(s for _, s in _all_statements())
    for word in ("latest", "cycles", "first"):
        assert not re.search(rf"\b{word}\s*[=:]", text), word


def test_backfill_is_dropped_for_an_existing_view_only():
    stmt = next(s for _, s in _all_statements() if "materialized-view" in s)
    assert "backfill" in kql.adapt_for_existing_views(stmt, set())
    adapted = kql.adapt_for_existing_views(stmt, {"mv_drops_5m"})
    assert "backfill" not in adapted and adapted.startswith(".create-or-alter materialized-view mv_drops_5m")


def test_alert_function_encodes_the_operations_agent_rule():
    stmt = next(s for _, s in _all_statements() if "region_alert_candidates(" in s)
    assert "min_calls: long = 50" in stmt and "threshold: real = 0.15" in stmt and "window: timespan = 5m" in stmt
    assert "calls >= 10" in stmt  # affected-tower minimum sample (KPI-DEF-001 section 2)


def test_towers_load_matches_the_seed_file():
    stmt = kql.towers_set_or_replace()
    rows = list(csv.DictReader((ROOT / "artifacts/seed/towers.csv").open(encoding="utf-8")))
    assert stmt.startswith(".set-or-replace towers <| datatable(")
    assert stmt.count('"GP-0') == sum(r["tower_id"].startswith("GP-") for r in rows)
    for r in rows:
        assert f'"{r["tower_id"]}"' in stmt
    assert len(rows) == 40
