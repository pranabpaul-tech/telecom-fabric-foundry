# Runs right after `azd provision`: records the Bicep outputs in state.json so the Python setup
# scripts can read them. Fabric items are created by the scripts in src/telcoops/setup, run
# from the local machine (see docs/PLAN.md), not here.

$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path "$PSScriptRoot/../.."

Push-Location $repoRoot
try {
    if (-not (Test-Path ".venv")) {
        Write-Host "Creating Python venv..." -ForegroundColor Cyan
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "python -m venv failed (exit $LASTEXITCODE)" }
    }
    & ".venv/Scripts/pip.exe" install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "pip install failed (exit $LASTEXITCODE)" }

    $env:PYTHONPATH = "src"
    $env:TELCO_FORCE_CLI_CREDENTIAL = "1"
    & ".venv/Scripts/python.exe" scripts/capture_state.py
    if ($LASTEXITCODE -ne 0) { throw "capture_state.py failed (exit $LASTEXITCODE)" }

    Write-Host "`nWave 1 is deployed and recorded in state.json. Next: python src/telcoops/setup/01_jumpstart.py" -ForegroundColor Green
}
finally {
    Pop-Location
}
