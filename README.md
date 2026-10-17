# Telecom Fabric Foundry

A telecom NOC copilot on **Microsoft Fabric Real-Time Intelligence** and **Microsoft Foundry**, published to **Microsoft Teams**.

- **Fabric:** the Real-Time Telecom Call Data Records Jumpstart (emulator → Eventstream → Eventhouse `cdr_raw`), extended with tower/region fields and a spike mode. An **Operations Agent** alerts through Activator and Power Automate email, and a **Fabric Data Agent** answers questions in natural language over KQL.
- **Foundry:** a hosted **orchestrator agent** (Microsoft Agent Framework) routes questions to the Fabric Data Agent ("what is happening") and to a **Telecom Knowledge agent** grounded on a **Foundry IQ** knowledge base ("what it means, what to do"), and is published to Teams.

## Status

**Plan only. Nothing is built or deployed yet.** The full step-by-step plan is in [`docs/PLAN.md`](docs/PLAN.md).

What already exists:

| Path | What it is |
|---|---|
| `docs/PLAN.md` | Implementation and deployment plan (phases P0–P6, Bicep + Python), region assessment, lessons from `pdm-fabric-foundry` |
| `artifacts/seed/towers.csv` | 40 synthetic towers across the nine South African provinces, the single source of truth for tower IDs |
| `artifacts/kb-docs/*.md` | Six synthetic Foundry IQ documents (runbook, site inventory, maintenance and incident log, KPI definitions, enterprise SLAs, regulatory QoS targets), at least 1,000 words each, reused on every deployment |
| `scripts/build_site_inventory.py` | Regenerates `site-inventory.md` from `towers.csv` |
| `scripts/check_kb_docs.py` | Checks word counts, the SYNTHETIC banner, tower IDs and SLA tower lists |

All documents and data describe a fictional operator, *Imvula Telecom*, and are labelled **SYNTHETIC – DEMO DATA**.
