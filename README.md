# Telecom Fabric Foundry

A telecom NOC copilot on **Microsoft Fabric Real-Time Intelligence** and **Microsoft Foundry**, published to **Microsoft Teams**.

- **Fabric:** the Real-Time Telecom Call Data Records Jumpstart (emulator → Eventstream → Eventhouse `cdr_raw`), extended with tower/region fields and a spike mode. An **Operations Agent** alerts through Activator and Power Automate email, and a **Fabric Data Agent** answers questions in natural language over KQL.
- **Foundry:** a hosted **orchestrator agent** (Microsoft Agent Framework) routes questions to the Fabric Data Agent ("what is happening") and to a **Telecom Knowledge agent** grounded on a **Foundry IQ** knowledge base ("what it means, what to do"), and is published to Teams.

![Architecture: local scripts build a Fabric workspace (emulator, Eventstream, Eventhouse, Operations Agent, Data Agent) and an Azure resource group with a VNet-injected Foundry project (hosted orchestrator, knowledge agent, Foundry IQ knowledge base), published to Teams through Bot Service; alerts go out through Activator, Power Automate and Outlook](docs/architecture.svg)

*Planned architecture; nothing is deployed yet. The arrows show the main calls: the emulator streams call records into the Eventhouse; the Operations Agent checks it every 5 minutes and emails the NOC through Activator and Power Automate; in Teams, the orchestrator answers "what is happening" through the Fabric Data Agent (user token) and read-only KQL, and "what it means and what to do" through the Knowledge agent and Foundry IQ. A PNG of the same diagram is in [`docs/architecture.png`](docs/architecture.png).*

## Status

**Deployed** to subscription `<subscription-id>` (Sweden Central, Search in UK South). See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for what exists, the deviations from the plan and the manual steps still open, and [`docs/PLAN.md`](docs/PLAN.md) for the original plan.

| Area | State |
|---|---|
| Azure (Waves 0 and 1) | Deployed: VNet, F8 capacity `telcof8`, Foundry account and project, Search, Storage, Cosmos DB, ACR, Key Vault |
| Fabric data | Jumpstart installed; emulator patched with `tower_id`, `region` and spike mode; KQL layer applied (`mv_drops_5m`, `mv_region_5m`, alert functions) |
| Operations Agent | Created (`Telco Drop Monitor`); the playbook generates from the final instructions. **Manual:** [portal steps](#build-the-operations-agent-portal-steps) for the action, Power Automate email, Teams app, Start |
| Fabric Data Agent | Created and published (`TalkToTelecomCdr`) |
| Foundry IQ | Knowledge base `telco-kb` over six documents (File knowledge source) |
| Orchestrator | Hosted agent `telco-orchestrator` v3 (adds `spike_period`, so maintenance is judged on when the drops were elevated), verified end to end on the showcase question |
| Teams | Bot Service deployed, app published at Shared scope; **not yet tried by a person** |
| Lock-down | Not applied: Foundry and Search are still public |

## Build the Operations Agent (portal steps)

`python src/telcoops/setup/04_ops_agent.py` creates the agent `Telco Drop Monitor` and pushes `artifacts/ops-agent/OperationsAgent.json`. The action, the Power Automate flow and Start can only be done in the portal. Do these once, in order.

**Before you start:** the capacity `telcof8` is Active, `03_kql_schema.py` has been run (it creates `mv_region_5m`, `region_alert_candidates` and `worst_towers`), and you can run the emulator (`scripts/run_spike.py`).

### 1. Open the agent and its data source
1. Open the workspace `telco-cdr-jumpstart` in Fabric and open **Telco Drop Monitor**.
2. Check the knowledge source is the KQL database `TelecomCallDataRecords`. If you added `mv_region_5m` after the agent was created, remove and re-add the database so the agent sees it.

### 2. Paste the instructions
1. Replace the contents of **Instructions** with the text of [`artifacts/ops-agent/instructions.txt`](artifacts/ops-agent/instructions.txt). It is the final text: the playbook generator accepted it.
2. Why it is written this way: the generator builds its plan from named tables, views and columns, so the spike rule is a condition on the plain columns of `mv_region_5m` (`calls >= 50` and `dropped / calls > 0.15`). Earlier versions were rejected when they asked for a flag such as `is_spike`, or for "no duplicate incident" and "30-minute suppression", because nothing in the data provides those.

### 3. Add the custom action
1. In **Actions**, choose **Add action**, then **Custom action**.
2. Name it exactly `Notify NOC`. Description: "Send an email to the NOC when a region's dropped-call rate exceeds the threshold".
3. Add six parameters, all text:

   | Parameter | Meaning |
   |---|---|
   | `region` | Province name, for example Gauteng |
   | `drop_pct` | Dropped-call rate over the window, as a percentage |
   | `calls` | Calls in the window |
   | `towers_affected` | Towers over the threshold |
   | `window_start` | Window start, UTC |
   | `window_end` | Window end, UTC |

4. Choose **Create flow**. Power Automate opens with the trigger already linked to the action.

### 4. Build the Power Automate flow
1. **Trigger:** keep **When an Activator rule is triggered**. Check the six parameters appear as dynamic content. If not, save, return to the agent and refresh the action.
2. **Add an action:** **Office 365 Outlook**, then **Send an email (V2)**. Sign in with the mailbox that will send the alert (use a shared mailbox in a real NOC).
3. Fill in the email, choosing the fields from the dynamic content picker:
   - **To:** the NOC address (your own for a demo).
   - **Subject:** `[NOC] Dropped-call alert: ` + region + ` at ` + drop_pct + `%`
   - **Body:**
     ```
     Region: <region>
     Dropped-call rate: <drop_pct>% over <calls> calls
     Towers over threshold: <towers_affected>
     Window (UTC): <window_start> to <window_end>

     Ask the NOC Copilot in Teams: "Which towers are affected in <region>, is there planned maintenance, and does this breach any SLA?"
     ```
4. Name the flow `Telco NOC alert email`, **Save**, and turn it **On**.
5. Optional rate limit: the agent checks every 5 minutes and has no memory of past alerts, so a long spike sends an email on each check. To limit that, add a **Condition** at the start of the flow that skips the email when one was already sent for the same region in the last 30 minutes. Do this in the flow, not in the agent instructions.

### 5. Generate the playbook, install the Teams app, and start
1. Back in the agent, check **Actions** shows `Notify NOC` linked to the flow.
2. Choose **Generate playbook**. Read it: it should use `mv_region_5m`, the 15% / 50-call condition, `region_alert_candidates`, `worst_towers` and `Notify NOC`.
3. Install the **Fabric Operations Agent** app from the Teams app store so you get the agent's messages.
4. **Save**, then **Start**. Check the agent shows Running and its recipient is you.

### 6. Test
1. Start a spike: `python scripts/run_spike.py --region Gauteng --offset 4 --minutes 10 --run-minutes 25`.
2. Wait about 10 minutes (the agent checks on a schedule). You should get a Teams message and the email.
3. If nothing arrives, check that the capacity is Active, the agent is Running, the flow is On (**My flows**, **Run history**), and that this query returns a Gauteng row in the Eventhouse:
   `mv_region_5m | where bin_start == bin(now(), 5m) - 5m | where calls >= 50 and todouble(dropped) / calls > 0.15`

If you change the instructions, edit `artifacts/ops-agent/instructions.txt`, copy the change into `OperationsAgent.json` and the portal, and generate the playbook again.

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
