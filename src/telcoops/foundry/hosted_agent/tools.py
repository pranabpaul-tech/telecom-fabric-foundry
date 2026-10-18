"""Deterministic logic for the telecom orchestrator's data tools: KQL builders and result shaping.

No Azure imports here, so every number the agent states can be unit-tested offline. main.py wraps these
functions as agent tools and runs the KQL with the agent's own identity (database viewer only).

All windows are anchored to the NEWEST 5-minute bin in mv_drops_5m, not to the wall clock: the emulator
runs only when somebody starts it, and the agent must say how old the data is rather than report an
empty "now".
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

REGIONS = ["Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape", "Free State", "Limpopo",
           "Mpumalanga", "North West", "Northern Cape"]
CUSTOMERS = ["Jacaranda Health Network", "Karoo Mutual Bank", "Highveld Mining Group", "Coastal Freight Logistics"]

# KPI-DEF-001 minimum samples
MIN_CALLS_REGION_5M = 50
MIN_CALLS_TOWER = 10
MIN_CALLS_SLA_HOUR = 100
STALE_AFTER_MINUTES = 15

_SAFE_TEXT = re.compile(r"^[A-Za-z0-9 \-]+$")


def validate_region(region: str) -> str:
    """Exact (case-insensitive) province name, or ValueError. Also keeps quotes out of KQL."""
    for known in REGIONS:
        if region.strip().lower() == known.lower():
            return known
    raise ValueError(f"unknown region '{region}'. Known regions: {', '.join(REGIONS)}")


def validate_customer(customer: str) -> str:
    for known in CUSTOMERS:
        if customer.strip().lower() == known.lower():
            return known
    raise ValueError(f"unknown enterprise customer '{customer}'. Known customers: {', '.join(CUSTOMERS)}")


def validate_window(minutes: int, lo: int = 5, hi: int = 1440) -> int:
    if not isinstance(minutes, int) or not lo <= minutes <= hi:
        raise ValueError(f"window must be a whole number of minutes between {lo} and {hi}")
    return minutes


def pct(numerator: float, denominator: float) -> float | None:
    return round(100.0 * numerator / denominator, 2) if denominator else None


# ----- KQL builders -------------------------------------------------------------------------------------

ANCHOR = "let newest = toscalar(mv_drops_5m | summarize max(bin_start));\nlet end_bin = newest + 5m;\n"


def freshness_kql() -> str:
    return "mv_drops_5m | summarize newest_bin_start = max(bin_start), rows = count()"


def region_rate_kql(region: str, minutes: int) -> str:
    region = validate_region(region)
    minutes = validate_window(minutes)
    return (ANCHOR +
            f"mv_drops_5m | where bin_start >= end_bin - {minutes}m and bin_start < end_bin and region == '{region}'\n"
            "| summarize calls = sum(calls), completed = sum(completed), failed = sum(failed), dropped = sum(dropped),"
            " towers = dcount(tower_id)\n"
            "| extend window_start = end_bin - " + f"{minutes}m" + ", window_end = end_bin")


def affected_towers_kql(region: str, minutes: int, threshold_pct: float, min_calls: int) -> str:
    region = validate_region(region)
    minutes = validate_window(minutes)
    if not 0 < threshold_pct < 100 or min_calls < 1:
        raise ValueError("threshold_pct must be between 0 and 100 and min_calls at least 1")
    return (ANCHOR +
            f"mv_drops_5m | where bin_start >= end_bin - {minutes}m and bin_start < end_bin and region == '{region}'\n"
            "| summarize calls = sum(calls), dropped = sum(dropped) by tower_id\n"
            f"| where calls >= {int(min_calls)}\n"
            "| extend drop_pct = round(100.0 * todouble(dropped) / calls, 2)\n"
            f"| where drop_pct > {float(threshold_pct)}\n"
            "| lookup (towers | project tower_id, site_name, city, vendor, technology, backhaul, backup_power,"
            " backup_hours, field_team, enterprise_customers) on tower_id\n"
            "| order by drop_pct desc")


def customer_rate_kql(customer: str, region: str, minutes: int) -> str:
    """Drop rate over the towers that serve one enterprise customer, inside one region."""
    customer = validate_customer(customer)
    region = validate_region(region)
    minutes = validate_window(minutes)
    return (ANCHOR +
            f"let served = towers | where region == '{region}' and enterprise_customers has '{customer}' | project tower_id;\n"
            f"mv_drops_5m | where bin_start >= end_bin - {minutes}m and bin_start < end_bin\n"
            "| where tower_id in (served)\n"
            "| summarize calls = sum(calls), dropped = sum(dropped), towers = dcount(tower_id)\n"
            f"| extend served_towers = toscalar(served | count), window_start = end_bin - {minutes}m, window_end = end_bin")


# ----- result shaping -----------------------------------------------------------------------------------

def _aware(ts) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def freshness(row: dict | None, now: datetime | None = None) -> dict:
    """How old the data is. The newest 5-minute bin covers [start, start + 5 min)."""
    now = now or datetime.now(timezone.utc)
    start = _aware((row or {}).get("newest_bin_start"))
    if start is None:
        return {"has_data": False, "message": "mv_drops_5m is empty: the emulator has not produced data yet."}
    age_min = round((now - (start + timedelta(minutes=5))).total_seconds() / 60, 1)
    age_min = max(age_min, 0.0)
    return {"has_data": True, "newest_bin_start_utc": start.isoformat(), "data_age_minutes": age_min,
            "stale": age_min > STALE_AFTER_MINUTES, "as_of_utc": now.strftime("%Y-%m-%d %H:%M:%S+00:00")}


def shape_region_rate(region: str, minutes: int, row: dict | None) -> dict:
    calls = int((row or {}).get("calls") or 0)
    dropped = int((row or {}).get("dropped") or 0)
    failed = int((row or {}).get("failed") or 0)
    out = {"region": region, "window_minutes": minutes, "calls": calls, "dropped": dropped, "failed": failed,
           "towers_with_traffic": int((row or {}).get("towers") or 0),
           "window_start_utc": str((row or {}).get("window_start", "")), "window_end_utc": str((row or {}).get("window_end", ""))}
    if calls < MIN_CALLS_REGION_5M:
        out.update(status="INSUFFICIENT_SAMPLE", drop_pct=None, setup_fail_pct=None,
                   note=f"fewer than {MIN_CALLS_REGION_5M} calls in the window; no rate is reported")
    else:
        d = pct(dropped, calls)
        out.update(status="OK", drop_pct=d, setup_fail_pct=pct(failed, calls),
                   above_alert_threshold=bool(d is not None and d > 15.0))
    return out


def shape_affected(region: str, minutes: int, threshold_pct: float, rows: list[dict]) -> dict:
    towers = [{"tower_id": r["tower_id"], "site": r.get("site_name"), "city": r.get("city"),
               "drop_pct": r["drop_pct"], "calls": int(r["calls"]), "vendor": r.get("vendor"),
               "technology": r.get("technology"), "backhaul": r.get("backhaul"),
               "backup": f"{r.get('backup_power')} {r.get('backup_hours')} h", "field_team": r.get("field_team"),
               "enterprise_customers": [c for c in str(r.get("enterprise_customers") or "").split(";") if c]}
              for r in rows]
    return {"region": region, "window_minutes": minutes, "threshold_pct": threshold_pct,
            "affected_tower_count": len(towers), "towers": towers,
            "enterprise_customers_affected": sorted({c for t in towers for c in t["enterprise_customers"]})}


def sla_verdict(customer: str, region: str, minutes: int, row: dict | None, limit_pct: float | None) -> dict:
    """Compare a customer's drop rate on its served towers with an any-hour limit.

    A breach is STRICTLY above the limit (SLA-ENT-001 section 8); an hour with fewer than 100 calls on the
    served towers is not assessed. The limit comes from the knowledge base (the caller passes it in); this
    function only does the arithmetic. Only a 60-minute window is a contractual clock hour measurement.
    """
    calls = int((row or {}).get("calls") or 0)
    dropped = int((row or {}).get("dropped") or 0)
    out = {"customer": customer, "region": region, "window_minutes": minutes, "served_towers_in_region":
           int((row or {}).get("served_towers") or 0), "served_towers_with_traffic": int((row or {}).get("towers") or 0),
           "calls": calls, "dropped": dropped, "limit_pct": limit_pct,
           "window_start_utc": str((row or {}).get("window_start", "")), "window_end_utc": str((row or {}).get("window_end", ""))}
    if not out["served_towers_in_region"]:
        out.update(status="NO_SERVED_TOWERS_IN_REGION", drop_pct=None, breach=False,
                   note=f"{customer} has no served towers in {region}")
        return out
    d = pct(dropped, calls)
    out["drop_pct"] = d
    if calls < MIN_CALLS_SLA_HOUR:
        out.update(status="INSUFFICIENT_SAMPLE", breach=False,
                   note=f"fewer than {MIN_CALLS_SLA_HOUR} calls on the served towers; the hour is not assessed")
    elif limit_pct is None:
        out.update(status="NO_LIMIT_GIVEN", breach=None,
                   note="pass the customer's any-hour limit from SLA-ENT-001 to get a verdict")
    else:
        breach = d > limit_pct
        out.update(status="BREACH" if breach else "WITHIN_LIMIT", breach=breach, margin_pp=round(d - limit_pct, 2))
    if minutes != 60:
        out["caveat"] = "this window is not a clock hour: indicative only. SLA hours are clock hours aligned to the hour (UTC)."
    return out


# ----- read-only guard for free-form KQL --------------------------------------------------------------

_BANNED = ("externaldata", "evaluate ", "http_request", "sql_request", "cosmosdb_request", ".ingest", "database(", "cluster(")


def reject_reason(kql: str) -> str | None:
    stripped = kql.strip()
    if not stripped:
        return "empty query"
    if stripped.startswith("."):
        return "management commands (leading '.') are not allowed; this tool is read-only"
    lowered = stripped.lower()
    for banned in _BANNED:
        if banned in lowered:
            return f"'{banned.strip()}' is not allowed in this tool"
    return None
