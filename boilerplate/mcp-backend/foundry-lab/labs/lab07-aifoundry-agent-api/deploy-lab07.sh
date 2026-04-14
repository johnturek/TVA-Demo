#!/usr/bin/env bash
# deploy-lab07.sh
# Builds and deploys the Lab07 AI Foundry Agent API (FastAPI) to Azure Container Apps.
# Reuses an existing ACR and Container Apps Environment (auto-discovered or set via LAB07_* env vars).
#
# Usage:
#   cd foundry-lab
#   bash labs/lab07-aifoundry-agent-api/deploy-lab07.sh

set -euo pipefail

# ── Status helpers ───────────────────────────────────────────────────────────

DEPLOY_START=${SECONDS}
STEP_NUM=0
STEP_START=${SECONDS}

step() {
  STEP_NUM=$((STEP_NUM + 1))
  STEP_START=${SECONDS}
  local label="$1"
  echo ""
  echo "┌──────────────────────────────────────────────────────────"
  echo "│ Step ${STEP_NUM} — ${label}"
  echo "└──────────────────────────────────────────────────────────"
}

step_done() {
  local elapsed=$(( SECONDS - STEP_START ))
  echo "  ✅ Done (${elapsed}s)"
}

status()  { echo "  ▸ $*"; }
ok()      { echo "  ✓ $*"; }
warn()    { echo "  ⚠ $*"; }
fail()    { echo "  ✗ $*"; }

elapsed_total() {
  local t=$(( SECONDS - DEPLOY_START ))
  local m=$(( t / 60 ))
  local s=$(( t % 60 ))
  printf '%dm %02ds' "$m" "$s"
}

# ── Resolve paths ────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOUNDRY_LAB_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${FOUNDRY_LAB_DIR}/.env"

# ── Load .env ────────────────────────────────────────────────────────────────

if [ ! -f "${ENV_FILE}" ]; then
  echo "ERROR: .env not found at ${ENV_FILE}"
  echo "Run the foundry-lab deploy.ps1 first to create it."
  exit 1
fi

# Source .env (skip comments and blank lines)
set -a
while IFS='=' read -r key value; do
  key=$(echo "$key" | xargs 2>/dev/null || true)
  [[ -z "$key" || "$key" == \#* ]] && continue
  value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  export "$key=$value" 2>/dev/null || true
done < "${ENV_FILE}"
set +a

# ── Configuration (from .env + az context) ───────────────────────────────────

SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:?Set AZURE_SUBSCRIPTION_ID in .env}"
LOCATION="${AZURE_LOCATION:-eastus2}"

# Container Apps infra — override via env or derive from az context
RESOURCE_GROUP="${LAB07_RESOURCE_GROUP:-}"
ACR_NAME="${LAB07_ACR_NAME:-}"
CONTAINER_ENV_NAME="${LAB07_CONTAINER_ENV_NAME:-}"

# AI Foundry project (for managed identity RBAC)
AI_FOUNDRY_RG="${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP in .env}"
AI_FOUNDRY_ACCOUNT="${AZURE_AI_FOUNDRY_ACCOUNT_NAME:?Set AZURE_AI_FOUNDRY_ACCOUNT_NAME in .env}"
AI_FOUNDRY_PROJECT="${AZURE_AI_PROJECT_NAME:?Set AZURE_AI_PROJECT_NAME in .env}"

CONTAINER_APP_NAME="${LAB07_CONTAINER_APP_NAME:-foundry-lab07-agent-api}"
IMAGE_NAME="lab07-agent-api"
IMAGE_TAG="v$(date +%Y%m%d-%H%M%S)"

# ── Auto-discover Container Apps infra if not set ────────────────────────────
# Finds the first ACR and Container Apps Environment in the subscription.

step "Preflight Checks"
status "Verifying Azure CLI login..."
az account show -o none 2>/dev/null || { fail "Not logged in. Run: az login"; exit 1; }
ok "Azure CLI logged in"
status "Setting subscription ${SUBSCRIPTION_ID}..."
az account set --subscription "${SUBSCRIPTION_ID}"

if [ -z "${ACR_NAME}" ]; then
  status "Auto-discovering ACR..."
  ACR_NAME=$(az acr list --subscription "${SUBSCRIPTION_ID}" --query "[0].name" -o tsv 2>/dev/null | xargs)
  if [ -z "${ACR_NAME}" ]; then
    fail "No ACR found. Set LAB07_ACR_NAME in .env or create one."
    exit 1
  fi
  ok "Found ACR: ${ACR_NAME}"
fi
RESOURCE_GROUP="${RESOURCE_GROUP:-$(az acr show --name "${ACR_NAME}" --query resourceGroup -o tsv 2>/dev/null | xargs)}"

if [ -z "${CONTAINER_ENV_NAME}" ]; then
  status "Auto-discovering Container Apps Environment..."
  CONTAINER_ENV_NAME=$(az resource list --resource-group "${RESOURCE_GROUP}" \
    --resource-type Microsoft.App/managedEnvironments --query "[0].name" -o tsv 2>/dev/null | xargs)
  if [ -z "${CONTAINER_ENV_NAME}" ]; then
    fail "No Container Apps Environment found in ${RESOURCE_GROUP}. Set LAB07_CONTAINER_ENV_NAME."
    exit 1
  fi
  ok "Found environment: ${CONTAINER_ENV_NAME}"
fi
CONTAINER_ENV_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/managedEnvironments/${CONTAINER_ENV_NAME}"

step_done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Lab07 — AI Foundry Agent API → Azure Container Apps"
echo "═══════════════════════════════════════════════════════════"
echo "  ACR:              ${ACR_NAME}"
echo "  Container App:    ${CONTAINER_APP_NAME}"
echo "  Image:            ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  Resource Group:   ${RESOURCE_GROUP}"
echo "  AI Foundry Acct:  ${AI_FOUNDRY_ACCOUNT}"
echo "  AI Foundry Proj:  ${AI_FOUNDRY_PROJECT}"
echo ""

# ── Build image in ACR ───────────────────────────────────────────────────────

step "Build Container Image in ACR"

IMAGE_REF="${IMAGE_NAME}:${IMAGE_TAG}"
ACR_LOGIN_SERVER=$(az acr show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" --query loginServer -o tsv)
FULL_IMAGE="${ACR_LOGIN_SERVER}/${IMAGE_REF}"

status "Image: ${FULL_IMAGE}"
status "Build context: ${SCRIPT_DIR}"

# Run az acr build in the background and show progress dots
az acr build \
  --registry "${ACR_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --image "${IMAGE_REF}" \
  "${SCRIPT_DIR}" \
  --no-logs &
BUILD_PID=$!

echo -n "  ▸ Building"
while kill -0 ${BUILD_PID} 2>/dev/null; do
  echo -n "."
  sleep 5
done
echo ""

# Check if the build succeeded
wait ${BUILD_PID}
BUILD_EXIT=$?
if [ ${BUILD_EXIT} -ne 0 ]; then
  fail "ACR build failed (exit code ${BUILD_EXIT})."
  echo "  Check logs: az acr task list-runs --registry '${ACR_NAME}' --resource-group '${RESOURCE_GROUP}' --top 1"
  exit 1
fi

# Verify the tag exists
status "Verifying image tag in registry..."
VERIFY=$(az acr repository show-tags --name "${ACR_NAME}" --repository "${IMAGE_NAME}" --query "[?contains(@, '${IMAGE_TAG}')]" -o tsv 2>/dev/null || true)
if [ -z "${VERIFY}" ]; then
  fail "Image tag ${IMAGE_TAG} not found in ACR after build."
  exit 1
fi
ok "Image confirmed: ${FULL_IMAGE}"
step_done

# ── Read .env and build secrets/env-vars ─────────────────────────────────────

step "Prepare Configuration"
status "Reading env vars from ${ENV_FILE}..."

declare -A ENV_SETTINGS
if [ -f "${ENV_FILE}" ]; then
  while IFS='=' read -r key value; do
    key=$(echo "$key" | xargs)
    if [ -z "$key" ] || [[ "$key" == \#* ]]; then continue; fi
    value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [ -n "$value" ]; then
      ENV_SETTINGS["$key"]="$value"
    fi
  done < "${ENV_FILE}"
fi

# Build ARM secrets and env-vars arrays
ARM_SECRETS='[{"name":"acr-password","value":"ACR_PW_PLACEHOLDER"}'
ARM_ENV_VARS='['
first_env=true

for key in "${!ENV_SETTINGS[@]}"; do
  secret_name=$(echo "$key" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
  ARM_SECRETS="${ARM_SECRETS},{\"name\":\"${secret_name}\",\"value\":\"${ENV_SETTINGS[$key]}\"}"
  if [ "$first_env" = true ]; then first_env=false; else ARM_ENV_VARS="${ARM_ENV_VARS},"; fi
  ARM_ENV_VARS="${ARM_ENV_VARS}{\"name\":\"${key}\",\"secretRef\":\"${secret_name}\"}"
done

ARM_SECRETS="${ARM_SECRETS}]"
ARM_ENV_VARS="${ARM_ENV_VARS}]"

ok "Loaded ${#ENV_SETTINGS[@]} env vars as container secrets"

# ── Get ACR credentials ──────────────────────────────────────────────────────

status "Fetching ACR credentials..."

ACR_USERNAME=$(az acr credential show --name "${ACR_NAME}" --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show --name "${ACR_NAME}" --query "passwords[0].value" -o tsv)

ARM_SECRETS=$(echo "${ARM_SECRETS}" | sed "s/ACR_PW_PLACEHOLDER/${ACR_PASSWORD}/")
ok "ACR credentials retrieved"
step_done

# ── Deploy Container App via az rest ─────────────────────────────────────────

step "Deploy Container App"
status "Deploying ${CONTAINER_APP_NAME} via Azure REST API..."

CONTAINER_APP_RESOURCE_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/containerApps/${CONTAINER_APP_NAME}"
API_VERSION="2024-03-01"

BODY_FILE=$(mktemp /tmp/lab07-deploy-XXXXXX.json)

cat > "${BODY_FILE}" <<EOJSON
{
  "location": "${LOCATION}",
  "properties": {
    "managedEnvironmentId": "${CONTAINER_ENV_ID}",
    "configuration": {
      "ingress": {
        "external": true,
        "targetPort": 8000,
        "transport": "auto"
      },
      "registries": [
        {
          "server": "${ACR_LOGIN_SERVER}",
          "username": "${ACR_USERNAME}",
          "passwordSecretRef": "acr-password"
        }
      ],
      "secrets": ${ARM_SECRETS}
    },
    "template": {
      "containers": [
        {
          "name": "lab07-agent-api",
          "image": "${FULL_IMAGE}",
          "env": ${ARM_ENV_VARS},
          "resources": {
            "cpu": 0.5,
            "memory": "1.0Gi"
          }
        }
      ],
      "scale": {
        "minReplicas": 1,
        "maxReplicas": 1
      }
    }
  }
}
EOJSON

az rest \
  --method PUT \
  --url "https://management.azure.com${CONTAINER_APP_RESOURCE_ID}?api-version=${API_VERSION}" \
  --body @"${BODY_FILE}" \
  -o none

rm -f "${BODY_FILE}"
ok "Container App deployed"

# Wait for provisioning to complete before modifying the app
status "Waiting for provisioning to complete..."
for i in $(seq 1 30); do
  PROV_STATE=$(az resource show --ids "${CONTAINER_APP_RESOURCE_ID}" \
    --query "properties.provisioningState" -o tsv 2>/dev/null || true)
  PROV_STATE=$(echo "${PROV_STATE}" | xargs)
  if [ "${PROV_STATE}" = "Succeeded" ]; then break; fi
  if [ "${PROV_STATE}" = "Failed" ]; then
    fail "Container App provisioning failed."
    exit 1
  fi
  sleep 5
done
if [ "${PROV_STATE}" != "Succeeded" ]; then
  fail "Container App provisioning did not complete within 150 seconds (state: ${PROV_STATE})."
  exit 1
fi
ok "Provisioning complete"
step_done

# ── Enable system-assigned Managed Identity ──────────────────────────────────
# DefaultAzureCredential in the container uses this identity to call AI Foundry.

step "Configure Managed Identity & RBAC"
status "Enabling system-assigned Managed Identity..."
az containerapp identity assign \
  --name "${CONTAINER_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --system-assigned \
  -o none

PRINCIPAL_ID=$(az containerapp show \
  --name "${CONTAINER_APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "identity.principalId" -o tsv)
ok "Identity enabled — Principal: ${PRINCIPAL_ID}"

# ── Assign Azure AI User role on AI Foundry account + project ────────────────

status "Assigning 'Azure AI User' role on AI Foundry account + project..."
AI_ACCOUNT_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${AI_FOUNDRY_RG}/providers/Microsoft.CognitiveServices/accounts/${AI_FOUNDRY_ACCOUNT}"
PROJECT_RESOURCE_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${AI_FOUNDRY_RG}/providers/Microsoft.CognitiveServices/accounts/${AI_FOUNDRY_ACCOUNT}/projects/${AI_FOUNDRY_PROJECT}"

az role assignment create \
  --assignee-object-id "${PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Azure AI User" \
  --scope "${AI_ACCOUNT_ID}" \
  -o none 2>&1 | grep -v "already exists" || true
ok "Azure AI User on AI Foundry account"

az role assignment create \
  --assignee-object-id "${PRINCIPAL_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "Azure AI User" \
  --scope "${PROJECT_RESOURCE_ID}" \
  -o none 2>&1 | grep -v "already exists" || true
ok "Azure AI User on AI Foundry project"
step_done

# ── Wait for FQDN ───────────────────────────────────────────────────────────

step "Wait for FQDN"
echo -n "  ▸ Polling"
APP_FQDN=""
for i in $(seq 1 18); do
  APP_FQDN=$(az resource show --ids "${CONTAINER_APP_RESOURCE_ID}" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || true)
  APP_FQDN=$(echo "${APP_FQDN}" | xargs)
  if [ -n "${APP_FQDN}" ]; then break; fi
  echo -n "."
  sleep 10
done
echo ""

if [ -z "${APP_FQDN}" ]; then
  fail "Container App created but FQDN not available after 3 minutes."
  exit 1
fi

APP_URL="https://${APP_FQDN}"
ok "FQDN ready: ${APP_FQDN}"
step_done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ DEPLOYMENT COMPLETE  ($(elapsed_total))"
echo "═══════════════════════════════════════════════════════════"
echo "  Container App:  ${CONTAINER_APP_NAME}"
echo "  FQDN:           ${APP_FQDN}"
echo "  Health:         ${APP_URL}/health"
echo "  Chat:           ${APP_URL}/chat"
echo "  Stream:         ${APP_URL}/chat/stream"
echo "  OpenAPI Docs:   ${APP_URL}/docs"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Test with:"
echo "    python labs/lab07-aifoundry-agent-api/test_lab07_api.py ${APP_URL}"
echo ""
