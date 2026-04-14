// ============================================================================
// Foundry Lab — Main Bicep Template
// Deploys: AI Foundry Account + Foundry Project + Azure AI Search
// ============================================================================

targetScope = 'resourceGroup'

// ─── Parameters ──────────────────────────────────────────────────────────────

@description('Base prefix for all resources.')
param prefix string = 'foundry-lab'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Azure region for the Search service. Defaults to the main location.')
param searchLocation string = location

@description('SKU for the Azure AI Search service.')
@allowed(['free', 'basic', 'standard', 'standard2', 'standard3'])
param searchSku string = 'basic'

@description('Display name for the Foundry project.')
param projectDisplayName string = 'Foundry Lab Project'

// ─── Derived Names ───────────────────────────────────────────────────────────

var aiServicesName = '${prefix}-ai'
var searchServiceName = '${prefix}-search'
var projectName = '${prefix}-project'

// ─── Modules ─────────────────────────────────────────────────────────────────

module aiServices 'modules/ai-services.bicep' = {
  name: 'deploy-ai-services'
  params: {
    aiServicesName: aiServicesName
    location: location
  }
}

module search 'modules/ai-search.bicep' = {
  name: 'deploy-ai-search'
  params: {
    searchServiceName: searchServiceName
    location: searchLocation
    skuName: searchSku
  }
}

module project 'modules/ai-project.bicep' = {
  name: 'deploy-ai-project'
  params: {
    projectName: projectName
    location: location
    aiServicesId: aiServices.outputs.aiServicesId
    searchServiceId: search.outputs.searchServiceId
    displayName: projectDisplayName
  }
}

// ─── Outputs ─────────────────────────────────────────────────────────────────

output aiServicesEndpoint string = aiServices.outputs.aiServicesEndpoint
output aiServicesName string = aiServices.outputs.aiServicesName
output searchEndpoint string = search.outputs.searchServiceEndpoint
output searchServiceName string = search.outputs.searchServiceName
output projectName string = project.outputs.projectName
