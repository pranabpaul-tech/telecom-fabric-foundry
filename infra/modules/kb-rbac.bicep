// Role assignments for Foundry IQ (Azure AI Search knowledge base over Blob documents).
// The vendored Foundry module already grants the project identity its Search/Storage/Cosmos
// roles; this adds what the knowledge base itself needs, plus the operator's data-plane roles
// so the local scripts can upload documents and create the knowledge source and base.

param searchName string
param searchPrincipalId string
param kbStorageAccountName string
param foundryAccountName string
param operatorPrincipalId string

var storageBlobDataReader = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
var storageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var searchServiceContributor = '7ca78c08-252a-4471-8644-bab5ee668cb4'
var searchIndexDataContributor = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var cognitiveServicesOpenAIUser = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
var azureAIUser = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var foundryProjectManager = 'eadc314b-1a2d-4efa-be10-5d325db5065e'

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchName
}

resource kbStorage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: kbStorageAccountName
}

resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: foundryAccountName
}

// Search managed identity: read the documents, call the embedding / chat models.
resource searchReadsBlobs 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kbStorage.id, searchPrincipalId, storageBlobDataReader)
  scope: kbStorage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataReader)
    principalId: searchPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource searchCallsModels 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, searchPrincipalId, cognitiveServicesOpenAIUser)
  scope: account
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUser)
    principalId: searchPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Operator: upload documents and manage the knowledge base from the local machine.
resource operatorBlobs 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kbStorage.id, operatorPrincipalId, storageBlobDataContributor)
  scope: kbStorage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributor)
    principalId: operatorPrincipalId
    principalType: 'User'
  }
}

resource operatorSearchService 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, operatorPrincipalId, searchServiceContributor)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributor)
    principalId: operatorPrincipalId
    principalType: 'User'
  }
}

resource operatorSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, operatorPrincipalId, searchIndexDataContributor)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributor)
    principalId: operatorPrincipalId
    principalType: 'User'
  }
}

resource operatorFoundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, operatorPrincipalId, azureAIUser)
  scope: account
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIUser)
    principalId: operatorPrincipalId
    principalType: 'User'
  }
}

resource operatorFoundryManager 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, operatorPrincipalId, foundryProjectManager)
  scope: account
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryProjectManager)
    principalId: operatorPrincipalId
    principalType: 'User'
  }
}
