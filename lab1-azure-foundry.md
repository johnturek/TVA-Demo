# Lab 1: Azure AI Foundry Setup
**Duration:** 90 minutes | **Session:** 1 of 3 | **Presenter:** Kevin

> 📚 **Microsoft Learn:** [Azure AI Foundry documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/) | [What is Azure AI Foundry?](https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-ai-foundry)

---

## Objectives
By the end of this lab, participants will have:
- A working Azure AI Foundry project connected to the demo tenant
- A vector index loaded with TVA regulatory and compliance documents
- A deployed gpt-4o endpoint
- Verified RAG queries returning TVA-relevant answers

---

## Prerequisites
- Access to JT's demo tenant (credentials distributed at check-in)
- Azure portal access: https://portal.azure.com
- Python 3.9+ installed (for boilerplate scripts)
- VS Code or any text editor

---

## Part 1: Create Your AI Foundry Project (20 min)

> 📚 **MS Learn:** [Quickstart — Create an Azure AI Foundry project](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/quickstart?pivots=ai-foundry-portal) | [Manage Azure AI Foundry hubs and projects](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/ai-foundry-hubs-projects-overview)

### Step 1: Open Azure AI Foundry
1. Navigate to https://ai.azure.com
2. Sign in with your demo tenant credentials
3. Click **+ New project**

### Step 2: Configure the Project
Fill in:
- **Project name:** `tva-doc-processor-[yourname]`
- **Hub:** Select the pre-provisioned `TVA-Workshop-Hub`
- **Region:** East US 2

Click **Create project** and wait ~2 minutes.

### Step 3: Verify Deployment
Once created, confirm you see:
- ✅ Project dashboard
- ✅ Connected resources (Azure OpenAI, Storage)
- ✅ gpt-4o model listed under **Models + endpoints**

> ⚠️ **Vignette: "No hubs available"**
> If you don't see the workshop hub, you may be in the wrong subscription. Click your name (top right) → **Switch directory** → select the workshop tenant.
>
> 📚 [Manage access to Azure AI Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/rbac-azure-ai-foundry)

---

## Part 2: Upload TVA Documents (25 min)

> 📚 **MS Learn:** [Add data to your project](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/data-add) | [Create and manage an Azure AI Search index](https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search)

We'll load the following TVA-relevant documents into the knowledge base:
- TVA NERC CIP Compliance Summary (provided in `/docs` folder)
- Grid Reliability Annual Report excerpt
- Nuclear Plant Safety Procedures overview
- Regulatory Affairs policy memo template

### Step 1: Navigate to Vector Index
1. In your project, click **Data + indexes** in the left nav
2. Click **+ New index**
3. Select **Upload files**

### Step 2: Upload Documents
1. Click **Browse** and select all files from the workshop `/docs` folder
2. Set index name: `tva-knowledge-base`
3. Leave chunking at default (512 tokens, 10% overlap)
4. Click **Next**

> 📚 [Understand data chunking in Azure AI Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/retrieval-augmented-generation)

### Step 3: Configure Embedding
- **Embedding model:** `text-embedding-ada-002`
- **Search type:** Hybrid (keyword + vector)
- Click **Create**

Indexing takes 3–5 minutes.

> ⚠️ **Vignette: Indexing stuck at 0%**
> This usually means the storage account hasn't finished provisioning. Wait 2 minutes and refresh. If still stuck, delete the index and recreate it — first-time provisioning occasionally needs a retry.
>
> 📚 [Troubleshoot Azure AI Search indexers](https://learn.microsoft.com/en-us/azure/search/search-indexer-troubleshooting)

### Step 4: Verify Index via Python

```python
# See boilerplate/upload-docs.py for the full script
import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY      = os.getenv("AZURE_SEARCH_KEY")

credential = AzureKeyCredential(SEARCH_KEY)
client = SearchIndexClient(SEARCH_ENDPOINT, credential)

for idx in client.list_indexes():
    print(f"Index: {idx.name}")
```

> 📚 [azure-search-documents Python SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/search-documents-readme)

---

## Part 3: Deploy gpt-4o Endpoint (15 min)

> 📚 **MS Learn:** [Deploy models in Azure AI Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/deployments-overview) | [Azure OpenAI models](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models)

### Step 1: Navigate to Models + Endpoints
1. Click **Models + endpoints** in left nav
2. Find `gpt-4o` in the deployment list (pre-provisioned for workshop)
3. Click the deployment name → copy the **Target URI** and **API Key**

Save these — you'll need them in Lab 2:
```
AZURE_OPENAI_ENDPOINT=https://tva-workshop.openai.azure.com/
AZURE_OPENAI_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

> ⚠️ **Vignette: Quota exceeded (429 error)**
> The workshop hub has shared quota. If you hit `429 TooManyRequests`, wait 30 seconds and retry. Do NOT create a new deployment — it pulls from the same shared pool.
>
> 📚 [Azure OpenAI quotas and limits](https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits)

---

## Part 4: Test RAG Queries (30 min)

> 📚 **MS Learn:** [Use your data with Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/use-your-data) | [Azure OpenAI On Your Data reference](https://learn.microsoft.com/en-us/azure/ai-services/openai/references/on-your-data)

### Step 1: Use the Playground
1. Click **Playgrounds** → **Chat**
2. Under **Add your data**, select your `tva-knowledge-base` index
3. Set system prompt:

```
You are the TVA Document Processor assistant. You help TVA engineers and compliance
officers find answers in TVA regulatory documents, NERC CIP compliance reports, and
grid reliability data. Always cite the source document and section number when answering.
If information is not in the provided documents, say so clearly.
```

### Step 2: Run Test Queries
Try each of these — verify the response cites a document:

| Query | Expected Source |
|-------|----------------|
| "What are TVA's NERC CIP-007 patch management requirements?" | NERC CIP Compliance Summary |
| "What was TVA's grid reliability performance last year?" | Grid Reliability Annual Report |
| "What coolant temperature limits apply to Browns Ferry?" | Nuclear Safety Procedures |
| "How do I submit a regulatory variance request?" | Regulatory Affairs memo |

### Step 3: REST API Test

```bash
curl -X POST "$AZURE_OPENAI_ENDPOINT/openai/deployments/gpt-4o/chat/completions?api-version=2024-05-01-preview" \
  -H "Content-Type: application/json" \
  -H "api-key: $AZURE_OPENAI_KEY" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a TVA compliance assistant."},
      {"role": "user", "content": "What are the NERC CIP-007 patch requirements?"}
    ],
    "data_sources": [{
      "type": "azure_search",
      "parameters": {
        "index_name": "tva-knowledge-base",
        "endpoint": "'"$AZURE_SEARCH_ENDPOINT"'",
        "authentication": {"type": "api_key", "key": "'"$AZURE_SEARCH_KEY"'"}
      }
    }],
    "max_tokens": 800
  }'
```

> 📚 [Azure OpenAI REST API reference](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference)

### Step 4: Python Integration Test

```python
# See boilerplate/upload-docs.py for full setup
import os
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-05-01-preview"
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a TVA compliance assistant. Cite sources."},
        {"role": "user", "content": "Summarize TVA's NERC CIP compliance posture."}
    ],
    extra_body={
        "data_sources": [{
            "type": "azure_search",
            "parameters": {
                "endpoint": os.getenv("AZURE_SEARCH_ENDPOINT"),
                "index_name": "tva-knowledge-base",
                "authentication": {
                    "type": "api_key",
                    "key": os.getenv("AZURE_SEARCH_KEY")
                }
            }
        }]
    }
)

print(response.choices[0].message.content)
if hasattr(response.choices[0].message, 'context'):
    for c in response.choices[0].message.context.get('citations', []):
        print(f"📄 Source: {c['title']}")
```

> 📚 [openai Python library for Azure](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/switching-endpoints)

> ⚠️ **Vignette: Responses not citing documents**
> If the model answers from general knowledge instead of your docs, check that **Add your data** is toggled ON in the playground. In API calls, verify the `data_sources` block is included — without it, the model ignores the index entirely.
>
> 📚 [Configure Azure OpenAI On Your Data](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/use-your-data#configuration)

---

## Lab 1 Checkpoint ✅

Before moving to lunch, verify:
- [ ] AI Foundry project created and accessible
- [ ] `tva-knowledge-base` index status = **Ready**
- [ ] gpt-4o endpoint URI and key saved
- [ ] At least 2 RAG queries returned document-cited answers
- [ ] Python test script runs without errors

**Save your endpoint URLs and keys** — you'll need them for Lab 2.

---

## Learn More
| Topic | Microsoft Learn Link |
|-------|---------------------|
| Azure AI Foundry overview | https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-ai-foundry |
| RAG concepts | https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/retrieval-augmented-generation |
| Azure AI Search overview | https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search |
| Azure OpenAI On Your Data | https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/use-your-data |
| Python SDK quickstart | https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart?pivots=programming-language-python |

---

## Executive Takeaway
TVA's compliance documents are now searchable by AI in plain English. An engineer asking "what are our patch requirements?" gets an instant, cited answer instead of searching through 200-page PDFs. This is the foundation everything else builds on.
