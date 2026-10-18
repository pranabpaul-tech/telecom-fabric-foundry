"""Offline tests for the orchestrator's deterministic tool logic (hosted_agent/tools.py)."""
from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tools", ROOT / "src/telcoops/foundry/hosted_agent/tools.py")
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


def test_region_and_customer_validation_is_exact_and_blocks_injection():
    assert tools.validate_region("gauteng") == "Gauteng"
    assert tools.validate_region(" Western Cape ") == "Western Cape"
    for bad in ["Gauteng' or 1==1 //", "Atlantis", "", "Gauteng; .drop table cdr_raw"]:
        with pytest.raises(ValueError):
            tools.validate_region(bad)
    assert tools.validate_customer("karoo mutual bank") == "Karoo Mutual Bank"
    with pytest.raises(ValueError):
        tools.validate_customer("Evil Corp")


def test_window_bounds():
    assert tools.validate_window(60) == 60
    for bad in (4, 0, 1441, -5, "60"):
        with pytest.raises(ValueError):
            tools.validate_window(bad)


def test_kql_builders_are_anchored_to_the_newest_bin_and_read_only():
    for kql in (tools.region_rate_kql("Gauteng", 60), tools.affected_towers_kql("Gauteng", 15, 15.0, 10),
                tools.customer_rate_kql("Jacaranda Health Network", "Gauteng", 60)):
        assert "toscalar(mv_drops_5m | summarize max(bin_start))" in kql
        assert tools.reject_reason(kql) is None
        assert "ago(" not in kql  # never the wall clock: the emulator is not always running
    assert "region == 'Gauteng'" in tools.region_rate_kql("gauteng", 60)
    assert "enterprise_customers has 'Jacaranda Health Network'" in tools.customer_rate_kql(
        "Jacaranda Health Network", "Gauteng", 60)


def test_reject_reason_blocks_management_and_escapes():
    assert tools.reject_reason("cdr_raw | take 5") is None
    assert tools.reject_reason(".drop table cdr_raw") is not None
    assert tools.reject_reason("  .set-or-append x <| y") is not None
    for q in ("externaldata(x:string)[h'http://a']", "cdr_raw | evaluate python()", "database('other').t", "cluster('c').database('d').t"):
        assert tools.reject_reason(q) is not None
    assert tools.reject_reason("   ") == "empty query"


def test_region_rate_needs_50_calls_and_flags_the_15_percent_threshold():
    row = {"calls": 600, "completed": 450, "failed": 30, "dropped": 150, "towers": 14, "window_start": "a", "window_end": "b"}
    out = tools.shape_region_rate("Gauteng", 5, row)
    assert out["status"] == "OK" and out["drop_pct"] == 25.0 and out["above_alert_threshold"] is True
    assert out["setup_fail_pct"] == 5.0
    low = tools.shape_region_rate("Northern Cape", 5, {"calls": 30, "dropped": 25, "failed": 0, "towers": 2})
    assert low["status"] == "INSUFFICIENT_SAMPLE" and low["drop_pct"] is None
    assert tools.shape_region_rate("Gauteng", 5, None)["status"] == "INSUFFICIENT_SAMPLE"
    # exactly 15.0% is NOT above the threshold (strictly greater than)
    edge = tools.shape_region_rate("Gauteng", 5, {"calls": 200, "dropped": 30, "failed": 0, "towers": 3})
    assert edge["drop_pct"] == 15.0 and edge["above_alert_threshold"] is False


def test_affected_towers_collects_enterprise_customers():
    rows = [{"tower_id": "GP-002", "site_name": "Sandton Central", "city": "Sandton", "drop_pct": 31.2, "calls": 90,
             "vendor": "Ericsson", "technology": "5G", "backhaul": "fibre", "backup_power": "battery+generator",
             "backup_hours": 24, "field_team": "GP-Central", "enterprise_customers": "Jacaranda Health Network;Karoo Mutual Bank"},
            {"tower_id": "GP-003", "site_name": "Soweto Orlando", "city": "Soweto", "drop_pct": 27.8, "calls": 97,
             "vendor": "Huawei", "technology": "4G", "backhaul": "microwave", "backup_power": "battery", "backup_hours": 4,
             "field_team": "GP-Central", "enterprise_customers": ""}]
    out = tools.shape_affected("Gauteng", 15, 15.0, rows)
    assert out["affected_tower_count"] == 2
    assert out["enterprise_customers_affected"] == ["Jacaranda Health Network", "Karoo Mutual Bank"]
    assert out["towers"][1]["enterprise_customers"] == []


def test_sla_verdict_is_strict_and_respects_minimum_sample():
    base = {"served_towers": 4, "towers": 4, "window_start": "s", "window_end": "e"}
    breach = tools.sla_verdict("Jacaranda Health Network", "Gauteng", 60, {**base, "calls": 800, "dropped": 80}, 9.0)
    assert breach["status"] == "BREACH" and breach["drop_pct"] == 10.0 and breach["margin_pp"] == 1.0
    equal = tools.sla_verdict("Jacaranda Health Network", "Gauteng", 60, {**base, "calls": 100, "dropped": 9}, 9.0)
    assert equal["status"] == "WITHIN_LIMIT" and equal["breach"] is False  # exactly at the limit is not a breach
    thin = tools.sla_verdict("Jacaranda Health Network", "Gauteng", 60, {**base, "calls": 99, "dropped": 90}, 9.0)
    assert thin["status"] == "INSUFFICIENT_SAMPLE" and thin["breach"] is False
    nolimit = tools.sla_verdict("Karoo Mutual Bank", "Gauteng", 60, {**base, "calls": 500, "dropped": 20}, None)
    assert nolimit["status"] == "NO_LIMIT_GIVEN" and nolimit["breach"] is None
    none = tools.sla_verdict("Karoo Mutual Bank", "Northern Cape", 60, {"calls": 10, "dropped": 1, "served_towers": 0}, 11.0)
    assert none["status"] == "NO_SERVED_TOWERS_IN_REGION"
    assert "caveat" in tools.sla_verdict("Jacaranda Health Network", "Gauteng", 15, {**base, "calls": 800, "dropped": 80}, 9.0)


def test_freshness_reports_age_and_staleness():
    now = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
    fresh = tools.freshness({"newest_bin_start": now - timedelta(minutes=7)}, now)   # bin ended 2 min ago
    assert fresh["data_age_minutes"] == 2.0 and fresh["stale"] is False
    old = tools.freshness({"newest_bin_start": now - timedelta(hours=14)}, now)
    assert old["stale"] is True and old["data_age_minutes"] > 800
    assert tools.freshness(None, now)["has_data"] is False
