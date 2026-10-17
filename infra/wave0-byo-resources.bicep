// Telecom NOC Copilot - Wave 0
// AI Search / agent Storage / Cosmos DB (the Foundry standard agent "BYO trio") plus a
// separate Storage account that holds the Foundry IQ knowledge documents.
// Deployed once, ahead of main.bicep, which takes their resource IDs as parameters.

@description('Location for Storage and Cosmos. Keep it equal to the Foundry region.')
param location string = 'swedencentral'

@description('Location for AI Search. swedencentral had no Search capacity in this subscription (InsufficientResourcesAvailable), so Search is in uksouth; Foundry agent setup allows Search in another region.')
param searchLocation string = 'uksouth'

param searchServiceName string = 'srch-telco-${uniqueString(resourceGroup().id)}'
param storageAccountName string = 'sttelco${uniqueString(resourceGroup().id)}'
param kbStorageAccountName string = 'stkbtelco${uniqueString(resourceGroup().id)}'
param cosmosAccountName string = 'cosmos-telco-${uniqueString(resourceGroup().id)}'
param kbContainerName string = 'kb-docs'

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: searchLocation
  sku: {
    name: 'standard'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled' // closed again in the lock-down phase
    // Semantic ranker is required by Foundry IQ knowledge bases (agentic retrieval).
    semanticSearch: 'standard'
    // Foundry's standard agent setup connects to Search with authType=AAD; apiKeyOnly (the
    // resource default) makes every agent call fail with a 403.
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

// Knowledge documents for Foundry IQ. Shared-key access is off: uploads and the Search
// indexer both use Entra identities (see modules/kb-rbac.bicep).
resource kbStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: kbStorageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Enabled' // closed again in the lock-down phase
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource kbBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: kbStorage
  name: 'default'
}

resource kbContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: kbBlobService
  name: kbContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: cosmosAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
  }
}

output aiSearchResourceId string = search.id
output aiSearchName string = search.name
output aiSearchPrincipalId string = search.identity.principalId
output azureStorageAccountResourceId string = storage.id
output azureCosmosDBAccountResourceId string = cosmos.id
output kbStorageAccountId string = kbStorage.id
output kbStorageAccountName string = kbStorage.name
output kbContainerName string = kbContainer.name
