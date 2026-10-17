# Regulatory Quality-of-Service Targets (QOS-REG-001)

> **SYNTHETIC – DEMO DATA.** This document describes a fictional mobile operator, *Imvula Telecom*, for a Microsoft Fabric and Foundry demonstration. The figures are **illustrative, ICASA-style targets written for this demo. They are not official ICASA regulations or figures.** For real obligations, read the current regulations published by the Independent Communications Authority of South Africa (ICASA).

| Field | Value |
|---|---|
| Document ID | QOS-REG-001 |
| Version | 1.0 |
| Effective date | 1 October 2026 |
| Owner | Regulatory Affairs and Compliance |
| Related documents | KPI-DEF-001, RB-NOC-001, MAINT-LOG-001, SLA-ENT-001 |

## 1. Purpose

Imvula Telecom holds an (illustrative) electronic communications network service licence and has to meet minimum quality-of-service (QoS) standards. It also has to report its performance to the regulator every quarter. This document summarises the QoS targets that apply to the mobile voice service, how Imvula measures them, how the synthetic demo network is calibrated against them, and what the NOC must do when an event could affect compliance.

Enterprise SLAs (SLA-ENT-001) are a separate, contractual obligation to individual customers. The regulatory targets apply to the service as a whole, for every subscriber, in each reporting area.

## 2. Reporting areas and periods

- **Reporting area:** each of the nine provinces (Gauteng, Western Cape, KwaZulu-Natal, Eastern Cape, Free State, Limpopo, Mpumalanga, North West, Northern Cape). The `region` field in the CDR data is the reporting area.
- **Measurement period:** calendar month (SAST). Monthly results are submitted together in a **quarterly** report.
- **Busy hour:** for each province and day, the clock hour with the most call attempts. Some targets are measured in the busy hour only, because that's when the network is most stressed.
- **Report deadline:** 30 days after the end of each quarter. The October–December 2026 quarter is due by **30 January 2027**.

## 3. Targets

Each target is shown twice: the **illustrative real-world target** (the type of figure a regulator would set for a real network) and the **demo-calibrated equivalent**. The synthetic network runs at about 7% DCR and 8% CSFR (KPI-DEF-001, section 5), well above a real network. For the demo, compliance is assessed against the **demo-calibrated** column.

| QoS parameter | Definition | Illustrative real-world target | Demo-calibrated target | Measured |
|---|---|---|---|---|
| Dropped-call rate (DCR) | Dropped ÷ all call attempts (KPI-DEF-001, 3.1) | ≤ 2.0% | **≤ 9.5%** | Monthly, per province |
| Busy-hour DCR | DCR in the daily busy hour, averaged over the month by total counts | ≤ 3.0% | **≤ 11.0%** | Monthly, per province |
| Call setup success rate (CSSR) | 100% − CSFR (KPI-DEF-001, 3.2) | ≥ 98.0% | **≥ 90.0%** | Monthly, per province |
| Busy-hour CSSR | CSSR in the daily busy hour | ≥ 97.0% | **≥ 88.0%** | Monthly, per province |
| Network availability | Share of site-minutes where the tower carried traffic or was able to | ≥ 99.5% | ≥ 99.5% | Monthly, per province |
| Major outage notification | Notify the regulator of an outage affecting more than 10% of a province's sites for more than 60 minutes | Within 24 hours | Within 24 hours | Per event |

**Network availability** isn't calibrated, because the demo network's silences are realistic. A tower that is silent for 10 minutes or more (KPI-DEF-001, 3.5) counts as unavailable for that time.

## 4. What counts and what doesn't

- **Planned maintenance** isn't excluded from the regulatory DCR or CSSR. Unlike the enterprise SLAs, the regulatory figures include every call. This is why the Gauteng backhaul migration (MAINT-LOG-001, section 2.1) is designed to limit impact to short bursts on one tower at a time.
- **Load shedding** isn't excluded from network availability. The regulator expects operators to provide backup power. Imvula can attach an explanatory note for months when load shedding was stage 6 or higher, but the figures aren't adjusted.
- **Force majeure** (natural disasters, civil unrest) can be excluded if the regulator is notified within 7 days with supporting evidence.
- **Data source:** the CDR records in `cdr_raw`, aggregated with `mv_drops_5m`. Monthly figures use total counts, never averages of percentages (KPI-DEF-001, section 4).

## 5. Effect of short incidents on compliance

A short, sharp incident rarely threatens a monthly regulatory target on its own. For example, a Gauteng province that carries about 7,200 call attempts per hour at a 7% baseline carries about 5.2 million attempts a month. A 10-minute event at 25% DCR adds about 216 extra dropped calls (2 windows × 600 calls × 18 percentage points). That moves the monthly DCR by about 0.004 percentage points.

What does threaten compliance:

1. **Repeated events on the same days.** The busy-hour DCR is computed per day, so an event that hits the busy hour several days in a month can push the busy-hour figure over its target even when the overall monthly figure is fine.
2. **Long outages that reduce availability.** A tower silent for 3 hours costs 180 site-minutes. Gauteng has 14 towers, so a month has about 625,000 Gauteng site-minutes. The 99.5% target allows about 3,125 unavailable site-minutes in a month, which is about 17 tower-outages of 3 hours each.
3. **A province-wide event.** The core switching fault of 18 August 2026 (MAINT-LOG-001, INC-2026-0818) affected every province at the same time.

## 6. NOC responsibilities

1. **Tag incidents** that affect a province's DCR or availability with the reporting area and the duration. The monthly compliance report is built from these tags and the CDR data.
2. **Major outage.** If more than 10% of a province's towers are silent for more than 60 minutes, tell Regulatory Affairs immediately. They notify the regulator within 24 hours. In Gauteng, two silent towers (14%) for more than an hour meet this condition. In Northern Cape, with only two towers, a single silent tower (50%) for more than an hour meets it.
3. **Busy-hour watch.** In the last week of each month, Regulatory Affairs sends the NOC a list of provinces whose busy-hour DCR is within 1 percentage point of the target. Changes on those provinces' towers during busy hours need extra approval.
4. **Evidence.** For force majeure claims, keep the incident record, the field team report and the weather or authority notice.

## 7. Monthly compliance check (procedure)

1. For each province, compute the monthly DCR, busy-hour DCR, CSSR, busy-hour CSSR and network availability from the CDR data.
2. Compare each figure with the demo-calibrated target in section 3. A figure is **non-compliant** if it is worse than the target (above a DCR target, below a CSSR or availability target).
3. For each non-compliant figure, list the contributing incidents from MAINT-LOG-001 and whether any qualify for force majeure.
4. Regulatory Affairs signs off the figures, which go into the quarterly report.

## 8. Penalties and consequences (illustrative)

The regulator can:
- ask for a written explanation and an improvement plan for a non-compliant month;
- publish the operator's QoS performance;
- issue fines for repeated non-compliance, or for failing to report or notify on time.

Under Imvula's internal policy, any province that is non-compliant on the same parameter in two consecutive months gets a network improvement plan led by the Head of RAN, with monthly progress reports to the executive committee.

## 9. Contacts (synthetic)

- Regulatory Affairs duty manager: +27 10 555 0500, regulatory@imvula.example.com
- Head of RAN: +27 10 555 0510
- NOC duty desk: +27 10 555 0100
