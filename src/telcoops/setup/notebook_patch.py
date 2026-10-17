"""Pure text transformation: patch the Jumpstart emulator notebook source (Fabric `notebook-content.py`).

No Azure calls here, so it can be unit-tested against a fixture. The caller (02_patch_emulator.py)
fetches the notebook definition, runs `patch_notebook_source`, and pushes the result back.

The notebook source is a sequence of cells, each introduced by a line such as
`# CELL ********************` (code), `# MARKDOWN ********************` or
`# PARAMETERS CELL ********************`, and each code cell ends with a `# METADATA` block that we
keep untouched. The patch:
  1. adds a PARAMETERS cell (spike_region, spike_drop_rate, ...), overridable from a notebook job
  2. replaces the cell that defines generate_cdr() with the tower-aware generator
     (artifacts/emulator/cdr_generator.py, with towers.csv inlined)
  3. replaces the last cell, which started the 1000-second stream, with a bounded stream loop that
     honours the spike parameters
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

MARKER = "# PATCHED BY telcoops 02_patch_emulator.py"
_HEADER = re.compile(r"^# (CELL|MARKDOWN|PARAMETERS CELL) \*{10,}\s*$", re.M)
_META = "# METADATA ********************"
_TOWERS_LINE = re.compile(r"^TOWERS: list\[.*\] = \[\]\s*$", re.M)
_PYTHON_META = ('# META {\n# META   "language": "python",\n# META   "language_group": "synapse_pyspark"\n# META }\n')

PARAMETERS_CODE = '''# Spike mode and run controls. A notebook job can override any of these.
spike_region = ""            # e.g. "Gauteng"; empty = steady state (85 / 8 / 7)
spike_drop_rate = 0.25       # share of Dropped calls in the spiked region during the spike
spike_start_offset_min = 0   # minutes after the run starts
spike_minutes = 10           # spike length
run_minutes = 60             # the run stops after this long (cost control)
records_per_second = 5       # same default as the original Jumpstart
'''

STREAM_CODE = '''# Bounded stream with optional spike (replaces the original 1000-second loop).
spike = make_spike(spike_region, float(spike_drop_rate), float(spike_start_offset_min), float(spike_minutes))
print("spike:", spike)

def stream_with_spike(producer, per_second, minutes, spike):
    interval = 1.0 / per_second
    started = time.time()
    sent = 0
    while time.time() - started < minutes * 60:
        cdr = generate_cdr(spike=spike)
        sendToEventsHub(cdr, producer)
        sent += 1
        if sent % 100 == 0:
            print(f"[{sent}] {cdr['region']} {cdr['tower_id']} {cdr['status']}")
        time.sleep(interval)
    return sent

total = stream_with_spike(producer_events, records_per_second, run_minutes, spike)
print("records sent:", total)
'''


def towers_literal(csv_path: Path) -> str:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    items = [f'    ({r["tower_id"]!r}, {r["region"]!r}, {float(r["lat"])!r}, {float(r["lon"])!r}, {float(r["traffic_weight"])!r}),'
             for r in rows]
    return "TOWERS = [\n" + "\n".join(items) + "\n]"


def inline_generator(generator_source: str, towers_csv: Path) -> str:
    """The generator module with its empty TOWERS list replaced by the literal from towers.csv."""
    if not _TOWERS_LINE.search(generator_source):
        raise ValueError("cdr_generator.py has no `TOWERS: list[...] = []` line to fill in")
    return _TOWERS_LINE.sub(lambda _m: towers_literal(towers_csv), generator_source, count=1)


def split_cells(source: str) -> tuple[str, list[tuple[str, str]]]:
    """(preamble, [(header_line, body), ...]); body keeps its METADATA trailer."""
    matches = list(_HEADER.finditer(source))
    if not matches:
        raise ValueError("no cell markers found: not a Fabric notebook-content.py")
    preamble = source[:matches[0].start()]
    cells = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        cells.append((m.group(0), source[m.end():end]))
    return preamble, cells


def join_cells(preamble: str, cells: list[tuple[str, str]]) -> str:
    return preamble + "".join(header + body for header, body in cells)


def _split_code_and_meta(body: str) -> tuple[str, str]:
    code, sep, meta = body.partition(_META)
    return code, (sep + meta) if sep else ""


def _cell(header: str, code: str, meta: str = "") -> tuple[str, str]:
    return header, "\n\n" + code.rstrip("\n") + "\n\n" + (meta or (_META + "\n\n" + _PYTHON_META + "\n"))


def is_patched(source: str) -> bool:
    return MARKER in source


def patch_notebook_source(source: str, generator_source: str, towers_csv: Path) -> str:
    """Return the patched notebook source. Raises if the expected cells are not where we expect them
    (a different Jumpstart version): better to stop than to push a half-patched notebook."""
    if is_patched(source):
        raise ValueError("notebook is already patched; restore the original first (02_patch_emulator.py --restore)")
    preamble, cells = split_cells(source)

    gen_idx = [i for i, (_, b) in enumerate(cells) if "def generate_cdr(" in _split_code_and_meta(b)[0]]
    if len(gen_idx) != 1:
        raise ValueError(f"expected exactly one cell defining generate_cdr(), found {len(gen_idx)}")
    last_idx = len(cells) - 1
    if "stream_cdrs_to_eventhub_with_send(" not in _split_code_and_meta(cells[last_idx][1])[0]:
        raise ValueError("the last cell is not the stream starter; Jumpstart version mismatch")
    if last_idx == gen_idx[0]:
        raise ValueError("generate_cdr() and the stream starter are in the same cell")

    generator = f"{MARKER}\n" + inline_generator(generator_source, towers_csv)

    new_cells: list[tuple[str, str]] = []
    for i, (header, body) in enumerate(cells):
        if i == gen_idx[0]:
            new_cells.append(_cell("# PARAMETERS CELL ********************", PARAMETERS_CODE))
            _, meta = _split_code_and_meta(body)
            new_cells.append(_cell(header, generator, meta))
        elif i == last_idx:
            _, meta = _split_code_and_meta(body)
            new_cells.append(_cell(header, STREAM_CODE, meta))
        else:
            new_cells.append((header, body))
    return join_cells(preamble, new_cells)
