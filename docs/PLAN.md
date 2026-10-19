# Telecom CDR Copilot: implementation and deployment plan

Status: **plan only. Nothing is built or deployed yet.** This document is written so that someone (or another model) who has not seen the planning conversation can carry it out step by step.

## 1. What we are building

```
                 ┌──────────── Microsoft Fabric (F8, swedencentral) ─────────────┐
Emulator nb ─► Eventstream ─► Eventhouse DemosEH / KQL DB TelecomCallDataRecords  │
 (+tower_id,       (custom        cdr_raw + towers + mv_drops_5m                  │
  region, spike)    endpoint)       │                    │                        │
                 │          Operations Agent        Fabric Data Agent             │
                 │           (every 5 min)          (NL → KQL, published)         │
                 │                 │                     │                        │
                 │   Activator ─► Power Automate ─► Outlook email (+ Teams link)  │
                 └───────────────────────────────────────┼────────────────────────┘
                                                         │ toolbox, user-token (OBO)
              ┌──────── Microsoft Foundry (swedencentral, VNet-injected) ───────────┐
              │   telco-orchestrator (hosted agent, Agent Framework) ◄── Teams      │
              │      │  deterministic KQL tools (read-only)              (Bot Svc)  │
              │      └─► telco-knowledge (prompt agent) ─► Foundry IQ KB telco-kb   │
              │                                   (AI Search + Blob kb-docs)        │
              └─────────────────────────────────────────────────────────────────────┘
```

- **Fabric** monitors and alerts. The Operations Agent is a Fabric Real-Time Intelligence item, and it reaches Power Automate through an Activator.
- **Foundry** handles the conversation. The orchestrator routes a question to the Fabric Data Agent ("what is happening") or to the Knowledge agent ("what does it mean, what do we do"), or to both for incident questions. It is published to Teams.

## 2. Decisions already made

| Topic | Decision |
|---|---|
| Subscription | `<subscription-id>` |
| Region | `swedencentral` for everything (Fabric capacity, Foundry, Search, Storage). The Operations Agent is supported there; it is not in East US or South Central US. **`uksouth` is an equally good fallback** (see "Region assessment" below). |
| Network | **Private** in the end state, like `pdm-fabric-foundry`, but **Foundry, AI Search and the KB storage account stay publicly reachable until every build step is done**. The lock-down is one of the last steps. Fabric workspace private link is the very last step, and optional. |
| Teams | In scope. The orchestrator is published to Teams through Azure Bot Service. |
| Repo | New repo a local clone of this repo (git initialised, nothing committed, no remote yet). |
| Where Fabric items are built | **From the local machine, not the jumpbox.** This only works while the workspace is public, which is why Fabric private link comes last. |
| Reference implementation | `C:\Users\pranabp\source\repos\pdm-fabric-foundry` (GitHub `pranabpaul-tech/pdm-fabric-foundry`). Copy its patterns and its fixes; section 9 lists them. |

### Region assessment: Sweden Central vs UK South (checked 17 October 2026)

| Need | Sweden Central | UK South | Source |
|---|---|---|---|
| Fabric, all workloads incl. Real-Time Intelligence | Yes | Yes (only "Fabric App (preview)" missing, which isn't used) | Fabric region availability |
| Fabric Operations Agent | Yes | Yes (missing only in East US and South Central US) | Fabric region availability |
| Foundry Agent Service, Responses API, private VNet | Yes | Yes | Agent Service limits/quotas/regions |
| Agent tools used here: Fabric Data Agent, Azure AI Search, MCP, Agent2Agent, Function | Yes | Yes | same page, "Tool support by region" |
| Default concurrent hosted-agent sessions per subscription | 2,000 | 1,000 (irrelevant at demo scale) | same page |
| Track record in `pdm-fabric-foundry` (other subscription) | Hosted agent deployed and fast route registration, but **no AI Search capacity** | AI Search capacity available, but **no Fabric quota** in that subscription | PdM commit `d5b320d` |

**Conclusion:** both regions support everything this design uses. Keep Sweden Central, and switch to UK South (all or part) only if the quota checks in section 3 fail in the new subscription. Rules for a split:
- the Foundry account and its VNet must be in the same region;
- Search, Storage and Cosmos may be in another region (cross-region private endpoints work);
- the Fabric capacity may be in another region from Foundry; `fabricCapacityLocation` stays a separate parameter for this.

Prefer keeping the Fabric capacity in the tenant's home geography (see 3.1). Re-check both Microsoft Learn pages at build time, because preview features move.

### Naming (use consistently)

| Thing | Name |
|---|---|
| Resource group | `rg-telco-fabric-foundry` |
| azd environment | `telco-dev` |
| Python package / env prefix | `src/telcoops/` / `TELCO_` |
| Fabric capacity | `telcof8` (F8, lowercase alphanumeric only) |
| Fabric workspace | `telco-cdr-jumpstart` |
| Foundry account base / project | `telcoai` / `telco-agents` (the vendored module appends a 4-character suffix to both) |
| Models | `gpt-4.1` (chat), `text-embedding-3-large` (KB vectorisation) |
| Hosted agent / knowledge agent | `telco-orchestrator` / `telco-knowledge` |
| Foundry IQ knowledge base | `telco-kb`, blob container `kb-docs` |
| Toolbox / connection | `telco-fabric-toolbox` / `fabric-dataagent-obo` |
| Fabric Data Agent | `TalkToTelecomCdr` |
| Operations Agent | `Telco Drop Monitor` |
| Bot Service | `bot-telco-orchestrator`, display name `Telco NOC Copilot` |

### What the Jumpstart deploys (from the `fabric_jumpstart` 0.1.12 catalog entry, `telecom-call-data-records.yml`)

- Install name: `telecom-call-data-records`. Source: `https://github.com/ecotte/fabric-rti-demos.git` at tag `v0.1.8`, path `telecom-call-data-records/`.
- Items:
  - `TelecomCallDataRecordsEmulator` (Notebook, the entry point);
  - `TelecomCallDataRecordsStream` (Eventstream with a CustomEndpoint source);
  - `DemosEH` (Eventhouse);
  - `TelecomCallDataRecords` (KQL database);
  - `TelecomCallDataRecordsDashboard` (KQL dashboard).
- The Eventstream lands rows in `cdr_raw` by DirectIngestion.
- Per the brief, `cdr_raw` holds `status` (Completed/Failed/Dropped), `call_type`, `call_quality`, tower latitude and longitude, and timestamps. The default mix is 85% Completed, 8% Failed, 7% Dropped. **Not yet verified against the source.** Step P0.6 captures the real schema and notebook code before anything is changed.

## 3. Checks to make before any step (blocking)

1. **Tenant home region.** In Fabric, go to Help (?) → About Fabric → "Your data is stored in". Power Automate actions from an Operations Agent can fail if the capacity is not in the tenant's home region. If the home region is not in the Europe geography, record that as a risk and test the email path early (P1). Don't move the capacity before that test.
2. **Quota in swedencentral** for the new subscription:
   - Fabric F8 (`az fabric capacity` / portal quotas);
   - AI Search Standard (the other subscription had **no Search capacity in swedencentral**);
   - `gpt-4.1` GlobalStandard at 30k TPM or more;
   - `text-embedding-3-large`.

   If Search has no capacity, add a `searchLocation` parameter to Wave 0 and use **`uksouth`**, the documented fallback (see "Region assessment"). A private endpoint in the swedencentral VNet can target a Search service in another region. If Fabric or Foundry quota is missing in swedencentral, move that tier to `uksouth`. Foundry and its VNet always move together.
3. **Resource providers** registered: `Microsoft.Fabric`, `Microsoft.BotService`, `Microsoft.App`, `Microsoft.CognitiveServices`, `Microsoft.Search`, `Microsoft.DocumentDB`, `Microsoft.Storage`, `Microsoft.KeyVault`, `Microsoft.ContainerRegistry`, `Microsoft.ContainerInstance`, `Microsoft.Network`.
4. **Fabric tenant settings** (Fabric admin):
   - Operations Agents (preview);
   - Copilot and Azure OpenAI;
   - "Users can create and share Data agent";
   - cross-geo processing if prompted.

   Azure Private Link and workspace-level inbound rules are needed only for the last step.
5. **Identities.** One human account (the "operator") runs every Fabric step and creates the Operations Agent: it runs as that person's delegated identity. Make the operator a Fabric capacity admin. List the demo users. Each needs Viewer on the workspace, viewer on the KQL database, and an Azure role on the Foundry project (for Teams access to the agent).
6. **Tooling:**
   - `az`, `azd` and Python 3.11+ for the repo; Python **3.10 to 3.13** in a separate `.venv-js` for `fabric-jumpstart`.
   - Bicep CLI.
   - Docker is not needed (ACR Tasks builds the image).
   - Sign in with `az login` / `azd auth login` as the operator and run `az account set -s <subscription-id>`.

## 4. Repository layout to create

Legend: **C** = copy from `pdm-fabric-foundry` and rename `pdmops` to `telcoops` / `PDMOPS_` to `TELCO_`; **A** = copy, then adapt; **N** = new.

```
azure.yaml                                   A  name telecom-fabric-foundry, same hooks
.env.example, .gitignore, requirements.txt   A  (add azure-ai-evaluation, azure-search-documents to requirements)
README.md                                    N  status table, kept up to date as steps finish
docs/PLAN.md                                 this file
infra/
  main.bicep, main.bicepparam                A  see P0.2
  wave0-byo-resources.bicep                  A  Search (semantic on), agent Storage, Cosmos, + KB storage
  wave2-fabric-privatelink.bicep(+param)     C  last, optional
  wave3-bot.bicep(+param)                    A  names/display name
  lockdown.bicep                             N  P6.2: public access off for Search + KB storage
  hooks/preprovision.ps1|.sh                 A  defaults for the new names; keep the @() fix
  hooks/postprovision.ps1|.sh                A  only capture_state + 01_jumpstart (see P0.4)
  modules/ network, fabric-capacity, keyvault, monitoring, rbac,
           private-endpoint, aci-jumpbox, aci-foundry-rbac, foundry.bicep   C/A
  modules/foundry-vendored/                  C  verbatim, do not edit
  modules/kb-rbac.bicep                      N  role assignments for Foundry IQ (P0.2)
  modules/embedding-deployment.bicep         N  text-embedding-3-large on the Foundry account
artifacts/
  seed/towers.csv                            EXISTS  single source of truth for sites (P0.5)
  kb-docs/*.md                               EXISTS  the six Foundry IQ documents (P3.1), reused on every deployment
  emulator/original/                         N  captured Jumpstart notebook (P0.6), for diffing
  emulator/patch_cells.py                    N  code cells inserted into the notebook (P0.7)
  kql/010_alter_cdr_raw.kql ... 040_functions.kql   N  (P0.8)
  ops-agent/OperationsAgent.json             N  captured from the portal (P1)
  power-automate/ops-alert-flow.zip          N  exported flow (P1)
  data-agent/instructions.md, examples.json  N  (P2)
src/telcoops/
  common/ auth, config, fabric_client, kusto_client, logging_setup,
          foundry_network, graph_client      C
  common/search_network.py                   N  open/close public access on Search + KB storage
  setup/01_jumpstart.py                      N  workspace + capacity + Jumpstart install + state capture
  setup/02_patch_emulator.py                 N  capture / patch / restore the emulator notebook
  setup/03_kql_schema.py                     C  (drop the --target switch; one target)
  setup/04_ops_agent.py                      A  from 06_ops_agent.py (capture/update/apply)
  setup/05_data_agent.py                     N  create + publish the Fabric Data Agent
  knowledge/upload_docs.py, create_kb.py, create_knowledge_agent.py   N
  foundry/_rest.py, create_toolbox.py, deploy_hosted_agent.py, publish_teams.py         A
  foundry/hosted_agent/ main.py, tools.py, Dockerfile, requirements.txt                 A/N
  validate/ smoke_kql.py, smoke_spike.py, smoke_kb.py, e2e_incident.py                  N
  eval/ dataset.jsonl, run_evals.py          N
scripts/ capture_state.py, foundry_access.py, search_access.py, run_spike.py,
         emulator_status.py, ask_agent.py, capacity.py   A/N
         build_site_inventory.py, check_kb_docs.py   EXISTS  (P3.1)
tests/   offline tests, no Azure (section 8)
```

`state.json` (git-ignored) connects Bicep outputs to the IDs that Python creates. Sections: `wave0`, `wave1`, `workspace`, `eventhouse`, `emulator`, `kql_schema`, `ops_agent`, `data_agent`, `kb`, `knowledge_agent`, `toolbox`, `foundry_agent`, `wave3`, `teams_publish`, `lockdown`. Every script reads its inputs from `state.json`, writes its outputs back, and is safe to re-run.

## 5. Phases and steps

Each step lists **Do**, then **Verify**, then **Gotchas**. Don't start a step until the previous step's verification passes.

---

### Phase 0: Platform and data (about 1 day)

#### P0.1 Scaffold the repo
- **Do:** create the layout in section 4. Copy the C/A files and rename identifiers. Copy `modules/foundry-vendored/` verbatim, together with its `VENDORED_FROM.md`.
- **Verify:** `az bicep build --file infra/main.bicep --stdout > $null`, and `python -m pytest tests -q` (the copied tests for common code pass).

#### P0.2 Bicep
- **Wave 0, `wave0-byo-resources.bicep`** (resource-group scope, deployment name `wave0-byo-deployment`):
  - AI Search `standard`, `publicNetworkAccess: enabled`, AAD auth (`aadOrApiKey`, `http401WithBearerChallenge`), **`semanticSearch: 'standard'`** (Foundry IQ knowledge bases use agentic retrieval, which needs the semantic ranker; check this against current Foundry IQ docs), and a system-assigned identity.
  - Agent Storage and Cosmos (serverless), as in PdM. These are the BYO trio for the Foundry standard agent setup.
  - **KB storage account** `stkb<unique>`, separate from the agent storage:
    - `allowSharedKeyAccess: false`, `publicNetworkAccess: Enabled` for now;
    - `networkAcls.bypass: AzureServices`, plus a `resourceAccessRules` entry for the Search service;
    - a blob container `kb-docs`.
  - Outputs: the three BYO IDs, plus `kbStorageAccountId`, `kbStorageAccountName` and `searchServiceName`.
- **Wave 1, `main.bicep`** (subscription scope, through `azd provision`). Same modules as PdM:
  - VNet `vnet-telco` (`snet-pe`, `snet-agent` delegated to `Microsoft.App/environments`, `snet-container` delegated to ACI);
  - F8 capacity `telcof8`;
  - Key Vault (private endpoint);
  - Log Analytics and App Insights;
  - ACI jumpbox (kept for data-plane work after lock-down only);
  - the vendored Foundry account and project, with `publicNetworkAccessAtCreation = true` and `enableContainerRegistry = true`;
  - `gpt-4.1` (GlobalStandard, 30).

  Additions:
  - `modules/embedding-deployment.bicep`: `text-embedding-3-large` on the Foundry account.
  - `modules/kb-rbac.bicep`:
    - Search MI → **Storage Blob Data Reader** on the KB storage.
    - Search MI → **Cognitive Services OpenAI User** on the Foundry account (vectoriser/embedding calls).
    - Foundry project MI → **Search Index Data Reader** + **Search Service Contributor** on Search.
    - Operator → **Search Service Contributor**, **Search Index Data Contributor** and **Storage Blob Data Contributor** (so the operator can upload documents and create the KB from the local machine).
    - Operator → **Foundry User** (or Project Manager) on the account.
  - Keep `fabricCapacityLocation` as a parameter, but set it to `swedencentral` like everything else.
- **`main.bicepparam`:** `location = 'swedencentral'`, `fabricCapacityLocation = 'swedencentral'`, and the names from section 2, read with `readEnvironmentVariable` as in PdM.
- **Verify:** `az bicep build` passes for every file. `az deployment sub what-if` against the azd parameters shows only creates.
- **Gotchas (from PdM):**
  - The vendored module's `existingDnsZones` must contain `privatelink.azurecr.io` even when ACR is off, and `dnsZoneNames` must be overridden (see PdM `modules/foundry.bicep`).
  - The real account and project names have a 4-character suffix (`telco-agents` becomes `telco-agentsXXXX`). `foundry.bicep` re-derives them; never hard-code them.
  - The Key Vault name has a 24-character limit.

#### P0.3 Deploy Azure (Waves 0 and 1)
- **Do:**
  ```powershell
  az account set -s <subscription-id>
  az group create -n rg-telco-fabric-foundry -l swedencentral
  az deployment group create -g rg-telco-fabric-foundry -n wave0-byo-deployment -f infra/wave0-byo-resources.bicep
  azd env new telco-dev ; azd env set AZURE_SUBSCRIPTION_ID <subscription-id> ; azd env set AZURE_LOCATION swedencentral
  azd provision          # about 20 minutes. If Graph is challenged, set FABRIC_ADMIN_UPN and OPERATOR_OBJECT_ID yourself
  ```
  Then run the vendored `createCapHost.sh` for the capability host, as in PdM. `scripts/capture_state.py` copies the azd outputs into `state.json['wave1']`.
- **Verify:** 
  - `az resource list -g rg-telco-fabric-foundry -o table` shows every resource.
  - The capacity is `Active`.
  - The Foundry account is `publicNetworkAccess: Enabled`, and the Search and KB storage accounts are both public.
- **Gotchas:**
  - Git Bash needs `MSYS_NO_PATHCONV=1` for arguments that start with `/subscriptions/`.
  - `az ad signed-in-user show` can hit a Conditional Access (CAE) challenge. The object ID is the `oid` claim of the ARM token.
  - PowerShell hooks must check `$LASTEXITCODE` after every native command.

#### P0.4 Workspace and Jumpstart install (`setup/01_jumpstart.py`)
- **Do:**
  - Create the workspace `telco-cdr-jumpstart` and assign it to `telcof8`. Look up the Fabric capacity GUID by display name; the ARM ID won't work.
  - Install the Jumpstart **unchanged** in `.venv-js`:
    ```powershell
    py -3.13 -m venv .venv-js ; .venv-js\Scripts\python -m pip install fabric-jumpstart
    $env:FABRIC_JUMPSTART_TOKEN_CREDENTIAL = "AzureCliCredential"
    .venv-js\Scripts\python -c "import fabric_jumpstart as j; j.install('telecom-call-data-records', workspace_id='<id>', unattended=True)"
    ```
  - List the workspace items and write their IDs to `state.json`: notebook, Eventstream, Eventhouse `DemosEH` (with `queryServiceUri`), KQL DB `TelecomCallDataRecords` and the dashboard.
- **Verify:** all five items exist. Run the emulator notebook **as its own job** and confirm that `cdr_raw | count` grows (`scripts/emulator_status.py`).
- **Gotchas:**
  - Check that the capacity isn't paused before Fabric work. It was found suspended once in PdM.
  - If the notebook job fails under the job API, try the run parameter `_inlineInstallationEnabled=true`; the PdM Jumpstart needed it.
  - The installer clones the source repo from GitHub at run time.

#### P0.5 Tower seed data (`artifacts/seed/towers.csv`). **Already created.**
- **Done:** 40 towers (Gauteng 14, Western Cape 6, KwaZulu-Natal 6, Eastern Cape 3, Free State 2, Limpopo 2, Mpumalanga 3, North West 2, Northern Cape 2). Columns: `tower_id, site_name, region, city, lat, lon, vendor, technology, backhaul, backup_power, backup_hours, field_team, traffic_weight, enterprise_customers`. Gauteng has about 38% of the relative `traffic_weight`. Use `traffic_weight` as the emulator's tower sampling weight. The original design notes follow:
  - Columns: `tower_id` (e.g. `GP-001`), `region` (`Gauteng`, `Western Cape`, `KwaZulu-Natal`, `Eastern Cape`, `Free State`, `Limpopo`, `Mpumalanga`, `North West`, `Northern Cape`), `lat`, `lon`, `vendor` (Ericsson/Nokia/Huawei), `technology` (4G/5G), `backup_power` (battery/generator/none, hours), `field_team`, `field_contact` (synthetic), `enterprise_customers` (`;`-separated, synthetic).
  - Weight Gauteng to about 35% of towers **and** traffic. The Operations Agent rule needs **at least 50 calls per region in 5 minutes**, so check the emulator's event rate in P0.6 and make sure Gauteng gets at least 10 calls a minute.
- **Rule:** the emulator, the KQL `towers` table and the KB site inventory are all generated from this one file. Never type tower IDs by hand anywhere else.

#### P0.6 Capture the emulator and schema (`setup/02_patch_emulator.py --capture`)
- **Do:**
  - Save the notebook to `artifacts/emulator/original/`: `getDefinition` with `format=ipynb`, decoded.
  - Save `.show table cdr_raw cslschema`, `.show table cdr_raw ingestion mappings`, and the Eventstream definition (to see the CustomEndpoint and the destination's mapping mode).
  - Commit these files so the patch can be reviewed as a diff.
- **Verify:** write down the real answers to:
  - the column names;
  - how the notebook authenticates to the Eventstream (connection string or Entra);
  - the event rate;
  - where the status probabilities are set.

  Update this plan if anything differs from the brief.

#### P0.7 Patch the emulator (`setup/02_patch_emulator.py --apply`)
- **Do:** change a copy of the definition and push it with `updateDefinition`. Keep `--restore` to push the original back.
  - **Parameters cell** (tagged `parameters`, so job runs can override it): `spike_region=""`, `spike_drop_rate=0.25`, `spike_start_offset_min=0`, `spike_minutes=10`, `run_minutes=60`.
  - **Tower selection:** load the tower list. Embed `towers.csv` as a Python literal in the cell, so the notebook has no file dependency. Choose a tower with weights per region and emit `tower_id`, `region`, and `lat`/`lon` with a small jitter **instead of** random coordinates. Keep every original field so the dashboard keeps working.
  - **Spike mode:** while `now` is inside `[start+offset, start+offset+spike_minutes)` and `region == spike_region`, draw status from `Dropped=spike_drop_rate` and `Failed=0.08`, with the rest Completed. Otherwise keep the original 85/8/7. Lower `call_quality` during the spike too, so the trends look consistent.
  - **Bounded run:** stop after `run_minutes` (cost control).
  - Put the generator logic in pure functions inside `artifacts/emulator/patch_cells.py`, so tests can import them as well as inject them into the notebook.
- **Add `scripts/run_spike.py --region Gauteng --minutes 10 [--offset 5] [--run-minutes 30]`**, which starts a notebook job with these parameters.
- **Verify:** offline: sampling 10k events from the generator gives 85/8/7 ± 1.5% normally, 25% Dropped ± 2% for the spike region inside the window, and an unchanged mix for other regions. Online: covered in P0.9.

#### P0.8 KQL layer (`setup/03_kql_schema.py`, files under `artifacts/kql/`)
- `010_alter_cdr_raw.kql`:
  - `.alter-merge table cdr_raw (tower_id:string, region:string)`.
  - **If** the Eventstream destination uses a named JSON ingestion mapping, also run `.alter-merge table cdr_raw ingestion json mapping '<name>' '[...tower_id, region...]'`. With DirectIngestion and no mapping update, the new fields arrive empty. You may need to update the Eventstream destination's schema in the Eventstream editor instead; record whatever you had to do.
- `020_towers.kql`: `.create-merge table towers (...)` plus an ingest of `towers.csv` (the script ingests it inline). Then create `towers_latest()` as a function.
- `030_mv_drops_5m.kql`:
  ```kusto
  .create-or-alter materialized-view with (backfill=true) mv_drops_5m on table cdr_raw {
      cdr_raw
      | summarize calls=count(), completed=countif(status=="Completed"),
                  failed=countif(status=="Failed"), dropped=countif(status=="Dropped"),
                  avg_quality=avg(todouble(call_quality))
        by bin(<timestamp column>, 5m), region, tower_id
  }
  ```
  Use the real timestamp column from P0.6. `call_quality` might be categorical; if so, use `countif` per category instead of `avg`.
- `040_functions.kql`:
  - `drop_rate_by_region(window:timespan)`, which returns region, calls, dropped, drop_pct and towers_affected.
  - `worst_towers(region:string, window:timespan, n:int)`.
  - `region_alert_candidates(window:timespan=5m, min_calls:long=50, threshold:real=0.15)`: exactly the Operations Agent rule, so the agent and the tests share one definition.
- **Gotchas (from PdM):**
  - `backfill=true` is valid only when the view is created. The applier already removes it for existing views; keep that code.
  - `latest`, `cycles` and `first` are reserved words.
  - An update policy can't reference another table while streaming ingestion is on for the source table. This layer avoids update policies; keep it that way.

#### P0.9 Phase 0 verification (`validate/smoke_kql.py`, `validate/smoke_spike.py`)
- The newest 1,000 rows in `cdr_raw` all have a non-null `tower_id` and `region`, and every tower ID is in `towers`.
- `mv_drops_5m` has rows for the last 15 minutes.
- During a run started with `run_spike.py --region Gauteng`, `drop_rate_by_region(5m)` shows Gauteng between 20% and 30% with at least 50 calls, other regions below 10%, and `region_alert_candidates()` returns Gauteng only.
- The Jumpstart dashboard still renders.

---

### Phase 1: Operations Agent and email (about 1 day)

#### P1.1 Create the agent
- **Do (portal first, then capture, which is the PdM pattern):**
  1. In workspace `telco-cdr-jumpstart`, create the Operations Agent `Telco Drop Monitor`. Data source: the KQL DB `TelecomCallDataRecords`.
  2. **Goal:** *"Raise an action when the dropped-call rate for any region exceeds 15% in the last 5 minutes with at least 50 calls."*
  3. **Instructions:** "Use `region_alert_candidates()` or `mv_drops_5m`. Report region, drop %, call count, number of affected towers (towers with drop rate > 15%), and the 5-minute window start and end in UTC. One action per region per window."
  4. Generate Playbook, then review the generated KQL under Query Insights. It must match `region_alert_candidates()`.
- **Then:** `python src/telcoops/setup/04_ops_agent.py --capture <id>` writes `artifacts/ops-agent/OperationsAgent.json` (Fabric's definition part is `Configurations.json`). Later changes go through `--update <id>`, which merges into the live definition so the compiled playbook and `shouldRun` survive.
- **Gotchas:**
  - Must run as the operator (delegated identity). The script calls `assert_delegated_identity()`.
  - The agent queries every 5 minutes.
  - Not available in CMK-encrypted workspaces.

#### P1.2 Action, Activator and Power Automate
- **Do (portal; this can't be done through ARM or Bicep):**
  1. On the Operations Agent, add a **custom action**, `Email NOC`, with parameters `region`, `drop_pct`, `calls`, `towers_affected`, `window_start` and `window_end`. This creates or links an **Activator**.
  2. Connect a **Power Automate** flow: trigger from the Activator action, then Outlook "Send an email (V2)" to the demo distribution list. Subject: `[Telco NOC] Drop spike in {region}: {drop_pct}%`. The body has all the parameters plus the **"Investigate in Teams" deep link** from P5.1; leave a placeholder for now.
  3. Export the flow (Power Automate → Export → Package) to `artifacts/power-automate/ops-alert-flow.zip`. Write down the manual import steps in the README.
  4. Install the **Fabric Operations Agent Teams app** for the operator and approvers. Approvals arrive there.
  5. **Start** the agent.
- **Verify:**
  - Steady state for 20 minutes: **no** email.
  - `run_spike.py --region Gauteng --minutes 10`: an email arrives within about 10 minutes of the spike starting, with the correct region, a drop % between 20 and 30, and a tower count.
  - The approval prompt appears in Teams if approval is turned on.
- **Gotchas:**
  - If the Power Automate step errors, check the tenant-home-region issue from section 3 first.
  - Stop the agent when you're not demoing (it consumes capacity).

---

### Phase 2: Fabric Data Agent (about 1 day)

#### P2.1 Create and publish (`setup/05_data_agent.py`)
- **Do:** create a Data Agent item `TalkToTelecomCdr` through the Fabric REST API (fall back to the portal if the definition API rejects it, then capture). Settings:
  - **Source:** KQL DB `TelecomCallDataRecords`; tables `cdr_raw`, `towers` and `mv_drops_5m`.
  - **Instructions** (`artifacts/data-agent/instructions.md`): column meanings; `region` = South African province; use `mv_drops_5m` for rates and `cdr_raw` for single calls; drop rate = dropped/calls; always show the time window and call counts; times in UTC.
  - **Example queries** (`artifacts/data-agent/examples.json`, about 8–10 pairs; reuse the dashboard tiles' KQL from P0.6):
    - drop rate by region (last hour);
    - top-N worst towers in a region;
    - call quality trend in 5-minute bins;
    - call type breakdown;
    - failed vs dropped by technology (join `towers`);
    - towers with zero traffic (silent sites);
    - compare a region with the national average.
  - **Publish** it, and record the published ID and endpoint in `state.json['data_agent']`.
- **Verify:** in the portal, as a demo user, ask *"Top 5 towers by drop rate in Gauteng in the last hour"*. The numbers must match `worst_towers('Gauteng', 1h, 5)`.

#### P2.2 Connect the agent to Foundry (`foundry/create_toolbox.py`)
- **Do:** create the project connection `fabric-dataagent-obo` (Fabric Data Agent, **identity passthrough / user token**) and the toolbox `telco-fabric-toolbox` pointing at the published agent.
- **Grants:**
  - Demo users → workspace Viewer + DB viewer.
  - Later, the orchestrator agent identity → **Foundry User** on the project. This was the most common PdM failure.
- **Gotchas:**
  - Works only for a signed-in person (Teams or an `az login` user), never for app-only callers.
  - Replies take 25–30 seconds.
  - It sometimes answers "no data access" first and succeeds on retry, so allow one retry in the orchestrator.

---

### Phase 3: Knowledge agent on Foundry IQ (1–2 days)

#### P3.1 Knowledge documents. **Already written; reuse them on every deployment.**
The six documents are committed in `artifacts/kb-docs/`. Every deployment and redeployment uploads **these exact files**; don't regenerate or rewrite them per deployment. They describe a fictional operator, *Imvula Telecom*, and each starts with a **SYNTHETIC – DEMO DATA** banner.

| File | Doc ID | Words | Content | Demo question it answers |
|---|---|---|---|---|
| `noc-dropped-call-runbook.md` | RB-NOC-001 | about 2,100 | Alert thresholds and severities, first-10-minute triage, a table of diagnostic signatures, procedures for handover, congestion, backhaul, power and load shedding, RF and hardware, core, and planned maintenance; communication and closure rules | "What should the field team do?" |
| `site-inventory.md` | SITE-INV-001 | about 3,000 | Generated from `towers.csv`: summary per region, field team directory (synthetic contacts), customers by tower, site table per region (backhaul hubs, backup power), one profile per tower | "Which towers, who serves them, what backup?" |
| `maintenance-and-incident-log.md` | MAINT-LOG-001 | about 1,400 | **Active Gauteng microwave-to-fibre migration on GP-003, GP-007 and GP-011, every weekday 09:00–15:00 SAST (07:00–13:00 UTC), 5 Oct 2026 – 26 Mar 2027, expected tower DCR up to 30%**; GP-012 battery swap on Saturdays in Oct 2026; planned KZN and WC changes; change freezes; 10 past incidents with lessons | "Is the spike explained by planned maintenance?" |
| `kpi-definitions.md` | KPI-DEF-001 | about 1,300 | DCR = dropped ÷ all attempts (matches the KQL), CSFR, CCR, poor-quality share, silent tower; 5-minute, hourly and monthly windows with minimum samples; **demo calibration** (baseline 7%; critical > 15% with ≥ 50 calls; major > 25% or ≥ 5 towers); worked example (a 10-minute 25% spike gives about 10% hourly DCR) | "How is the drop rate defined?" |
| `enterprise-sla-contracts.md` | SLA-ENT-001 | about 1,500 | Four customers with served towers that match `towers.csv`: **Jacaranda Health Network (any-hour ≤ 9.0%, notify within 15 minutes)**, Karoo Mutual Bank (≤ 11.0%, 30 minutes), Highveld Mining Group (≤ 12.0%, 30 minutes), Coastal Freight Logistics (≤ 12.0%, 60 minutes); credits, caps, exclusions (planned work needs ≥ 72 h notice); assessment procedure with a worked Gauteng example | "Does this breach any enterprise SLA?" |
| `qos-regulatory-targets.md` | QOS-REG-001 | about 1,150 | Illustrative ICASA-style targets (clearly marked as not official) next to demo-calibrated equivalents; reporting areas and periods; the major-outage notification rule; the effect of short incidents on compliance | "Is there a regulatory impact?" |

**How the showcase question resolves.** A 10-minute 25% spike on all of Gauteng on a weekday between 07:00 and 13:00 UTC gives this answer:
- about 10% hourly DCR;
- GP-003, GP-007 and GP-011 are explained by the migration, the other Gauteng towers are not;
- Jacaranda's 9.0% any-hour limit is breached;
- Karoo, Highveld and Coastal are not breached but are owed notifications;
- the runbook steps follow from the backhaul/power/congestion signatures.

Outside 07:00–13:00 UTC on weekdays, no maintenance explains the spike. Make sure the demo spike runs inside the window if you want the "partly explained" answer.

**Dates:** the documents are written as at 16 October 2026, and the migration programme runs until 26 March 2027. A deployment after that date needs updated dates in `maintenance-and-incident-log.md` (and the SLA-ENT-001 section 7 notice status). Change nothing else.

**Tools (already in the repo):**
- `python scripts/build_site_inventory.py <repo root>` regenerates `site-inventory.md` from `towers.csv`. Run it only after you change `towers.csv`.
- `python scripts/check_kb_docs.py <repo root>` checks the word counts (≥ 1,000 each), the SYNTHETIC banner, that every tower ID exists in `towers.csv`, and that the SLA tower lists match the CSV.

- **Verify:** `check_kb_docs.py` reports no unknown IDs, all four customers OK, and every document at 1,000 words or more. Move these checks into `tests/test_kb_docs.py` when the test suite is created.

#### P3.2 Upload the documents (`knowledge/upload_docs.py`)
- Upload `artifacts/kb-docs/*.md` to `kb-docs` on the KB storage account with an Entra token (operator role from P0.2). No account keys.
- Overwrite blobs with the same name, so a redeploy is idempotent. Delete blobs that are no longer in the folder, so the KB never holds stale documents.
- Set blob metadata `doc_id` (for example `RB-NOC-001`) and `synthetic=true`.

#### P3.3 Create the knowledge source and KB (`knowledge/create_kb.py`)
- **Do (through the Search / Foundry IQ REST API; pin the API version you use in code and record it in the README):**
  1. A knowledge source of type Azure Blob over `kb-docs`, with a managed-identity connection, chunking and vectorisation through `text-embedding-3-large` on the Foundry account.
  2. A knowledge base `telco-kb` over that source, using `gpt-4.1` for query planning and answer synthesis, with citations on.
  3. Connect the KB to the Foundry project. Foundry IQ shows it as an MCP endpoint, and agents attach it as an MCP tool.
  4. Poll until ingestion and indexing finish, then record the IDs and the MCP endpoint in `state.json['kb']`.
- **Gotchas:**
  - Search must still be **public** here; that's the decision in section 2.
  - The Search managed identity needs Storage Blob Data Reader and Cognitive Services OpenAI User, both from `kb-rbac.bicep`.
  - Semantic ranker must be on.

#### P3.4 Knowledge agent (`knowledge/create_knowledge_agent.py`)
- **Do:** create a Foundry **prompt agent**, `telco-knowledge` (`gpt-4.1`), with the `telco-kb` MCP tool only. Instructions:
  - Answer **only** from the knowledge base.
  - Always cite the document and section.
  - If the answer isn't in the KB, say "Not in the knowledge base".
  - Never invent tower IDs, SLA numbers or contacts.
  - When given a list of tower IDs, return the matching inventory, maintenance and SLA facts for each.
- **Verify (`validate/smoke_kb.py`):** five questions with known answers, each needing the correct fact **and** a citation:
  - the backup power at a named tower;
  - the SLA threshold for a named customer;
  - the runbook steps for backhaul failure;
  - the definition of drop call rate;
  - one question whose answer isn't in the KB (expect a refusal).

---

### Phase 4: Orchestrator hosted agent and Teams (1–2 days)

#### P4.1 The agent (`foundry/hosted_agent/`)
- **Framework:** Microsoft Agent Framework hosted agent, as in PdM `hosted_agent/main.py` (same Dockerfile and base image approach).
- **Tools:**

  | Tool | Purpose | Implementation |
  |---|---|---|
  | `telco-fabric-toolbox` (Fabric Data Agent) | Open-ended "what's happening" questions | Toolbox from P2.2, user token |
  | `ask_knowledge(question, tower_ids?)` | Procedures, SLAs, site details, maintenance | Calls the `telco-knowledge` agent through the project Responses API and returns the answer with citations. (Alternative if agent-to-agent calls misbehave: attach the KB MCP tool directly.) |
  | `region_drop_rate(region, window)` | Exact numbers for one region | `drop_rate_by_region()`, in code |
  | `affected_towers(region, window, threshold=0.15)` | Tower list for an incident | `mv_drops_5m` + `towers` join, in code |
  | `sla_check(customers_or_region, observed_rate, window)` | Breach yes/no, with the margin | Takes thresholds from `ask_knowledge` and compares **in code** |

  Follow the PdM rule: **compute the numbers in code and let the model narrate them.** All KQL runs through `execute_query` (never `execute`), with a row cap and a rejection for any statement that starts with `.` or calls an external-data function or plugin. The agent identity has database **viewer** only.
- **Routing instructions:**
  - Numbers and trends → data tools.
  - Procedures, SLAs, site and maintenance questions → `ask_knowledge`.
  - **Incident questions → both, in this order:** `affected_towers`, then `ask_knowledge` with those tower IDs (maintenance, inventory, SLA), then `sla_check`, then a combined answer that keeps the measured data separate from the documented guidance, with citations.
  - Never state the current time or the state of the data without querying it.
  - Answer in one turn; never promise to follow up later.
- **Showcase question:** *"Drops spiked in Gauteng in the last hour. Which towers are affected, is there planned maintenance, does this breach any enterprise SLA, and what should the field team do?"*
- **Optional:** `escalate_email(to_role, summary)` through a Logic App (Bicep, HTTP trigger with managed-identity auth). Show the draft and require "confirm" in the same conversation before sending. Proactive alerting stays with the Operations Agent.

#### P4.2 Deploy (`foundry/deploy_hosted_agent.py`, adapted from PdM)
- Build with ACR Tasks, create a version, and route traffic.
- Grant the agent identity workspace Viewer, Eventhouse DB viewer (by **app ID**: `aadapp=<appId>;<tenantId>`) and Foundry User on the project.
- **Keep the PdM endpoint guard:** `update_details()` rewrites the endpoint with only the `responses` protocol and **silently drops the Activity Protocol route Teams needs**. The script must capture the endpoint config and restore it after every deploy. Copy the regression test from PdM `tests/test_agent_guardrails.py`.
- **Verify:** `python scripts/ask_agent.py "<showcase question>"` while a Gauteng spike is running. The answer names Gauteng, lists the towers that `affected_towers` returned, mentions the planned maintenance (if the P3.1 window overlaps), gives an SLA verdict with numbers, and gives runbook steps with citations.

#### P4.3 Teams (Wave 3)
- **Do:**
  ```powershell
  az deployment group create -g rg-telco-fabric-foundry -n wave3-bot -f infra/wave3-bot.bicep --parameters botName=bot-telco-orchestrator "botDisplayName=Telco NOC Copilot" msaAppId=<agent clientId from state.json> "activityEndpoint=<activityEndpoint from state.json>"
  python src/telcoops/foundry/publish_teams.py --scope Shared --skip-network-toggle
  ```
  - `Shared` scope with `BotServiceRbac` needs no admin approval; demo users need an Azure role on the project.
  - `Tenant` scope needs Microsoft 365 admin approval.
  - The bot keeps `publicNetworkAccess: Enabled` (setting it to Disabled breaks the channel), and the Teams channel sets `acceptedTerms: true` explicitly.
- **Verify:** a demo user opens `https://teams.microsoft.com/l/app/<teamsAppId>` and asks the showcase question. Bot Service `RequestsTraffic` shows 2xx. The app can take up to an hour to show under "Your agents"; the direct link works sooner.

---

### Phase 5: Close the loop and evaluate (about 1 day, optional)

#### P5.1 Deep link from the alert email
- Build the link in the Power Automate flow: open the Teams app chat with a pre-filled message, e.g. `Investigate {region} {window_start}–{window_end} UTC`. Use the Teams deep-link format for app chats (`https://teams.microsoft.com/l/chat/0/0?users=28:<botAppId>&message=<urlencoded>`) and test which format the client honours.
- **Verify:** clicking the link in the spike email opens the Teams chat with the message filled in, and sending it gives the incident answer.

#### P5.2 Evaluations (`eval/run_evals.py`, `azure-ai-evaluation`)
- `eval/dataset.jsonl` holds about 30 questions, each labelled with the expected route (`data`, `knowledge` or `both`), the expected facts, and for numeric questions a reference KQL.
- Metrics and pass bars to start with:
  - **routing accuracy** (tool calls in the trace) ≥ 90%;
  - **numeric correctness** (agent numbers within ±0.5 pp of the reference KQL) ≥ 95%;
  - **groundedness and citation presence** on KB answers ≥ 4/5 and 100%;
  - **refusal** on out-of-KB questions 100%.
- Write the results to `eval/results/<date>.json` and a summary table in the README.

#### P5.3 End-to-end test (`validate/e2e_incident.py`)
- Start a spike, wait for `mv_drops_5m`, ask the orchestrator the showcase question, and assert the region, the tower set (equal to `affected_towers`), the maintenance mention, the SLA verdict and at least one citation. Optionally check that the alert email arrived, through Graph mail search as the operator.

---

### Phase 6: Lock-down (last)

#### P6.1 Pre-flight
- Every step above has passed verification, and the agent's Teams route is present (`foundry_access.py` checks it).
- Any further Fabric item edits must be done before P6.3.

#### P6.2 Foundry, Search and KB storage to private
- `python scripts/foundry_access.py close` refuses if the Activity Protocol route is missing.
- `python scripts/search_access.py close` sets Search `publicNetworkAccess: disabled`. Deploy `infra/lockdown.bicep` to set KB storage `publicNetworkAccess: Disabled`; it keeps the `resourceAccessRules` for Search, plus a Search **shared private link** to the KB blob if the indexer needs it after lock-down.
- **Verify:**
  - From the local machine, direct calls get `403`.
  - A Teams message still works (Bot Service RequestsTraffic 2xx).
  - The orchestrator still answers a KB question: the Foundry agent subnet reaches Search through its private endpoint.
  - Re-indexing still works (start an indexer run with the jumpbox or a temporary open).
- After lock-down, Foundry and Search data-plane work needs `foundry_access.py open` / `search_access.py open` (and close again afterwards), or the jumpbox.

#### P6.3 Fabric workspace private link (optional, very last)
- Enable the tenant settings (Azure Private Link, workspace-level inbound rules), deploy `infra/wave2-fabric-privatelink.bicep`, then apply the workspace inbound policy.
- **Warning:** after this, Fabric items can no longer be built from the local machine. Only do it once nothing else needs changing. DNS for a new capacity can take up to 24 hours.

## 6. Timeline and gates

| Phase | Effort | Gate |
|---|---|---|
| 0 Platform and data | about 1 day | P0.9 passes during a spike |
| 1 Operations Agent | about 1 day | Spike sends an email, steady state doesn't |
| 2 Data Agent | about 1 day | Data Agent numbers match the KQL functions |
| 3 Knowledge | 1–2 days | `smoke_kb.py` 5/5 |
| 4 Orchestrator and Teams | 1–2 days | Showcase question answered correctly in Teams |
| 5 Loop and evals | about 1 day | Eval bars met |
| 6 Lock-down | ½ day | Teams + KB still work while private |

## 7. Cost controls

- The emulator always runs as a bounded job (`run_minutes`). Cancel leftover jobs with `scripts/emulator_status.py --cancel`.
- Close the 1-second-refresh Jumpstart dashboard when you're not demoing.
- Stop the Operations Agent between demos.
- `scripts/capacity.py pause|resume` for `telcof8`. Pausing stops Fabric billing, but the Operations Agent, Data Agent and Eventstream are unavailable while it's paused.
- Search Standard and the jumpbox bill all the time. Remove the jumpbox if P6 is never deployed.
- Teardown: delete the Fabric workspace (REST), then `azd down --purge`, then delete the Wave 0 resources and the resource group.

## 8. Offline tests (`tests/`, no Azure needed)

- `test_emulator.py`: status distributions in and out of the spike window; every emitted `tower_id` is in `towers.csv`; region weights hold.
- `test_kql_artifacts.py`: statement parsing; `backfill` removed for existing views; no reserved-word column names; functions referenced by the Operations Agent instructions exist in `040_functions.kql`.
- `test_kb_docs.py`: port of `scripts/check_kb_docs.py`. Each doc has at least 1,000 words, the SYNTHETIC header, and only known tower IDs; the SLA tower lists match `towers.csv`; the migration towers (GP-003, GP-007, GP-011) are in Gauteng and microwave-backhauled; `site-inventory.md` is identical to a fresh `build_site_inventory.py` run.
- `test_tools.py`: the KQL guard rejects `.` commands and plugins; `sla_check` maths and margin; `affected_towers` threshold logic on fixtures.
- `test_agent_guardrails.py`: (from PdM) the endpoint restore keeps the Activity Protocol route.

## 9. Lessons carried over from `pdm-fabric-foundry` (don't relearn these)

1. Create Foundry **public**, and close it only at the end. Toggling an account that was created Disabled can leave a fronting layer returning 403 for 30+ minutes, and agent routes don't register while the account is private.
2. `update_details()` drops the Teams Activity Protocol route. Always restore it, and `foundry_access.py close` must check it.
3. Fabric capacity `assignToCapacity` needs the **Fabric capacity GUID** (`GET /v1/capacities` by display name), not the ARM ID. It returns 202 with no `Location` header; treat that as complete.
4. The Operations Agent definition part is `Configurations.json`. Updates must **merge** into the live definition, or the playbook and `shouldRun` get wiped.
5. KQL: `backfill` only on first view creation; `latest`/`cycles`/`first` are reserved; the Kusto SDK `servertimeout` needs a `timedelta`.
6. The Data Agent through a toolbox needs the agent identity to hold **Foundry User** on the project. It works for user tokens only, takes 25–30 seconds, and may need a retry.
7. Models misjudge numbers, so put baselines, rates and thresholds in tested code. Never let instructions assert the state of the data, and forbid promises to answer later.
8. Windows and Git Bash: `MSYS_NO_PATHCONV=1`; resolve `az` with `shutil.which` (the `az.cmd` shim); `azd env get-value` prints errors to stdout with exit code 0; PowerShell hooks must check `$LASTEXITCODE`; use `@()` around `Get-Content` results.
9. Graph can return a CAE challenge after `az login`. Read the object ID from the ARM token's `oid` claim, and verify a delegated identity from the Fabric token's claims.
10. On the jumpbox, `DefaultAzureCredential` picks the container's managed identity. Set `TELCO_FORCE_CLI_CREDENTIAL=1` for steps that need a human token (Teams publish, Operations Agent).
11. The Bot Service must keep `publicNetworkAccess: Enabled`. Set `acceptedTerms: true` on the Teams channel explicitly.

## 10. Open items to resolve while building

- [ ] Tenant home region (section 3.1). If it isn't in Europe, test the Power Automate path first.
- [ ] Real `cdr_raw` schema, emulator auth and event rate (P0.6). Update P0.5, P0.7 and P0.8 to match.
- [ ] Whether DirectIngestion needs an ingestion-mapping change or an Eventstream schema change for the new columns (P0.8).
- [ ] The Foundry IQ REST API version and request shapes for a Blob knowledge source and a KB at build time (P3.3). Pin them in code.
- [ ] Agent-to-agent call (`ask_knowledge` → `telco-knowledge`) versus direct KB MCP on the orchestrator. Choose based on P4.2 latency and reliability.
- [ ] The Teams deep-link format that pre-fills a message to an app chat (P5.1).
