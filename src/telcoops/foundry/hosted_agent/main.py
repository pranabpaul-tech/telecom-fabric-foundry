# Copyright (c) Microsoft. All rights reserved.
"""Telco NOC Copilot: orchestrator hosted agent (Microsoft Agent Framework).

Packaged as a Foundry hosted agent (see foundry/deploy_hosted_agent.py). It routes each question:

- numbers and trends       -> deterministic KQL tools (tools.py) and the Fabric Data Agent (toolbox)
- procedures, SLAs, sites,
  maintenance, KPI/QoS     -> telco_knowledge, an in-process sub-agent grounded on the Foundry IQ
                              knowledge base (agent-to-agent calls between Foundry agents are a known
                              platform bug, so the sub-agent runs in this process via Agent.as_tool())
- incident questions       -> both, then one synthesis

Identities: KQL tools run as this agent's own identity (database viewer only). The Fabric Data Agent
toolbox forwards the CALLER's token, so it works for a person (Teams, or an az-login user) and not for
an app-only caller.

Environment: FOUNDRY_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME come from the platform;
EVENTHOUSE_QUERY_URI, EVENTHOUSE_DATABASE_NAME, AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_KNOWLEDGE_BASE_NAME and
TOOLBOX_NAME are set by deploy_hosted_agent.py. Do not set FOUNDRY_* or AGENT_* variables yourself.
"""
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework.azure import AzureAISearchContextProvider
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import FoundryToolbox, ResponsesHostServer
from azure.identity import DefaultAzureCredential
from azure.kusto.data import ClientRequestProperties, KustoClient, KustoConnectionStringBuilder
from dotenv import load_dotenv
from pydantic import Field

import tools as tl  # deterministic logic (tools.py, same directory)

load_dotenv()

_credential = DefaultAzureCredential()
_kusto: KustoClient | None = None
MAX_ROWS = 200
QUERY_TIMEOUT_SECONDS = 60


def _client() -> KustoClient:
    global _kusto
    if _kusto is None:
        kcsb = KustoConnectionStringBuilder.with_azure_token_credential(
            connection_string=os.environ["EVENTHOUSE_QUERY_URI"], credential=_credential)
        _kusto = KustoClient(kcsb)
    return _kusto


def _rows(kql: str, limit: int = MAX_ROWS) -> list[dict]:
    props = ClientRequestProperties()
    props.set_option("servertimeout", timedelta(seconds=QUERY_TIMEOUT_SECONDS))  # the SDK needs a timedelta
    # execute_query, never execute: the latter would run '.' management commands.
    table = _client().execute_query(os.environ["EVENTHOUSE_DATABASE_NAME"], kql, props).primary_results[0]
    cols = [c.column_name for c in table.columns]
    return [dict(zip(cols, r)) for r in table.rows[:limit]]


def _weekday(ts) -> str:
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).strftime("%A")
    except ValueError:
        return ""


def _with_weekdays(result: dict) -> dict:
    """Models are unreliable at day-of-week arithmetic, and planned work is tied to weekdays (MAINT-LOG-001)."""
    for key in ("window_start_utc", "window_end_utc"):
        if result.get(key):
            result[key.replace("_utc", "_weekday")] = _weekday(result[key])
    return result


@tool(approval_mode="never_require")
def data_freshness() -> str:
    """How old the newest call data is (UTC), and whether it is stale. The emulator runs only when somebody
    starts it, so call this FIRST for any 'now', 'latest' or 'last hour' question and say plainly if the data is
    stale: windows below are anchored to the newest data, not to the clock."""
    try:
        rows = _rows(tl.freshness_kql(), 1)
        return json.dumps(tl.freshness(rows[0] if rows else None), default=str)
    except Exception as exc:  # noqa: BLE001 - surfaced to the model verbatim
        return f"FRESHNESS FAILED: {exc}"


@tool(approval_mode="never_require")
def region_drop_rate(
    region: Annotated[str, Field(description="A South African province, e.g. 'Gauteng'.")],
    window_minutes: Annotated[int, Field(ge=5, le=1440, description="Window length ending at the newest 5-minute bin.")] = 60,
) -> str:
    """Dropped-call rate of one region over a window ending at the newest data: calls, dropped, failed, drop_pct
    (dropped / ALL attempts), whether it is above the 15% alert threshold, plus the window in UTC with weekdays.
    The percentage is computed in code: quote it, never recompute it. Returns INSUFFICIENT_SAMPLE below 50 calls."""
    try:
        rows = _rows(tl.region_rate_kql(region, window_minutes), 1)
        return json.dumps(_with_weekdays(tl.shape_region_rate(tl.validate_region(region), window_minutes,
                                                              rows[0] if rows else None)), default=str)
    except Exception as exc:  # noqa: BLE001
        return f"REGION_DROP_RATE FAILED: {exc}"


@tool(approval_mode="never_require")
def affected_towers(
    region: Annotated[str, Field(description="A South African province, e.g. 'Gauteng'.")],
    window_minutes: Annotated[int, Field(ge=5, le=1440, description="Window ending at the newest 5-minute bin.")] = 15,
    threshold_pct: Annotated[float, Field(gt=0, lt=100, description="A tower is affected above this drop percentage.")] = 15.0,
) -> str:
    """The towers of one region whose drop rate is above the threshold (default 15%) over the window, worst first,
    each with site, vendor, technology, backhaul (fibre or microwave), backup power, field team and the enterprise
    customers it serves. Towers with fewer than 10 calls are left out (insufficient sample). Also lists
    enterprise_customers_affected. Use it to answer 'which towers are affected'."""
    try:
        rows = _rows(tl.affected_towers_kql(region, window_minutes, threshold_pct, tl.MIN_CALLS_TOWER))
        return json.dumps(tl.shape_affected(tl.validate_region(region), window_minutes, threshold_pct, rows), default=str)
    except Exception as exc:  # noqa: BLE001
        return f"AFFECTED_TOWERS FAILED: {exc}"


@tool(approval_mode="never_require")
def customer_sla_check(
    customer: Annotated[str, Field(description="Jacaranda Health Network, Karoo Mutual Bank, Highveld Mining Group or Coastal Freight Logistics.")],
    region: Annotated[str, Field(description="A South African province.")],
    limit_pct: Annotated[float | None, Field(description="The customer's any-hour drop-rate limit in percent, taken from SLA-ENT-001 via telco_knowledge. Omit to get the measured rate only.")] = None,
    window_minutes: Annotated[int, Field(ge=5, le=1440, description="Use 60 for the contractual clock-hour view.")] = 60,
) -> str:
    """Measured drop rate on the towers that serve ONE enterprise customer inside ONE region over the window, and,
    if limit_pct is given, a verdict: BREACH is strictly above the limit; fewer than 100 calls is not assessed. The
    limit itself is NOT in the data: get it from telco_knowledge (SLA-ENT-001) first. The tool does not know about
    planned-maintenance exclusions: those come from telco_knowledge (MAINT-LOG-001, SLA-ENT-001 section 6)."""
    try:
        cust, reg = tl.validate_customer(customer), tl.validate_region(region)
        rows = _rows(tl.customer_rate_kql(cust, reg, window_minutes), 1)
        return json.dumps(_with_weekdays(tl.sla_verdict(cust, reg, window_minutes, rows[0] if rows else None, limit_pct)), default=str)
    except Exception as exc:  # noqa: BLE001
        return f"CUSTOMER_SLA_CHECK FAILED: {exc}"


@tool(approval_mode="never_require")
def query_cdr(
    kql: Annotated[str, Field(description=(
        "A read-only KQL query. Sources: mv_drops_5m (bin_start, region, tower_id, calls, completed, failed, dropped, "
        "quality_sum), towers (tower_id, site_name, region, city, vendor, technology, backhaul, backup_power, "
        "backup_hours, field_team, enterprise_customers), cdr_raw (one row per call), and the functions "
        "drop_rate_by_region(window), worst_towers(region_name, window, n), silent_towers(window). "
        f"Results are capped at {MAX_ROWS} rows: aggregate. Anchor time windows to max(bin_start), not ago()."))],
) -> str:
    """Run a read-only KQL query on the call data and return rows as JSON. Use it for follow-up detail the other
    tools do not give. Prefer region_drop_rate, affected_towers and customer_sla_check for anything they cover."""
    reason = tl.reject_reason(kql)
    if reason:
        return f"QUERY REJECTED: {reason}"
    try:
        rows = _rows(kql)
        return json.dumps({"as_of_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00"),
                           "rows": rows, "row_count": len(rows), "truncated": len(rows) >= MAX_ROWS}, default=str)
    except Exception as exc:  # noqa: BLE001
        return f"QUERY FAILED: {exc}"


KNOWLEDGE_INSTRUCTIONS = """\
You answer questions about the fictional telecom operator Imvula Telecom using ONLY the connected knowledge base:
the NOC dropped-call runbook (RB-NOC-001), tower and site inventory (SITE-INV-001), maintenance and incident log
(MAINT-LOG-001), KPI definitions (KPI-DEF-001), enterprise SLAs (SLA-ENT-001) and regulatory QoS targets (QOS-REG-001).
All of it is synthetic demo data.

Rules:
- Cite the document ID and section for every fact, for example (SLA-ENT-001, section 2).
- Keep tower IDs, customer names, dates, times and numbers exactly as written. Times in the documents are given in
  SAST and UTC; say which one you quote.
- If the answer is not in the knowledge base, say "Not in the knowledge base" and stop. Never invent a tower ID, SLA
  threshold, contact or procedure, and never use outside knowledge.
- When asked about planned maintenance for given towers and a time window, list each matching entry with its towers,
  recurring window, expected impact and customer-notice status, and state for EACH tower whether it is listed. Do not
  decide whether a measured spike is "explained"; report what the document says and let the caller compare.
- Answer once, completely. Do not promise to look anything up later.
"""

ORCHESTRATOR_INSTRUCTIONS = """\
You are the Telco NOC Copilot for network operations engineers at the fictional operator Imvula Telecom. All data is
synthetic demonstration data. You have these tools and must route each question to the right one(s):

NUMBERS AND TRENDS (what is happening):
- data_freshness: how old the newest call data is. Call it first for any 'now', 'latest', 'last hour' question.
- region_drop_rate, affected_towers, customer_sla_check: deterministic figures computed in code from the live
  call data. These are authoritative: quote their numbers, never recompute or re-judge them.
- query_cdr: read-only KQL for follow-up detail the tools above do not give.
- The Fabric Data Agent (a tool from the connected toolbox): a natural-language analyst over the same call data. Use it
  for open-ended trend questions (quality trends, call-type breakdowns, comparisons). It runs with the asker's own
  Fabric permissions: if it errors or says access is denied, say so plainly. Prefer the deterministic tools when they
  cover the question; if the data agent disagrees with them, trust them and say that they differ.

PROCEDURES, SLAs, SITES, MAINTENANCE, DEFINITIONS (what it means, what to do):
- telco_knowledge: answers only from the knowledge base, with citations. Use it for runbook steps, enterprise SLA
  limits and notification deadlines, site and field-team details, planned maintenance and past incidents, KPI
  definitions and regulatory targets. The data tools do NOT know any of this.

INCIDENT QUESTIONS (a spike, an outage, 'what should we do'): use BOTH, in this order:
1. data_freshness, then region_drop_rate for the region and affected_towers (window 15 minutes, and 60 if the spike
   may be older). Note the window in UTC WITH its weekday as returned.
2. telco_knowledge: ask for planned maintenance covering the affected tower IDs, naming the weekday and UTC time range,
   and for the runbook procedure that fits the pattern. Also ask for the SLA limit and notification deadline of every
   enterprise customer the affected towers serve.
3. customer_sla_check for each affected customer with the limit from the knowledge base, window 60.
4. Decide maintenance for each tower yourself from what the knowledge base returned: a tower is explained by planned
   work ONLY if it is listed AND the incident window falls inside the recurring window on a matching weekday AND the
   impact is within the expected level. Towers that are not listed are NOT explained, even in the same region. If a
   customer was given notice at least 72 hours ahead, say the SLA exclusion may apply, but still state the measured
   figure and the verdict without the exclusion.
5. Answer with: a one-line verdict; which towers are affected (and which are explained by maintenance); SLA position per
   enterprise customer (measured % vs limit, notification deadline); what the field team and NOC should do next,
   from the runbook. Keep measured facts clearly separate from documented guidance, and cite documents.

RULES:
- Every number must come from a tool result in this conversation. Never invent readings, tower IDs, SLA limits or
  contacts. Say exactly what a tool returned if it failed or returned nothing.
- If data is stale (data_freshness), your FIRST sentence says how old the newest data is, and you phrase results 'as of'
  that time. Do not claim a spike is happening now unless the data is fresh.
- The synthetic network's normal drop rate is about 7%; the alert threshold is above 15% in a 5-minute window with at
  least 50 calls (KPI-DEF-001). Windows below the minimum sample are 'insufficient sample', not 0%.
- You are read-only: you cannot dispatch teams, send email or change anything. Say so if asked, and describe what you
  would propose.
- You answer once and cannot run anything afterwards: never write 'please wait', 'I will fetch' or promise results later.
- Be concise: lead with the answer, then the evidence.
"""


async def main() -> None:
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=_credential,
    )

    search_provider = AzureAISearchContextProvider(
        source_id="telco_knowledge_base",
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        credential=_credential,
        mode="agentic",
        knowledge_base_name=os.environ["AZURE_SEARCH_KNOWLEDGE_BASE_NAME"],
        knowledge_base_output_mode="extractive_data",
        retrieval_reasoning_effort="minimal",
    )

    data_tools: list = [data_freshness, region_drop_rate, affected_towers, customer_sla_check, query_cdr]
    toolbox_name = os.environ.get("TOOLBOX_NAME")
    if toolbox_name:
        # Only FoundryToolbox forwards the caller's identity to the Fabric MCP proxy.
        toolbox_url = f"{os.environ['FOUNDRY_PROJECT_ENDPOINT'].rstrip('/')}/toolboxes/{toolbox_name}/mcp?api-version=v1"
        data_tools.append(FoundryToolbox(_credential, url=toolbox_url, name="fabric_dataagent"))

    async with search_provider:
        knowledge_agent = Agent(
            client=client,
            name="telco_knowledge",
            description="Imvula Telecom knowledge base: runbook, site inventory, maintenance log, KPI definitions, enterprise SLAs, QoS targets.",
            instructions=KNOWLEDGE_INSTRUCTIONS,
            context_providers=[search_provider],
            default_options={"store": False},
        )
        orchestrator = Agent(
            client=client,
            instructions=ORCHESTRATOR_INSTRUCTIONS,
            tools=[
                *data_tools,
                knowledge_agent.as_tool(
                    name="telco_knowledge",
                    description=("Answer from the telecom knowledge base with citations: NOC runbook steps, enterprise SLA limits "
                                 "and notification deadlines, tower and site details, planned maintenance and past incidents, "
                                 "KPI definitions, regulatory QoS targets."),
                    arg_description="A self-contained question; include tower IDs, customer names, the weekday and the UTC time range when they matter.",
                ),
            ],
            default_options={"store": False},
        )
        server = ResponsesHostServer(orchestrator)
        await server.run_async()


if __name__ == "__main__":
    asyncio.run(main())
