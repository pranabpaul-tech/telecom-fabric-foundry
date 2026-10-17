# NOC Runbook: Dropped-Call Spikes (RB-NOC-001)

> **SYNTHETIC – DEMO DATA.** This document describes a fictional mobile operator, *Imvula Telecom*, for a Microsoft Fabric and Foundry demonstration. Sites, people, phone numbers, customers and procedures are invented. Do not use it for real network operations.

| Field | Value |
|---|---|
| Document ID | RB-NOC-001 |
| Version | 1.0 |
| Effective date | 1 October 2026 |
| Owner | Network Operations Centre (NOC), Johannesburg |
| Applies to | All Imvula Telecom radio sites (tower IDs GP-, WC-, KZN-, EC-, FS-, LP-, MP-, NW-, NC-) |
| Related documents | KPI-DEF-001 (KPI definitions), SITE-INV-001 (site inventory), MAINT-LOG-001 (maintenance and incident log), SLA-ENT-001 (enterprise SLAs), QOS-REG-001 (regulatory QoS targets) |

## 1. Purpose and scope

This runbook tells NOC engineers and regional field teams what to do when the dropped-call rate (DCR) rises above normal for a region or for individual towers. It covers how to confirm the alert, how to classify the likely cause, what to check, what to fix, who to tell, and when to close the incident. It applies to alerts raised by the Fabric Operations Agent *Telco Drop Monitor*, to issues spotted on the real-time dashboard, and to customer complaints that point to dropped calls.

All telemetry timestamps are in **UTC**. Field teams work in **South African Standard Time (SAST = UTC+2)**. Always state both when you write to a field team or a customer, for example "14:05–14:10 UTC (16:05–16:10 SAST)".

## 2. Thresholds that start this runbook

The demo network has a normal DCR of about **7%** and a normal call setup failure rate of about **8%**. These are deliberately higher than a real network, so the thresholds below are calibrated to the demo baseline (see KPI-DEF-001, section 5).

| Trigger | Condition | Default severity |
|---|---|---|
| Regional critical event | Region DCR **> 15%** in a 5-minute window **with at least 50 calls** | P2 |
| Regional major event | Region DCR **> 25%** in a 5-minute window, or **five or more towers** affected in the same region and window | P1 |
| Affected tower | Tower DCR **> 15%** in a 5-minute window with at least 10 calls | Used for counting; P3 on its own |
| Enterprise-impacting | Any affected tower that serves an enterprise customer listed in SLA-ENT-001 | Raise severity one level (P3 → P2, P2 → P1) |
| Silent tower | A tower that normally carries traffic has **zero calls for 10 minutes** or more | P2 (often power or backhaul) |

A tower counts as *affected* only when it has enough calls to be meaningful. Do not escalate a tower with fewer than 10 calls in the window; mark it "insufficient sample" and look at the next window.

## 3. First 10 minutes: confirm and frame

1. **Acknowledge the alert** in the NOC queue, or approve the Operations Agent action in the Fabric Operations Agent Teams app. Write down the alert window (start and end, UTC) and the region.
2. **Confirm with data.** Ask the NOC Copilot, or query directly: region DCR for the last 15 minutes in 5-minute bins, call counts, and the list of affected towers. One bad window followed by normal windows usually means a short transient; keep watching but don't dispatch yet.
3. **Check planned maintenance.** Look in MAINT-LOG-001 for planned work on the affected towers that overlaps the alert window. If the affected towers match an active planned window, this is a **maintenance-related event** (section 5.7). It still has to be logged, but enterprise SLA exclusions may apply (SLA-ENT-001, section 6).
4. **Check scope.** Count affected towers and see whether other regions are affected too. Several regions at the same moment usually means a core-network problem (section 5.6), not a radio problem.
5. **Check enterprise exposure.** Look up the affected towers in SITE-INV-001 to see which enterprise customers they serve, then read SLA-ENT-001 for each customer's notification deadline. The Jacaranda Health Network deadline is the shortest at **15 minutes**.
6. **Open an incident** with the severity from section 2, the region, the affected tower IDs, the window, and your initial view of the cause.

## 4. Diagnostic signatures

Use the pattern in the data to choose the most likely cause before you dispatch anyone. More than one cause can apply.

| Pattern in the data | Most likely cause | Section |
|---|---|---|
| DCR rises on **microwave-backhauled** towers that share a hub; fibre towers nearby are normal | Backhaul degradation | 5.3 |
| Towers go **silent** (zero calls) after a short rise in drops; often during load-shedding hours | Power outage, battery exhausted | 5.4 |
| **Failed** calls rise more than dropped calls, in the busy hour (07:00–09:00 or 16:00–19:00 SAST), at high-traffic towers | Congestion | 5.2 |
| Drops concentrate on **5G** towers and mobile calls, at the edge between two towers; failed rate is normal | Handover failure | 5.1 |
| One tower, steady rise over hours, call quality worsening, neighbours normal | RF interference or hardware fault | 5.5 |
| **Several regions at once**, sudden start, all technologies | Core network / switching problem | 5.6 |
| Affected towers match an **active planned window** in MAINT-LOG-001 | Planned maintenance (expected, or overrunning) | 5.7 |

## 5. Procedures by cause

### 5.1 Handover failure

**Signature:** higher drops on mobile calls, mostly at 5G sites next to 4G-only neighbours, with a normal setup failure rate. Call quality often drops just before the call ends.

**Checks:**
- Compare drops on 5G and 4G towers in the same region for the alert window.
- Check whether a neighbour list or parameter change was deployed in the last 24 hours (change calendar, MAINT-LOG-001 section 3).
- Check whether the affected towers share a vendor. Mixed-vendor borders (for example Ericsson 5G next to Huawei 4G) are the most common trouble spot.

**Actions:**
- If a parameter change went in during the last 24 hours, ask the radio optimisation team to **roll it back**. This is the fastest fix.
- If not, raise a ticket with the radio optimisation team with the tower pair and the window. No field dispatch is needed unless hardware alarms are present.

**Escalation:** P2 to radio optimisation within 30 minutes. P1 also notifies the Head of RAN.

**Typical time to restore:** 30–90 minutes after rollback.

### 5.2 Congestion

**Signature:** the call setup failure rate rises first and the DCR rises after it. It happens in the busy hour, at high-traffic urban towers (Johannesburg CBD, Sandton, Durban Point, Cape Town Foreshore), or during events such as stadium matches or public holidays.

**Checks:**
- Compare call volume with the same hour last week.
- Check the event calendar for the area.
- Check whether a neighbouring tower is silent. Its traffic moves onto this tower and congests it.

**Actions:**
- Turn on the load-balancing profile for the affected cell cluster (a NOC action that needs no dispatch).
- If a neighbour is silent, fix that neighbour first. The congestion is a symptom.
- For planned events, ask for a temporary capacity uplift 48 hours in advance.

**Escalation:** P3/P2 handled by the NOC. P1 also notifies capacity planning.

**Typical time to restore:** 15–60 minutes, or until the busy hour ends.

### 5.3 Backhaul degradation or failure

**Signature:** microwave-backhauled towers that share a hub show drops at the same time. Fibre towers in the same city are normal. If the link fails completely, the towers go silent.

The Gauteng microwave towers are **GP-003 (Soweto Orlando), GP-007 (Randburg Ferndale), GP-008 (Roodepoort Florida), GP-011 (Benoni Lakes) and GP-014 (Soshanguve Block L)**. SITE-INV-001 lists which hub each one depends on.

**Checks:**
- Group the affected towers by backhaul hub (SITE-INV-001). If all the affected towers share one hub, suspect that hub's link.
- Check for rain-fade weather warnings (severe Highveld thunderstorms are common October to March in the afternoon).
- Check MAINT-LOG-001 for **backhaul migration work**. The Gauteng microwave-to-fibre programme is active from 5 October 2026 to 26 March 2027.

**Actions:**
- If planned migration work is running on these towers, contact the migration crew lead (MAINT-LOG-001, section 2) and confirm whether the cutover is overrunning. Ask for a rollback if the window has ended.
- If it's weather, monitor. Rain fade usually clears within 30 minutes. Dispatch only if the link stays down after the storm.
- If the link is down without weather or planned work, dispatch the regional field team to the hub site with spare microwave radio units.

**Escalation:** P2 to transmission operations within 15 minutes. P1 also notifies the regional field team lead.

**Typical time to restore:** 20–40 minutes for rain fade; 2–4 hours for a hardware swap.

### 5.4 Power outage (load shedding or grid failure)

**Signature:** a short rise in drops, then the tower goes **silent**. It often happens at the start of a scheduled load-shedding block or two to four hours later, when batteries run out.

Towers with short battery autonomy are at the highest risk: **GP-012 Boksburg (2 h), GP-014 Soshanguve (2 h), EC-003 Mthatha (2 h), LP-002 Thohoyandou (2 h)**, and every tower with four hours of battery.

**Checks:**
- Look up the backup type and autonomy in SITE-INV-001.
- Check the current load-shedding stage and the block schedule for the area.
- Check the site power alarms (mains fail, battery low, generator start failure).

**Actions:**
- Battery-only sites that are expected to run out within one hour: dispatch the field team with a **mobile generator**. Priority order: enterprise-serving sites first, then the sites with the most traffic.
- Generator sites: confirm the generator started. If it didn't, dispatch for a manual start and a fuel check.
- Record the outage start, the backup exhaustion time and the time restored. The SLA exclusion rules in SLA-ENT-001 section 6 depend on these times.

**Escalation:** P2 to the regional field team immediately. P1, or any enterprise-serving site, also notifies the Regional Manager.

**Typical time to restore:** 60–120 minutes for a mobile-generator deployment in metro areas, and up to 4 hours in rural areas (Northern Cape, Limpopo).

### 5.5 RF interference or hardware fault

**Signature:** a single tower degrades steadily over hours with worsening call quality while its neighbours are normal. There may be VSWR or radio-unit alarms.

**Checks:**
- Check hardware alarms and the uplink interference trend.
- Check whether new equipment was installed nearby recently.

**Actions:**
- Reset the affected radio unit remotely (allowed outside the busy hour only).
- If that doesn't clear it, dispatch the field team with a spectrum analyser and a spare radio unit.

**Escalation:** P3 handled by the NOC. P2 if an enterprise customer is affected.

**Typical time to restore:** 1–6 hours.

### 5.6 Core network or switching problem

**Signature:** a sudden rise in drops across **several regions at once**, on all technologies and vendors.

**Actions:**
- Call the core network on-call engineer **immediately** and declare P1.
- Do not dispatch field teams; the problem isn't at the sites.
- Freeze all planned work nationally until the cause is found.

**Escalation:** P1 to the Head of Core Network and to the duty executive within 15 minutes.

### 5.7 Planned maintenance (expected or overrunning)

**Signature:** the affected towers match an active window in MAINT-LOG-001.

**Actions:**
- **Inside the window, with impact within the expected level** (MAINT-LOG-001 lists the expected DCR during cutovers): log the event as maintenance-related, don't dispatch, and confirm with the work crew.
- **Outside the window, or above the expected impact:** treat it as an overrun. Ask the crew to stop and roll back, and handle it as a backhaul incident under section 5.3.
- In both cases, check SLA-ENT-001 section 6. Planned work is excluded from SLA measurement **only if** the customer was notified at least 72 hours in advance.

## 6. Communication

| Audience | When | How | Content |
|---|---|---|---|
| Regional field team | When dispatching | Phone call plus the incident ticket | Tower IDs, site names, the window in UTC and SAST, suspected cause, spares to bring |
| Regional Manager | Any P1; P2 affecting enterprise sites | Email and phone | Region, drop %, number of affected towers, enterprise customers affected, ETA |
| Enterprise customers | Within the SLA notification deadline (SLA-ENT-001) | Account manager email | Affected service area, start time, actions taken, next update time |
| Regulatory compliance team | When an event may affect a QoS reporting period (QOS-REG-001) | Email | Region, duration, measured DCR, cause |

**Customer update template:**
"Imvula Telecom is investigating higher dropped-call rates affecting [area] since [time SAST]. Field teams are [action]. We will update you by [time SAST]."

## 7. Closing the incident

Close the incident only when:
- the region DCR has been **below 10% for three consecutive 5-minute windows**;
- no affected towers remain;
- every silent tower is carrying traffic again;
- enterprise customers have received a final update.

Record the root cause, the time restored and whether any SLA breach or exclusion applies. P1 incidents need a post-incident review within five working days, and the result goes into MAINT-LOG-001 section 4.

## 8. Contacts

Regional field team leads are listed in SITE-INV-001, section 2. The NOC duty desk is +27 10 555 0100 (synthetic) and noc.duty@imvula.example.com (synthetic).
