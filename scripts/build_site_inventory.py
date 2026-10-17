"""Render artifacts/kb-docs/site-inventory.md from artifacts/seed/towers.csv. Usage: python scripts/build_site_inventory.py <repo root>"""
import csv
import sys
from collections import OrderedDict
from pathlib import Path

repo = Path(sys.argv[1])
rows = list(csv.DictReader((repo / "artifacts/seed/towers.csv").open(encoding="utf-8")))

HUBS = {
    "GP-003": "GP-001 Johannesburg CBD fibre POP", "GP-007": "GP-002 Sandton fibre POP",
    "GP-008": "GP-002 Sandton fibre POP", "GP-011": "GP-010 Germiston fibre POP",
    "GP-014": "GP-005 Pretoria CBD fibre POP", "WC-004": "WC-002 Bellville fibre POP",
    "WC-005": "George exchange (third-party fibre)", "KZN-003": "KZN-001 Durban Point fibre POP",
    "KZN-006": "Newcastle exchange (third-party fibre)", "EC-003": "Mthatha exchange (third-party fibre)",
    "FS-002": "Welkom exchange (third-party fibre)", "LP-002": "LP-001 Polokwane fibre POP",
    "NW-002": "Mahikeng exchange (third-party fibre)", "NC-002": "NC-001 Kimberley fibre POP (long-haul microwave, 3 hops)",
}

TEAMS = OrderedDict([
    ("GP-North", ("Pretoria depot", "Lead: T. Mokoena", "+27 10 555 0111", "ft.gp-north@imvula.example.com", "Pretoria, Centurion, Midrand, Kempton Park, Soshanguve")),
    ("GP-Central", ("Johannesburg depot (Braamfontein)", "Lead: A. Pillay", "+27 10 555 0112", "ft.gp-central@imvula.example.com", "Johannesburg CBD, Sandton, Randburg, Roodepoort, Soweto")),
    ("GP-East-South", ("Germiston depot", "Lead: R. Venter", "+27 10 555 0113", "ft.gp-east-south@imvula.example.com", "Germiston, Boksburg, Benoni, Vereeniging")),
    ("WC-Field", ("Bellville depot", "Lead: F. Adams", "+27 10 555 0121", "ft.wc@imvula.example.com", "Cape Town metro, Stellenbosch, Paarl, George (George is a 5-hour drive; use the George contractor for first response)")),
    ("KZN-Field", ("Pinetown depot", "Lead: S. Zulu", "+27 10 555 0131", "ft.kzn@imvula.example.com", "Durban, Umhlanga, Pinetown, Pietermaritzburg, Richards Bay, Newcastle")),
    ("EC-Field", ("Gqeberha depot", "Lead: L. Ndlovu", "+27 10 555 0141", "ft.ec@imvula.example.com", "Gqeberha, East London, Mthatha")),
    ("FS-Field", ("Bloemfontein depot", "Lead: J. Steyn", "+27 10 555 0151", "ft.fs@imvula.example.com", "Bloemfontein, Welkom")),
    ("LP-Field", ("Polokwane depot", "Lead: M. Nkuna", "+27 10 555 0161", "ft.lp@imvula.example.com", "Polokwane, Thohoyandou")),
    ("MP-Field", ("eMalahleni depot", "Lead: B. Mahlangu", "+27 10 555 0171", "ft.mp@imvula.example.com", "Mbombela, eMalahleni, Secunda")),
    ("NW-Field", ("Rustenburg depot", "Lead: K. Molefe", "+27 10 555 0181", "ft.nw@imvula.example.com", "Rustenburg, Mahikeng")),
    ("NC-Field", ("Kimberley depot", "Lead: D. Jacobs", "+27 10 555 0191", "ft.nc@imvula.example.com", "Kimberley, Upington (Upington is a 4-hour drive; a spare solar charge controller is kept in Upington)")),
])

REGION_NOTES = {
    "Gauteng": "Gauteng is the busiest province and carries roughly a third of all traffic. Five towers use microwave backhaul (GP-003, GP-007, GP-008, GP-011, GP-014) and are the most exposed to afternoon thunderstorms; GP-003, GP-007 and GP-011 are being moved to fibre under CHG-2026-0412 (MAINT-LOG-001). GP-012 and GP-014 have only 2 hours of battery and go silent first during load shedding; GP-012 is getting a 6-hour battery under CHG-2026-0431.",
    "Western Cape": "Cape Town metro towers are on fibre with good backup. George (WC-005) is remote from the Bellville depot, so first response there is by a local contractor.",
    "KwaZulu-Natal": "Durban Point and Richards Bay serve port operations for Coastal Freight Logistics. KZN-003 Pinetown had a wind-related dish misalignment in August 2026 (INC-2026-0805).",
    "Eastern Cape": "EC-003 Mthatha has only 2 hours of battery and a microwave link to a third-party exchange, which makes it the most fragile site in the province.",
    "Free State": "FS-002 Welkom serves Highveld Mining Group's Goldfields operations over microwave backhaul.",
    "Limpopo": "LP-002 Thohoyandou has 2 hours of battery and a long drive from the Polokwane depot.",
    "Mpumalanga": "MP-002 and MP-003 serve Highveld Mining Group and carry 48-hour generators. MP-003's generator failed to start in September 2026 (INC-2026-0916); the controller was replaced.",
    "North West": "NW-001 on the platinum belt serves Highveld Mining Group with a 48-hour generator.",
    "Northern Cape": "Only two towers serve a very large area. NC-002 Upington runs on battery plus solar and reaches Kimberley over a three-hop microwave link. With two towers, one silent tower is 50% of the province (QOS-REG-001, section 6).",
}


def backup_text(r):
    kind, hours = r["backup_power"], r["backup_hours"]
    return {"battery": f"battery, {hours} h", "generator": f"generator, {hours} h fuel",
            "battery+generator": f"battery and generator, {hours} h", "battery+solar": f"battery and solar, about {hours} h"}[kind]


out = []
w = out.append
w("# Tower and Site Inventory (SITE-INV-001)\n")
w("> **SYNTHETIC – DEMO DATA.** This document describes a fictional mobile operator, *Imvula Telecom*, for a Microsoft Fabric and Foundry demonstration. Sites, people, phone numbers and customers are invented. Coordinates are approximate city locations, not real tower sites.\n")
w("| Field | Value |\n|---|---|")
w("| Document ID | SITE-INV-001 |\n| Version | 1.0 |\n| Effective date | 1 October 2026 |\n| Owner | Network Planning and Field Operations |")
w("| Source | Generated from `artifacts/seed/towers.csv`, the same file that drives the CDR emulator and the KQL `towers` table. Tower IDs in this document always match `tower_id` in the call data. |")
w("| Related documents | RB-NOC-001, MAINT-LOG-001, SLA-ENT-001, KPI-DEF-001 |\n")

w("## 1. Summary\n")
regions = OrderedDict()
for r in rows:
    regions.setdefault(r["region"], []).append(r)
w(f"Imvula Telecom operates **{len(rows)} towers** across the nine South African provinces. Each tower ID starts with a province prefix: GP Gauteng, WC Western Cape, KZN KwaZulu-Natal, EC Eastern Cape, FS Free State, LP Limpopo, MP Mpumalanga, NW North West, NC Northern Cape.\n")
w("| Region | Towers | 5G towers | Microwave backhaul | Towers with 2 h battery | Towers serving enterprise customers |\n|---|---|---|---|---|---|")
for reg, rs in regions.items():
    w(f"| {reg} | {len(rs)} | {sum(r['technology']=='5G' for r in rs)} | {sum(r['backhaul']=='microwave' for r in rs)} | "
      f"{sum(r['backup_hours']=='2' for r in rs)} | {sum(bool(r['enterprise_customers']) for r in rs)} |")
w("")

w("## 2. Field teams\n")
w("| Field team | Depot | Lead | Phone | Email | Coverage |\n|---|---|---|---|---|---|")
for name, (depot, lead, phone, email, cov) in TEAMS.items():
    w(f"| {name} | {depot} | {lead.replace('Lead: ', '')} | {phone} | {email} | {cov} |")
w("\nDispatch through the NOC duty desk (+27 10 555 0100). Outside business hours each team has an on-call engineer, reached on the team phone number.\n")

w("## 3. Enterprise customers by tower\n")
cust = OrderedDict()
for r in rows:
    for c in filter(None, r["enterprise_customers"].split(";")):
        cust.setdefault(c, []).append(r["tower_id"])
w("| Customer | Served towers |\n|---|---|")
for c, ts in cust.items():
    w(f"| {c} | {', '.join(ts)} |")
w("\nFor SLA terms, see SLA-ENT-001. A tower that serves an enterprise customer raises the incident severity by one level (RB-NOC-001, section 2).\n")

w("## 4. Sites by region\n")
for i, (reg, rs) in enumerate(regions.items(), 1):
    w(f"### 4.{i} {reg}\n")
    w(REGION_NOTES[reg] + "\n")
    w("| Tower | Site | City | Lat, Lon | Vendor | Tech | Backhaul | Backup power | Field team | Enterprise customers |\n|---|---|---|---|---|---|---|---|---|---|")
    for r in rs:
        bh = r["backhaul"] if r["backhaul"] == "fibre" else f"microwave to {HUBS.get(r['tower_id'], 'regional POP')}"
        w(f"| {r['tower_id']} | {r['site_name']} | {r['city']} | {r['lat']}, {r['lon']} | {r['vendor']} | {r['technology']} | {bh} | "
          f"{backup_text(r)} | {r['field_team']} | {r['enterprise_customers'].replace(';', ', ') or 'none'} |")
    w("")

w("## 5. Site profiles\n")
w("Each profile gives the facts the NOC needs when a single tower is affected.\n")
for r in rows:
    custs = r["enterprise_customers"].replace(";", " and ") or "no enterprise customers"
    bh = "fibre backhaul" if r["backhaul"] == "fibre" else f"microwave backhaul to {HUBS.get(r['tower_id'], 'a regional POP')}"
    risk = []
    if r["backup_hours"] == "2":
        risk.append("only 2 hours of battery, so it is high-risk during load shedding")
    if r["backhaul"] == "microwave":
        risk.append("exposed to rain-fade and wind on its microwave link")
    if r["tower_id"] in ("GP-003", "GP-007", "GP-011"):
        risk.append("part of the Gauteng fibre migration (CHG-2026-0412, weekdays 09:00-15:00 SAST)")
    if r["tower_id"] == "GP-012":
        risk.append("battery replacement on Saturdays in October 2026 (CHG-2026-0431)")
    risk_txt = ("; ".join(risk)) if risk else "no special risks recorded"
    w(f"- **{r['tower_id']} {r['site_name']}** ({r['city']}, {r['region']}): {r['vendor']} {r['technology']}, {bh}, "
      f"backup {backup_text(r)}. Field team {r['field_team']}. Serves {custs}. Notes: {risk_txt}.")
w("\n## 6. Keeping this inventory current\n")
w("Change `artifacts/seed/towers.csv` first, then regenerate this document, reload the KQL `towers` table and update the emulator. Never edit tower attributes only here, because the call data and the agents would then disagree with this document.")

(repo / "artifacts/kb-docs/site-inventory.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("written")
