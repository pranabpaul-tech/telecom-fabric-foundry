#!/usr/bin/env python
"""Apply the telecom KQL layer to the Jumpstart's Eventhouse database.

Applies artifacts/kql/[0-9]*.kql in filename order (each statement is fatal on failure), then loads
artifacts/seed/towers.csv into the `towers` table with `.set-or-replace`. Every command is
create-merge / create-or-alter / set-or-replace, so re-running is safe.

Run `--dry-run` to print the statements without connecting.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from telcoops.common.config import StateStore, get_settings  # noqa: E402
from telcoops.common.kusto_client import EventhouseKustoClient  # noqa: E402
from telcoops.common.logging_setup import setup_logging  # noqa: E402

logger = setup_logging(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
KQL_DIR = REPO_ROOT / "artifacts" / "kql"
TOWERS_CSV = REPO_ROOT / "artifacts" / "seed" / "towers.csv"

TOWER_COLUMNS = [
    ("tower_id", "string"), ("site_name", "string"), ("region", "string"), ("city", "string"),
    ("lat", "real"), ("lon", "real"), ("vendor", "string"), ("technology", "string"),
    ("backhaul", "string"), ("backup_power", "string"), ("backup_hours", "int"),
    ("field_team", "string"), ("traffic_weight", "real"), ("enterprise_customers", "string"),
]


def parse_kql_statements(text: str) -> list[str]:
    """Split a .kql file into individual management commands.

    A new statement starts at a line beginning with '.'; every following non-comment, non-blank line
    is appended to it until the next dot-command line. '//' comment lines and blank lines are always
    dropped. This is a deliberately simple heuristic for the hand-authored files in artifacts/kql/:
    a continuation line must never start with '.'.
    """
    statements: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or not stripped:
            continue
        if stripped.startswith("."):
            if current:
                statements.append("\n".join(current).strip())
            current = [line]
        elif current:
            current.append(line)
    if current:
        statements.append("\n".join(current).strip())
    return [s for s in statements if s]


_MV_WITH_BACKFILL = re.compile(
    r"^(\.create-or-alter\s+materialized-view)\s+with\s*\(\s*backfill\s*=\s*true\s*\)\s+(\[?'?[\w-]+'?\]?)", re.I)


def adapt_for_existing_views(statement: str, existing_views: set[str]) -> str:
    """`.create-or-alter materialized-view with (backfill = true) X ...` is valid only while X does not
    exist; on an existing view Eventhouse rejects the option. Drop it for existing views so the file
    stays re-runnable."""
    m = _MV_WITH_BACKFILL.match(statement)
    if not m:
        return statement
    name = m.group(2).strip("[]'")
    if name in existing_views:
        return statement[:m.start()] + f"{m.group(1)} {m.group(2)}" + statement[m.end():]
    return statement


def towers_set_or_replace(csv_path: Path = TOWERS_CSV) -> str:
    """`.set-or-replace towers <| datatable(...)[...]` built from the seed file."""
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    header = ", ".join(f"{n}:{t}" for n, t in TOWER_COLUMNS)
    lines = []
    for r in rows:
        cells = []
        for name, typ in TOWER_COLUMNS:
            v = r[name]
            cells.append(json.dumps(v) if typ == "string" else (v if v != "" else "0"))
        lines.append("    " + ", ".join(cells))
    return f".set-or-replace towers <| datatable({header})\n[\n" + ",\n".join(lines) + "\n]"


def kql_files(directory: Path = KQL_DIR) -> list[Path]:
    return sorted(directory.glob("[0-9]*.kql"), key=lambda p: p.name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the statements, do not connect")
    args = parser.parse_args()

    if args.dry_run:
        for path in kql_files():
            for statement in parse_kql_statements(path.read_text(encoding="utf-8")):
                print(f"-- {path.name}\n{statement}\n")
        print(towers_set_or_replace())
        return

    settings = get_settings()
    state = StateStore()
    eventhouse = state.require("eventhouse", "queryServiceUri", "kqlDatabaseName")
    client = EventhouseKustoClient(eventhouse["queryServiceUri"], eventhouse["kqlDatabaseName"])
    try:
        existing_views = {r[0] for r in client.execute_mgmt(".show materialized-views | project Name").primary_results[0].rows}
        for path in kql_files():
            logger.info("Applying %s", path.name)
            for statement in parse_kql_statements(path.read_text(encoding="utf-8")):
                client.execute_mgmt(adapt_for_existing_views(statement, existing_views))
            if path.name.startswith("020_"):
                logger.info("Loading towers.csv into towers")
                client.execute_mgmt(towers_set_or_replace())
        n = client.query_to_dicts("towers | count")[0]["Count"]
        logger.info("towers holds %s rows", n)
    finally:
        client.close()

    state.merge("kql_schema", {"applied": True, "database": eventhouse["kqlDatabaseName"],
                               "table": settings.raw_table_name})
    logger.info("Schema applied to '%s'.", eventhouse["kqlDatabaseName"])


if __name__ == "__main__":
    main()
