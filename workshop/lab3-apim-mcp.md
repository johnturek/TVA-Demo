# Lab 3: APIM + MCP Integration — Deploy to Production
**Duration:** 90 minutes | **Session:** 3 of 3 | **Presenter:** JT

> 📚 **Microsoft Learn:** [Azure API Management overview](https://learn.microsoft.com/en-us/azure/api-management/api-management-key-concepts) | [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/) | [Copilot Studio MCP](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-mcp)

---

## Objectives
By the end of this lab, participants will have:
- **A production-ready MCP server on Azure Container Apps** — live, secured, shareable URL
- Azure APIM configured with Entra ID JWT validation
- Copilot Studio agent calling the backend securely via APIM
- Understanding of OBO token flow for production-grade auth
- Know when to use MCP vs agent flows vs sub-agent models

---

## Prerequisites
- Labs 1 and 2 complete
- Azure CLI installed and logged in (`az login`)
- PowerShell 7+ installed (`pwsh --version`)
- Your agent from Lab 2 open in Copilot Studio

> ℹ️ **No Docker required.** This lab deploys directly to Azure. If you want to iterate locally first, see [Appendix: Local Development with Docker](#appendix-local-development-with-docker) at the bottom.

---

## Part 1: Deploy the Full Azure Stack (25 min)

This is the core of Lab 3 — one script deploys everything to Azure.

> 📚 **MS Learn:** [Deploy to Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/quickstart-portal) | [APIM with Container Apps backend](https://learn.microsoft.com/en-us/azure/api-management/import-container-app-with-oas)

### Step 1: Run the Provisioning Script

```bash
cd ~/TVA-Demo/boilerplate/mcp-backend
pwsh ./deploy.ps1 -LabNum l01 -Walkthrough
```

> 💡 **Use `-Walkthrough`** — it pauses at each step with detailed explanations of what's being deployed and why. This is the teaching version.

This script (~15 min) automatically:
1. Creates an **Entra ID app registration** with correct API permissions (OAuth scopes, app roles, PRM metadata)
2. Builds and pushes your MCP server image to **Azure Container Registry**
3. Deploys the MCP server as a **Container App** (publicly accessible HTTPS endpoint)
4. Provisions **APIM** in front of it with JWT validation policy
5. Updates your `.env` with all credentials and endpoints

### Step 2: Review the Outputs
When the script completes, you'll see:
```
==================== APIM OUTPUTS ====================
APIM_NAME:      mcp-workshop-l01-apim
APIM_GATEWAY:   https://mcp-workshop-l01-apim.azure-api.net
MCP_ENDPOINT:   https://mcp-workshop-l01-apim.azure-api.net/mcp
PRM_METADATA:   https://mcp-workshop-l01-apim.azure-api.net/.well-known/oauth-protected-resource
BACKEND_URL:    https://mcp-workshop-l01-mcp.agreeabledune-xxx.eastus2.azurecontainerapps.io
JWT_AUDIENCE:   api://[your-app-id]
JWT_ISSUER:     https://login.microsoftonline.us/[tenant-id]/v2.0
=======================================================
```

### Step 3: Verify the Deployment
```bash
# Check PRM metadata (no auth needed)
curl -sf https://mcp-workshop-l01-apim.azure-api.net/.well-known/oauth-protected-resource | python3 -m json.tool

# Get a token and call the MCP endpoint
TOKEN=$(az account get-access-token --resource $JWT_AUDIENCE --query accessToken -o tsv)
curl -X POST $MCP_ENDPOINT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

> ⚠️ **Vignette: APIM provisioning takes 10-15 minutes**
> The Consumption tier APIM is fast to create but still takes time. The script is idempotent — safe to re-run if it fails mid-way.
>
> 📚 [APIM tiers comparison](https://learn.microsoft.com/en-us/azure/api-management/api-management-features)

---

## Part 2: Understand the Architecture (10 min)

### What `deploy.ps1` Built

```
User
  │
  ▼
Copilot Studio Agent
  │  (Entra ID SSO — user's identity forwarded)
  ▼
Azure APIM  ──── JWT validation (`validate-azure-ad-token` policy)
  │           ──── CORS policy
  │           ──── Rate limiting
  ▼
Azure Container Apps (TVA MCP Server)
  │  (always-on, auto-scaling, HTTPS)
  ▼
TVA Knowledge Base (Azure AI Search + AI Foundry)
```

### The Four Layers
1. **Entra ID** — Identity: Who is calling? (OAuth 2.0 / JWT tokens)
2. **APIM** — Gateway: Is the caller allowed in? (validate-jwt policy)
3. **Container App** — Server: The FastMCP server that runs the tools
4. **OBO** — Downstream: Call Microsoft Graph AS the user (On-Behalf-Of)

---

## Part 3: Connect MCP to Copilot Studio (15 min)

MCP (Model Context Protocol) lets your agent call structured tools instead of free-form HTTP.

### What's Running in the Workshop MCP Server
Your deployed MCP server exposes these tools via Streamable HTTP at `/mcp`:
- `help` — list all tools and usage
- `get_my_profile` — OBO demo: fetches the authenticated user's Graph profile
- `analyze_policy` — Federal Policy Analyst: answers compliance/regulatory questions

> 🚨 **Transport Warning: SSE is no longer supported**
> Copilot Studio dropped **SSE (Server-Sent Events)** transport support after August 2025. Your MCP server **must** use **Streamable HTTP** transport. The workshop MCP server is already configured for this.

### Connect MCP to Copilot Studio
1. In your agent, go to the **Tools** page
2. Click **Add a tool** → **New tool** → **Model Context Protocol**
3. A setup wizard opens — fill in:
   - **Server name:** `TVA MCP Server`
   - **Description:** `TVA document search and NERC compliance tools`
   - **URL:** Your `MCP_ENDPOINT` from deploy output (e.g. `https://mcp-workshop-l01-apim.azure-api.net/mcp`)
   - **Authentication:** OAuth 2.0 → configure with your `JWT_AUDIENCE` and Entra ID endpoints
4. Complete the wizard — tools surface automatically

> 📚 [Connect Copilot Studio to an MCP server](https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent)

### Test MCP Tools
In the Test panel:
- "What are the FedRAMP requirements for cloud services?" → should call `analyze_policy`
- "Show me available tools" → should call `help`
- "Who am I?" → should call `get_my_profile` (OBO demo)

---

## Part 4: OBO Token Flow (10 min)

For production TVA deployment, the agent must pass the user's identity to backend systems — not a service account.

### Why OBO Matters for TVA
- **Audit trail:** NERC CIP requires logging who accessed compliance data
- **Role-based access:** Nuclear plant data vs. grid data have different clearance levels
- **User context:** Responses can be personalized to the user's division

### The Flow
```
User → Copilot Studio → [user token] → APIM → [OBO exchange] → Backend API
                                          ↑
                                    Token validation
                                    + user context added
```

### APIM Policy for OBO
```xml
<inbound>
  <base />
  <validate-azure-ad-token header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized">
    <client-application-ids>
      <application-id>api://tva-doc-processor</application-id>
    </client-application-ids>
    <audiences>
      <audience>api://tva-doc-processor</audience>
    </audiences>
  </validate-azure-ad-token>
  <set-header name="X-TVA-UserId" exists-action="override">
    <value>@(context.Request.Headers.GetValueOrDefault("Authorization","").Split(' ').Last().Split('.')[1])</value>
  </set-header>
</inbound>
```

See `boilerplate/obo-token-flow.py` for the full Python implementation.

> ⚠️ **Vignette: Token expiry mid-conversation**
> Azure AD tokens expire after 1 hour. For long workshop sessions, users may get auth errors mid-lab. Fix: in Copilot Studio settings, enable **Token refresh** under Authentication. In production, implement refresh token handling in your backend.

---

## Part 5: When to Use What — Decision Tree (10 min)

```
User needs info from a document/knowledge base?
  └── YES → Use Knowledge Source (Azure AI Search connected to Foundry)
  
User needs to trigger an action or workflow?
  └── YES → Is the action a well-defined tool with a schema?
        ├── YES → Use MCP (cleaner, model picks the right tool)
        └── NO → Use Agent Flow / HTTP Action (more control)

Multiple specialized agents needed?
  └── YES → Use Sub-agent model (orchestrator + specialist agents)
  └── NO → Keep it in one agent with topics

Needs to work across Teams, web, mobile, API?
  └── YES → Use Agent SDK (consistent identity across channels)
```

**Rule of thumb for TVA:**
- **Read-only compliance queries** → Knowledge source
- **Structured lookups** (get NERC requirement by ID) → MCP
- **Multi-step workflows** (submit variance request, escalate finding) → Agent flow
- **Cross-system orchestration** → Sub-agent model

---

## Part 6: End-to-End Demo (20 min)

Run this conversation to show the full stack working:

1. **User:** "What are TVA's patch management requirements under NERC CIP-007?"
   - *Should: call MCP `analyze_policy`, return structured answer*

2. **User:** *(uploads `tva-compliance-report-q1.pdf`)* "Review this for compliance gaps"
   - *Should: process file, call Azure AI Foundry, return gap analysis*

3. **User:** "Search for any documents about Browns Ferry nuclear plant procedures"
   - *Should: call APIM backend, return document list with metadata*

4. **User:** "Summarize the top 3 risks"
   - *Should: use conversation context, return prioritized risk summary*

---

## Lab 3 Checkpoint ✅

- [ ] `deploy.ps1` ran successfully (all 4 steps passed)
- [ ] Production MCP endpoint responds to authenticated requests
- [ ] PRM metadata returns valid JSON at `/.well-known/oauth-protected-resource`
- [ ] MCP tools discovered and connected in Copilot Studio
- [ ] MCP tool called automatically in at least one test conversation
- [ ] OBO flow explained and APIM policy reviewed
- [ ] End-to-end demo conversation works against live Azure backend

---

## Learn More
| Topic | Microsoft Learn Link |
|-------|---------------------|
| Azure Container Apps | https://learn.microsoft.com/en-us/azure/container-apps/ |
| APIM Entra ID token validation | https://learn.microsoft.com/en-us/azure/api-management/validate-azure-ad-token-policy |
| APIM + Entra ID | https://learn.microsoft.com/en-us/azure/api-management/api-management-howto-protect-backend-with-aad |
| Copilot Studio MCP | https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-mcp |
| Connect MCP server | https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent |
| OBO token flow | https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow |
| Container Apps auth (Entra ID) | https://learn.microsoft.com/en-us/azure/container-apps/authentication-entra |

---

## Executive Takeaway
This is the pattern every government AI deployment should follow: the user talks to Copilot in plain English, Copilot routes to the right system through a secure API gateway, and every request is logged with the user's identity. TVA's compliance team gets AI capability without compromising the audit controls NERC CIP requires.

**What TVA owns at the end of today:** A production-ready, Entra ID–secured, auto-scaling AI agent connected to TVA's own knowledge base — deployed in Azure, accessible from Teams, and ready for real users.

---

## Appendix: Local Development with Docker

> ℹ️ **This section is optional.** Use it if you want to iterate on the MCP server locally before deploying to Azure, or if Azure provisioning is still running.

### Start the Local MCP Server
```bash
cd ~/TVA-Demo/boilerplate
docker compose up -d
```

This starts the MCP server on **port 8000** with auth disabled.

### Verify It's Running
```bash
curl -sf http://localhost:8000/.well-known/oauth-protected-resource
# Expected: JSON PRM metadata object

# Test the MCP endpoint
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

> ⚠️ **Docker tips:**
> - Run from `~/TVA-Demo/boilerplate/` (not the repo root)
> - If port 8000 is in use: `lsof -i :8000`
> - Copy env file if missing: `cp mcp-backend/example.env mcp-backend/.env`
> - In Codespaces, Docker works via docker-in-docker (pre-configured in devcontainer)

### Stop Local Containers
```bash
npx just clean   # or: docker compose down --volumes
```
