# Telecom Fabric Foundry

A telecom NOC copilot on **Microsoft Fabric Real-Time Intelligence** and **Microsoft Foundry**, published to **Microsoft Teams**.

- **Fabric:** the Real-Time Telecom Call Data Records Jumpstart (emulator → Eventstream → Eventhouse `cdr_raw`), extended with tower/region fields and a spike mode. An **Operations Agent** alerts through Activator and Power Automate email, and a **Fabric Data Agent** answers questions in natural language over KQL.
- **Foundry:** a hosted **orchestrator agent** (Microsoft Agent Framework) routes questions to the Fabric Data Agent ("what is happening") and to a **Telecom Knowledge agent** grounded on a **Foundry IQ** knowledge base ("what it means, what to do"), and is published to Teams.

![Architecture: local scripts build a Fabric workspace (emulator, Eventstream, Eventhouse, Operations Agent, Data Agent) and an Azure resource group with a VNet-injected Foundry project (hosted orchestrator, knowledge agent, Foundry IQ knowledge base), published to Teams through Bot Service; alerts go out through Activator, Power Automate and Outlook](docs/architecture.svg)

*Planned architecture; nothing is deployed yet. The arrows show the main calls: the emulator streams call records into the Eventhouse; the Operations Agent checks it every 5 minutes and emails the NOC through Activator and Power Automate; in Teams, the orchestrator answers "what is happening" through the Fabric Data Agent (user token) and read-only KQL, and "what it means and what to do" through the Knowledge agent and Foundry IQ. A PNG of the same diagram is in [`docs/architecture.png`](docs/architecture.png).*

## Status

**Deployed** to subscription `bcc55c5e-9e12-4ddc-8645-fa2006032074` (Sweden Central, Search in UK South). See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for what exists, the deviations from the plan and the manual steps still open, and [`docs/PLAN.md`](docs/PLAN.md) for the original plan.

| Area | State |
|---|---|
| Azure (Waves 0 and 1) | Deployed: VNet, F8 capacity `telcof8`, Foundry account and project, Search, Storage, Cosmos DB, ACR, Key Vault |
| Fabric data | Jumpstart installed; emulator patched with `tower_id`, `region` and spike mode; KQL layer applied (`mv_drops_5m`, alert functions) |
| Operations Agent | Created (`Telco Drop Monitor`). **Manual:** playbook, Activator, Power Automate email, Teams app, Start |
| Fabric Data Agent | Created and published (`TalkToTelecomCdr`) |
| Foundry IQ | Knowledge base `telco-kb` over six documents (File knowledge source) |
| Orchestrator | Hosted agent `telco-orchestrator` v2, verified end to end on the showcase question |
| Teams | Bot Service deployed, app published at Shared scope; **not yet tried by a person** |
| Lock-down | Not applied: Foundry and Search are still public |

What is in the repo:

| Path | What it is |
|---|---|
| `infra/` | Bicep: Wave 0 (`wave0-byo-resources.bicep`), Wave 1 (`main.bicep`), Teams bot (`wave3-bot.bicep`), azd hooks |
| `src/telcoops/setup/` | `01_jumpstart`, `02_patch_emulator`, `03_kql_schema`, `04_ops_agent`, `05_data_agent` |
| `src/telcoops/knowledge/` | `create_kb.py` (file knowledge source and knowledge base) |
| `src/telcoops/foundry/` | hosted orchestrator (`hosted_agent/`), toolbox, deploy and Teams publish scripts |
| `artifacts/` | seed towers, KQL, emulator generator, agent definitions, the six knowledge documents |
| `scripts/` | `run_spike.py`, `emulator_status.py`, `ask_agent.py`, `foundry_access.py`, KB document tools |
| `tests/` | 29 offline tests (generator, notebook patcher, KQL files, tool logic) |

Run a demo: `python scripts/run_spike.py --region Gauteng --offset 4 --minutes 10 --run-minutes 25`, then
`python scripts/ask_agent.py "Drops spiked in Gauteng in the last hour. Which towers are affected, is there planned maintenance, does this breach any enterprise SLA, and what should the field team do?"`.
The F8 capacity bills while Active and was found paused by another principal each night; see DEPLOYMENT.md.

All documents and data describe a fictional operator, *Imvula Telecom*, and are labelled **SYNTHETIC – DEMO DATA**.
