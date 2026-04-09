# Lab 1: Microsoft Foundry Setup
**Duration:** 90 minutes | **Session:** 1 of 3 | **Presenter:** Kevin

> 📚 **Microsoft Learn:** [Microsoft Foundry documentation](https://learn.microsoft.com/en-us/azure/foundry/) | [What is Microsoft Foundry?](https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry)

---

## Objectives
By the end of this lab, participants will have:
- A working Microsoft Foundry project connected to the demo tenant
- A vector index loaded with TVA regulatory and compliance documents
- A deployed gpt-4o endpoint
- A working AI agent using the Foundry Agent Service (File Search tool)

---

## Prerequisites
- Access to JT's demo tenant (credentials distributed at check-in)
- Azure portal access: https://portal.azure.com
- Python 3.9+ installed
- VS Code or any text editor

---

## Part 1: Create Your Foundry Project (20 min)

> 📚 **MS Learn:** [Quickstart — Create a Microsoft Foundry project](https://learn.microsoft.com/en-us/azure/foundry/quickstarts/get-started-code) | [Microsoft Foundry projects overview](https://learn.microsoft.com/en-us/azure/foundry/how-to/create-projects)

> ⚠️ **Note on naming:** Microsoft rebranded "Azure AI Foundry" to **Microsoft Foundry** in early 2026. The portal is still at **https://ai.azure.com** — click the **"New Foundry"** toggle at the top if you see the old interface. Hub-based projects are now labeled "classic" — use the new flow below. Note: "Azure AI Foundry" still appears in some SDK package names and service URLs (e.g. `azure-ai-projects`, `services.ai.azure.com`) — this is expected; the brand name changed but the underlying service identifiers haven't all been updated yet.

> ⚠️ **Important — SDK deprecation:** The classic Agents API (azure-ai-projects v1.x — threads/messages/runs pattern) is **deprecated** and will be retired **March 31, 2027**. This lab uses the **new Agents SDK (v2.x)** with the Conversations/Responses pattern. Do not use tutorials or examples that reference `create_thread()`, `create_message()`, or `list_messages()` — those are the old API.

### Step 1: Open Microsoft Foundry
1. Navigate to https://ai.azure.com
2. Sign in with your demo tenant credentials
3. If prompted, switch to the **New Foundry** experience (toggle, top-right)
4. Click **+ Create project**

### Step 2: Configure the Project
Fill in:
- **Project name:** `tva-doc-processor-[yourname]`
- **Foundry resource:** Select the pre-provisioned `TVA-Workshop-Foundry`
- **Region:** East US 2

> ⚠️ **No hub selection needed** — the new Foundry model uses a Foundry resource directly. If you see a "Hub" dropdown, you're in the classic view. Click the **New Foundry** toggle.

Click **Create project** and wait ~2 minutes.

### Step 3: Verify Deployment
Once created, confirm you see:
- ✅ Project dashboard
- ✅ Connected resources (Azure OpenAI, Storage)
- ✅ gpt-4o model listed under **Models + endpoints**

> ⚠️ **Vignette: Wrong subscription**
> If you don't see the workshop Foundry resource, click your name (top right) → **Switch directory** → select the workshop tenant.
>
> 📚 [Manage access to Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/concepts/rbac-foundry)

---

## Part 2: Upload TVA Documents (25 min)

> 📚 **MS Learn:** [Add data to your project](https://learn.microsoft.com/en-us/azure/foundry/how-to/data-add) | [Foundry Agent Service — File Search](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/file-search)

We'll load the following TVA-relevant documents into the agent's knowledge base:
- TVA NERC CIP Compliance Summary (provided in `/docs` folder)
- Grid Reliability Annual Report excerpt
- Nuclear Plant Safety Procedures overview
- Regulatory Affairs policy memo template

### Step 1: Navigate to Files

> ⚠️ **Two portal paths exist — use the new one:**
> - **New Foundry portal (use this):** From the project home page, click **Create an agent** → lands in the agent playground where you configure the agent inline.
> - **Classic portal (avoid):** `Agents → + New agent` in the left nav — this is the hub-based classic flow. If you see a left nav with "Agents", you may be in the classic experience.

1. From your project's home page, click **Create an agent**
2. In the agent playground, scroll to **Knowledge** → click **+ Add**
3. Select **Files** → upload all files from the workshop `/docs` folder

> 📚 [Foundry Agent Service overview](https://learn.microsoft.com/en-us/azure/foundry/agents/overview)

### Step 2: Configure the Agent
- **Agent name:** `TVA Document Processor`
- **Model:** `gpt-4o` (pre-provisioned)
- **Instructions:**
```
You are the TVA Document Processor assistant. You help TVA engineers and compliance
officers find answers in TVA regulatory documents, NERC CIP compliance reports, and
grid reliability data. Always cite the source document and section when answering.
If information is not in the provided documents, say so clearly.
```
- **Tools:** Enable **File Search**

Click **Save**.

> ⚠️ **Vignette: File upload stuck**
> If files are stuck at "Processing", wait 2–3 minutes — first-time vector store provisioning can be slow. Refresh the page. If still stuck, remove and re-upload the files.
>
> 📚 [Troubleshoot Foundry Agent file uploads](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/file-search)

### Step 3: Verify via Python

Install the SDK — **version 2.0.0+ is required**:
```bash
pip install "azure-ai-projects>=2.0.0" azure-identity
```

> ⚠️ **Version matters:** Without `>=2.0.0`, pip may install 1.x which uses the deprecated thread/message/run API. All code in this lab requires v2.x.

```python
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

project = AIProjectClient(
    endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    credential=DefaultAzureCredential()
)

# Get an OpenAI client scoped to this project
openai = project.get_openai_client()

# Quick test — chat completion
response = openai.chat.completions.create(
    model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
    messages=[{"role": "user", "content": "What is Azure AI Foundry?"}],
    max_tokens=100
)
print(response.choices[0].message.content)
```

> 📚 [azure-ai-projects Python SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-projects-readme)

---

## Part 3: Deploy gpt-4o Endpoint (15 min)

> 📚 **MS Learn:** [Deploy models in Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/deploy-models) | [Azure OpenAI models](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models)

### Step 1: Navigate to Models + Endpoints
1. Click **Models + endpoints** in left nav
2. Find `gpt-4o` in the deployment list (pre-provisioned for workshop)
3. Click the deployment name → copy the **Target URI** and **API Key**

Save these — you'll need them in Lab 2:
```
AZURE_OPENAI_ENDPOINT=https://tva-workshop.openai.azure.com/
AZURE_OPENAI_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_AI_PROJECT_ENDPOINT=https://tva-workshop.services.ai.azure.com/api/projects/tva-doc-processor-[yourname]

# Lab 2 uses these same values under these names:
FOUNDRY_AGENT_ENDPOINT=https://tva-workshop.services.ai.azure.com/api/projects/tva-doc-processor-[yourname]
FOUNDRY_AGENT_KEY=<same as AZURE_OPENAI_KEY above>
```

> ⚠️ **Vignette: Quota exceeded (429 error)**
> The workshop resource has shared quota. Wait 30 seconds and retry. Do NOT create a new deployment.
>
> 📚 [Azure OpenAI quotas and limits](https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits)

---

## Part 4: Test Agent Queries (30 min)

> 📚 **MS Learn:** [Foundry Agent Service quickstart](https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/prompt-agent) | [Build with agents, conversations, and responses](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/runtime-components)

### Step 1: Test in the Playground
1. Click **Agents** → select your `TVA Document Processor` agent
2. Click **Test in playground**
3. Run the following queries and verify each cites a document:

| Query | Expected Source |
|-------|----------------|
| "What are TVA's NERC CIP-007 patch management requirements?" | NERC CIP Compliance Summary |
| "What was TVA's grid reliability performance last year?" | Grid Reliability Annual Report |
| "What coolant temperature limits apply to Browns Ferry?" | Nuclear Safety Procedures |
| "How do I submit a regulatory variance request?" | Regulatory Affairs memo |

### Step 2: REST API Test

> ⚠️ **New API routes:** The classic `threads` endpoint with `api-version=2025-05-01` is deprecated. The new API uses `/openai/v1/` stable routes with no monthly api-version parameters. Terminology: Threads → Conversations, Messages → Items, Runs → Responses.

```bash
# Create a conversation (replaces "create thread")
PROJECT_ENDPOINT="https://tva-workshop.services.ai.azure.com/api/projects/tva-doc-processor-[yourname]"
AGENT_ID="<your-agent-id>"

curl -X POST "$PROJECT_ENDPOINT/openai/v1/conversations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(az account get-access-token --query accessToken -o tsv)" \
  -d "{\"agent_id\": \"$AGENT_ID\"}"
```

> 📚 [Foundry Agents REST API reference](https://learn.microsoft.com/en-us/rest/api/aifoundry/)

### Step 3: Python Integration Test

> ⚠️ **New SDK pattern (v2.x):** The old `create_thread()` / `create_message()` / `create_and_process_run()` / `list_messages()` methods and `MessageTextContent` import are from the deprecated classic SDK (v1.x). Use the new Responses API pattern below.

```python
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

project = AIProjectClient(
    endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    credential=DefaultAzureCredential()
)

openai = project.get_openai_client()

# Use responses.create() with instructions — the agent pattern used in this workshop.
# The model + instructions + tools = an "inline agent" that doesn't need to be registered.
response = openai.responses.create(
    model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
    instructions="""You are the TVA Document Processor assistant. You help TVA engineers
    and compliance officers find answers in TVA regulatory documents, NERC CIP compliance
    reports, and grid reliability data. Always cite the source document when answering.
    If information is not in the provided documents, say so clearly.""",
    input="Summarize TVA's NERC CIP compliance posture and cite sources."
)

print(response.output_text)
```

> 📚 [Build with agents, conversations, and responses](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/runtime-components)

> 💡 **Workshop labs:** Aaron's `foundry-lab/` directory in the mcp-backend submodule contains 6 hands-on Python labs that build on this pattern — from basic completions through multi-agent architectures and RAG. Run them with:
> ```bash
> cd boilerplate/mcp-backend/foundry-lab
> python labs/lab01-prompts-completions/lab01_completions.py
> ```

> ⚠️ **Vignette: Responses not citing documents**
> If the agent answers from general knowledge, verify **File Search** is enabled in the agent's Tools section. Also confirm your files finished processing (status = "completed" in the Files panel).
>
> 📚 [File Search tool reference](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/file-search)

---

## Lab 1 Checkpoint ✅

Before moving to lunch, verify:
- [ ] Foundry project created and accessible
- [ ] TVA documents uploaded and processed (status = Ready)
- [ ] gpt-4o endpoint URI and key saved
- [ ] `AZURE_AI_PROJECT_ENDPOINT`, `AZURE_AGENT_NAME`, `FOUNDRY_AGENT_ENDPOINT`, and `FOUNDRY_AGENT_KEY` saved to your `.env`
- [ ] At least 2 agent queries returned document-cited answers
- [ ] Python test script runs without errors

**Save your endpoint URLs and keys** — you'll need them for Lab 2.

---

## Learn More
| Topic | Microsoft Learn Link |
|-------|---------------------|
| Microsoft Foundry overview | https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry |
| Foundry Agent Service | https://learn.microsoft.com/en-us/azure/foundry/agents/overview |
| File Search tool | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/file-search |
| azure-ai-projects SDK | https://learn.microsoft.com/en-us/python/api/overview/azure/ai-projects-readme |
| Foundry RBAC | https://learn.microsoft.com/en-us/azure/foundry/concepts/rbac-foundry |
| Build with agents, conversations, responses | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/runtime-components |

---

## Executive Takeaway
TVA's compliance documents are now searchable by AI in plain English. An engineer asking "what are our patch requirements?" gets an instant, cited answer instead of searching through 200-page PDFs. This is the foundation everything else builds on.
