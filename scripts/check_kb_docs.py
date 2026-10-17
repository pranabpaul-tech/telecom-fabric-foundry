"""Validate artifacts/kb-docs: word counts, SYNTHETIC banner, tower IDs vs towers.csv, SLA tower lists. Usage: python scripts/check_kb_docs.py <repo root>"""
import csv, re, sys, datetime
from pathlib import Path
R = Path(sys.argv[1]); docs = sorted((R/"artifacts/kb-docs").glob("*.md"))
towers = {r["tower_id"]: r for r in csv.DictReader((R/"artifacts/seed/towers.csv").open(encoding="utf-8"))}
for d in docs:
    t = d.read_text(encoding="utf-8")
    words = len(re.findall(r"[A-Za-z0-9][\w'%.-]*", t))
    ids = set(re.findall(r"\b(?:GP|WC|KZN|EC|FS|LP|MP|NW|NC)-\d{3}\b", t))
    print(f"{d.name:40s} words={words:5d} synthetic={'SYNTHETIC' in t[:300]} unknown_ids={sorted(ids - towers.keys())}")
# SLA served towers vs CSV
sla = (R/"artifacts/kb-docs/enterprise-sla-contracts.md").read_text(encoding="utf-8")
for cust in ["Jacaranda Health Network","Karoo Mutual Bank","Highveld Mining Group","Coastal Freight Logistics"]:
    csv_ids = sorted(k for k,v in towers.items() if cust in v["enterprise_customers"])
    row = next(l for l in sla.splitlines() if l.startswith(f"| {cust} |") and "%" in l)
    doc_ids = sorted(re.findall(r"\b[A-Z]{2,3}-\d{3}\b", row))
    print(cust, "OK" if csv_ids == doc_ids else f"MISMATCH csv={csv_ids} doc={doc_ids}")
for s in ["2026-10-05","2026-10-08","2026-10-09","2026-10-10","2026-10-12","2026-10-14","2026-10-15","2026-10-16","2026-10-17","2026-10-19","2026-10-24","2026-10-31","2027-03-26","2026-09-28"]:
    print(s, datetime.date.fromisoformat(s).strftime("%A"))
