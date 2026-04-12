# TVA Workshop — Microsoft Copilot Studio + Azure AI

> **6-hour workshop** | April 15, 2026 | TVA HQ, Knoxville TN
>
> Build a production-ready, Entra ID–secured AI agent connected to TVA's knowledge base — live in Azure by end of day.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/johnturek/TVA-Demo?quickstart=1)

---

## What You'll Build

The **TVA Document Processor** — a Copilot Studio agent that:
- Answers questions about TVA regulatory documents and NERC CIP compliance
- Processes uploaded compliance reports via Azure AI Foundry RAG
- Routes securely through Azure APIM with full user identity (OBO)
- Runs on Azure Container Apps — production-grade, auto-scaling, shareable URL

```
You → Copilot Studio → APIM (JWT validated) → Container Apps (MCP Server) → Azure AI Foundry → TVA Knowledge Base
```

---

## Quick Start

**Fastest:** Click 👉 **[Open in Codespaces](https://codespaces.new/johnturek/tva-demo?quickstart=1)** — everything is pre-configured.

**Or clone locally:**

```bash
# 1. Clone the repo (with submodules)
git clone --recurse-submodules https://github.com/johnturek/TVA-Demo
cd TVA-Demo

# 2. Install dependencies (auto-inits submodules if you forgot --recurse-submodules)
npm install

# 3. See all available tasks
npx just --list

# 4. Start the local workshop stack
npx just setup
```

---

## Task Runner (`just`)

This repo uses [`just-task`](https://github.com/microsoft/just) — Microsoft's task library for JS projects.

| Command | What it does |
|---------|-------------|
| `npx just --list` | List all available tasks |
| `npx just install` | Install Python + AI Search dependencies |
| `npx just dev` | Start MCP server locally (Python/FastMCP) |
| `npx just dev:docker` | Run MCP server in Docker locally |
| `npx just dev:stop` | Stop Docker containers |
| `npx just upload-docs` | Upload TVA docs to Azure AI Search index |
| `npx just test:local` | Health check local MCP server |
| `npx just test:prod` | Full endpoint test suite (device-code auth + 8 tests) |
| `npx just provision` | Deploy full Azure stack (silent mode) |
| `npx just provision:teach` | Deploy full Azure stack **(walkthrough mode — use in workshop)** |
| `npx just add-user` | Add a user to the MCP.User app role (`USER_EMAIL=...`) |
| `npx just sync` | Pull latest updates from Aaron's mcp-backend submodule |
| `npx just setup` | Install deps + upload docs |
| `npx just workshop:start` | Full Lab 1+2 setup |
| `npx just workshop:ship` | End-of-day: provision Azure (walkthrough) + verify production |
| `npx just clean` | Stop containers, remove volumes |
| `npx just slides` | Open workshop slides in browser |
| `npx just foundry:deploy` | Deploy Foundry Lab infrastructure (AI Foundry + AI Search) |
| `npx just foundry:lab` | Run a Foundry lab (`FOUNDRY_LAB=01` through `06`) |

> **Workshop tip:** Use `npx just provision:teach` for Lab 3 — it pauses at each step with explanations so participants understand what's being deployed.

---

## Workshop Environment — Choose Your Setup

We support **three ways** to run this workshop. Pick what works for you:

| Option | Best For | What You Need | Time to Ready |
|--------|----------|---------------|---------------|
| **A. GitHub Codespaces** ⭐ | Everyone (recommended) | GitHub account + browser | ~2 min |
| **B. Azure Cloud Shell** | Already in Azure Portal | Azure subscription + browser | ~5 min |
| **C. Local Install** | Experienced devs | Node, Python, PowerShell, Azure CLI | ~15 min |

### Option A: GitHub Codespaces (Recommended)

👉 **[Open in Codespaces](https://codespaces.new/johnturek/tva-demo?quickstart=1)** — zero installs, full VS Code in the browser, everything pre-configured.

Every free GitHub account gets 60 hours/month — more than enough for this workshop.

### Option B: Azure Cloud Shell

Go to **[shell.azure.com](https://shell.azure.com)**, clone the repo, and run. You're already signed in.

### Option C: Local Install

Node 18+, Python 3.10+, PowerShell 7+, Azure CLI. See details below.

> 📖 **Full setup guide with step-by-step instructions for all three options:** [`workshop/setup-environment.md`](workshop/setup-environment.md)

### Verify Your Environment (All Options)

```bash
az account show --query '{name:name, user:user.name}' -o table
node --version
python3 --version
pwsh --version
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values (distributed at workshop check-in):

```bash
cp .env.example .env
```

```env
# Microsoft Foundry / Azure AI Projects (Lab 1)
AZURE_AI_PROJECT_ENDPOINT=https://tva-workshop.services.ai.azure.com/api/projects/tva-doc-processor-[yourname]
AZURE_AGENT_ID=
AZURE_OPENAI_ENDPOINT=https://tva-workshop.openai.azure.com/
AZURE_OPENAI_KEY=
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Foundry Agent Endpoint (Lab 2 — same values as above)
FOUNDRY_AGENT_ENDPOINT=https://tva-workshop.services.ai.azure.com/api/projects/tva-doc-processor-[yourname]
FOUNDRY_AGENT_KEY=

# Azure Identity (filled by deploy.ps1 / setup-entra-apps.ps1)
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=

# Production (filled after running: npx just provision)
MCP_ENDPOINT=
APIM_GATEWAY=
JWT_AUDIENCE=
JWT_ISSUER=
```

---

## Repo Structure

```
TVA-Demo/
├── just.config.js          # Task runner — all workshop commands
├── package.json
├── .env.example
├── .gitmodules             # Submodule: Aaron's mcp-backend
│
├── boilerplate/
│   ├── mcp-backend/            # ⭐ Git submodule — Aaron's production MCP server
│   │   ├── mcp_server.py           # Python/FastMCP with PRM + OBO
│   │   ├── deploy.ps1              # One-command Azure deployment (-Walkthrough for teaching)
│   │   ├── setup-entra-apps.ps1    # Full Entra ID app registration
│   │   ├── deploy-infrastructure.ps1
│   │   ├── deploy-apim.ps1         # APIM + JWT policy
│   │   ├── test-endpoints.ps1      # Full test suite (8 endpoint tests)
│   │   ├── add-reply-url.ps1       # Add Copilot Studio redirect URI
│   │   ├── add-users.ps1           # Assign users to MCP.User app role
│   │   ├── Dockerfile
│   │   ├── example.env
│   │   ├── requirements.txt
│   │   └── foundry-lab/            # ⭐ Aaron's 6 hands-on Foundry labs
│   │       ├── deploy.ps1              # Bicep infra deployment
│   │       ├── labs/lab01-prompts-completions/
│   │       ├── labs/lab02-responses-api/
│   │       ├── labs/lab03-agents/
│   │       ├── labs/lab04-multi-agent/
│   │       ├── labs/lab05-rag/
│   │       └── labs/lab06-foundry-iq/
│   ├── upload-docs.py          # Upload TVA docs to Azure AI Search
│   ├── agent-template.yaml     # Copilot Studio agent definition
│   └── test-agent.http         # REST Client test file
│
├── docs/                   # Sample TVA documents for the knowledge base
│   ├── nerc-cip-007.txt
│   ├── nerc-cip-010.txt
│   ├── tva-grid-reliability.txt
│   ├── nuclear-safety-overview.txt
│   └── regulatory-variance-process.txt
│
├── slides/                 # Reveal.js presentation slides
│   └── index.html              # Full workshop slide deck (open in browser)
│
├── .devcontainer/          # GitHub Codespaces / devcontainer config
│   └── devcontainer.json
│
└── workshop/               # Workshop materials
    ├── setup-environment.md    # ⭐ Environment setup (Codespaces / Cloud Shell / Local)
    ├── agenda.md
    ├── exec-brief.md
    ├── lab1-azure-foundry.md
    ├── lab2-copilot-studio.md
    ├── lab3-apim-mcp.md
    ├── facilitator-guide.md
    └── boilerplate-readme.md
```

### Keeping mcp-backend in sync

Aaron's MCP server lives at `boilerplate/mcp-backend` as a git submodule. To pull his latest:

```bash
npx just sync
git add boilerplate/mcp-backend && git commit -m "chore: sync mcp-backend"
```

---

## Workshop Agenda (Quick View)

| Time | Session | Presenter |
|------|---------|-----------|
| 9:00–9:15 AM | Session 0: Welcome & Intro | Kevin / Wesley / TVA Leader |
| 9:15–11:30 AM | Session 1: Copilot Studio | John |
| 11:30–12:30 PM | Lunch (Frontier AI Discussion) | Kevin + TVA Leadership |
| 12:30–2:30 PM | Session 2: AI Foundry | Aaron / JT |
| 2:30–4:00 PM | Session 3: Use Case Development | All |

> **Total:** 5h content + 1h lunch = 6h (9:00 AM–4:00 PM)

Full agenda: [`workshop/agenda.md`](workshop/agenda.md)

---

## Reusing This for Other Customers

This repo is built as a template. To clone for a new customer:

```bash
# 1. Fork or copy the repo
gh repo create [CUSTOMER]-Demo --template johnturek/TVA-Demo --public

# 2. Find/replace TVA-specific content
grep -r "TVA\|Tennessee Valley\|NERC CIP\|Browns Ferry" workshop/ boilerplate/

# 3. Update docs/ with customer-relevant documents

# 4. Update agent-template.yaml system prompt

# 5. Run the workshop
npx just workshop:start
```

---

## Microsoft Learn Resources

| Topic | Link |
|-------|------|
| Microsoft Foundry | https://learn.microsoft.com/en-us/azure/foundry/ |
| Foundry Agent Service | https://learn.microsoft.com/en-us/azure/foundry/agents/overview |
| Copilot Studio overview | https://learn.microsoft.com/en-us/microsoft-copilot-studio/ |
| Copilot Studio + MCP | https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-mcp |
| Copilot Studio auth (OBO) | https://learn.microsoft.com/en-us/microsoft-copilot-studio/configuration-authentication-azure-ad |
| Azure API Management | https://learn.microsoft.com/en-us/azure/api-management/ |
| APIM Entra ID token validation | https://learn.microsoft.com/en-us/azure/api-management/validate-azure-ad-token-policy |
| Azure Container Apps | https://learn.microsoft.com/en-us/azure/container-apps/ |
| Entra ID OBO flow | https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow |
| just-task runner | https://microsoft.github.io/just/ |

---

## Questions?

Contact JT or open an issue in this repo.
