# GCC Tenant — Endpoint Reference

> ⚠️ **This workshop runs on a GCC (Government Community Cloud) tenant.** M365 and Entra ID endpoints use `.us` domains, not `.com`. Azure services remain on commercial cloud.

## Endpoint Mapping

| Service | Commercial (worldwide) | **GCC (use this)** |
|---------|----------------------|-------------------|
| Entra ID login | `login.microsoftonline.com` | **`login.microsoftonline.us`** |
| Microsoft Graph | `graph.microsoft.com` | **`graph.microsoft.us`** |
| Copilot Studio | `copilotstudio.microsoft.com` | **`copilotstudio.microsoft.us`** |
| Azure Portal | `portal.azure.com` | `portal.azure.com` (same) |
| Azure AI Foundry | `ai.azure.com` | `ai.azure.com` (same — commercial) |
| Azure OpenAI | `*.openai.azure.com` | `*.openai.azure.com` (same — commercial) |

## What This Means for the Workshop

### Entra ID / OAuth
All OAuth URLs must use `.us`:
```
# ✅ GCC
https://login.microsoftonline.us/{tenant-id}/oauth2/v2.0/authorize
https://login.microsoftonline.us/{tenant-id}/oauth2/v2.0/token
https://login.microsoftonline.us/{tenant-id}/oauth2/v2.0/devicecode

# ❌ NOT this
https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/...
```

### OBO / Graph API
```
# ✅ GCC
OBO_SCOPE=https://graph.microsoft.us/.default
Graph endpoint: https://graph.microsoft.us/v1.0/me

# ❌ NOT this
OBO_SCOPE=https://graph.microsoft.com/.default
```

### APIM JWT Validation
The issuer in your `validate-jwt` policy must be:
```
https://login.microsoftonline.us/{tenant-id}/v2.0
```

### Copilot Studio
Access at `https://copilotstudio.microsoft.us` (not `.com`)

### Azure (stays commercial)
Azure portal, AI Foundry, OpenAI, Container Apps, APIM — all use normal commercial endpoints. No changes needed for Azure-side resources.

## .env File for GCC

When running `deploy.ps1` or setting up manually, ensure your `.env` has:
```env
OAUTH_AUTHORIZATION_URL=https://login.microsoftonline.us/{tenant-id}/oauth2/v2.0/authorize
OAUTH_TOKEN_URL=https://login.microsoftonline.us/{tenant-id}/oauth2/v2.0/token
OAUTH_DEVICE_CODE_URL=https://login.microsoftonline.us/{tenant-id}/oauth2/v2.0/devicecode
OBO_SCOPE=https://graph.microsoft.us/.default
```

## Quick Test
```bash
# Verify you're hitting the right Entra endpoint
curl -s https://login.microsoftonline.us/{tenant-id}/v2.0/.well-known/openid-configuration | jq .issuer
# Should return: "https://login.microsoftonline.us/{tenant-id}/v2.0"
```
