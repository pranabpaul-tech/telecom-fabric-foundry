#!/usr/bin/env python
"""Upload artifacts/kb-docs/*.md to the KB storage account (container kb-docs).

Idempotent: blobs with the same name are overwritten, and blobs that are no longer in the folder
are deleted, so the knowledge base never holds stale documents. Uses the operator's Entra identity
(Storage Blob Data Contributor from infra/modules/kb-rbac.bicep); the account has shared-key access off.

    python src/telcoops/knowledge/upload_docs.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from azure.core.exceptions import HttpResponseError  # noqa: E402
from azure.storage.blob import BlobServiceClient, ContentSettings  # noqa: E402

from telcoops.common.auth import get_token_provider  # noqa: E402
from telcoops.common.config import StateStore, get_settings  # noqa: E402
from telcoops.common.logging_setup import setup_logging  # noqa: E402

logger = setup_logging(__name__)

DOCS_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "kb-docs"


def doc_id(text: str) -> str:
    m = re.search(r"\|\s*Document ID\s*\|\s*([A-Z0-9-]+)\s*\|", text)
    return m.group(1) if m else ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    state = StateStore()
    account = state.require("wave0", "kbStorageAccountName")["kbStorageAccountName"]
    files = sorted(DOCS_DIR.glob("*.md"))
    if not files:
        raise RuntimeError(f"no documents in {DOCS_DIR}")

    if args.dry_run:
        for f in files:
            print(f"{f.name}  doc_id={doc_id(f.read_text(encoding='utf-8'))}  words={len(f.read_text(encoding='utf-8').split())}")
        return

    service = BlobServiceClient(f"https://{account}.blob.core.windows.net",
                                credential=get_token_provider().get_credential())
    container = service.get_container_client(settings.kb_container_name)

    wanted = set()
    for f in files:
        text = f.read_text(encoding="utf-8")
        wanted.add(f.name)
        container.upload_blob(
            f.name, text.encode("utf-8"), overwrite=True,
            content_settings=ContentSettings(content_type="text/markdown; charset=utf-8"),
            metadata={"doc_id": doc_id(text), "synthetic": "true"})
        logger.info("uploaded %s (%s)", f.name, doc_id(text))

    for blob in container.list_blobs():
        if blob.name not in wanted:
            container.delete_blob(blob.name)
            logger.info("deleted stale blob %s", blob.name)

    names = sorted(b.name for b in container.list_blobs())
    state.merge("kb", {"storageAccount": account, "container": settings.kb_container_name, "blobs": names})
    logger.info("container '%s' holds %d documents", settings.kb_container_name, len(names))


if __name__ == "__main__":
    try:
        main()
    except HttpResponseError as exc:
        sys.exit(f"Storage call failed: {exc.message[:400]}\n"
                 "If this is an authorization error, the Blob Data Contributor role from kb-rbac.bicep may still be "
                 "propagating; wait a few minutes and retry.")
