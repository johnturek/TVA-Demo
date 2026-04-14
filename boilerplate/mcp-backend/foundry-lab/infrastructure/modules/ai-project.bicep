// ============================================================================
// AI Foundry Project
// Deploys a project under an existing AI Foundry account and optionally
// connects Azure AI Search as a data source.
// ============================================================================

@description('Name for the Foundry project.')
param projectName string

@description('Azure region.')
param location string = resourceGroup().location

@description('Resource ID of the parent AI Foundry account.')
param aiServicesId string

@description('Resource ID of the Azure AI Search service to connect.')
param searchServiceId string = ''

@description('Display name shown in the Foundry portal.')
param displayName string = 'Foundry Lab Project'

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  name: projectName
  parent: existing_aiServices
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: displayName
  }
}

resource existing_aiServices 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: last(split(aiServicesId, '/'))
}

output projectName string = project.name
output projectId string = project.id
