# TVA Workshop — Boilerplate Code Reference

Clone the repo: `git clone https://github.com/johnturek/TVA-Demo`

All boilerplate files live in `/boilerplate/`.

---

## 1. `docker-compose.yml` — TVA Backend Simulator

Spins up two containers: the TVA document API backend and the MCP server.

```yaml
version: '3.8'
services:
  tva-backend:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./backend:/app
    command: sh -c "npm install && node server.js"
    ports:
      - "3001:3001"
    environment:
      - PORT=3001
      - API_KEY=workshop-demo-key-2026
      - NODE_ENV=development

  tva-mcp:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./mcp-server:/app
    command: sh -c "npm install && node mcp-server.js"
    ports:
      - "3002:3002"
    environment:
      - PORT=3002
```

**Usage:** `docker compose up -d`
**Stop:** `docker compose down`

---

## 2. `upload-docs.py` — Batch Upload to AI Foundry Vector Index

```python
import os
import glob
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchFieldDataType
)
from azure.core.credentials import AzureKeyCredential

# --- CONFIG ---
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")  # e.g. https://xxx.search.windows.net
SEARCH_KEY      = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME      = "tva-knowledge-base"
DOCS_FOLDER     = "./docs"

def upload_documents():
    credential = AzureKeyCredential(SEARCH_KEY)
    index_client = SearchIndexClient(SEARCH_ENDPOINT, credential)
    
    # Create index if not exists
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="filename", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="category", type=SearchFieldDataType.String, filterable=True),
    ]
    index = SearchIndex(name=INDEX_NAME, fields=fields)
    index_client.create_or_update_index(index)
    print(f"✅ Index '{INDEX_NAME}' ready")
    
    # Upload documents
    search_client = SearchClient(SEARCH_ENDPOINT, INDEX_NAME, credential)
    docs = []
    for i, filepath in enumerate(glob.glob(f"{DOCS_FOLDER}/*.txt") + glob.glob(f"{DOCS_FOLDER}/*.md")):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        filename = os.path.basename(filepath)
        docs.append({
            "id": str(i),
            "content": content,
            "filename": filename,
            "category": "tva-regulatory"
        })
        print(f"  📄 Queued: {filename}")
    
    result = search_client.upload_documents(docs)
    print(f"✅ Uploaded {len(docs)} documents")

if __name__ == "__main__":
    upload_documents()
```

**Key variables:** `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_KEY`, `DOCS_FOLDER`

---

## 3. `agent-template.yaml` — Copilot Studio Agent Definition

```yaml
kind: AdaptiveDialog
beginDialog:
  kind: OnRecognizedIntent
  id: main
  intent:
    displayName: Search TVA Documents
    triggerQueries:
      - search documents
      - find compliance requirement
      - what does NERC CIP say about
      - look up TVA policy
  actions:
    - kind: SendActivity
      id: thinking
      activity: Searching TVA knowledge base...

    - kind: HttpRequest
      id: queryFoundry
      url: >-
        ${config.AZURE_OPENAI_ENDPOINT}/openai/deployments/gpt-4o/chat/completions?api-version=2024-05-01-preview
      method: POST
      headers:
        Content-Type: application/json
        api-key: ${config.AZURE_OPENAI_KEY}
      body: >-
        {
          "messages": [
            {"role": "system", "content": "You are a TVA compliance assistant. Always cite sources."},
            {"role": "user", "content": "${turn.activity.text}"}
          ],
          "data_sources": [{
            "type": "azure_search",
            "parameters": {
              "endpoint": "${config.AZURE_SEARCH_ENDPOINT}",
              "index_name": "tva-knowledge-base",
              "authentication": {"type": "api_key", "key": "${config.AZURE_SEARCH_KEY}"}
            }
          }],
          "max_tokens": 800
        }
      resultVariable: Topic.FoundryResponse

    - kind: SendActivity
      id: respond
      activity: ${Topic.FoundryResponse.choices[0].message.content}
```

---

## 4. `setup-app-registration.ps1` — Azure App Registration for OBO

```powershell
# Prerequisites: az cli logged in, correct tenant selected
param(
    [string]$AppName = "tva-doc-processor",
    [string]$TenantId = $env:AZURE_TENANT_ID
)

Write-Host "Creating app registration: $AppName"

# Create the app
$app = az ad app create `
    --display-name $AppName `
    --sign-in-audience "AzureADMyOrg" `
    --output json | ConvertFrom-Json

$appId = $app.appId
Write-Host "✅ App ID: $appId"

# Add required API permissions
az ad app permission add `
    --id $appId `
    --api "00000003-0000-0000-c000-000000000000" `
    --api-permissions `
        "e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope" `  # User.Read
        "37f7f235-527c-4136-accd-4a02d197296e=Scope"     # openid

# Create service principal
az ad sp create --id $appId
Write-Host "✅ Service principal created"

# Create client secret
$secret = az ad app credential reset --id $appId --output json | ConvertFrom-Json
Write-Host "✅ Client Secret: $($secret.password)"
Write-Host ""
Write-Host "Save these values:"
Write-Host "  AZURE_CLIENT_ID=$appId"
Write-Host "  AZURE_CLIENT_SECRET=$($secret.password)"
Write-Host "  AZURE_TENANT_ID=$TenantId"
Write-Host "  APP_URI=api://$appId"
```

---

## 5. `obo-token-flow.py` — On-Behalf-Of Token Exchange

```python
import os
import requests

TENANT_ID     = os.getenv("AZURE_TENANT_ID")
CLIENT_ID     = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SCOPE         = "api://tva-doc-processor/.default"

def exchange_token_obo(user_access_token: str) -> str:
    """
    Exchange a user's access token for a token scoped to the TVA backend API.
    Call this in your APIM policy or backend middleware.
    """
    url = f"https://login.microsoftonline.us/{TENANT_ID}/oauth2/v2.0/token"
    
    data = {
        "grant_type":            "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "client_id":             CLIENT_ID,
        "client_secret":         CLIENT_SECRET,
        "assertion":             user_access_token,
        "scope":                 SCOPE,
        "requested_token_use":   "on_behalf_of"
    }
    
    response = requests.post(url, data=data)
    response.raise_for_status()
    
    token_data = response.json()
    return token_data["access_token"]

def call_tva_backend(user_token: str, query: str) -> dict:
    """Example: call TVA backend with OBO token"""
    obo_token = exchange_token_obo(user_token)
    
    headers = {
        "Authorization": f"Bearer {obo_token}",
        "Content-Type":  "application/json"
    }
    
    response = requests.post(
        "https://tva-workshop-apim.azure-api.net/tva/api/query",
        headers=headers,
        json={"query": query, "top": 3}
    )
    return response.json()

if __name__ == "__main__":
    # Test with a dummy token (replace with real token in production)
    print("OBO flow ready. Integrate with your APIM inbound policy.")
```

---

## 6. `mcp-server-stub.js` — MCP Server with TVA Docs

```javascript
const express = require('express');
const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3002;

// TVA knowledge base (pre-loaded public docs)
const TVA_DOCS = {
  "nerc-cip-007": {
    title: "NERC CIP-007 — Systems Security Management",
    content: "Requires entities to define methods, processes, and procedures for securing BES Cyber Systems. Patch management must occur within 35 days of availability for security patches. Ports and services must be reviewed every 15 months."
  },
  "nerc-cip-010": {
    title: "NERC CIP-010 — Configuration Change Management",
    content: "Requires baseline configurations for BES Cyber Systems. Changes must be documented and reviewed. Vulnerability assessments required annually for high/medium impact systems."
  },
  "tva-grid-reliability": {
    title: "TVA Grid Reliability Annual Report",
    content: "TVA's transmission system achieved 99.97% reliability in the reporting period. SAIDI improved 12% year-over-year. Brownsville and Cumberland facilities met all NERC TPL standards."
  },
  "nuclear-safety": {
    title: "TVA Nuclear Safety Procedures Overview",
    content: "Browns Ferry, Sequoyah, and Watts Bar operate under NRC license. Primary coolant temperature limits: 550°F normal operation, 620°F maximum. Emergency core cooling systems tested quarterly."
  }
};

// MCP tool definitions
const TOOLS = [
  {
    name: "search_tva_docs",
    description: "Search TVA regulatory and compliance documents",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Search query" },
        top: { type: "number", description: "Number of results (default 3)" }
      },
      required: ["query"]
    }
  },
  {
    name: "get_nerc_requirement",
    description: "Get specific NERC CIP standard requirements",
    inputSchema: {
      type: "object",
      properties: {
        standard: { type: "string", description: "NERC standard (e.g. CIP-007, CIP-010)" }
      },
      required: ["standard"]
    }
  },
  {
    name: "check_compliance_status",
    description: "Get TVA compliance posture for a given standard",
    inputSchema: {
      type: "object",
      properties: {
        standard: { type: "string" }
      },
      required: ["standard"]
    }
  }
];

// MCP endpoint
app.post('/mcp', (req, res) => {
  const { method, params } = req.body;

  if (method === 'tools/list') {
    return res.json({ tools: TOOLS });
  }

  if (method === 'tools/call') {
    const { name, arguments: args } = params;

    if (name === 'search_tva_docs') {
      const results = Object.values(TVA_DOCS)
        .filter(doc => doc.content.toLowerCase().includes(args.query.toLowerCase()) ||
                       doc.title.toLowerCase().includes(args.query.toLowerCase()))
        .slice(0, args.top || 3);
      return res.json({ content: [{ type: 'text', text: JSON.stringify(results) }] });
    }

    if (name === 'get_nerc_requirement') {
      const key = `nerc-${args.standard.toLowerCase().replace(' ', '-')}`;
      const doc = TVA_DOCS[key] || { title: "Not found", content: `No data for ${args.standard}` };
      return res.json({ content: [{ type: 'text', text: JSON.stringify(doc) }] });
    }

    if (name === 'check_compliance_status') {
      return res.json({
        content: [{
          type: 'text',
          text: JSON.stringify({
            standard: args.standard,
            status: "Compliant",
            lastAssessed: "2026-01-15",
            nextDue: "2026-07-15",
            findings: 0
          })
        }]
      });
    }

    return res.status(400).json({ error: `Unknown tool: ${name}` });
  }

  res.status(400).json({ error: `Unknown method: ${method}` });
});

app.get('/health', (_, res) => res.json({ status: 'ok', service: 'TVA MCP Server' }));

app.listen(PORT, () => console.log(`TVA MCP Server running on port ${PORT}`));
```

---

## 7. `test-agent.http` — REST Client Test File

Use with VS Code REST Client extension.

```http
### Health Check — TVA Backend
GET http://localhost:3001/health

###

### Health Check — MCP Server
GET http://localhost:3002/health

###

### Query TVA Backend Directly
POST http://localhost:3001/api/query
Content-Type: application/json
X-Api-Key: workshop-demo-key-2026

{
  "query": "NERC CIP-007 patch management requirements",
  "top": 3
}

###

### MCP — List Tools
POST http://localhost:3002/mcp
Content-Type: application/json

{
  "method": "tools/list",
  "params": {}
}

###

### MCP — Search TVA Docs
POST http://localhost:3002/mcp
Content-Type: application/json

{
  "method": "tools/call",
  "params": {
    "name": "search_tva_docs",
    "arguments": {
      "query": "nuclear plant safety",
      "top": 2
    }
  }
}

###

### Query via APIM (update URL with your suffix)
POST https://tva-workshop-apim.azure-api.net/tva-YOURNAME/api/query
Content-Type: application/json
X-Api-Key: workshop-demo-key-2026

{
  "query": "grid reliability performance",
  "top": 3
}

###

### Azure OpenAI Direct Test
POST {{$dotenv AZURE_OPENAI_ENDPOINT}}/openai/deployments/gpt-4o/chat/completions?api-version=2024-05-01-preview
Content-Type: application/json
api-key: {{$dotenv AZURE_OPENAI_KEY}}

{
  "messages": [
    {"role": "system", "content": "You are a TVA compliance assistant."},
    {"role": "user", "content": "What are the NERC CIP-007 patch requirements?"}
  ],
  "max_tokens": 500
}
```
