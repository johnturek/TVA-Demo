#!/bin/bash
# =============================================================================
# TVA Workshop — Azure Infrastructure Provisioning Script
# Deploys: Container Apps (MCP server), APIM, App Registration
# Output: All values needed for Copilot Studio + Lab 3 configuration
#
# Usage:
#   chmod +x provision-azure.sh
#   ./provision-azure.sh
#
# Prerequisites:
#   - az cli logged in: az login
#   - Correct subscription selected: az account set --subscription <id>
#   - Docker image built: docker build -t tva-mcp ./boilerplate/mcp-server
#
# Microsoft Learn References:
#   - Container Apps: https://learn.microsoft.com/en-us/azure/container-apps/
#   - APIM: https://learn.microsoft.com/en-us/azure/api-management/
#   - App Registration: https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app
# =============================================================================

set -e

# =============================================================================
# CONFIGURE THESE
# =============================================================================
PARTICIPANT_SUFFIX="${1:-l01}"          # Pass your initials/number: ./provision-azure.sh jt
RESOURCE_GROUP="tva-workshop-rg"
LOCATION="eastus2"
TENANT_ID=$(az account show --query tenantId -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Derived names
PREFIX="mcp-workshop-${PARTICIPANT_SUFFIX}"
APIM_NAME="${PREFIX}-apim"
CONTAINER_APP_NAME="${PREFIX}-mcp"
CONTAINER_ENV_NAME="${PREFIX}-env"
ACR_NAME="tvawsacr${PARTICIPANT_SUFFIX}"   # Must be globally unique, alphanumeric only
APP_REG_NAME="${PREFIX}-app"

echo ""
echo "=================================================="
echo "  TVA Workshop — Azure Provisioning"
echo "  Participant: ${PARTICIPANT_SUFFIX}"
echo "  Resource Group: ${RESOURCE_GROUP}"
echo "  Location: ${LOCATION}"
echo "=================================================="
echo ""

# =============================================================================
# 1. Resource Group
# =============================================================================
echo "[ 1/7 ] Creating resource group..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none
echo "        ✅ Resource group ready"

# =============================================================================
# 2. App Registration (Entra ID)
# Learn: https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app
# =============================================================================
echo "[ 2/7 ] Creating app registration..."
APP_JSON=$(az ad app create \
  --display-name "$APP_REG_NAME" \
  --sign-in-audience "AzureADMyOrg" \
  --output json)

APP_ID=$(echo "$APP_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['appId'])")

# Expose API scope
az ad app update \
  --id "$APP_ID" \
  --identifier-uris "api://$APP_ID" \
  --output none

# Create service principal
az ad sp create --id "$APP_ID" --output none

# Create client secret
SECRET_JSON=$(az ad app credential reset \
  --id "$APP_ID" \
  --years 1 \
  --output json)
APP_SECRET=$(echo "$SECRET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

JWT_AUDIENCE="api://${APP_ID}"
JWT_ISSUER="https://login.microsoftonline.com/${TENANT_ID}/v2.0"

echo "        ✅ App registration created: ${APP_ID}"

# =============================================================================
# 3. Azure Container Registry
# =============================================================================
echo "[ 3/7 ] Creating Container Registry and pushing MCP image..."
az acr create \
  --name "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --sku Basic \
  --admin-enabled true \
  --output none

# Build and push MCP server image
ACR_SERVER="${ACR_NAME}.azurecr.io"
az acr build \
  --registry "$ACR_NAME" \
  --image "tva-mcp:latest" \
  --file "./boilerplate/Dockerfile.mcp" \
  . \
  --output none

echo "        ✅ Container image pushed to ${ACR_SERVER}"

# =============================================================================
# 4. Container Apps Environment
# Learn: https://learn.microsoft.com/en-us/azure/container-apps/environment
# =============================================================================
echo "[ 4/7 ] Creating Container Apps environment..."
az containerapp env create \
  --name "$CONTAINER_ENV_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none
echo "        ✅ Container Apps environment ready"

# =============================================================================
# 5. Deploy MCP Server as Container App
# Learn: https://learn.microsoft.com/en-us/azure/container-apps/quickstart-portal
# =============================================================================
echo "[ 5/7 ] Deploying MCP server to Container Apps..."
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query passwords[0].value -o tsv)

BACKEND_URL=$(az containerapp create \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV_NAME" \
  --image "${ACR_SERVER}/tva-mcp:latest" \
  --target-port 3002 \
  --ingress external \
  --registry-server "$ACR_SERVER" \
  --registry-username "$ACR_NAME" \
  --registry-password "$ACR_PASSWORD" \
  --env-vars \
      PORT=3002 \
      JWT_AUDIENCE="$JWT_AUDIENCE" \
      JWT_ISSUER="$JWT_ISSUER" \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

BACKEND_URL="https://${BACKEND_URL}"
echo "        ✅ MCP server deployed: ${BACKEND_URL}"

# =============================================================================
# 6. API Management
# Learn: https://learn.microsoft.com/en-us/azure/api-management/get-started-create-service-instance-cli
# Note: APIM creation takes 10-15 minutes on Consumption tier
# =============================================================================
echo "[ 6/7 ] Creating APIM instance (this takes ~15 min on first run)..."
az apim create \
  --name "$APIM_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --publisher-name "TVA Workshop" \
  --publisher-email "workshop@tva.gov" \
  --sku-name Consumption \
  --output none

APIM_GATEWAY="https://${APIM_NAME}.azure-api.net"
MCP_ENDPOINT="${APIM_GATEWAY}/mcp"
PRM_METADATA="${APIM_GATEWAY}/.well-known/oauth-protected-resource"

# Import MCP API definition
az apim api create \
  --service-name "$APIM_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --api-id "mcp-api" \
  --display-name "TVA MCP Server" \
  --service-url "$BACKEND_URL" \
  --path "mcp" \
  --protocols https \
  --output none

# Apply JWT validation policy
# Learn: https://learn.microsoft.com/en-us/azure/api-management/validate-jwt-policy
POLICY_XML=$(cat <<EOF
<policies>
  <inbound>
    <base />
    <validate-azure-ad-token
      tenant-id="${TENANT_ID}"
      failed-validation-httpcode="401"
      failed-validation-error-message="Unauthorized — valid Entra ID token required">
      <audiences>
        <audience>${JWT_AUDIENCE}</audience>
      </audiences>
    </validate-azure-ad-token>
    <set-header name="X-TVA-UserId" exists-action="override">
      <value>@(context.Request.Headers.GetValueOrDefault("Authorization",""))</value>
    </set-header>
    <cors>
      <allowed-origins>
        <origin>https://copilotstudio.microsoft.com</origin>
      </allowed-origins>
      <allowed-methods>
        <method>POST</method>
        <method>GET</method>
        <method>OPTIONS</method>
      </allowed-methods>
      <allowed-headers>
        <header>*</header>
      </allowed-headers>
    </cors>
  </inbound>
  <backend>
    <base />
  </backend>
  <outbound>
    <base />
  </outbound>
</policies>
EOF
)

az apim api policy create \
  --service-name "$APIM_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --api-id "mcp-api" \
  --policy "$POLICY_XML" \
  --output none

echo "        ✅ APIM deployed and secured with Entra ID JWT validation"

# =============================================================================
# 7. Output Summary
# =============================================================================
echo ""
echo "==================== APIM OUTPUTS ===================="
echo "APIM_NAME:      ${APIM_NAME}"
echo "APIM_GATEWAY:   ${APIM_GATEWAY}"
echo "MCP_ENDPOINT:   ${MCP_ENDPOINT}"
echo "PRM_METADATA:   ${PRM_METADATA}"
echo "BACKEND_URL:    ${BACKEND_URL}"
echo "JWT_AUDIENCE:   ${JWT_AUDIENCE}"
echo "JWT_ISSUER:     ${JWT_ISSUER}"
echo "======================================================="
echo ""
echo "==================== APP REGISTRATION ================="
echo "AZURE_TENANT_ID:     ${TENANT_ID}"
echo "AZURE_CLIENT_ID:     ${APP_ID}"
echo "AZURE_CLIENT_SECRET: ${APP_SECRET}"
echo "======================================================="
echo ""
echo "Next steps:"
echo "  1. Add MCP_ENDPOINT to Copilot Studio → Tools → Add tool → Model Context Protocol"
echo "  2. Set Copilot Studio auth to 'Authenticate with Microsoft' using AZURE_CLIENT_ID"
echo "  3. Test: curl -H 'Authorization: Bearer <token>' ${MCP_ENDPOINT}/health"
echo ""
echo "📚 MS Learn:"
echo "  Container Apps: https://learn.microsoft.com/en-us/azure/container-apps/"
echo "  APIM JWT policy: https://learn.microsoft.com/en-us/azure/api-management/validate-jwt-policy"
echo "  Copilot Studio MCP: https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent"
echo ""

# Save outputs to .env file for use in other scripts
cat > .workshop-outputs.env <<ENVEOF
APIM_NAME=${APIM_NAME}
APIM_GATEWAY=${APIM_GATEWAY}
MCP_ENDPOINT=${MCP_ENDPOINT}
PRM_METADATA=${PRM_METADATA}
BACKEND_URL=${BACKEND_URL}
JWT_AUDIENCE=${JWT_AUDIENCE}
JWT_ISSUER=${JWT_ISSUER}
AZURE_TENANT_ID=${TENANT_ID}
AZURE_CLIENT_ID=${APP_ID}
AZURE_CLIENT_SECRET=${APP_SECRET}
ENVEOF

echo "✅ Outputs saved to .workshop-outputs.env"
