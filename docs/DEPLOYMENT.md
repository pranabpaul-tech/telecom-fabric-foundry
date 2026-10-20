# Deployment record

What was actually deployed from `docs/PLAN.md`, where it differs from the plan, and what is still manual.
Subscription `<subscription-id>`, resource group `rg-telco-fabric-foundry`, deployed 17-19 October 2026.

## Deployed

| Layer | What | Name / id |
|---|---|---|
| Azure, Wave 0 | AI Search (Standard, semantic ranker), agent Storage, Cosmos DB (serverless), KB Storage | `srch-telco-77kjeqakj77i6` (uksouth), `sttelco…`, `cosmos-telco-…`, `stkbtelco…` (swedencentral) |
| Azure, Wave 1 | VNet, F8 Fabric capacity, Key Vault, Log Analytics, App Insights, ACR, ACI jumpbox, Foundry account + project (VNet-injected), `gpt-4.1`, `text-embedding-3-large`, private endpoints, role assignments | `vnet-telcoops`, `telcof8`, `telcoai77kj` / `telco-agents77kj` (47 resources in the group) |
| Fabric | Workspace with the Jumpstart installed unchanged | `telco-cdr-jumpstart` (`f501c201-618f-4bbc-b197-2cd98b05ba1e`) |
| Fabric data | Emulator patched (tower_id, region, spike mode); `cdr_raw` + 12-column mapping; `towers` (40 rows); `mv_drops_5m`; `drop_rate_by_region`, `worst_towers`, `region_alert_candidates`, `silent_towers` | KQL database `TelecomCallDataRecords` |
| Fabric agents | Operations Agent **`Telco Drop Monitor`** (created, not started); Data Agent **`TalkToTelecomCdr`** (created and published, 12 verified example queries) | `2a5e9baf-…`, `8cf487f8-…` |
| Foundry IQ | File knowledge source `telco-docs-ks` + knowledge base `telco-kb` (6 documents) | on `srch-telco-77kjeqakj77i6` |
| Foundry | Toolbox `telco-fabric-toolbox` (connection `fabric-dataagent-obo`, user token); hosted agent `telco-orchestrator` **version 3** | |
| Teams | Bot Service `bot-telco-orchestrator`; published at Shared scope | https://teams.microsoft.com/l/app/a806c434-04b6-4cfc-94eb-08f26514f9eb |

## Verified

- Emulator spike: Gauteng drop rate 5-7% at baseline, 26.5% in the worst 5-minute bin; `region_alert_candidates()` fires for Gauteng only during the spike.
- Knowledge base: known-answer questions return the right facts with document IDs (Karoo limit 11.0% / 30 minutes, GP-012 battery 2 h, GP-007 in the migration window, GP-008 not).
- Orchestrator, showcase question with fresh data (Monday 08:43 UTC, inside the weekday maintenance window): 13 affected towers, only the migration towers explained by maintenance, SLA verdicts against the limits fetched from the knowledge base, runbook actions with citations. With stale data (Sunday), it says so in its first sentence.
- 29 offline tests pass.

## Deviations from the plan, and why

1. **Search is in UK South, everything else in Sweden Central.** Sweden Central returned `InsufficientResourcesAvailable` for AI Search in this subscription. The Foundry agent setup allows Search in another region.
2. **The knowledge base uses a File knowledge source, not Blob.** The subscription's governance policy `StorageAccount_PublicNetwork_Modify` (MCAPSGovDeployPolicies) forces every storage account to public access Disabled, so documents could not be uploaded from the operator's machine. A File knowledge source uploads straight into Search. The `kb-docs` container in `stkbtelco…` is therefore unused and can be deleted.
3. **The orchestrator calls the knowledge base's retrieve endpoint itself** (`hosted_agent/kb_client.py`, API `2026-08-01-preview`) instead of `AzureAISearchContextProvider`, whose SDK API version rejects the `file` knowledge-source kind.
4. **Names:** the VNet is `vnet-telcoops` and the jumpbox `ci-telcoops-jump` (a rename-order slip), and the Key Vault is `kv-pdm-…`. Cosmetic.
5. **Wave 2 (Fabric private link) and the Foundry/Search lock-down are not applied** (see below).

## Things that will catch you out

- **The F8 capacity gets paused by someone else.** `telcof8` was suspended at about 00:37 UTC on both nights by a principal outside this project (it does not resolve in the tenant). While paused, the Eventhouse hostname does not resolve and every Fabric step fails. Check with `az resource show -g rg-telco-fabric-foundry -n telcof8 --resource-type Microsoft.Fabric/capacities --query properties.state`, and resume with `az rest --method post --url https://management.azure.com/subscriptions/<sub>/resourceGroups/rg-telco-fabric-foundry/providers/Microsoft.Fabric/capacities/telcof8/resume?api-version=2023-11-01`.
- **While the capacity is Active it bills.** Pause it when you are not demoing (same URL with `/suspend`).
- **`Failed to invoke the Azure CLI`** from azure-identity is a transient token hiccup. `deploy_hosted_agent.py --resume-version N` finishes a deploy whose version already exists.
- **`Storage operation exceeded its 45-second deadline`** on `create_version_from_code` or on the first agent call is a transient platform timeout; retry.
- The emulator runs only as a bounded job: `python scripts/run_spike.py --region Gauteng --offset 4 --minutes 10 --run-minutes 25`. The agent reports stale data rather than a false "now".

## Still manual or not done

1. **Operations Agent, in the Fabric portal** (not scriptable): Generate Playbook, add the custom action (`region`, `drop_pct`, `calls`, `towers_affected`, `window_start`, `window_end`), connect an Activator and a Power Automate flow that sends the Outlook email, install the Fabric Operations Agent Teams app, then **Start**. Its definition is in `artifacts/ops-agent/OperationsAgent.json` and was created with `shouldRun: false`.
2. **Try the agent in Teams as a person.** The Teams route is published and the Activity Protocol route is preserved, but nobody has sent a message through Teams yet.
3. **Lock-down (last):** `python scripts/foundry_access.py close` (refuses if the Teams route is missing), then disable public access on Search. Do this only after step 2, because afterwards the local scripts need `foundry_access.py open`.
4. Optional: Wave 2 Fabric private link, evaluations (`eval/`), the email deep link (plan P5.1).
