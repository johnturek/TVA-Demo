# GCC Copilot Studio Scripts

Portable scripts for managing Copilot Studio agents in **GCC (Government Community Cloud)** environments via direct Dataverse REST API — no LSP binary or VS Code extension required.

## Why?

The official Copilot Studio VS Code extension uses the Island API gateway, which requires a platform-specific `.NET` binary (`LanguageServerHost`). These scripts bypass that entirely by hitting the **Dataverse REST API** directly, making them work in:

- ✅ **Azure Cloud Shell** (via `az-cli` auth)
- ✅ **GitHub Codespaces** (via `device` code auth)
- ✅ **Local dev** (via `az-cli`, `msal` cache, or `device` code)
- ✅ **Any environment with Node.js** — no VS Code extension needed

## Setup

```bash
cd scripts
npm install
```

Set environment variables (or pass as CLI args):
```bash
export CPS_TENANT_ID="your-gcc-tenant-id"
export CPS_ENVIRONMENT_URL="https://yourorg.crm9.dynamics.com"
```

## Authentication

Auth mode is **auto-detected** in this order:

| Mode | How | Best For |
|------|-----|----------|
| `az-cli` | `az account get-access-token` | Cloud Shell, local with Azure CLI |
| `msal` | VS Code extension token cache | Local dev with Copilot Studio extension |
| `device` | MSAL device code flow (paste URL in browser) | Codespaces, headless servers |

Override with `--auth <mode>` or `CPS_AUTH_MODE` env var.

## Scripts

### List agents
```bash
node list-agents.js
```

### Clone an agent
```bash
node clone-agent.js --agent-id <guid> --output-dir ./MyAgent
```
Creates a local folder with `agent.yml`, `topics/`, `actions/`, `entities/`.

### Push changes
```bash
node push-agent.js --workspace ./MyAgent
```
Compares local YAML to Dataverse, updates changed topics, creates new ones.

### Publish
```bash
node publish-agent.js --agent-id <guid>
```

## Common Options

All scripts accept:
```
--tenant-id <id>          Azure AD tenant (or CPS_TENANT_ID env var)
--environment-url <url>   Dataverse URL (or CPS_ENVIRONMENT_URL env var)
--auth <mode>             Force auth mode: az-cli, device, msal
-h, --help                Show usage
```

## Workflow Example

```bash
# Cloud Shell or Codespace — no VS Code extension needed
export CPS_TENANT_ID="9b17922a-ed30-46e3-845d-94b577f0e53c"
export CPS_ENVIRONMENT_URL="https://org8a6d1179.crm9.dynamics.com"

cd scripts && npm install

# List agents to find the ID
node list-agents.js

# Clone, edit, push
node clone-agent.js --agent-id <guid> --output-dir ../my-agent
# ...edit topics YAML...
node push-agent.js --workspace ../my-agent

# Publish
node publish-agent.js --agent-id <guid>
```
