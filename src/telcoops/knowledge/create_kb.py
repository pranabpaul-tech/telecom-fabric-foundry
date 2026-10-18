#!/usr/bin/env python
"""Create the Foundry IQ knowledge base from artifacts/kb-docs/*.md.

Uses a *file* knowledge source (Azure AI Search, API 2026-08-01-preview): the documents are uploaded
straight to Search, which extracts, chunks and embeds them. No storage account or indexer is needed.
That matters in this subscription: the MCAPS policy StorageAccount_PublicNetwork_Modify forces every
storage account to public access Disabled, so a Blob knowledge source could not be loaded from the
operator's machine.

Idempotent: the knowledge source and base are create-or-update, and uploaded files are replaced
(files with the same name are deleted first), so re-running gives the same result.

    python src/telcoops/knowledge/create_kb.py [--no-upload] [--ask "question"]

Needs: Search public access enabled (until the lock-down phase), the operator's Search Service
Contributor / Search Index Data Contributor roles, and the Search managed identity holding
Cognitive Services OpenAI User on the Foundry account (infra/modules/kb-rbac.bicep).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from telcoops.common.auth import get_token_provider  # noqa: E402
from telcoops.common.config import StateStore, get_settings  # noqa: E402
from telcoops.common.logging_setup import setup_logging  # noqa: E402

logger = setup_logging(__name__)

API = "2026-08-01-preview"
SEARCH_SCOPE = "https://search.azure.com/.default"
DOCS_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "kb-docs"
KS_NAME = "telco-docs-ks"

KB_RETRIEVAL_INSTRUCTIONS = (
    "The knowledge source holds six synthetic documents about the fictional operator Imvula Telecom: "
    "the NOC dropped-call runbook (RB-NOC-001), the tower and site inventory (SITE-INV-001), the maintenance "
    "and incident log (MAINT-LOG-001), KPI definitions (KPI-DEF-001), enterprise SLAs (SLA-ENT-001) and "
    "regulatory QoS targets (QOS-REG-001). Retrieve the passages that answer the question and keep tower IDs, "
    "customer names, dates and numbers exactly as written. Always return the document ID and section."
)


class Search:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")
        self._tokens = get_token_provider()

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"Authorization": f"Bearer {self._tokens.get_token(SEARCH_SCOPE)}"}
        h.update(extra or {})
        return h

    def call(self, method: str, path: str, *, json_body=None, data=None, headers=None, ok=(200, 201, 204),
             timeout=240) -> requests.Response:
        sep = "&" if "?" in path else "?"
        url = f"{self.endpoint}{path}{sep}api-version={API}"
        h = self._headers(headers)
        if json_body is not None:
            h["Content-Type"] = "application/json"
        r = requests.request(method, url, headers=h, json=json_body, data=data, timeout=timeout)
        if r.status_code not in ok:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:700]}")
        return r


def knowledge_source_body(openai_endpoint: str, embedding: str) -> dict:
    return {
        "name": KS_NAME,
        "kind": "file",
        "description": "Imvula Telecom NOC documents: runbook, site inventory, maintenance log, KPI definitions, "
                       "enterprise SLAs, regulatory QoS targets (synthetic demo data).",
        "fileParameters": {"ingestionParameters": {
            "embeddingModel": {"kind": "azureOpenAI", "azureOpenAIParameters": {
                "resourceUri": openai_endpoint, "deploymentId": embedding, "modelName": embedding}},
            "contentExtractionMode": "minimal"}},
    }


def knowledge_base_body(name: str, openai_endpoint: str, chat: str) -> dict:
    return {
        "name": name,
        "description": "Telecom NOC knowledge: procedures, sites, maintenance, KPI definitions, SLAs and QoS targets.",
        "retrievalInstructions": KB_RETRIEVAL_INSTRUCTIONS,
        "knowledgeSources": [{"name": KS_NAME}],
        "models": [{"kind": "azureOpenAI", "azureOpenAIParameters": {
            "resourceUri": openai_endpoint, "deploymentId": chat, "modelName": chat}}],
        "retrievalReasoningEffort": {"kind": "low"},
    }


def replace_files(search: Search, files: list[Path]) -> None:
    listing = search.call("GET", f"/knowledgesources/{KS_NAME}/files").json().get("value", [])
    by_name: dict[str, list[str]] = {}
    for f in listing:
        by_name.setdefault(f["fileName"], []).append(f["fileId"])
    for path in files:
        for file_id in by_name.get(path.name, []):
            search.call("DELETE", f"/knowledgesources/{KS_NAME}/files/{file_id}")
            logger.info("deleted previous %s (%s)", path.name, file_id)
    for stale, ids in by_name.items():
        if stale not in {p.name for p in files}:
            for file_id in ids:
                search.call("DELETE", f"/knowledgesources/{KS_NAME}/files/{file_id}")
                logger.info("deleted stale file %s", stale)
    for path in files:
        for attempt in range(1, 6):
            try:
                search.call("POST", f"/knowledgesources/{KS_NAME}/files", data=path.read_bytes(), timeout=300,
                            headers={"Content-Type": "application/octet-stream",
                                     "Content-Disposition": f'attachment; filename="{path.name}"'})
                logger.info("uploaded %s", path.name)
                break
            except RuntimeError as exc:
                if attempt == 5 or not any(c in str(exc) for c in (" 429:", " 503:", " 504:", " 403:")):
                    raise
                wait = 15 * attempt
                logger.warning("upload of %s not accepted yet (%s); retrying in %ds", path.name, str(exc)[:160], wait)
                time.sleep(wait)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-upload", action="store_true", help="only (re)create the knowledge source and base")
    parser.add_argument("--ask", help="run one retrieval against the knowledge base and print it")
    args = parser.parse_args()

    settings = get_settings()
    state = StateStore()
    wave0, wave1 = state.require("wave0", "aiSearchName"), state.require("wave1", "foundryAccountName")
    endpoint = f"https://{wave0['aiSearchName']}.search.windows.net"
    openai_endpoint = f"https://{wave1['foundryAccountName']}.openai.azure.com"
    embedding, chat = "text-embedding-3-large", "gpt-4.1"
    search = Search(endpoint)

    search.call("PUT", f"/knowledgesources/{KS_NAME}", json_body=knowledge_source_body(openai_endpoint, embedding),
                headers={"Prefer": "return=representation"})
    logger.info("knowledge source '%s' ready", KS_NAME)

    if not args.no_upload:
        files = sorted(DOCS_DIR.glob("*.md"))
        if not files:
            raise RuntimeError(f"no documents in {DOCS_DIR}")
        replace_files(search, files)

    kb = settings.knowledge_base_name
    search.call("PUT", f"/knowledgebases/{kb}", json_body=knowledge_base_body(kb, openai_endpoint, chat),
                headers={"Prefer": "return=representation"})
    logger.info("knowledge base '%s' ready", kb)

    uploaded = search.call("GET", f"/knowledgesources/{KS_NAME}/files").json().get("value", [])
    bad = [f for f in uploaded if f.get("errorMessage")]
    if bad:
        raise RuntimeError(f"files with errors: {[(f['fileName'], f['errorMessage']) for f in bad]}")
    mcp = f"{endpoint}/knowledgebases/{kb}/mcp?api-version={API}"
    state.merge("kb", {"searchEndpoint": endpoint, "knowledgeSource": KS_NAME, "knowledgeBase": kb,
                       "apiVersion": API, "mcpEndpoint": mcp, "files": sorted(f["fileName"] for f in uploaded)})
    logger.info("%d files in the knowledge source; MCP endpoint %s", len(uploaded), mcp)

    if args.ask:
        body = {"messages": [{"role": "user", "content": [{"type": "text", "text": args.ask}]}],
                "includeActivity": False}
        r = search.call("POST", f"/knowledgebases/{kb}/retrieve", json_body=body)
        data = r.json()
        for msg in data.get("response", []):
            for part in msg.get("content", []):
                text = part.get("text", "")
                try:  # extractive output is a JSON array of {ref_id, content}
                    for item in json.loads(text):
                        print(f"[{item.get('ref_id')}] {str(item.get('content', ''))[:900]}")
                        print()
                except (ValueError, TypeError):
                    print(text[:3000])
        for ref in data.get("references", []):
            src = ref.get("sourceData") or {}
            print("ref:", ref.get("type"), ref.get("id"), src.get("title") or src.get("fileName") or ref.get("docKey"))


if __name__ == "__main__":
    main()
