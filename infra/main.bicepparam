using './main.bicep'

// Values come from the azd environment (set by infra/hooks/preprovision.*), with safe
// literals as fallbacks for a plain `az deployment sub create`.

// swedencentral supports the Operations Agent, Agent Service (VNet injection) and the
// Fabric Data Agent tool. uksouth is the documented fallback (docs/PLAN.md, "Region assessment").
param location = readEnvironmentVariable('AZURE_LOCATION', 'swedencentral')
param fabricCapacityLocation = readEnvironmentVariable('FABRIC_CAPACITY_LOCATION', 'swedencentral')
param resourceGroupName = readEnvironmentVariable('AZURE_RESOURCE_GROUP_NAME', 'rg-telco-fabric-foundry')

// Fabric capacity administrators. Include whoever runs setup/04_ops_agent.py - the
// Operations Agent runs under its creator's delegated identity.
param fabricAdminMembers = [
  readEnvironmentVariable('FABRIC_ADMIN_UPN', 'CHANGE_ME@yourtenant.onmicrosoft.com')
]

// az ad signed-in-user show --query id -o tsv
param operatorPrincipalId = readEnvironmentVariable('OPERATOR_OBJECT_ID', '00000000-0000-0000-0000-000000000000')

param fabricCapacityName = readEnvironmentVariable('FABRIC_CAPACITY_NAME', 'telcof8')

param foundryAiServicesBaseName = readEnvironmentVariable('FOUNDRY_AI_SERVICES_BASE_NAME', 'telcoai')
param foundryProjectName = 'telco-agents'
param foundryModelName = 'gpt-4.1'
param foundryModelFormat = 'OpenAI'
param foundryModelVersion = '2025-04-14'
param foundryModelSkuName = 'GlobalStandard'
param foundryModelCapacity = 30

// Created by wave0-byo-resources.bicep (deployment name: wave0-byo-deployment). The
// preprovision hook copies them from that deployment's outputs into the azd env.
param aiSearchResourceId = readEnvironmentVariable('AI_SEARCH_RESOURCE_ID', '')
param azureStorageAccountResourceId = readEnvironmentVariable('AZURE_STORAGE_RESOURCE_ID', '')
param azureCosmosDBAccountResourceId = readEnvironmentVariable('AZURE_COSMOS_RESOURCE_ID', '')
param aiSearchName = readEnvironmentVariable('AI_SEARCH_NAME', '')
param aiSearchPrincipalId = readEnvironmentVariable('AI_SEARCH_PRINCIPAL_ID', '')
param kbStorageAccountName = readEnvironmentVariable('KB_STORAGE_ACCOUNT_NAME', '')

// Agents are deployed from an image built with ACR Tasks.
param enableContainerRegistry = true
// Must stay true through agent deploy + Teams publish; the lock-down phase flips it back.
param publicNetworkAccessAtCreation = true
