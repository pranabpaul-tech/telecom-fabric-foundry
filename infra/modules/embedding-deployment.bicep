// Adds an embedding model deployment to the Foundry (AIServices) account. Foundry IQ uses it
// to vectorise knowledge documents. The chat model is deployed by the vendored Foundry module.

param foundryAccountName string
param modelName string = 'text-embedding-3-large'
param modelVersion string = '1'
param skuName string = 'GlobalStandard'
param capacity int = 50

resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: foundryAccountName
}

resource embedding 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: account
  name: modelName
  sku: {
    name: skuName
    capacity: capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
  }
}

output deploymentName string = embedding.name
