# Runs right before `azd provision`. Non-interactive: threads the operator identity and the
# Wave 0 outputs (infra/wave0-byo-resources.bicep) into the azd environment, which
# infra/main.bicepparam reads through readEnvironmentVariable().
#
# Override any value first with `azd env set NAME value` (for example FABRIC_ADMIN_UPN).

$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path "$PSScriptRoot/../.."

Push-Location $repoRoot
try {
    function Get-AzdValue([string]$Key) {
        # azd env get-value prints its "key not found" error to STDOUT and still exits 0;
        # it can also print an "Update available" notice ahead of the value. Strip the noise.
        $out = azd env get-value $Key 2>$null |
            Where-Object { $_ -notmatch '^(Update available:|To update, run|ERROR:|Suggestion:|Run .azd env|\s*$)' }
        return ($out -join "`n")
    }

    function Set-AzdDefault([string]$Key, [string]$Value) {
        if ([string]::IsNullOrWhiteSpace((Get-AzdValue $Key))) {
            azd env set $Key $Value | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "azd env set $Key failed (exit $LASTEXITCODE)" }
        }
    }

    $rg = Get-AzdValue "AZURE_RESOURCE_GROUP_NAME"
    if ([string]::IsNullOrWhiteSpace($rg)) { $rg = "rg-telco-fabric-foundry"; azd env set AZURE_RESOURCE_GROUP_NAME $rg | Out-Null }

    Set-AzdDefault "AZURE_LOCATION" "swedencentral"
    Set-AzdDefault "FABRIC_CAPACITY_NAME" "telcof8"
    Set-AzdDefault "FOUNDRY_AI_SERVICES_BASE_NAME" "telcoai"

    # Operator identity (the account that runs the Fabric setup scripts). Graph can answer with a
    # Conditional Access challenge, so fall back to the claims of the ARM token.
    $upn = Get-AzdValue "FABRIC_ADMIN_UPN"
    $oid = Get-AzdValue "OPERATOR_OBJECT_ID"
    if ([string]::IsNullOrWhiteSpace($upn) -or [string]::IsNullOrWhiteSpace($oid)) {
        $token = az account get-access-token --resource https://management.azure.com --query accessToken -o tsv
        if ($LASTEXITCODE -ne 0) { throw "az account get-access-token failed (exit $LASTEXITCODE)" }
        $payload = $token.Split('.')[1].Replace('-', '+').Replace('_', '/')
        $payload = $payload + ('=' * ((4 - $payload.Length % 4) % 4))
        $claims = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload)) | ConvertFrom-Json
        if ([string]::IsNullOrWhiteSpace($upn)) { $upn = if ($claims.upn) { $claims.upn } else { $claims.unique_name } }
        if ([string]::IsNullOrWhiteSpace($oid)) { $oid = $claims.oid }
    }
    azd env set FABRIC_ADMIN_UPN $upn | Out-Null
    azd env set OPERATOR_OBJECT_ID $oid | Out-Null

    # Wave 0 outputs -> azd env
    $pairs = [ordered]@{
        "AI_SEARCH_RESOURCE_ID"     = "aiSearchResourceId"
        "AI_SEARCH_NAME"            = "aiSearchName"
        "AI_SEARCH_PRINCIPAL_ID"    = "aiSearchPrincipalId"
        "AZURE_STORAGE_RESOURCE_ID" = "azureStorageAccountResourceId"
        "AZURE_COSMOS_RESOURCE_ID"  = "azureCosmosDBAccountResourceId"
        "KB_STORAGE_ACCOUNT_NAME"   = "kbStorageAccountName"
    }
    foreach ($key in $pairs.Keys) {
        if ([string]::IsNullOrWhiteSpace((Get-AzdValue $key))) {
            $val = az deployment group show -g $rg -n wave0-byo-deployment --query "properties.outputs.$($pairs[$key]).value" -o tsv 2>$null
            if (-not [string]::IsNullOrWhiteSpace($val)) { azd env set $key $val | Out-Null }
        }
    }
    if ([string]::IsNullOrWhiteSpace((Get-AzdValue "AI_SEARCH_RESOURCE_ID"))) {
        throw "No Wave 0 outputs found. Run: az deployment group create -g $rg -n wave0-byo-deployment -f infra/wave0-byo-resources.bicep"
    }

    Write-Host "Using resource group '$rg', operator '$upn' ($oid)." -ForegroundColor Green
}
finally {
    Pop-Location
}
