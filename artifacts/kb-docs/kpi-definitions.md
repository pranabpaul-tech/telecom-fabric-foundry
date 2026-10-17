# KPI Definitions for Call Data Records (KPI-DEF-001)

> **SYNTHETIC – DEMO DATA.** This document describes a fictional mobile operator, *Imvula Telecom*, for a Microsoft Fabric and Foundry demonstration. All thresholds are calibrated to a synthetic data generator, not to a real network.

| Field | Value |
|---|---|
| Document ID | KPI-DEF-001 |
| Version | 1.0 |
| Effective date | 1 October 2026 |
| Owner | Network Performance Engineering |
| Related documents | RB-NOC-001, SITE-INV-001, SLA-ENT-001, QOS-REG-001 |

## 1. Purpose

This document defines how Imvula Telecom measures call performance from call data records (CDRs). The NOC, the enterprise account teams, the regulatory compliance team and the analytics agents all use these definitions, so that when one of them says "the drop rate in Gauteng was 18%", the others know what was counted, over which window and with what sample size. Where a contract or a regulation uses a different definition, that document says so, and its own definition applies for that purpose only.

## 2. The call data record

Every call attempt produces one record in the `cdr_raw` table of the Eventhouse KQL database `TelecomCallDataRecords`. These fields are used for KPIs:

| Field | Meaning |
|---|---|
| Timestamp fields | When the call started and ended, in **UTC**. KPIs are assigned to a window by the call **start** time. |
| `status` | `Completed` (the call ended normally), `Failed` (the call never connected), or `Dropped` (the call connected and then ended abnormally) |
| `call_type` | The type of call, for example voice or video, or mobile-originated versus mobile-terminated, as the data generator records it |
| `call_quality` | The quality indicator the generator records for the call |
| `tower_id` | The serving tower, for example `GP-005`. It links to SITE-INV-001. |
| `region` | The South African province of the serving tower, for example `Gauteng` |
| Tower latitude and longitude | The serving tower's position, with small jitter |

The `towers` reference table, and the site inventory SITE-INV-001, hold the static attributes of each tower: vendor, technology, backhaul, backup power, field team and the enterprise customers it serves.

## 3. Core KPIs

### 3.1 Dropped-call rate (DCR)

**Definition:** DCR = number of `Dropped` calls ÷ number of **all call attempts** (Completed + Failed + Dropped) in the window, expressed as a percentage.

Industry practice often divides by *established* calls only (Completed + Dropped). Imvula's operational DCR uses all attempts so that it matches the real-time dashboard and the KQL functions exactly. When you compare against an external figure, convert it first: established-call DCR = Dropped ÷ (Completed + Dropped). At the demo baseline (85% Completed, 8% Failed, 7% Dropped) the operational DCR is 7.0% and the established-call DCR is about 7.6%.

### 3.2 Call setup failure rate (CSFR)

**Definition:** CSFR = `Failed` calls ÷ all call attempts. The call setup success rate (CSSR) is 100% − CSFR. A CSFR that rises before the DCR does usually means congestion (RB-NOC-001, section 5.2).

### 3.3 Call completion rate (CCR)

**Definition:** CCR = `Completed` calls ÷ all call attempts. CCR + CSFR + DCR = 100%.

### 3.4 Poor-quality share

**Definition:** the share of calls whose `call_quality` is in the lowest quality band the generator produces. If `call_quality` is numeric, the lowest band is the bottom quartile of the previous seven days. Poor-quality share is an early warning sign: it often rises 5–15 minutes before the DCR during interference or backhaul degradation.

### 3.5 Silent tower

**Definition:** a tower that carried at least 20 calls in the same hour of the previous day, and carries **zero calls for 10 consecutive minutes** now. A silent tower doesn't count in DCR (it has no calls), so always check for silent towers next to DCR. Otherwise a power outage can make a region look *healthier* because its worst tower has dropped out of the calculation.

## 4. Windows, aggregation and minimum samples

| Window | Used for | Minimum calls for a valid value |
|---|---|---|
| 5 minutes, aligned to the clock (00, 05, 10 ... minutes past the hour, UTC) | Real-time alerting, the Operations Agent, incident triage | Region: **50 calls**. Tower: **10 calls**. |
| 1 hour, aligned to the clock | Enterprise SLA "any-hour" limits (SLA-ENT-001) | Region: 300 calls |
| Calendar day (SAST) | Daily operations report | Region: 2,000 calls |
| Calendar month (SAST) | Enterprise SLA monthly targets, regulatory reporting (QOS-REG-001) | Not applicable |

**Aggregation rule:** always compute a rate as the sum of the numerators divided by the sum of the denominators over the period. **Never average percentages across windows or towers**, because a small tower with few calls would then count as much as a large one. For example, the regional 1-hour DCR is the total dropped calls in the region over the hour divided by the total call attempts in the region over the hour.

**Insufficient sample:** a window below its minimum call count is reported as "insufficient sample", not as 0% or 100%. It's never used to raise an alert.

## 5. Demo calibration

The synthetic network deliberately produces a **baseline DCR of about 7%** and a **CSFR of about 8%**, so that changes are easy to see in a demo. A real network typically runs at 0.5–2% DCR. Every threshold in Imvula documents is therefore set relative to the synthetic baseline:

| Level | Region DCR, 5-minute window | Meaning |
|---|---|---|
| Normal | ≤ 10% | Normal variation around the 7% baseline |
| Elevated | > 10% and ≤ 15% | Watch; no alert |
| Critical event | **> 15%** with at least 50 calls | Operations Agent action; NOC incident P2 |
| Major event | **> 25%**, or five or more affected towers | NOC incident P1 |

**Affected tower:** a tower whose DCR is **above 15%** in a 5-minute window with at least 10 calls.

**Closing an incident:** region DCR below 10% for three consecutive 5-minute windows (RB-NOC-001, section 7).

## 6. Worked example

On a weekday afternoon the Gauteng region carries about 600 call attempts per 5-minute window. Normally about 42 are dropped (7%).

1. During a 10-minute disturbance, the drop probability for Gauteng calls rises to 25%. In each of the two affected windows about 150 of 600 calls are dropped. The region DCR is **25%**, above the 15% critical threshold, with far more than 50 calls. The Operations Agent raises an action for each window. 25% is not *above* 25%, so on the DCR alone this is a P2. It becomes a P1 if five or more towers are affected.
2. Gauteng has 14 towers carrying about the same traffic, so each tower has about 43 calls per window. With a 25% drop probability, nearly every Gauteng tower will cross 15%, so the count of affected towers is likely to be 10 or more. That makes it a **major event (P1)**.
3. Over the full clock hour that contains the disturbance, there are 12 windows. Ten windows at 7% and two at 25% give (10 × 42 + 2 × 150) ÷ (12 × 600) = 720 ÷ 7,200 = **10.0%** hourly DCR for the region. Enterprise SLA "any-hour" limits are compared with this hourly figure, not with the 5-minute peak (SLA-ENT-001, section 4).
4. If the same disturbance happens once in a month, the monthly DCR rises by only about 0.04 percentage points, so it has almost no effect on monthly targets.

This example is why the same event can be a P1 incident operationally, breach one customer's hourly SLA, and still leave every monthly target untouched.

## 7. Query guidance for analysts and agents

- Use the materialized view `mv_drops_5m` for rates. It has calls, completed, failed and dropped per 5-minute bin, region and tower. Recompute region totals by summing tower rows, then divide.
- Use `cdr_raw` only when you need individual calls (call type mix, quality distribution).
- Always state the time window in UTC and the call count alongside any rate.
- Join `towers` on `tower_id` to break results down by vendor, technology or backhaul.
- Before you call a tower "healthy", check that it isn't silent (section 3.5).
- Use the functions `drop_rate_by_region(window)`, `worst_towers(region, window, n)` and `region_alert_candidates(window, min_calls, threshold)`. They implement the definitions in this document; `region_alert_candidates` is exactly the Operations Agent rule.

## 8. Change control

Any change to a definition, window or threshold in this document must also be made in the KQL functions and in the Operations Agent instructions in the same change, and announced to the NOC and the account teams. The version number goes up with each change. Version 1.0 is the first issue.
