// ============================================================================
// AI Foundry Account (AI Services)
// Deploys the top-level Foundry resource using CognitiveServices/accounts.
// ============================================================================

@description('Name for the AI Foundry account.')
param aiServicesName string

@description('Azure region.')
param location string = resourceGroup().location

@description('SKU for the AI Services account.')
param skuName string = 'S0'

@description('Name of the GPT chat model deployment.')
param chatModelDeploymentName string = 'gpt-4.1'

@description('Name of the GPT chat model to deploy.')
param chatModelName string = 'gpt-4.1'

@description('Name of the embedding model deployment.')
param embeddingModelDeploymentName string = 'text-embedding-3-large'

@description('Name of the embedding model to deploy.')
param embeddingModelName string = 'text-embedding-3-large'

resource aiServices 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: aiServicesName
  location: location
  kind: 'AIServices'
  sku: {
    name: skuName
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    customSubDomainName: aiServicesName
    allowProjectManagement: true
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ─── Model Deployments ────────────────────────────────────────────────────

resource chatModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiServices
  name: chatModelDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: chatModelName
      version: '2025-04-14'
    }
  }
}

resource embeddingModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiServices
  name: embeddingModelDeploymentName
  dependsOn: [chatModelDeployment]
  sku: {
    name: 'Standard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: embeddingModelName
      version: '1'
    }
  }
}

output aiServicesId string = aiServices.id
output aiServicesName string = aiServices.name
output aiServicesEndpoint string = aiServices.properties.endpoint
