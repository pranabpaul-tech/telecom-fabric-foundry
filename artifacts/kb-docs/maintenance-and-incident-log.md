# Maintenance Schedule and Incident Log (MAINT-LOG-001)

> **SYNTHETIC – DEMO DATA.** This document describes a fictional mobile operator, *Imvula Telecom*, for a Microsoft Fabric and Foundry demonstration. The work, incidents, people and contact details are invented.

| Field | Value |
|---|---|
| Document ID | MAINT-LOG-001 |
| Version | 1.0 (log as at 16 October 2026) |
| Owner | Network Change Management and NOC |
| Related documents | RB-NOC-001, SITE-INV-001, SLA-ENT-001, KPI-DEF-001 |

## 1. How to use this log

Use this log to answer "**is this spike explained by planned work?**" and "**has this happened before?**".

- **Planned work** (section 2) lists every approved programme and change that can affect live traffic: the towers, the recurring windows, the expected impact and who to call.
- **Change freezes** are in section 3.
- **Past incidents** (section 4) give the dates, causes, durations and lessons. Look for repeat patterns on the same towers.

Windows are given in **SAST (UTC+2)** with the **UTC** equivalent, because telemetry is in UTC. An event is explained by planned work only when **the tower matches, the time is inside the window and the impact is within the expected level**. Otherwise treat it as a normal incident or as an overrun (RB-NOC-001, section 5.7).

## 2. Active and upcoming planned work

### 2.1 Gauteng Microwave-to-Fibre Backhaul Migration (CHG-2026-0412)

| Item | Detail |
|---|---|
| Status | **Active** |
| Programme dates | **5 October 2026 to 26 March 2027**, excluding the change freeze (section 3) |
| Towers | **GP-003 Soweto Orlando, GP-007 Randburg Ferndale, GP-011 Benoni Lakes** |
| Recurring window | **Every weekday (Monday–Friday), 09:00–15:00 SAST (07:00–13:00 UTC)** |
| Work | Install new fibre backhaul, then move traffic from the microwave link to fibre, one sector at a time, with a rollback to microwave after each step if tests fail |
| Expected impact | Short bursts of dropped calls on the tower under work while each sector moves. **Tower DCR up to 30%** in individual 5-minute windows inside the window. Neighbouring towers are not expected to be affected. |
| Not expected | DCR above 30% on these towers, any impact on other towers, any impact outside the window, a tower silent for more than 10 minutes |
| Customer notice | Karoo Mutual Bank (served by GP-007) notified on **28 September 2026**, more than 72 hours ahead. GP-003 and GP-011 serve no enterprise customer. |
| Crew lead | Fibre Migration Crew Lead, M. Khumalo (synthetic), +27 10 555 0410 |
| Change owner | Transmission Engineering, Gauteng |

**Interpretation for incident triage:**
- If the affected towers in a weekday 07:00–13:00 UTC window are **only some of GP-003, GP-007 and GP-011**, and their DCR is 30% or less, the event is **explained by the migration**. Log it and don't dispatch.
- If **other Gauteng towers** are affected at the same time, the migration explains only GP-003, GP-007 and GP-011. Investigate the other towers as a separate cause (RB-NOC-001, section 4).
- If GP-003, GP-007 or GP-011 is affected **outside the window**, or above 30%, treat it as an **overrun**. Call the crew lead and ask for a rollback.

**Progress to date:**

| Date | Tower | Result |
|---|---|---|
| 5–9 Oct 2026 | GP-003 | Fibre installed. Sector 1 moved on 8 Oct. Highest 5-minute DCR on GP-003 was 22%. |
| 12–16 Oct 2026 | GP-007 | Fibre installed. Sector 1 move on 14 Oct was rolled back after a fibre splice fault and redone on 15 Oct. Highest 5-minute DCR was 27%. |
| From 19 Oct 2026 | GP-011 | Fibre installation planned. Sector moves continue on all three towers until the programme completes. |

### 2.2 GP-012 Boksburg battery bank replacement (CHG-2026-0431)

| Item | Detail |
|---|---|
| Status | **Active** |
| Dates | Saturdays **10, 17, 24 and 31 October 2026** |
| Window | **06:00–10:00 SAST (04:00–08:00 UTC)** |
| Work | Replace the 2-hour battery bank with a 6-hour lithium bank |
| Expected impact | No impact on traffic while mains power is present. If mains fails during the work, GP-012 will go **silent** until the work is finished, because there is no battery during the swap. |
| Customer notice | Not needed (no enterprise customer on GP-012) |
| Contact | GP-East-South Field Team (SITE-INV-001) |

### 2.3 KwaZulu-Natal radio software upgrade (CHG-2026-0450)

| Item | Detail |
|---|---|
| Status | **Planned** |
| Dates | Nights of **3 and 4 November 2026** |
| Window | **01:00–04:00 SAST (23:00–02:00 UTC, the previous evening)** |
| Towers | KZN-003 and KZN-004 only on 3 November; KZN-001, KZN-002 and KZN-005 on 4 November |
| Expected impact | Each tower restarts once, giving about 5 minutes of silence per tower |
| Customer notice | Coastal Freight Logistics (KZN-001, KZN-005) and Jacaranda Health Network (KZN-002) to be notified by **30 October 2026** |

### 2.4 Western Cape neighbour list tuning (CHG-2026-0455)

| Item | Detail |
|---|---|
| Status | **Planned** |
| Date | **11 November 2026**, 10:00–12:00 SAST (08:00–10:00 UTC) |
| Towers | WC-001, WC-002, WC-003 |
| Work | Update the 5G/4G neighbour lists to reduce handover drops at the WC-001 to WC-002 border |
| Expected impact | None expected. A rise in handover drops means the change should be rolled back (RB-NOC-001, section 5.1). |

## 3. Change freezes

| Freeze | Dates | Scope |
|---|---|---|
| Festive season freeze | 15 December 2026 to 5 January 2027 | National. No planned work except emergency fixes. The Gauteng migration pauses. |
| Year-end financial close | 28–31 March 2027 | Towers serving Karoo Mutual Bank (GP-002, GP-004, GP-007, WC-001) |

## 4. Incident history (July–October 2026)

| Incident | Date (SAST) | Towers | Cause | Duration | Peak DCR | Notes and lessons |
|---|---|---|---|---|---|---|
| INC-2026-0701 | 3 Jul 2026, 18:10 | GP-001, GP-002 | Congestion during a stadium concert near Johannesburg CBD | 55 min | 19% region-tower level | Load-balancing profile was activated late. **Lesson:** turn on the event profile 30 minutes before large events. |
| INC-2026-0714 | 14 Jul 2026, 06:30 | GP-012, GP-014 | Load shedding stage 4. Both 2-hour batteries ran out. | 2 h 40 min (silent) | Towers silent | Battery upgrade for GP-012 approved as CHG-2026-0431. GP-014 is still at 2 hours: **high risk during load shedding.** |
| INC-2026-0729 | 29 Jul 2026, 14:45 | GP-007, GP-008 | Rain-fade on the microwave link to the GP-002 hub during a hailstorm | 35 min | 33% on GP-007 | Cleared without dispatch. One of the reasons for the fibre migration. |
| INC-2026-0805 | 5 Aug 2026, 11:20 | KZN-003 | Microwave dish misaligned by high winds | 4 h 10 min | 41% | Field team realigned the dish. Bracket replaced. |
| INC-2026-0818 | 18 Aug 2026, 09:05 | All regions | Core switching software fault after a vendor patch | 25 min | 31% national | **P1.** Patch rolled back. National change freeze for 48 hours. Post-incident review PIR-2026-08. |
| INC-2026-0902 | 2 Sep 2026, 17:40 | GP-005, GP-006 | Handover failures after a 5G parameter change | 1 h 30 min | 18% | Jacaranda Health Network notified in 12 minutes (deadline 15). Change rolled back. **No SLA breach** because the hourly DCR on Jacaranda's Gauteng towers was 8.7%. |
| INC-2026-0916 | 16 Sep 2026, 19:15 | MP-002, MP-003 | Generator at MP-003 failed to start during a grid failure. MP-002 congested by the traffic moved from MP-003. | 3 h 05 min | MP-003 silent; 21% on MP-002 | Highveld Mining Group notified late (42 minutes, deadline 30). **Missed notification: 3% credit applied.** Generator controller replaced. |
| INC-2026-0927 | 27 Sep 2026, 13:00 | NC-002 | Solar charge controller fault; battery drained overnight | 5 h 20 min (silent) | Tower silent | Remote site, long travel time for the field team. Spare controller now kept in Upington. |
| INC-2026-1008 | 8 Oct 2026, 10:35 | GP-003 | Planned sector move (CHG-2026-0412) | 15 min | 22% | **Explained by planned work.** Within the expected impact. No dispatch. |
| INC-2026-1014 | 14 Oct 2026, 11:50 | GP-007 | Fibre splice fault during a planned sector move (CHG-2026-0412) | 40 min | 27% | Inside the window and within the expected impact, but the move was rolled back. **Excluded for Karoo Mutual Bank** under SLA-ENT-001 section 6 (notified planned work). |

## 5. Repeat patterns to watch

- **Gauteng microwave towers (GP-003, GP-007, GP-008, GP-011, GP-014)** are the most likely to have drops during afternoon thunderstorms (October–March) until the fibre migration is complete. GP-008 and GP-014 aren't part of the current migration.
- **Short battery autonomy (GP-012 until its upgrade, GP-014, EC-003, LP-002)** means these towers go silent first during load shedding. Check the load-shedding stage before blaming another cause.
- **Neighbouring towers inherit traffic.** When a tower goes silent, the next tower often shows congestion (INC-2026-0916). Fix the silent tower first.
- **Parameter changes cause handover drops** (INC-2026-0902). Always check the change calendar for the previous 24 hours.

## 6. Adding to this log

The NOC adds every P1 and P2 incident, and every planned-work window that had an impact, within one working day of closing the incident. Each entry needs the towers, times in SAST, the cause, the duration, the peak DCR and any SLA result. Change Management adds new planned work at least 7 days before it starts, and records the customer notice dates required by SLA-ENT-001.
