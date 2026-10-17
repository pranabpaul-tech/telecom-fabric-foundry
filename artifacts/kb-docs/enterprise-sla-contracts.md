# Enterprise Mobile Service Level Agreements (SLA-ENT-001)

> **SYNTHETIC – DEMO DATA.** This document describes a fictional mobile operator, *Imvula Telecom*, and fictional enterprise customers, for a Microsoft Fabric and Foundry demonstration. It isn't a real contract. Thresholds are calibrated to a synthetic network with a baseline dropped-call rate of about 7% (KPI-DEF-001, section 5).

| Field | Value |
|---|---|
| Document ID | SLA-ENT-001 |
| Version | 1.0 |
| Effective date | 1 October 2026 |
| Owner | Enterprise Business Unit, Service Assurance |
| Related documents | KPI-DEF-001, SITE-INV-001, MAINT-LOG-001, RB-NOC-001 |

## 1. Purpose

This document summarises the service level terms that Imvula Telecom has agreed with its four enterprise mobile customers. It's the reference the NOC and the account managers use during an incident to answer three questions: **which customers are affected**, **does the event breach their SLA**, and **what must we tell them, and by when**. The signed contracts take precedence. This summary reproduces their service level schedules.

## 2. Customers at a glance

| Customer | Tier | Served towers (SITE-INV-001) | Monthly DCR target | Any-hour DCR limit | Notification deadline |
|---|---|---|---|---|---|
| Jacaranda Health Network | Platinum (critical services) | GP-001, GP-002, GP-005, GP-006, WC-002, KZN-002 | ≤ 8.5% | **≤ 9.0%** | **15 minutes** |
| Karoo Mutual Bank | Gold | GP-002, GP-004, GP-007, WC-001 | ≤ 9.0% | ≤ 11.0% | 30 minutes |
| Highveld Mining Group | Gold Industrial | GP-013, FS-002, MP-002, MP-003, NW-001, NC-001 | ≤ 9.0% | ≤ 12.0% | 30 minutes |
| Coastal Freight Logistics | Silver | GP-009, WC-001, KZN-001, KZN-005, EC-001 | ≤ 9.5% | ≤ 12.0% | 60 minutes |

All DCR figures use the operational definition in KPI-DEF-001, section 3.1: dropped calls divided by all call attempts.

## 3. Measurement scope

- **Served towers.** Each customer's SLA is measured only on the towers listed for that customer in section 2 and in SITE-INV-001. A disturbance on other towers in the same region does not count toward that customer's SLA, even when the regional figure is high.
- **The SLA region.** For the any-hour limit, the measurement is the DCR **across that customer's served towers within one region** over a clock hour (UTC). Jacaranda Health Network, for example, has a Gauteng measurement (GP-001, GP-002, GP-005, GP-006), a Western Cape measurement (WC-002) and a KwaZulu-Natal measurement (KZN-002).
- **Monthly target.** The DCR across all the customer's served towers over a calendar month (SAST).
- **Minimum sample.** An hour with fewer than 100 call attempts on the customer's served towers in a region isn't assessed (no breach, no compliance), and is reported as "insufficient sample".
- **Data source.** The operator's CDR records in the Eventhouse (`cdr_raw` and `mv_drops_5m`). The customer can ask for the hourly figures for any reported breach.

## 4. Service levels

### 4.1 Any-hour DCR limit

If the DCR on a customer's served towers in one region, over any clock hour, is **above** the customer's any-hour limit, that hour is a **breached hour**.

### 4.2 Monthly DCR target

If the monthly DCR on a customer's served towers is above the monthly target, the month is a **breached month**.

### 4.3 Critical-event notification

A **critical event** is any 5-minute window in which a tower serving the customer has a DCR above 15% with at least 10 calls, or a served tower is silent for 10 minutes or more (KPI-DEF-001, sections 3.5 and 5). For each critical event, Imvula must notify the customer's nominated contact **within the notification deadline in section 2**, counted from the end of the first window in which the event was detected. Imvula must then send updates at least every 60 minutes until the event is resolved, and a final report within five working days for any event that lasted longer than one hour.

A missed notification deadline is a breach in its own right, even when no DCR level was breached.

## 5. Service credits

| Customer | Credit per breached hour | Credit per breached month | Credit per missed notification | Monthly cap |
|---|---|---|---|---|
| Jacaranda Health Network | 10% of the monthly fee | 15% | 5% | 30% |
| Karoo Mutual Bank | 5% | 10% | 3% | 20% |
| Highveld Mining Group | 5% | 10% | 3% | 25% |
| Coastal Freight Logistics | 3% | 5% | 2% | 15% |

Credits are applied to the next invoice. A single hour that breaches the any-hour limit in two regions counts as two breached hours. Credits for one month never exceed the monthly cap.

### 5.1 Additional obligations by customer

- **Jacaranda Health Network:** the served towers carry clinical communication for hospitals and ambulance dispatch. Every critical event on a Jacaranda tower is handled at least as **P1** (RB-NOC-001, section 2), and the Regional Manager phones the Jacaranda duty officer in addition to the email notification. Jacaranda towers have the first claim on mobile generators during power outages.
- **Karoo Mutual Bank:** branch and ATM backup connectivity depends on the served towers. During business hours (08:00–17:00 SAST, weekdays), any silent served tower must have a field team assigned within 30 minutes.
- **Highveld Mining Group:** the served towers support mine-site safety communication. Imvula must keep generator backup at GP-013, MP-002, MP-003 and NW-001 with at least 48 hours of fuel, and report generator test results monthly.
- **Coastal Freight Logistics:** the served towers cover ports and the airport corridor. Notifications go to the logistics control room, which runs 24 hours a day.

## 6. Exclusions

The following are excluded from SLA measurement (breached hours and months), but **not** from the notification duty in section 4.3, unless stated otherwise:

1. **Notified planned maintenance.** Work recorded in MAINT-LOG-001, for which the customer was notified **at least 72 hours before** the window started, is excluded **for the served towers named in the notice and only inside the notified window**. If the work overruns the window, the overrun time is not excluded. If the customer was notified with less than 72 hours' warning, nothing is excluded. Notified planned work doesn't require a critical-event notification, but an overrun does.
2. **Force majeure.** Events outside Imvula's reasonable control, such as natural disasters, civil unrest or acts of government. Grid power failure is force majeure **only after** the site's contracted backup autonomy (SITE-INV-001) has run out **and** the national load-shedding stage is 6 or higher. Below stage 6, power outages are not excluded.
3. **Customer-caused events,** such as faulty customer equipment or the customer's own misconfiguration.

Excluded hours still appear in the monthly report, marked with the reason.

## 7. Status of planned-work notices in October 2026

The **Gauteng Microwave-to-Fibre Backhaul Migration** (MAINT-LOG-001, section 2.1) affects GP-003, GP-007 and GP-011. Karoo Mutual Bank, which is served by GP-007, was notified on 28 September 2026, more than 72 hours before the programme began on 5 October 2026. Notified windows on GP-007 are therefore excluded for Karoo Mutual Bank. GP-003 and GP-011 serve no enterprise customer.

The **GP-012 battery replacement** (MAINT-LOG-001, section 2.2) affects no enterprise customer.

No other notified planned work affects enterprise towers in October 2026.

## 8. How to assess an incident

1. List the affected towers in the incident window (RB-NOC-001, section 3).
2. For each customer in section 2, take the intersection of the affected towers with the customer's served towers. If it's empty, the customer isn't affected; stop for that customer.
3. Check the notification duty (section 4.3). Note the deadline and who must be called.
4. Remove excluded towers and times (section 6). For notified planned maintenance, check the window and the notice date in MAINT-LOG-001.
5. Compute the clock-hour DCR on the customer's remaining served towers in that region, as total dropped divided by total attempts (KPI-DEF-001, section 4). Compare it with the any-hour limit. A breach is **strictly above** the limit.
6. Record breached hours and work out the credits (section 5). Report them to the account manager.

### 8.1 Example

A 10-minute disturbance in Gauteng raises the drop probability to 25% on every Gauteng tower. The clock-hour DCR is then about 10% on any set of Gauteng towers (KPI-DEF-001, section 6).

- **Jacaranda Health Network** (GP-001, GP-002, GP-005, GP-006): about 10.0% is above the 9.0% limit, so this is a **breached hour**, a credit of 10% of the monthly fee, a notification within 15 minutes and a P1 phone call.
- **Karoo Mutual Bank** (GP-002, GP-004; GP-007 is excluded if the event falls inside a notified migration window): about 10.0% is below the 11.0% limit, so **no breach**, but a notification within 30 minutes is still due.
- **Highveld Mining Group** (GP-013 only in Gauteng): about 10.0% is below 12.0%, so **no breach**; notification within 30 minutes.
- **Coastal Freight Logistics** (GP-009 only in Gauteng): about 10.0% is below 12.0%, so **no breach**; notification within 60 minutes.

The exact figures depend on the actual call counts. Always compute them from the data rather than assuming the example's numbers.

## 9. Contacts (synthetic)

| Customer | Notification contact | Escalation |
|---|---|---|
| Jacaranda Health Network | Clinical Communications Duty Officer, +27 10 555 0201, duty@jacaranda-health.example.com | Account Manager N. Dlamini, +27 10 555 0301 |
| Karoo Mutual Bank | IT Service Desk, +27 10 555 0202, servicedesk@karoo-mutual.example.com | Account Manager P. van Wyk, +27 10 555 0302 |
| Highveld Mining Group | Mine Communications Control, +27 10 555 0203, control@highveld-mining.example.com | Account Manager S. Naidoo, +27 10 555 0303 |
| Coastal Freight Logistics | Logistics Control Room (24/7), +27 10 555 0204, control@coastal-freight.example.com | Account Manager L. Botha, +27 10 555 0304 |
