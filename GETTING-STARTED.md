# 🚀 TVA Workshop — Getting Started

**Welcome!** Your environment is set up and ready. Follow these steps to get started.

---

## Step 1: Sign into GitHub and Azure (required)

### GitHub CLI (for cloning and repo operations)

```bash
gh auth login
```

Follow the prompts to authenticate with your GitHub account.

### Azure CLI (for resource deployment)

```bash
az login --use-device-code
```

Follow the prompt — open the URL, enter the code, and sign in with your **workshop demo tenant** credentials (not your personal account).

**Verify it worked:**
```bash
az account show --query '{name:name, user:user.name}' -o table
```

---

## Step 2: Configure your `.env` file

Open `.env` in the editor (it was auto-created from the template). Fill in the values your facilitator provides at check-in:

```bash
code .env
```

**Key values you'll need from check-in:**
| Variable | Where to get it |
|----------|----------------|
| `AZURE_AI_PROJECT_ENDPOINT` | Foundry portal → your project → Overview |
| `AZURE_OPENAI_KEY` | Foundry portal → Models + endpoints → gpt-4o → Key |

> 💡 Most other values are auto-populated by the deploy scripts during the labs.

---

## Step 3: Choose your starting lab

| Lab | Command | What you'll do |
|-----|---------|---------------|
| **Lab 1** — Azure AI Foundry | Open `workshop/lab1-azure-foundry.md` | Create a Foundry project, upload docs, test AI agent |
| **Lab 2** — Copilot Studio | Open `workshop/lab2-copilot-studio.md` | Build a Copilot Studio agent |
| **Lab 3** — APIM + MCP | Open `workshop/lab3-apim-mcp.md` | Deploy to Azure, connect MCP |

### Aaron's Hands-On Python Labs (Session 2)

Run interactive Python exercises during Lab 1:

```bash
# Lab 01: Prompts & Completions (start here)
FOUNDRY_LAB=01 npx just foundry:lab

# Lab 02: Responses API
FOUNDRY_LAB=02 npx just foundry:lab

# Lab 03: Agents
FOUNDRY_LAB=03 npx just foundry:lab

# Lab 04: Multi-Agent (stretch goal)
FOUNDRY_LAB=04 npx just foundry:lab

# Lab 05: RAG with AI Search (stretch goal)
FOUNDRY_LAB=05 npx just foundry:lab

# Lab 06: Foundry IQ (stretch goal)
FOUNDRY_LAB=06 npx just foundry:lab
```

> 💡 Each lab has an interactive menu — pick exercises to run individually.

---

## Step 4: Deploy to Azure (Lab 3)

When you're ready for production deployment, run the following commands from the repo root.  
Replace `tvad01` with your unique `LAB_NUM` (each student needs a unique value for per-student resources).

```bash
# Provision Azure resources (Entra ID → Container Registry → Container App → APIM)
LAB_NUM=tvad01 npx just provision

# Deploy Foundry Lab infrastructure (AI Foundry Account + AI Search)
LAB_NUM=tvad01 WALKTHROUGH=true SEARCH_LOCATION=westus npx just foundry:deploy

# (Optional) Deploy into a specific pre-existing resource group
LAB_NUM=tvad01 WALKTHROUGH=true SEARCH_LOCATION=westus RESOURCE_GROUP_OVERRIDE=mcp-workshop-rg npx just foundry:deploy
```

> 💡 **`LAB_NUM`** must be unique per student when using per-student resources (e.g. `tvad01`, `tvad02`). It can be the same value for all students if they share resources — e.g., use `tva01` during the live TVA workshop.
>
> 💡 **`WALKTHROUGH=true`** pauses at each deployment step with explanations — recommended for teaching mode.

This deploys: Entra ID app → Container Registry → Container App → APIM (takes ~15 min).

---

## Quick Reference

| Command | What it does |
|---------|-------------|
| `npx just --list` | Show all available tasks |
| `npx just slides` | Open the presentation slides |
| `npx just dev` | Start MCP server locally |
| `npx just test:local` | Health-check local server |
| `LAB_NUM=tvad01 WALKTHROUGH=true SEARCH_LOCATION=westus npx just foundry:deploy` | Deploy Foundry Lab infrastructure |
| `LAB_NUM=tvad01 WALKTHROUGH=true SEARCH_LOCATION=westus RESOURCE_GROUP_OVERRIDE=mcp-workshop-rg npx just foundry:deploy` | Deploy Foundry Lab into a specific pre-existing resource group |
| `npx just workshop:ship` | Full production deploy |
| `npx just clean` | Stop & clean Docker containers |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `gh auth login` fails | Ensure GitHub CLI is installed: `gh --version`. Retry and follow the browser prompt. |
| `az login` fails | Use `--use-device-code`. Check you're using demo tenant credentials. |
| Python import errors | Run `pip install -r boilerplate/mcp-backend/foundry-lab/requirements.txt` |
| `.env` is empty | Run `cp .env.example .env` and fill in values from check-in card |
| Submodule is empty | Run `git submodule update --init --recursive` |
| PowerShell not found | Already installed — try `pwsh --version` |

---

## Resources

- 📖 **Workshop slides:** `slides/index.html` (or run `npx just slides`)
- 📚 **Lab guides:** `workshop/` directory
- 🔧 **MCP server code:** `boilerplate/mcp-backend/`
- 🧪 **Foundry labs:** `boilerplate/mcp-backend/foundry-lab/`
- 📄 **Sample TVA docs:** `docs/`

**Questions?** Ask your facilitator or open an issue at [github.com/johnturek/TVA-Demo](https://github.com/johnturek/TVA-Demo).
