# Workshop Environment Setup
**Choose ONE of the three options below.** All three get you to the same place.

| Option | Best For | What You Need | Time to Ready |
|--------|----------|---------------|---------------|
| **A. GitHub Codespaces** ⭐ | Everyone (recommended) | GitHub account + browser | ~2 min |
| **B. Azure Cloud Shell** | Already in Azure Portal | Azure subscription + browser | ~5 min |
| **C. Local Install** | Experienced devs who prefer local | Node, Python, PowerShell, Azure CLI | ~15 min |

---

## Option A: GitHub Codespaces (Recommended) ⭐

**Zero installs. Full VS Code in the browser. Everything pre-configured.**

### Step 1: Open the Codespace

Click this link (or scan QR code at check-in):

👉 **[Open in Codespaces](https://codespaces.new/johnturek/tva-demo?quickstart=1)**

> If prompted, select **2-core** machine type (default). This is free — every GitHub account gets 60 hours/month.

### Step 2: Wait for Setup (~2 min)

The devcontainer automatically installs:
- Azure CLI
- PowerShell 7+
- Python 3.12
- Node.js 22
- Docker-in-Docker (for Lab 3)
- All npm + pip dependencies
- Azure AI Projects SDK v2 (`azure-ai-projects>=2.0.0`)
- Aaron's Foundry Lab dependencies (`rich`, `azure-search-documents`, `openai`)
- VS Code extensions (REST Client, Python, PowerShell, Azure)
- `.env` file copied from `.env.example`

You'll see the terminal when it's ready.

### Step 3: Sign into Azure

```bash
az login --use-device-code
```

Follow the device code prompt — sign in with your **workshop demo tenant** credentials.

### Step 4: Verify

```bash
az account show --query '{name:name, user:user.name}' -o table
node --version
python3 --version
pwsh --version
```

✅ **You're ready.** Proceed to Lab 1.

---

## Option B: Azure Cloud Shell

**No installs. Uses Azure's built-in browser terminal. Already signed in.**

### Step 1: Open Azure Cloud Shell

Go to **[shell.azure.com](https://shell.azure.com)** and sign in with your workshop demo tenant credentials.

> Choose **Bash** or **PowerShell** when prompted. We recommend **PowerShell** for this workshop since the deploy scripts are `.ps1`.

### Step 2: Clone the Repo

```bash
git clone --recurse-submodules https://github.com/johnturek/tva-demo.git
cd tva-demo
```

### Step 3: Install Dependencies

```bash
npm install
pip install -r boilerplate/mcp-backend/requirements.txt
```

### Step 4: Verify

```bash
az account show --query '{name:name, user:user.name}' -o table
node --version
python3 --version
pwsh --version
```

> ℹ️ **Cloud Shell notes:**
> - You're **already authenticated** — no `az login` needed
> - Storage persists across sessions (mounted at `$HOME/clouddrive`)
> - Cloud Shell has a 20-minute idle timeout — keep the tab active
> - No Docker daemon available — but you don't need it; everything deploys to Azure directly
> - To edit files, use the built-in editor: click `{}` in the toolbar, or run `code .`

### Step 5: Open Files for Editing (Optional)

For a better editing experience alongside Cloud Shell, open the repo in vscode.dev in a second tab:

👉 **[Open in vscode.dev](https://vscode.dev/github/johnturek/tva-demo)**

This gives you full VS Code editing (syntax highlighting, Markdown preview, file tree) while Cloud Shell handles the terminal.

✅ **You're ready.** Proceed to Lab 1.

---

## Option C: Local Install

**For experienced developers who prefer their own machine.**

### Prerequisites

Install these before the workshop:

| Tool | Install | Version |
|------|---------|---------|
| Node.js | https://nodejs.org | 18+ |
| Python | https://python.org | 3.10+ (3.12 recommended) |
| PowerShell | https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell | 7+ |
| Azure CLI | https://learn.microsoft.com/en-us/cli/azure/install-azure-cli | Latest |
| VS Code | https://code.visualstudio.com | Latest |
| VS Code REST Client | Extensions → `humao.rest-client` | Latest |

### Step 1: Clone the Repo

```bash
git clone --recurse-submodules https://github.com/johnturek/tva-demo.git
cd tva-demo
```

### Step 2: Install Dependencies

```bash
npm install
pip install -r boilerplate/mcp-backend/requirements.txt
```

### Step 3: Sign into Azure

```bash
az login --use-device-code
```

Sign in with your **workshop demo tenant** credentials.

### Step 4: Verify

```bash
az account show --query '{name:name, user:user.name}' -o table
node --version
python3 --version
pwsh --version
```

✅ **You're ready.** Proceed to Lab 1.

---

## Environment Variables

After choosing your option above, set up your `.env` file:

```bash
cp .env.example .env
```

Fill in the values distributed at workshop check-in. See the main [README](../README.md) for the full variable reference.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Codespace won't start | Make sure you're signed into github.com. Try a private/incognito window. |
| `az login` fails | Use `--use-device-code` flag. Make sure you're using demo tenant creds, not personal. |
| Cloud Shell times out | Click "Reconnect" — your files are preserved in `$HOME/clouddrive`. |
| `npm install` fails | Check Node version: `node --version` (need 18+). |
| Python packages missing | Run `pip install -r boilerplate/mcp-backend/requirements.txt` manually. |
| PowerShell not found | Install: https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell |
| Submodule empty | Run `git submodule update --init --recursive` |
| Lab 03 Exercise 2 fails (Code Interpreter) | Set `DISABLE_CODE_INTERPRETER_LAB=true` in `.env` — your region may not support container-based Code Interpreter. |
| Foundry-lab uses wrong model name | Aaron's labs default to `gpt-4.1`. Set `AZURE_OPENAI_DEPLOYMENT_NAME` in `.env` to match your actual Foundry deployment (may be `gpt-4o`). |
