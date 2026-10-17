# Tower and Site Inventory (SITE-INV-001)

> **SYNTHETIC – DEMO DATA.** This document describes a fictional mobile operator, *Imvula Telecom*, for a Microsoft Fabric and Foundry demonstration. Sites, people, phone numbers and customers are invented. Coordinates are approximate city locations, not real tower sites.

| Field | Value |
|---|---|
| Document ID | SITE-INV-001 |
| Version | 1.0 |
| Effective date | 1 October 2026 |
| Owner | Network Planning and Field Operations |
| Source | Generated from `artifacts/seed/towers.csv`, the same file that drives the CDR emulator and the KQL `towers` table. Tower IDs in this document always match `tower_id` in the call data. |
| Related documents | RB-NOC-001, MAINT-LOG-001, SLA-ENT-001, KPI-DEF-001 |

## 1. Summary

Imvula Telecom operates **40 towers** across the nine South African provinces. Each tower ID starts with a province prefix: GP Gauteng, WC Western Cape, KZN KwaZulu-Natal, EC Eastern Cape, FS Free State, LP Limpopo, MP Mpumalanga, NW North West, NC Northern Cape.

| Region | Towers | 5G towers | Microwave backhaul | Towers with 2 h battery | Towers serving enterprise customers |
|---|---|---|---|---|---|
| Gauteng | 14 | 6 | 5 | 2 | 8 |
| Western Cape | 6 | 2 | 2 | 0 | 2 |
| KwaZulu-Natal | 6 | 2 | 2 | 0 | 3 |
| Eastern Cape | 3 | 0 | 1 | 1 | 1 |
| Free State | 2 | 0 | 1 | 0 | 1 |
| Limpopo | 2 | 0 | 1 | 1 | 0 |
| Mpumalanga | 3 | 0 | 0 | 0 | 2 |
| North West | 2 | 0 | 1 | 0 | 1 |
| Northern Cape | 2 | 0 | 1 | 0 | 1 |

## 2. Field teams

| Field team | Depot | Lead | Phone | Email | Coverage |
|---|---|---|---|---|---|
| GP-North | Pretoria depot | T. Mokoena | +27 10 555 0111 | ft.gp-north@imvula.example.com | Pretoria, Centurion, Midrand, Kempton Park, Soshanguve |
| GP-Central | Johannesburg depot (Braamfontein) | A. Pillay | +27 10 555 0112 | ft.gp-central@imvula.example.com | Johannesburg CBD, Sandton, Randburg, Roodepoort, Soweto |
| GP-East-South | Germiston depot | R. Venter | +27 10 555 0113 | ft.gp-east-south@imvula.example.com | Germiston, Boksburg, Benoni, Vereeniging |
| WC-Field | Bellville depot | F. Adams | +27 10 555 0121 | ft.wc@imvula.example.com | Cape Town metro, Stellenbosch, Paarl, George (George is a 5-hour drive; use the George contractor for first response) |
| KZN-Field | Pinetown depot | S. Zulu | +27 10 555 0131 | ft.kzn@imvula.example.com | Durban, Umhlanga, Pinetown, Pietermaritzburg, Richards Bay, Newcastle |
| EC-Field | Gqeberha depot | L. Ndlovu | +27 10 555 0141 | ft.ec@imvula.example.com | Gqeberha, East London, Mthatha |
| FS-Field | Bloemfontein depot | J. Steyn | +27 10 555 0151 | ft.fs@imvula.example.com | Bloemfontein, Welkom |
| LP-Field | Polokwane depot | M. Nkuna | +27 10 555 0161 | ft.lp@imvula.example.com | Polokwane, Thohoyandou |
| MP-Field | eMalahleni depot | B. Mahlangu | +27 10 555 0171 | ft.mp@imvula.example.com | Mbombela, eMalahleni, Secunda |
| NW-Field | Rustenburg depot | K. Molefe | +27 10 555 0181 | ft.nw@imvula.example.com | Rustenburg, Mahikeng |
| NC-Field | Kimberley depot | D. Jacobs | +27 10 555 0191 | ft.nc@imvula.example.com | Kimberley, Upington (Upington is a 4-hour drive; a spare solar charge controller is kept in Upington) |

Dispatch through the NOC duty desk (+27 10 555 0100). Outside business hours each team has an on-call engineer, reached on the team phone number.

## 3. Enterprise customers by tower

| Customer | Served towers |
|---|---|
| Jacaranda Health Network | GP-001, GP-002, GP-005, GP-006, WC-002, KZN-002 |
| Karoo Mutual Bank | GP-002, GP-004, GP-007, WC-001 |
| Coastal Freight Logistics | GP-009, WC-001, KZN-001, KZN-005, EC-001 |
| Highveld Mining Group | GP-013, FS-002, MP-002, MP-003, NW-001, NC-001 |

For SLA terms, see SLA-ENT-001. A tower that serves an enterprise customer raises the incident severity by one level (RB-NOC-001, section 2).

## 4. Sites by region

### 4.1 Gauteng

Gauteng is the busiest province and carries roughly a third of all traffic. Five towers use microwave backhaul (GP-003, GP-007, GP-008, GP-011, GP-014) and are the most exposed to afternoon thunderstorms; GP-003, GP-007 and GP-011 are being moved to fibre under CHG-2026-0412 (MAINT-LOG-001). GP-012 and GP-014 have only 2 hours of battery and go silent first during load shedding; GP-012 is getting a 6-hour battery under CHG-2026-0431.

| Tower | Site | City | Lat, Lon | Vendor | Tech | Backhaul | Backup power | Field team | Enterprise customers |
|---|---|---|---|---|---|---|---|---|---|
| GP-001 | Johannesburg CBD Rooftop | Johannesburg | -26.2041, 28.0473 | Ericsson | 5G | fibre | battery and generator, 24 h | GP-Central | Jacaranda Health Network |
| GP-002 | Sandton Central | Sandton | -26.1076, 28.0567 | Ericsson | 5G | fibre | battery and generator, 24 h | GP-Central | Jacaranda Health Network, Karoo Mutual Bank |
| GP-003 | Soweto Orlando | Soweto | -26.2485, 27.8540 | Huawei | 4G | microwave to GP-001 Johannesburg CBD fibre POP | battery, 4 h | GP-Central | none |
| GP-004 | Midrand Waterfall | Midrand | -25.9992, 28.1263 | Nokia | 5G | fibre | battery and generator, 24 h | GP-North | Karoo Mutual Bank |
| GP-005 | Pretoria CBD | Pretoria | -25.7479, 28.2293 | Ericsson | 5G | fibre | battery and generator, 24 h | GP-North | Jacaranda Health Network |
| GP-006 | Centurion Lake | Centurion | -25.8603, 28.1894 | Nokia | 5G | fibre | battery, 6 h | GP-North | Jacaranda Health Network |
| GP-007 | Randburg Ferndale | Randburg | -26.0936, 28.0064 | Huawei | 4G | microwave to GP-002 Sandton fibre POP | battery, 4 h | GP-Central | Karoo Mutual Bank |
| GP-008 | Roodepoort Florida | Roodepoort | -26.1625, 27.8725 | Huawei | 4G | microwave to GP-002 Sandton fibre POP | battery, 4 h | GP-Central | none |
| GP-009 | Kempton Park Airport Corridor | Kempton Park | -26.1000, 28.2333 | Ericsson | 5G | fibre | battery and generator, 24 h | GP-North | Coastal Freight Logistics |
| GP-010 | Germiston Junction | Germiston | -26.2309, 28.1772 | Nokia | 4G | fibre | battery, 6 h | GP-East-South | none |
| GP-011 | Benoni Lakes | Benoni | -26.1885, 28.3207 | Huawei | 4G | microwave to GP-010 Germiston fibre POP | battery, 4 h | GP-East-South | none |
| GP-012 | Boksburg East Rand Mall | Boksburg | -26.2125, 28.2596 | Nokia | 4G | fibre | battery, 2 h | GP-East-South | none |
| GP-013 | Vereeniging Industrial | Vereeniging | -26.6731, 27.9261 | Ericsson | 4G | fibre | generator, 48 h fuel | GP-East-South | Highveld Mining Group |
| GP-014 | Soshanguve Block L | Soshanguve | -25.5225, 28.1003 | Huawei | 4G | microwave to GP-005 Pretoria CBD fibre POP | battery, 2 h | GP-North | none |

### 4.2 Western Cape

Cape Town metro towers are on fibre with good backup. George (WC-005) is remote from the Bellville depot, so first response there is by a local contractor.

| Tower | Site | City | Lat, Lon | Vendor | Tech | Backhaul | Backup power | Field team | Enterprise customers |
|---|---|---|---|---|---|---|---|---|---|
| WC-001 | Cape Town Foreshore | Cape Town | -33.9249, 18.4241 | Ericsson | 5G | fibre | battery and generator, 24 h | WC-Field | Coastal Freight Logistics, Karoo Mutual Bank |
| WC-002 | Bellville Tygervalley | Bellville | -33.9000, 18.6333 | Nokia | 5G | fibre | battery and generator, 24 h | WC-Field | Jacaranda Health Network |
| WC-003 | Stellenbosch Central | Stellenbosch | -33.9321, 18.8602 | Nokia | 4G | fibre | battery, 6 h | WC-Field | none |
| WC-004 | Mitchells Plain Town Centre | Mitchells Plain | -34.0515, 18.6181 | Huawei | 4G | microwave to WC-002 Bellville fibre POP | battery, 4 h | WC-Field | none |
| WC-005 | George N2 Corridor | George | -33.9630, 22.4617 | Huawei | 4G | microwave to George exchange (third-party fibre) | battery, 4 h | WC-Field | none |
| WC-006 | Paarl Main Road | Paarl | -33.7342, 18.9621 | Nokia | 4G | fibre | battery, 6 h | WC-Field | none |

### 4.3 KwaZulu-Natal

Durban Point and Richards Bay serve port operations for Coastal Freight Logistics. KZN-003 Pinetown had a wind-related dish misalignment in August 2026 (INC-2026-0805).

| Tower | Site | City | Lat, Lon | Vendor | Tech | Backhaul | Backup power | Field team | Enterprise customers |
|---|---|---|---|---|---|---|---|---|---|
| KZN-001 | Durban Point | Durban | -29.8587, 31.0218 | Ericsson | 5G | fibre | battery and generator, 24 h | KZN-Field | Coastal Freight Logistics |
| KZN-002 | Umhlanga Ridge | Umhlanga | -29.7277, 31.0844 | Ericsson | 5G | fibre | battery and generator, 24 h | KZN-Field | Jacaranda Health Network |
| KZN-003 | Pinetown Hub | Pinetown | -29.8167, 30.8500 | Huawei | 4G | microwave to KZN-001 Durban Point fibre POP | battery, 4 h | KZN-Field | none |
| KZN-004 | Pietermaritzburg Central | Pietermaritzburg | -29.6006, 30.3794 | Nokia | 4G | fibre | battery, 6 h | KZN-Field | none |
| KZN-005 | Richards Bay Harbour | Richards Bay | -28.7830, 32.0377 | Ericsson | 4G | fibre | generator, 48 h fuel | KZN-Field | Coastal Freight Logistics |
| KZN-006 | Newcastle North | Newcastle | -27.7580, 29.9318 | Huawei | 4G | microwave to Newcastle exchange (third-party fibre) | battery, 4 h | KZN-Field | none |

### 4.4 Eastern Cape

EC-003 Mthatha has only 2 hours of battery and a microwave link to a third-party exchange, which makes it the most fragile site in the province.

| Tower | Site | City | Lat, Lon | Vendor | Tech | Backhaul | Backup power | Field team | Enterprise customers |
|---|---|---|---|---|---|---|---|---|---|
| EC-001 | Gqeberha Harbour | Gqeberha | -33.9608, 25.6022 | Ericsson | 4G | fibre | battery and generator, 24 h | EC-Field | Coastal Freight Logistics |
| EC-002 | East London Quigney | East London | -33.0153, 27.9116 | Nokia | 4G | fibre | battery, 6 h | EC-Field | none |
| EC-003 | Mthatha Central | Mthatha | -31.5889, 28.7844 | Huawei | 4G | microwave to Mthatha exchange (third-party fibre) | battery, 2 h | EC-Field | none |

### 4.5 Free State

FS-002 Welkom serves Highveld Mining Group's Goldfields operations over microwave backhaul.

| Tower | Site | City | Lat, Lon | Vendor | Tech | Backhaul | Backup power | Field team | Enterprise customers |
|---|---|---|---|---|---|---|---|---|---|
| FS-001 | Bloemfontein Central | Bloemfontein | -29.0852, 26.1596 | Nokia | 4G | fibre | battery and generator, 24 h | FS-Field | none |
| FS-002 | Welkom Goldfields | Welkom | -27.9774, 26.7351 | Huawei | 4G | microwave to Welkom exchange (third-party fibre) | battery, 4 h | FS-Field | Highveld Mining Group |

### 4.6 Limpopo

LP-002 Thohoyandou has 2 hours of battery and a long drive from the Polokwane depot.

| Tower | Site | City | Lat, Lon | Vendor | Tech | Backhaul | Backup power | Field team | Enterprise customers |
|---|---|---|---|---|---|---|---|---|---|
| LP-001 | Polokwane CBD | Polokwane | -23.9045, 29.4689 | Nokia | 4G | fibre | battery, 6 h | LP-Field | none |
| LP-002 | Thohoyandou Central | Thohoyandou | -22.9456, 30.4847 | Huawei | 4G | microwave to LP-001 Polokwane fibre POP | battery, 2 h | LP-Field | none |

### 4.7 Mpumalanga

MP-002 and MP-003 serve Highveld Mining Group and carry 48-hour generators. MP-003's generator failed to start in September 2026 (INC-2026-0916); the controller was replaced.

| Tower | Site | City | Lat, Lon | Vendor | Tech | Backhaul | Backup power | Field team | Enterprise customers |
|---|---|---|---|---|---|---|---|---|---|
| MP-001 | Mbombela Riverside | Mbombela | -25.4658, 30.9853 | Nokia | 4G | fibre | battery, 6 h | MP-Field | none |
| MP-002 | eMalahleni Coalfields | eMalahleni | -25.8713, 29.2332 | Ericsson | 4G | fibre | generator, 48 h fuel | MP-Field | Highveld Mining Group |
| MP-003 | Secunda Industrial | Secunda | -26.5167, 29.1833 | Ericsson | 4G | fibre | generator, 48 h fuel | MP-Field | Highveld Mining Group |

### 4.8 North West

NW-001 on the platinum belt serves Highveld Mining Group with a 48-hour generator.

| Tower | Site | City | Lat, Lon | Vendor | Tech | Backhaul | Backup power | Field team | Enterprise customers |
|---|---|---|---|---|---|---|---|---|---|
| NW-001 | Rustenburg Platinum Belt | Rustenburg | -25.6676, 27.2421 | Ericsson | 4G | fibre | generator, 48 h fuel | NW-Field | Highveld Mining Group |
| NW-002 | Mahikeng Central | Mahikeng | -25.8652, 25.6442 | Huawei | 4G | microwave to Mahikeng exchange (third-party fibre) | battery, 4 h | NW-Field | none |

### 4.9 Northern Cape

Only two towers serve a very large area. NC-002 Upington runs on battery plus solar and reaches Kimberley over a three-hop microwave link. With two towers, one silent tower is 50% of the province (QOS-REG-001, section 6).

| Tower | Site | City | Lat, Lon | Vendor | Tech | Backhaul | Backup power | Field team | Enterprise customers |
|---|---|---|---|---|---|---|---|---|---|
| NC-001 | Kimberley Big Hole | Kimberley | -28.7282, 24.7499 | Nokia | 4G | fibre | battery, 6 h | NC-Field | Highveld Mining Group |
| NC-002 | Upington Orange River | Upington | -28.4478, 21.2561 | Huawei | 4G | microwave to NC-001 Kimberley fibre POP (long-haul microwave, 3 hops) | battery and solar, about 12 h | NC-Field | none |

## 5. Site profiles

Each profile gives the facts the NOC needs when a single tower is affected.

- **GP-001 Johannesburg CBD Rooftop** (Johannesburg, Gauteng): Ericsson 5G, fibre backhaul, backup battery and generator, 24 h. Field team GP-Central. Serves Jacaranda Health Network. Notes: no special risks recorded.
- **GP-002 Sandton Central** (Sandton, Gauteng): Ericsson 5G, fibre backhaul, backup battery and generator, 24 h. Field team GP-Central. Serves Jacaranda Health Network and Karoo Mutual Bank. Notes: no special risks recorded.
- **GP-003 Soweto Orlando** (Soweto, Gauteng): Huawei 4G, microwave backhaul to GP-001 Johannesburg CBD fibre POP, backup battery, 4 h. Field team GP-Central. Serves no enterprise customers. Notes: exposed to rain-fade and wind on its microwave link; part of the Gauteng fibre migration (CHG-2026-0412, weekdays 09:00-15:00 SAST).
- **GP-004 Midrand Waterfall** (Midrand, Gauteng): Nokia 5G, fibre backhaul, backup battery and generator, 24 h. Field team GP-North. Serves Karoo Mutual Bank. Notes: no special risks recorded.
- **GP-005 Pretoria CBD** (Pretoria, Gauteng): Ericsson 5G, fibre backhaul, backup battery and generator, 24 h. Field team GP-North. Serves Jacaranda Health Network. Notes: no special risks recorded.
- **GP-006 Centurion Lake** (Centurion, Gauteng): Nokia 5G, fibre backhaul, backup battery, 6 h. Field team GP-North. Serves Jacaranda Health Network. Notes: no special risks recorded.
- **GP-007 Randburg Ferndale** (Randburg, Gauteng): Huawei 4G, microwave backhaul to GP-002 Sandton fibre POP, backup battery, 4 h. Field team GP-Central. Serves Karoo Mutual Bank. Notes: exposed to rain-fade and wind on its microwave link; part of the Gauteng fibre migration (CHG-2026-0412, weekdays 09:00-15:00 SAST).
- **GP-008 Roodepoort Florida** (Roodepoort, Gauteng): Huawei 4G, microwave backhaul to GP-002 Sandton fibre POP, backup battery, 4 h. Field team GP-Central. Serves no enterprise customers. Notes: exposed to rain-fade and wind on its microwave link.
- **GP-009 Kempton Park Airport Corridor** (Kempton Park, Gauteng): Ericsson 5G, fibre backhaul, backup battery and generator, 24 h. Field team GP-North. Serves Coastal Freight Logistics. Notes: no special risks recorded.
- **GP-010 Germiston Junction** (Germiston, Gauteng): Nokia 4G, fibre backhaul, backup battery, 6 h. Field team GP-East-South. Serves no enterprise customers. Notes: no special risks recorded.
- **GP-011 Benoni Lakes** (Benoni, Gauteng): Huawei 4G, microwave backhaul to GP-010 Germiston fibre POP, backup battery, 4 h. Field team GP-East-South. Serves no enterprise customers. Notes: exposed to rain-fade and wind on its microwave link; part of the Gauteng fibre migration (CHG-2026-0412, weekdays 09:00-15:00 SAST).
- **GP-012 Boksburg East Rand Mall** (Boksburg, Gauteng): Nokia 4G, fibre backhaul, backup battery, 2 h. Field team GP-East-South. Serves no enterprise customers. Notes: only 2 hours of battery, so it is high-risk during load shedding; battery replacement on Saturdays in October 2026 (CHG-2026-0431).
- **GP-013 Vereeniging Industrial** (Vereeniging, Gauteng): Ericsson 4G, fibre backhaul, backup generator, 48 h fuel. Field team GP-East-South. Serves Highveld Mining Group. Notes: no special risks recorded.
- **GP-014 Soshanguve Block L** (Soshanguve, Gauteng): Huawei 4G, microwave backhaul to GP-005 Pretoria CBD fibre POP, backup battery, 2 h. Field team GP-North. Serves no enterprise customers. Notes: only 2 hours of battery, so it is high-risk during load shedding; exposed to rain-fade and wind on its microwave link.
- **WC-001 Cape Town Foreshore** (Cape Town, Western Cape): Ericsson 5G, fibre backhaul, backup battery and generator, 24 h. Field team WC-Field. Serves Coastal Freight Logistics and Karoo Mutual Bank. Notes: no special risks recorded.
- **WC-002 Bellville Tygervalley** (Bellville, Western Cape): Nokia 5G, fibre backhaul, backup battery and generator, 24 h. Field team WC-Field. Serves Jacaranda Health Network. Notes: no special risks recorded.
- **WC-003 Stellenbosch Central** (Stellenbosch, Western Cape): Nokia 4G, fibre backhaul, backup battery, 6 h. Field team WC-Field. Serves no enterprise customers. Notes: no special risks recorded.
- **WC-004 Mitchells Plain Town Centre** (Mitchells Plain, Western Cape): Huawei 4G, microwave backhaul to WC-002 Bellville fibre POP, backup battery, 4 h. Field team WC-Field. Serves no enterprise customers. Notes: exposed to rain-fade and wind on its microwave link.
- **WC-005 George N2 Corridor** (George, Western Cape): Huawei 4G, microwave backhaul to George exchange (third-party fibre), backup battery, 4 h. Field team WC-Field. Serves no enterprise customers. Notes: exposed to rain-fade and wind on its microwave link.
- **WC-006 Paarl Main Road** (Paarl, Western Cape): Nokia 4G, fibre backhaul, backup battery, 6 h. Field team WC-Field. Serves no enterprise customers. Notes: no special risks recorded.
- **KZN-001 Durban Point** (Durban, KwaZulu-Natal): Ericsson 5G, fibre backhaul, backup battery and generator, 24 h. Field team KZN-Field. Serves Coastal Freight Logistics. Notes: no special risks recorded.
- **KZN-002 Umhlanga Ridge** (Umhlanga, KwaZulu-Natal): Ericsson 5G, fibre backhaul, backup battery and generator, 24 h. Field team KZN-Field. Serves Jacaranda Health Network. Notes: no special risks recorded.
- **KZN-003 Pinetown Hub** (Pinetown, KwaZulu-Natal): Huawei 4G, microwave backhaul to KZN-001 Durban Point fibre POP, backup battery, 4 h. Field team KZN-Field. Serves no enterprise customers. Notes: exposed to rain-fade and wind on its microwave link.
- **KZN-004 Pietermaritzburg Central** (Pietermaritzburg, KwaZulu-Natal): Nokia 4G, fibre backhaul, backup battery, 6 h. Field team KZN-Field. Serves no enterprise customers. Notes: no special risks recorded.
- **KZN-005 Richards Bay Harbour** (Richards Bay, KwaZulu-Natal): Ericsson 4G, fibre backhaul, backup generator, 48 h fuel. Field team KZN-Field. Serves Coastal Freight Logistics. Notes: no special risks recorded.
- **KZN-006 Newcastle North** (Newcastle, KwaZulu-Natal): Huawei 4G, microwave backhaul to Newcastle exchange (third-party fibre), backup battery, 4 h. Field team KZN-Field. Serves no enterprise customers. Notes: exposed to rain-fade and wind on its microwave link.
- **EC-001 Gqeberha Harbour** (Gqeberha, Eastern Cape): Ericsson 4G, fibre backhaul, backup battery and generator, 24 h. Field team EC-Field. Serves Coastal Freight Logistics. Notes: no special risks recorded.
- **EC-002 East London Quigney** (East London, Eastern Cape): Nokia 4G, fibre backhaul, backup battery, 6 h. Field team EC-Field. Serves no enterprise customers. Notes: no special risks recorded.
- **EC-003 Mthatha Central** (Mthatha, Eastern Cape): Huawei 4G, microwave backhaul to Mthatha exchange (third-party fibre), backup battery, 2 h. Field team EC-Field. Serves no enterprise customers. Notes: only 2 hours of battery, so it is high-risk during load shedding; exposed to rain-fade and wind on its microwave link.
- **FS-001 Bloemfontein Central** (Bloemfontein, Free State): Nokia 4G, fibre backhaul, backup battery and generator, 24 h. Field team FS-Field. Serves no enterprise customers. Notes: no special risks recorded.
- **FS-002 Welkom Goldfields** (Welkom, Free State): Huawei 4G, microwave backhaul to Welkom exchange (third-party fibre), backup battery, 4 h. Field team FS-Field. Serves Highveld Mining Group. Notes: exposed to rain-fade and wind on its microwave link.
- **LP-001 Polokwane CBD** (Polokwane, Limpopo): Nokia 4G, fibre backhaul, backup battery, 6 h. Field team LP-Field. Serves no enterprise customers. Notes: no special risks recorded.
- **LP-002 Thohoyandou Central** (Thohoyandou, Limpopo): Huawei 4G, microwave backhaul to LP-001 Polokwane fibre POP, backup battery, 2 h. Field team LP-Field. Serves no enterprise customers. Notes: only 2 hours of battery, so it is high-risk during load shedding; exposed to rain-fade and wind on its microwave link.
- **MP-001 Mbombela Riverside** (Mbombela, Mpumalanga): Nokia 4G, fibre backhaul, backup battery, 6 h. Field team MP-Field. Serves no enterprise customers. Notes: no special risks recorded.
- **MP-002 eMalahleni Coalfields** (eMalahleni, Mpumalanga): Ericsson 4G, fibre backhaul, backup generator, 48 h fuel. Field team MP-Field. Serves Highveld Mining Group. Notes: no special risks recorded.
- **MP-003 Secunda Industrial** (Secunda, Mpumalanga): Ericsson 4G, fibre backhaul, backup generator, 48 h fuel. Field team MP-Field. Serves Highveld Mining Group. Notes: no special risks recorded.
- **NW-001 Rustenburg Platinum Belt** (Rustenburg, North West): Ericsson 4G, fibre backhaul, backup generator, 48 h fuel. Field team NW-Field. Serves Highveld Mining Group. Notes: no special risks recorded.
- **NW-002 Mahikeng Central** (Mahikeng, North West): Huawei 4G, microwave backhaul to Mahikeng exchange (third-party fibre), backup battery, 4 h. Field team NW-Field. Serves no enterprise customers. Notes: exposed to rain-fade and wind on its microwave link.
- **NC-001 Kimberley Big Hole** (Kimberley, Northern Cape): Nokia 4G, fibre backhaul, backup battery, 6 h. Field team NC-Field. Serves Highveld Mining Group. Notes: no special risks recorded.
- **NC-002 Upington Orange River** (Upington, Northern Cape): Huawei 4G, microwave backhaul to NC-001 Kimberley fibre POP (long-haul microwave, 3 hops), backup battery and solar, about 12 h. Field team NC-Field. Serves no enterprise customers. Notes: exposed to rain-fade and wind on its microwave link.

## 6. Keeping this inventory current

Change `artifacts/seed/towers.csv` first, then regenerate this document, reload the KQL `towers` table and update the emulator. Never edit tower attributes only here, because the call data and the agents would then disagree with this document.
