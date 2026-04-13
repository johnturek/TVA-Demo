#!/bin/bash
# Post-create setup for TVA Workshop Codespace / devcontainer
set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          TVA Workshop — Environment Setup                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 1. Submodules (best-effort — mcp-backend is now inline, no submodules required)
echo "⏳ Checking submodules..."
git submodule update --init --recursive 2>/dev/null || true
echo "   ✅ Submodules checked"

# 2. Node dependencies
echo "⏳ Installing Node.js dependencies..."
npm install --quiet 2>&1 | tail -1
echo "   ✅ Node.js ready"

# 3. Python dependencies (MCP server + Foundry labs)
echo "⏳ Installing Python dependencies..."
pip install --quiet \
  -r boilerplate/mcp-backend/requirements.txt \
  -r boilerplate/mcp-backend/foundry-lab/requirements.txt \
  2>&1 | tail -1 || true
echo "   ✅ Python ready"

# 4. Copy .env template and auto-populate from Codespace secrets
if [ ! -f .env ]; then
  cp .env.example .env
  echo "   ✅ Created .env from template"
else
  echo "   ✅ .env already exists"
fi

# Auto-wire Codespace secrets into .env if available
# Repo owner: add these as Codespace secrets in repo Settings → Secrets → Codespaces
ENV_VARS=(
  AZURE_AI_PROJECT_ENDPOINT
  AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_KEY
  AZURE_OPENAI_DEPLOYMENT
  AZURE_AGENT_NAME
  FOUNDRY_AGENT_ENDPOINT
  FOUNDRY_AGENT_KEY
  AZURE_AI_FOUNDRY_ACCOUNT_NAME
  AZURE_SEARCH_SERVICE_NAME
  AZURE_SEARCH_ENDPOINT
  AZURE_SEARCH_ADMIN_KEY
  AZURE_SEARCH_INDEX_NAME
  AZURE_OPENAI_EMBEDDING_DEPLOYMENT
  AZURE_OPENAI_DEPLOYMENT_NAME
  OAUTH_CLIENT_ID
  OAUTH_CLIENT_SECRET
  OBO_CLIENT_ID
  OBO_CLIENT_SECRET
  OBO_TENANT_ID
)

secrets_found=0
for var in "${ENV_VARS[@]}"; do
  val="${!var}"
  if [ -n "$val" ]; then
    sed -i "s|^${var}=.*|${var}=${val}|" .env
    secrets_found=$((secrets_found + 1))
  fi
done

if [ "$secrets_found" -gt 0 ]; then
  echo "   ✅ Auto-populated $secrets_found values from Codespace secrets"
else
  echo "   ℹ️  No Codespace secrets found — fill in .env manually (see GETTING-STARTED.md)"
fi

# Also create MCP backend .env for local dev if missing
MCP_ENV="boilerplate/mcp-backend/.env"
if [ ! -f "$MCP_ENV" ]; then
  cp boilerplate/.env.workshop-local "$MCP_ENV"
  echo "   ✅ Created MCP backend .env for local dev"
fi

# 5. Verify tools
echo ""
echo "── Installed Tools ──────────────────────────────────────"
printf "   Node.js:     %s\n" "$(node --version 2>/dev/null || echo 'NOT FOUND')"
printf "   Python:      %s\n" "$(python3 --version 2>/dev/null || echo 'NOT FOUND')"
printf "   PowerShell:  %s\n" "$(pwsh --version 2>/dev/null || echo 'NOT FOUND')"
printf "   Azure CLI:   %s\n" "$(az version --query '\"azure-cli\"' -o tsv 2>/dev/null || echo 'NOT FOUND')"
printf "   Docker:      %s\n" "$(docker --version 2>/dev/null || echo 'NOT FOUND')"
echo "───────────────────────────────────────────────────────"

if [ "$secrets_found" -gt 0 ]; then
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║  ✅  WORKSHOP ENVIRONMENT READY                          ║"
  echo "║                                                          ║"
  echo "║  📋 Open GETTING-STARTED.md for your next steps          ║"
  echo "║  🔑 Credentials pre-loaded from Codespace secrets        ║"
  echo "║  👉 Run: az login --use-device-code                      ║"
  echo "╚══════════════════════════════════════════════════════════╝"
else
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║  ✅  WORKSHOP ENVIRONMENT READY                          ║"
  echo "║                                                          ║"
  echo "║  📋 Open GETTING-STARTED.md for your next steps          ║"
  echo "║  🔑 First: az login --use-device-code                    ║"
  echo "║  📝 Then:  Fill in .env with values from check-in card   ║"
  echo "╚══════════════════════════════════════════════════════════╝"
fi
echo ""
