"""Offline tests for the emulator notebook patcher, using a fixture shaped like the Jumpstart notebook."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from telcoops.setup import notebook_patch as np_  # noqa: E402

META = ('# METADATA ********************\n\n# META {\n# META   "language": "python",\n'
        '# META   "language_group": "synapse_pyspark"\n# META }\n\n')


def _fixture() -> str:
    return (
        "# Fabric notebook source\n\n# METADATA ********************\n\n# META {\n# META   \"kernel_info\": {}\n# META }\n\n"
        "# MARKDOWN ********************\n\n# # CDR generator\n\n"
        "# CELL ********************\n\n! pip install azure-eventhub\n\n" + META +
        "# CELL ********************\n\nimport json, time\nproducer_events = object()\n\n" + META +
        "# CELL ********************\n\ndef sendToEventsHub(e, p):\n    pass\n\n" + META +
        "# CELL ********************\n\nSA_LAT_MIN = -35.0\ndef generate_cdr():\n    return {}\n\n" + META +
        "# CELL ********************\n\ndef stream_cdrs_to_eventhub_with_send(records_per_second=1, duration_seconds=None, producer=None):\n    pass\n\n"
        "stream_cdrs_to_eventhub_with_send(records_per_second=5, duration_seconds=1000, producer=producer_events)\n\n" + META
    )


GEN = (ROOT / "artifacts/emulator/cdr_generator.py").read_text(encoding="utf-8")
CSV = ROOT / "artifacts/seed/towers.csv"


def test_patch_replaces_generator_and_stream_cells_and_adds_parameters():
    out = np_.patch_notebook_source(_fixture(), GEN, CSV)
    assert out.count("# PARAMETERS CELL") == 1
    assert "def generate_cdr(rng" in out and "SA_LAT_MIN" not in out
    assert "stream_cdrs_to_eventhub_with_send(records_per_second=5" not in out
    assert "stream_with_spike(producer_events" in out
    assert np_.is_patched(out)


def test_untouched_cells_and_metadata_survive():
    out = np_.patch_notebook_source(_fixture(), GEN, CSV)
    assert "! pip install azure-eventhub" in out and "def sendToEventsHub" in out
    assert out.startswith("# Fabric notebook source")
    # every code cell still has its metadata trailer: 5 original code cells + 1 new parameters cell
    assert out.count("# METADATA ********************") == 1 + 6


def test_every_code_cell_is_valid_python_and_towers_are_inlined():
    out = np_.patch_notebook_source(_fixture(), GEN, CSV)
    _, cells = np_.split_cells(out)
    checked = 0
    for header, body in cells:
        if header.startswith("# MARKDOWN") or "pip install" in body:
            continue
        code, _ = np_._split_code_and_meta(body)
        ast.parse(code)
        checked += 1
    assert checked >= 5
    assert "TOWERS = [" in out and "'GP-001', 'Gauteng'" in out
    assert len(re.findall(r"^    \('[A-Z]+-\d{3}'", out, re.M)) == 40


def test_inlined_generator_runs_without_the_repo_module():
    """Execute the patched generator cell in a clean namespace, as the Fabric notebook would."""
    out = np_.patch_notebook_source(_fixture(), GEN, CSV)
    _, cells = np_.split_cells(out)
    code = next(np_._split_code_and_meta(b)[0] for _, b in cells if np_.MARKER in b)
    ns: dict = {}
    exec(compile(code, "<cell>", "exec"), ns)
    spike = ns["make_spike"]("Gauteng", 0.25, 0, 10)
    rec = ns["generate_cdr"](spike=spike)
    assert rec["tower_id"] and rec["region"] and rec["status"] in ("Completed", "Failed", "Dropped")


def test_refuses_double_patch_and_unexpected_layouts():
    out = np_.patch_notebook_source(_fixture(), GEN, CSV)
    with pytest.raises(ValueError, match="already patched"):
        np_.patch_notebook_source(out, GEN, CSV)
    with pytest.raises(ValueError, match="generate_cdr"):
        np_.patch_notebook_source(_fixture().replace("def generate_cdr", "def other"), GEN, CSV)
    with pytest.raises(ValueError, match="stream starter"):
        np_.patch_notebook_source(_fixture().replace("stream_cdrs_to_eventhub_with_send(", "something_else("), GEN, CSV)
    with pytest.raises(ValueError, match="not a Fabric notebook"):
        np_.patch_notebook_source("print('hi')", GEN, CSV)
