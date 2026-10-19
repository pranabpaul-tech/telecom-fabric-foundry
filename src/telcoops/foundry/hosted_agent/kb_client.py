"""Retrieval from the Foundry IQ knowledge base (Azure AI Search knowledge base, `retrieve` action).

Why this exists instead of agent_framework_azure_ai_search.AzureAISearchContextProvider: the knowledge base is
backed by a *file* knowledge source, which only exists in the 2026-08-01-preview API. The provider's SDK uses an
older API version and refuses the knowledge base ("kind 'file' is not supported in this API version"), so the
agent calls the retrieve endpoint directly with the right version.

format_retrieval() is pure so it can be tested offline; retrieve() does the HTTP call.
"""
from __future__ import annotations

import json

import requests

API_VERSION = "2026-08-01-preview"
SEARCH_SCOPE = "https://search.azure.com/.default"

# File name -> document ID used in the documents themselves (and in citations).
DOC_IDS = {
    "noc-dropped-call-runbook.md": "RB-NOC-001",
    "site-inventory.md": "SITE-INV-001",
    "maintenance-and-incident-log.md": "MAINT-LOG-001",
    "kpi-definitions.md": "KPI-DEF-001",
    "enterprise-sla-contracts.md": "SLA-ENT-001",
    "qos-regulatory-targets.md": "QOS-REG-001",
}

MAX_PASSAGE_CHARS = 2500


def format_retrieval(response: dict, max_passages: int = 8) -> dict:
    """Passages with the document they came from.

    The response holds the passages as a JSON array in response[0].content[0].text ({ref_id, content}) and a
    `references` list whose `id` matches ref_id and whose `docName` is the uploaded file name.
    """
    names = {str(r.get("id")): r.get("docName") for r in response.get("references", [])}
    passages: list[dict] = []
    for message in response.get("response", []):
        for part in message.get("content", []):
            text = part.get("text", "")
            try:
                items = json.loads(text)
            except (ValueError, TypeError):
                items = [{"ref_id": None, "content": text}] if text.strip() else []
            for item in items:
                doc_name = names.get(str(item.get("ref_id")))
                passages.append({
                    "document_id": DOC_IDS.get(doc_name or "", doc_name or "unknown"),
                    "file": doc_name,
                    "text": str(item.get("content", ""))[:MAX_PASSAGE_CHARS],
                })
    passages = passages[:max_passages]
    return {"passage_count": len(passages), "passages": passages,
            "note": None if passages else "Not in the knowledge base: no passage matched the question."}


def retrieve(endpoint: str, knowledge_base: str, question: str, credential, timeout: int = 120) -> dict:
    token = credential.get_token(SEARCH_SCOPE).token
    body = {"messages": [{"role": "user", "content": [{"type": "text", "text": question}]}], "includeActivity": False}
    r = requests.post(f"{endpoint.rstrip('/')}/knowledgebases/{knowledge_base}/retrieve",
                      params={"api-version": API_VERSION},
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                      json=body, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"knowledge base retrieve failed ({r.status_code}): {r.text[:500]}")
    return format_retrieval(r.json())
