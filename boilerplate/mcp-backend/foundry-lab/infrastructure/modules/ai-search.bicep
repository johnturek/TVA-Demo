// ============================================================================
// Azure AI Search — Foundry Lab
// Deploys a search service for RAG and Foundry IQ labs.
// ============================================================================

@description('Globally unique name for the Azure AI Search service.')
param searchServiceName string

@description('Azure region.')
param location string = resourceGroup().location

@description('SKU for the search service.')
@allowed(['free', 'basic', 'standard', 'standard2', 'standard3'])
param skuName string = 'basic'

@description('Number of replicas (1-12).')
param replicaCount int = 1

@description('Number of partitions (1-12).')
param partitionCount int = 1

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: location
  sku: {
    name: skuName
  }
  properties: {
    replicaCount: replicaCount
    partitionCount: partitionCount
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

output searchServiceId string = searchService.id
output searchServiceName string = searchService.name
output searchServiceEndpoint string = 'https://${searchService.name}.search.windows.net'
