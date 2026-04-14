# MCP Workshop — PRM + APIM + OBO (FastMCP)

Workshop MCP server demonstrating **Protected Resource Metadata (PRM)**, **Azure API Management (APIM)** with `validate-jwt`, and **On-Behalf-Of (OBO)** token exchange — all over **Streamable HTTP** transport (not SSE).

## Architecture

```
MCP Client ──Bearer──▶ APIM (validate-jwt) ──▶ Container App (FastMCP)
                                                      │
                                                      ├── PRM metadata (no auth)
                                                      ├── MCP tools (Bearer required)
                                                      └── OBO ──▶ Microsoft Graph /me
```

- **Transport**: Streamable HTTP (`POST /mcp` with `Accept: application/json`)
- **Auth**: One Entra ID app serves as both the JWT audience (APIM) and the OBO confidential client
- **PRM**: `/.well-known/oauth-protected-resource` — unauthenticated, tells clients where to get tokens
- **OBO**: MCP server exchanges the caller's token for a Microsoft Graph token via `ConfidentialClientApplication.acquire_token_on_behalf_of()`

## Tools

| Tool | Auth | Category | Description |
|------|------|----------|-------------|
| **help** | Required | Help | Lists all available tools or returns detailed usage for a specific tool. Params: `tool_name` (optional). |
| **get_my_profile** | Required | OBO | Exchanges the caller's PRM bearer token for a Graph token via OBO, calls `GET /v1.0/me`, and returns the user's profile. |
| **analyze_policy** | Required | Federal Policy | Analyzes a federal policy question (regulations, compliance, cybersecurity, privacy, procurement) via the Federal Policy Analyst service. Params: `query` (required), `context` (optional). |

## Prerequisites

- Azure subscription with permissions to create resources
- Azure CLI 2.80+ (`az --version`)
- PowerShell 7+ (`pwsh`)
- An Entra ID tenant where you can create app registrations

## Deployment

Automated deployment via three PowerShell scripts, orchestrated by `deploy.ps1`:

```powershell
# Full deployment (Entra + Infrastructure + APIM)
.\deploy.ps1 -LabNum l01

# Skip steps that are already done
.\deploy.ps1 -LabNum l01 -SkipEntra
.\deploy.ps1 -LabNum l01 -SkipEntra -SkipInfrastructure

# Preview commands without executing
.\deploy.ps1 -LabNum l01 -WhatIf

# Walkthrough mode — pauses at each step with detailed explanations
.\deploy.ps1 -LabNum l01 -Walkthrough
```

### What gets created

| Script | Resources |
|--------|-----------|
| `setup-entra-apps.ps1` | Single app registration (audience + `mcp.invoke` scope + `MCP.User` app role + client secret for OBO + Graph `User.Read` permission), service principal, admin consent, user role assignment |
| `deploy-infrastructure.ps1` | Resource group, Azure Container Registry, Container Apps Environment, ACR image build, Container App with env vars from `.env` |
| `deploy-apim.ps1` | APIM Consumption instance, API with 4 operations (`POST /mcp`, `GET /mcp`, `DELETE /mcp`, `GET /.well-known/oauth-protected-resource`), `validate-jwt` inbound policy (skips auth on PRM endpoint) |

### Naming convention

- Resource group: `<prefix>-rg` (shared across labs)
- All other resources: `<prefix>-<labnum>-<resource>` (e.g. `mcp-workshop-l01-apim`)

## Setup

1. Clone this repo
2. Create a `.env` file based on `example.env` (populated automatically by `setup-entra-apps.ps1`)
3. Run `.\deploy.ps1 -LabNum l01`

## Run Locally

- Run via script: `.\run_mcp_server.ps1`
- Run directly: `python mcp_server.py`
- MCP endpoint: `http://localhost:8000/mcp`
- PRM metadata: `http://localhost:8000/.well-known/oauth-protected-resource`

Install dependencies: `pip install -r requirements.txt`

## Test

```powershell
.\test-endpoints.ps1
```

Acquires a token via device-code flow, then runs tests against both the Container App and APIM:

| Test | Expected |
|------|----------|
| PRM metadata (GET, no auth) | 200 + `resource` field |
| MCP POST without token | 401 Unauthorized |
| MCP initialize (POST, Bearer) | 200 + `protocolVersion` |
| MCP tools/list (POST, Bearer + session) | 200 + tool names |
| get_my_profile (tools/call, OBO) | 200 + displayName via Graph /me |
| help (tools/call) | 200 + tool categories |
| analyze_policy (tools/call) | 200 + policy analysis result |
| MCP DELETE without session | 400/405 |

## MCP Clients

### VS Code

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "workshop-mcp": {
      "url": "https://<CONTAINER_APP_FQDN>/mcp",
      "type": "http"
    }
  }
}
```

VS Code discovers PRM metadata automatically, acquires a token via the Windows broker (WAM), and sends it as a Bearer token. The app registration must have:

- **Public client redirect URIs** (added by `setup-entra-apps.ps1`): `https://login.microsoftonline.com/common/oauth2/nativeclient`, `http://localhost`, `ms-appx-web://microsoft.aad.brokerplugin/<CLIENT_ID>`
- **VS Code pre-authorized** (added by `setup-entra-apps.ps1`): Client ID `aebc6443-996d-45c2-90f0-388ff96faa56` with delegated permission `mcp.invoke`

### Copilot Studio

1. In Copilot Studio, go to **Tools** → **+ Add a tool** → **Model Context Protocol**
2. Select **Manual** type and fill in:

| Field | Value |
|-------|-------|
| **Client ID** | `<OAUTH_CLIENT_ID>` from `.env` |
| **Client secret** | `<OBO_CLIENT_SECRET>` from `.env` |
| **Authorization URL** | `https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/authorize` |
| **Token URL template** | `https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/token` |
| **Refresh URL** | `https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/token` |
| **Scopes** | `api://<OAUTH_CLIENT_ID>/mcp.invoke` |

3. Click **Create** — Copilot Studio generates a **Redirect URL**
4. Add the redirect URL to the app registration:

```powershell
.\add-reply-url.ps1 -TenantId "<TENANT_ID>" -AppClientId "<OAUTH_CLIENT_ID>" -ReplyUrl "<REDIRECT_URL_FROM_COPILOT_STUDIO>"
```

5. Return to Copilot Studio and complete the OAuth connection

### Add Users

Assign users to the `MCP.User` app role so they can access the MCP server:

```powershell
.\add-users.ps1 -TenantId "<TENANT_ID>" -AppClientId "<CLIENT_ID>" -Users "alice@contoso.com, bob@contoso.com"
```

## Environment Variables

### Required — MCP Server Configuration
- `MCP_REQUIRE_AUTH` — Enable PRM authentication (`true` or `false`)
- `MCP_PRM_METADATA_PATH` — Path to PRM metadata JSON file (e.g. `prm_metadata.json`)
- `MCP_SESSION_TOKEN_TTL_SECONDS` — TTL in seconds for cached MCP session tokens (e.g. `3600`)
- `FASTMCP_HOST` — Bind host (`0.0.0.0` for container, `127.0.0.1` for local)
- `FASTMCP_PORT` — Bind port (default: `8000`)
- `FASTMCP_SCHEME` — URL scheme for PRM metadata (`http` for local, `https` for production)

### Required — OAuth / Device-Code Flow
- `OAUTH_AUTHORIZATION_URL` — Entra v2.0 authorization endpoint
- `OAUTH_TOKEN_URL` — Entra v2.0 token endpoint
- `OAUTH_DEVICE_CODE_URL` — Entra device-code endpoint
- `OAUTH_CLIENT_ID` — App registration client ID (same app used for OBO)
- `OAUTH_SCOPES` — Scopes (e.g. `api://<CLIENT_ID>/mcp.invoke`)
- `OAUTH_TIMEOUT_SECONDS` — Device-code polling timeout in seconds (e.g. `900`)

### Required — OBO (On-Behalf-Of)
- `OBO_CLIENT_ID` — Same as `OAUTH_CLIENT_ID` (single-app model)
- `OBO_CLIENT_SECRET` — App client secret (created by `setup-entra-apps.ps1`)
- `OBO_TENANT_ID` — Entra tenant ID
- `OBO_SCOPE` — Downstream scope (e.g. `https://graph.microsoft.com/.default`)

### Optional
- `OAUTH_CLIENT_SECRET` — Not needed for public-client device-code flow


## PRM (Protected Resource Metadata)

The MCP server serves PRM metadata at:
`/.well-known/oauth-protected-resource`

The `prm_metadata.json` file is a structural template. At runtime, `authorization_servers` and `scopes_supported` are dynamically set from `OAUTH_TOKEN_URL` and `OAUTH_CLIENT_ID` environment variables. The `resource` field is set from the request origin. All three values are required — missing env vars cause an immediate startup error.

When deployed behind APIM, the PRM endpoint is served without authentication (the `validate-jwt` policy uses a `<choose>` block to skip auth for the `prm-metadata` operation).

## APIM Policy

The `validate-jwt` inbound policy:
- Validates bearer tokens against the Entra v2.0 OpenID configuration
- Accepts audiences `api://<CLIENT_ID>` and raw `<CLIENT_ID>`
- Accepts issuers `https://login.microsoftonline.com/<TENANT_ID>/v2.0` and `https://sts.windows.net/<TENANT_ID>/`
- Skips validation on the PRM metadata endpoint

## OBO Flow

The `get_my_profile` tool demonstrates On-Behalf-Of:
1. MCP client sends a bearer token (issued for the API app audience)
2. APIM validates the token and forwards the request
3. The MCP server extracts the bearer token from the `Authorization` header
4. MSAL `ConfidentialClientApplication.acquire_token_on_behalf_of()` exchanges it for a Microsoft Graph token
5. The server calls `GET https://graph.microsoft.com/v1.0/me` and returns the user's profile
