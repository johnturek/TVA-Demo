# Foundry Lab — Azure AI Foundry Workshop

Hands-on labs for **TVA AI Data Scientists** covering the full Microsoft
Foundry stack: AI Foundry Accounts & Projects, Agent Framework v1.0 GA, Agent
Service v2, Foundry SDK v2.0, Responses API, multi-agent architectures, RAG
with Azure AI Search, and Foundry IQ.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Resource Group                         │
│                                                                 │
│  ┌──────────────────────┐  ┌──────────────────────────────┐    │
│  │  AI Foundry Account  │  │      Azure AI Search         │    │
│  │  (AIServices)        │  │  • Hybrid retrieval           │    │
│  │                      │  │  • Vector + BM25 + Semantic   │    │
│  │  ┌────────────────┐  │  │  • Foundry IQ knowledge layer │    │
│  │  │ Foundry Project│  │  └──────────────────────────────┘    │
│  │  │  • Models      │  │                                       │
│  │  │  • Agents      │  │                                       │
│  │  │  • Evaluations │  │                                       │
│  │  └────────────────┘  │                                       │
│  └──────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
  Foundry SDK v2.0 (azure-ai-projects >= 2.0)
          │
    ┌─────┴──────┐
    │ Labs 01-06 │
    └────────────┘
```

## Labs

| Lab | Topic | Concepts |
|-----|-------|----------|
| [01](labs/lab01-prompts-completions/) | **Prompts & Completions** | Chat completions with TVA personas (grid operator, environmental analyst), load forecasting prompts, demand response multi-turn |
| [02](labs/lab02-responses-api/) | **Responses API** | `responses.create()`, TVA generation assets structured output, FERC web search, intra-hour load forecasting multi-turn |
| [03](labs/lab03-agents/) | **Agents** | Agent lifecycle with TVA personas, Code Interpreter for load data analysis, function calling, Agent-as-Code: YAML definition → Foundry Agent Service v2 (create_version, Responses API chat) |
| [04](labs/lab04-multi-agent/) | **Multi-Agent Architectures** | TVA dispatch pipeline (data engineer → forecaster → dispatcher), solar/storage fan-out analysis, vegetation risk supervisor, PI historian critic loop |
| [05](labs/lab05-rag/) | **RAG** | Index TVA operational docs (NERC, vegetation, dam safety), hybrid search, grounded generation from TVA procedures |
| [06](labs/lab06-foundry-iq/) | **Foundry IQ** | Agentic retrieval across TVA dam/vegetation/cold-weather docs, multi-hop coal retirement analysis, naive RAG vs. Foundry IQ |
| [07](labs/lab07-aifoundry-agent-api/) | **AI Foundry Agent API** | FastAPI REST API wrapping hosted agents with OBO auth, SSE streaming, Container App deployment, Copilot Studio custom connector (OpenAPI) |

## Prerequisites

- Azure subscription with permissions to create resources
- Azure CLI 2.80+ (`az --version`)
- PowerShell 7+ (`pwsh`) — for infrastructure deployment
- Python 3.9+
- `az login` authenticated session

## Quick Start

### 1. Deploy Infrastructure

```powershell
cd foundry-lab
.\deploy.ps1 -Prefix "foundry-lab" -Location "eastus2"

# Preview without executing
.\deploy.ps1 -Prefix "foundry-lab" -WhatIf

# Walkthrough mode with explanations
.\deploy.ps1 -Prefix "foundry-lab" -Walkthrough
```

This deploys:
- **AI Foundry Account** (`Microsoft.CognitiveServices/accounts`, kind=AIServices)
- **Foundry Project** (sub-resource of the account)
- **Azure AI Search** (`Microsoft.Search/searchServices`, basic SKU)

### 2. Configure Environment

```bash
cp example.env .env
# Paste the output values from deploy.ps1 into .env
```

### 3. Install Dependencies

```bash
pip install --user -r requirements.txt
```

### 4. Run Labs

```bash
# Lab 01: Prompts & Completions
python labs/lab01-prompts-completions/lab01_completions.py

# Lab 02: Responses API
python labs/lab02-responses-api/lab02_responses.py

# Lab 03: Agents
python labs/lab03-agents/lab03_agents.py

# Lab 04: Multi-Agent Architectures
python labs/lab04-multi-agent/lab04_multi_agent.py

# Lab 05: RAG (run before Lab 06)
python labs/lab05-rag/lab05_rag.py

# Lab 06: Foundry IQ
python labs/lab06-foundry-iq/lab06_foundry_iq.py

# Lab 07 — AI Foundry Agent API (FastAPI + OBO)
python labs/lab07-aifoundry-agent-api/lab07_agent_api.py
```

## SDK & Framework Versions

| Component | Version | Status |
|-----------|---------|--------|
| Azure AI Foundry SDK (`azure-ai-projects`) | ≥ 2.0.0 | GA |
| Microsoft Agent Framework | 1.0 | GA |
| Azure AI Foundry Agent Service | v2 | GA |
| Foundry IQ | Preview | Public Preview |
| Azure AI Search | 2024-06-01-preview | GA |

## Project Structure

```
foundry-lab/
├── deploy.ps1                      # Orchestrates infrastructure deployment
├── requirements.txt                # Python dependencies
├── example.env                     # Environment template
├── infrastructure/
│   ├── main.bicep                  # Root Bicep template
│   └── modules/
│       ├── ai-services.bicep       # AI Foundry Account
│       ├── ai-project.bicep        # Foundry Project
│       └── ai-search.bicep         # Azure AI Search
├── shared/
│   └── config.py                   # Shared auth & config
└── labs/
    ├── lab01-prompts-completions/   # Basic prompts & chat completions
    ├── lab02-responses-api/         # OpenAI Responses API
    ├── lab03-agents/                # Agent Framework + Agent Service
    ├── lab04-multi-agent/           # Multi-agent orchestration patterns
    ├── lab05-rag/                   # RAG with Azure AI Search
    ├── lab06-foundry-iq/            # Foundry IQ agentic retrieval
    └── lab07-aifoundry-agent-api/   # FastAPI agent API with OBO + streaming
```

## Key SDK Patterns

### Authentication

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

client = AIProjectClient(
    endpoint="https://<account>.services.ai.azure.com/api/projects/<project>",
    credential=DefaultAzureCredential(),
)
```

### Chat Completions (via OpenAI-compatible client)

```python
openai = client.get_openai_client()
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

### Responses API

```python
response = openai.responses.create(
    model="gpt-4o",
    input="Explain RAG.",
)
print(response.output_text)
```

### Agent Service v2

```python
agent = project_client.agents.create_version(
    agent_name="my-agent",
    body={
        "definition": {
            "kind": "prompt",
            "model": "gpt-4o",
            "instructions": "You are a helpful assistant.",
        },
    },
)
```

## Cleanup

Delete all lab resources:

```bash
az group delete --name foundry-lab-rg --yes --no-wait
```

## Related Resources

- [Azure AI Foundry Documentation](https://learn.microsoft.com/en-us/azure/foundry/)
- [Foundry SDK Reference](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-projects-readme)
- [Agent Framework GitHub](https://github.com/microsoft/agent-framework)
- [Foundry IQ Announcement](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/foundry-iq-unlocking-ubiquitous-knowledge-for-agents/4470812)
- [Foundry Samples Repository](https://github.com/microsoft-foundry/foundry-samples)
