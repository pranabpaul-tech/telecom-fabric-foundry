#!/usr/bin/env python
"""Write the Bicep outputs into state.json.

- state.json['wave1']: the azd environment's outputs for infra/main.bicep (`azd provision` keeps
  them in its own environment, not in state.json).
- state.json['wave0']: the outputs of the `wave0-byo-deployment` resource-group deployment.

Run it right after `azd provision`. Re-running is a no-op.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telcoops.common.config import StateStore, get_settings  # noqa: E402
from telcoops.common.logging_setup import setup_logging  # noqa: E402

logger = setup_logging(__name__)

# azd also exposes its own AZURE_* bookkeeping alongside the Bicep outputs; only the outputs
# declared by infra/main.bicep are copied.
WAVE1_OUTPUT_KEYS = [
    "location", "resourceGroupName", "vnetId", "vnetName", "agentSubnetId", "agentSubnetName",
    "peSubnetId", "peSubnetName", "containerSubnetId", "jumpboxContainerGroupName",
    "jumpboxPrincipalId", "fabricCapacityId", "fabricCapacityName", "keyVaultName",
    "keyVaultUri", "logAnalyticsWorkspaceId", "appInsightsConnectionString",
    "foundryAccountName", "foundryAccountId", "foundryAccountEndpoint",
    "foundryProjectName", "foundryProjectId", "foundryAcrName",
    "embeddingDeploymentName", "aiSearchName", "kbStorageAccountName",
]


def run(*args: str) -> str:
    exe = shutil.which(args[0])
    if exe is None:
        raise RuntimeError(f"{args[0]} not found on PATH")
    result = subprocess.run([exe, *args[1:]], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed ({result.returncode}): {result.stderr.strip()[:500]}")
    return result.stdout


def main() -> None:
    settings = get_settings()
    state = StateStore()

    values = json.loads(run("azd", "env", "get-values", "--output", "json"))
    wave1 = {key: values[key] for key in WAVE1_OUTPUT_KEYS if key in values}
    missing = [key for key in WAVE1_OUTPUT_KEYS if key not in values]
    if missing:
        logger.warning("azd env is missing these expected Wave 1 outputs: %s", missing)
    state.merge("wave1", wave1)
    logger.info("Wrote %d Wave 1 outputs to state.json.", len(wave1))

    rg = values.get("AZURE_RESOURCE_GROUP_NAME", settings.resource_group)
    outputs = json.loads(run(
        "az", "deployment", "group", "show", "-g", rg, "-n", "wave0-byo-deployment",
        "--query", "properties.outputs", "-o", "json"))
    wave0 = {k: v["value"] for k, v in outputs.items()}
    state.merge("wave0", wave0)
    logger.info("Wrote %d Wave 0 outputs to state.json.", len(wave0))


if __name__ == "__main__":
    main()
