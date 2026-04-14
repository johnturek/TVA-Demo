# deploy.ps1
# Orchestrates Foundry Lab infrastructure: AI Foundry Account, Foundry Project, Azure AI Search.
# Uses Azure CLI + Bicep.  -WhatIf previews commands without executing.

[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]
param(
  [string] $TenantId = "",
  [string] $SubscriptionId = "",
  [string] $Prefix = "foundry-lab",
  [string] $LabNum = "",
  [string] $Location = "eastus2",
  [string] $SearchLocation = "",
  [string] $SearchSku = "basic",

  # Override the resource group name (skip "$Prefix-rg" derivation)
  [string] $ResourceGroupOverride = "",

  [Alias("Explain")]
  [switch] $Walkthrough,

  [switch] $SkipCodeInterpreterLab,

  [switch] $Menu,
  [switch] $ExplainOnly
)

$ErrorActionPreference = "Stop"

function Write-Info($msg)  { Write-Host $msg -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host $msg -ForegroundColor Magenta }
function Write-AzCmd($msg) { Write-Host $msg -ForegroundColor Yellow }

function Write-Explain {
  param([string]$Title, [string[]]$Lines)
  if (-not $Walkthrough) { return }
  Write-Host ""
  Write-Host ("=" * 80) -ForegroundColor DarkCyan
  Write-Host "  $Title" -ForegroundColor White
  Write-Host ("=" * 80) -ForegroundColor DarkCyan
  foreach ($line in $Lines) { Write-Host "  $line" -ForegroundColor Gray }
  Write-Host ""
  Write-Host "  Press ENTER to continue, or Ctrl+C to stop..." -ForegroundColor DarkYellow -NoNewline
  Read-Host
  Write-Host ""
}

# ── Lab definitions & menu function ──────────────────────────────────────────

$labs = @(
  @{
    Num = "1"; Name = "Lab 01 — Prompts & Completions"
    Script = "labs/lab01-prompts-completions/lab01_completions.py"
    Description = "Fundamentals: message roles, prompt engineering, temperature, streaming, multi-turn."
  }
  @{
    Num = "2"; Name = "Lab 02 — Responses API"
    Script = "labs/lab02-responses-api/lab02_responses.py"
    Description = "Stateless Responses API: structured output, web search, multi-turn chaining, streaming."
  }
  @{
    Num = "3"; Name = "Lab 03 — Agents"
    Script = "labs/lab03-agents/lab03_agents.py"
    Description = "Agentic patterns: instructions, Code Interpreter, function calling, Agent-as-Code YAML → Agent Service v2."
  }
  @{
    Num = "4"; Name = "Lab 04 — Multi-Agent"
    Script = "labs/lab04-multi-agent/lab04_multi_agent.py"
    Description = "Multi-agent orchestration: sequential, parallel, supervisor/worker, critic loop, workflow."
  }
  @{
    Num = "5"; Name = "Lab 05 — RAG"
    Script = "labs/lab05-rag/lab05_rag.py"
    Description = "RAG pipeline: search index, embeddings, hybrid search, grounded generation with citations."
  }
  @{
    Num = "6"; Name = "Lab 06 — Foundry IQ"
    Script = "labs/lab06-foundry-iq/lab06_foundry_iq.py"
    Description = "Agentic retrieval: multi-hop reasoning, query decomposition, naive vs. agentic comparison."
  }
  @{
    Num = "7"; Name = "Lab 07 — AI Foundry Agent API"
    Script = "labs/lab07-aifoundry-agent-api/lab07_agent_api.py"
    Description = "FastAPI REST API: hosted agent wrapper, SSE streaming, OBO auth, Copilot Studio integration."
  }
)

function Show-LabExplanation($lab) {
  $scriptPath = Join-Path $PSScriptRoot $lab.Script
  python $scriptPath --intro-only
  Write-Host ""
  Write-Host "  Press Enter to continue..." -ForegroundColor DarkYellow -NoNewline
  Read-Host
}

function Show-LabMenu {
  param([switch]$ExplainOnly)
  $modeLabel = if ($ExplainOnly) { "LAB EXPLORER (Explain Only)" } else { "LAB RUNNER" }
  while ($true) {
    Write-Host ""
    Write-Ok "==================== $modeLabel ===================="
    foreach ($lab in $labs) {
      Write-Host ("  [{0}] {1}" -f $lab.Num, $lab.Name) -NoNewline
      Write-Host ("  — {0}" -f $lab.Description) -ForegroundColor DarkGray
    }
    Write-Host ("  [A] {0} ALL labs" -f $(if ($ExplainOnly) { "Explain" } else { "Run" }))
    Write-Host "  [Q] Quit"
    Write-Ok "====================================================="
    Write-Host ""
    $choice = Read-Host "Select a lab"

    if ($choice -eq "Q" -or $choice -eq "q") {
      Write-Info "Done. Goodbye!"
      return
    }

    if ($choice -eq "A" -or $choice -eq "a") {
      foreach ($lab in $labs) {
        if ($ExplainOnly) {
          Show-LabExplanation $lab
        } else {
          Write-Host ""
          Write-Info ("== Running: {0} ==" -f $lab.Name)
          $scriptPath = Join-Path $PSScriptRoot $lab.Script
          python $scriptPath
          Write-Ok ("== Finished: {0} ==" -f $lab.Name)
        }
      }
      continue
    }

    $selected = $labs | Where-Object { $_.Num -eq $choice }
    if ($selected) {
      if ($ExplainOnly) {
        Show-LabExplanation $selected
      } else {
        Write-Host ""
        Write-Info ("== Running: {0} ==" -f $selected.Name)
        $scriptPath = Join-Path $PSScriptRoot $selected.Script
        python $scriptPath
        Write-Ok ("== Finished: {0} ==" -f $selected.Name)
      }
    } else {
      Write-Warn "Invalid selection. Please try again."
    }
  }
}

# ── -Menu / -ExplainOnly: skip deployment, jump straight to lab menu ─────────

if ($ExplainOnly) { $Menu = $true }

if ($Menu) {
  if (-not $ExplainOnly) {
    $envFile = Join-Path $PSScriptRoot ".env"
    if (-not (Test-Path $envFile)) {
      Write-Warn "No .env file found at $envFile — run a full deploy first."
      exit 1
    }
    Write-Ok "== -Menu: .env found, skipping deployment — launching lab runner =="
  } else {
    Write-Ok "== -ExplainOnly: showing lab explanations =="
  }
  Show-LabMenu -ExplainOnly:$ExplainOnly
  return
}

# ── Login & resolve context ──────────────────────────────────────────────────

Write-Info "== Checking Azure CLI login =="
$acct = az account show -o json 2>$null | ConvertFrom-Json
if (-not $acct) {
  Write-Info "Not logged in — running az login..."
  az login | Out-Null
  $acct = az account show -o json | ConvertFrom-Json
}

if (-not $TenantId)       { $TenantId = $acct.tenantId }
if (-not $SubscriptionId) { $SubscriptionId = $acct.id }

Write-AzCmd "AZ> tenant=$TenantId  subscription=$SubscriptionId"

# ── Derived names ────────────────────────────────────────────────────────────

if ($LabNum) { $Prefix = "$Prefix-$LabNum" }
if (-not $SearchLocation) { $SearchLocation = $Location }

$ResourceGroup    = if ($ResourceGroupOverride) { $ResourceGroupOverride } else { "$Prefix-rg" }
$AiServicesName   = "$Prefix-ai"
$SearchName       = "$Prefix-search"
$ProjectName      = "$Prefix-project"

Write-Info "== Deployment Plan =="
Write-Host "  Resource Group:      $ResourceGroup"
Write-Host "  AI Foundry Account:  $AiServicesName"
Write-Host "  Foundry Project:     $ProjectName"
Write-Host "  Azure AI Search:     $SearchName"
Write-Host "  Location:            $Location"
Write-Host "  Search Location:     $SearchLocation"
Write-Host "  Search SKU:          $SearchSku"
Write-Host ""

# ── Pre-flight: Check which resources already exist ──────────────────────────

Write-Explain "Pre-flight — Resource Existence Checks" @(
  "Before deploying anything, we check whether each resource already exists.",
  "If all resources are present, the Bicep deployment is skipped entirely.",
  "This saves time on re-runs and avoids unnecessary ARM operations."
)

Write-Info "== Checking for existing resources =="

$rgExists      = $false
$aiExists      = $false
$searchExists  = $false
$projectExists = $false

# Resource Group
$rgCheck = az group show --name $ResourceGroup --subscription $SubscriptionId -o json 2>$null | ConvertFrom-Json
if ($rgCheck) {
  $rgExists = $true
  Write-Ok "  Resource group '$ResourceGroup' already exists."
} else {
  Write-Warn "  Resource group '$ResourceGroup' not found."
}

# AI Foundry Account (CognitiveServices)
if ($rgExists) {
  $aiCheck = az cognitiveservices account show --name $AiServicesName --resource-group $ResourceGroup --subscription $SubscriptionId -o json 2>$null | ConvertFrom-Json
  if ($aiCheck) {
    $aiExists = $true
    Write-Ok "  AI Foundry Account '$AiServicesName' already exists."
  } else {
    Write-Warn "  AI Foundry Account '$AiServicesName' not found."
  }

  # Azure AI Search
  $searchCheck = az search service show --name $SearchName --resource-group $ResourceGroup --subscription $SubscriptionId -o json 2>$null | ConvertFrom-Json
  if ($searchCheck) {
    $searchExists = $true
    Write-Ok "  Azure AI Search '$SearchName' already exists."
  } else {
    Write-Warn "  Azure AI Search '$SearchName' not found."
  }

  # AI Foundry Project (sub-resource — use az rest)
  if ($aiExists) {
    $projectResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$AiServicesName/projects/$ProjectName"
    $projectCheck = az rest --method GET --url "https://management.azure.com${projectResourceId}?api-version=2025-04-01-preview" -o json 2>$null | ConvertFrom-Json
    if ($projectCheck) {
      $projectExists = $true
      Write-Ok "  AI Foundry Project '$ProjectName' already exists."
    } else {
      Write-Warn "  AI Foundry Project '$ProjectName' not found."
    }
  }
}

$allExist = $rgExists -and $aiExists -and $searchExists -and $projectExists
Write-Host ""

# ── Step 1: Resource Group ───────────────────────────────────────────────────

Write-Explain "Step 1 — Resource Group" @(
  "Creates the resource group that holds all Foundry Lab resources.",
  "All labs share a single resource group for easy cleanup."
)

if ($rgExists) {
  Write-Ok "== Resource group '$ResourceGroup' already exists — skipping creation. =="
} else {
  Write-Info "== Creating resource group: $ResourceGroup =="
  if ($PSCmdlet.ShouldProcess($ResourceGroup, "Create resource group")) {
    az group create --name $ResourceGroup --location $Location --subscription $SubscriptionId -o none
    Write-Ok "Resource group '$ResourceGroup' ready."
  }
}

# ── Step 2: Bicep deployment (or skip if all resources exist) ────────────────

Write-Explain "Step 2 — Bicep Deployment" @(
  "Deploys three resources via a single Bicep template:",
  "  1. AI Foundry Account (Microsoft.CognitiveServices/accounts, kind=AIServices)",
  "  2. AI Foundry Project (sub-resource of the account)",
  "  3. Azure AI Search (Microsoft.Search/searchServices)",
  "",
  "The AI Foundry Account is the top-level organizational boundary.",
  "The Foundry Project is where you deploy models, create agents, and run evaluations.",
  "Azure AI Search powers the RAG and Foundry IQ labs.",
  "",
  "If all resources already exist, the Bicep deployment is skipped and",
  "outputs are retrieved directly from the existing resources."
)

$templateFile = Join-Path $PSScriptRoot "infrastructure" "main.bicep"

if ($allExist) {
  Write-Ok "== All resources already exist — skipping Bicep deployment. =="
  Write-Info "== Retrieving outputs from existing resources =="

  $aiEndpoint     = $aiCheck.properties.endpoint
  $searchEndpoint = "https://$($searchCheck.name).search.windows.net"

  # Build an outputs object that matches what the Bicep deployment would return
  $outputs = [PSCustomObject]@{
    aiServicesEndpoint = [PSCustomObject]@{ value = $aiEndpoint }
    aiServicesName     = [PSCustomObject]@{ value = $aiCheck.name }
    aiServicesId       = [PSCustomObject]@{ value = $aiCheck.id }
    searchEndpoint     = [PSCustomObject]@{ value = $searchEndpoint }
    searchServiceName  = [PSCustomObject]@{ value = $searchCheck.name }
    projectName        = [PSCustomObject]@{ value = $projectCheck.name }
  }

  Write-Ok "==================== OUTPUTS ===================="
  Write-Host ("  AI Services Endpoint:  {0}" -f $outputs.aiServicesEndpoint.value)
  Write-Host ("  AI Services Name:      {0}" -f $outputs.aiServicesName.value)
  Write-Host ("  Search Endpoint:       {0}" -f $outputs.searchEndpoint.value)
  Write-Host ("  Search Service Name:   {0}" -f $outputs.searchServiceName.value)
  Write-Host ("  Project Name:          {0}" -f $outputs.projectName.value)
  Write-Ok "================================================="
} else {
  Write-Info "== Deploying Bicep template =="

  # Check for an already-running deployment with the same name
  $activeDeployment = az deployment group show `
    --name main `
    --resource-group $ResourceGroup `
    --subscription $SubscriptionId `
    -o json 2>$null | ConvertFrom-Json
  if ($activeDeployment -and $activeDeployment.properties.provisioningState -eq "Running") {
    $startedAt = $activeDeployment.properties.timestamp
    Write-Warn "== A deployment is already in progress (started at $startedAt). =="
    Write-Warn "   Please wait for it to complete, then re-run this script."
    Write-Warn "   To cancel the active deployment instead, run:"
    Write-Warn "     az deployment group cancel --name main --resource-group $ResourceGroup"
    exit 0
  }

  if ($PSCmdlet.ShouldProcess("Bicep deployment", "Deploy infrastructure")) {
    $deployment = az deployment group create `
      --resource-group $ResourceGroup `
      --template-file $templateFile `
      --parameters prefix=$Prefix location=$Location searchLocation=$SearchLocation searchSku=$SearchSku `
      --subscription $SubscriptionId `
      -o json | ConvertFrom-Json

    if (-not $deployment) {
      throw "Bicep deployment failed."
    }

    $outputs = $deployment.properties.outputs

    Write-Ok "Bicep deployment complete."
    Write-Host ""
    Write-Ok "==================== OUTPUTS ===================="
    Write-Host ("  AI Services Endpoint:  {0}" -f $outputs.aiServicesEndpoint.value)
    Write-Host ("  AI Services Name:      {0}" -f $outputs.aiServicesName.value)
    Write-Host ("  Search Endpoint:       {0}" -f $outputs.searchEndpoint.value)
    Write-Host ("  Search Service Name:   {0}" -f $outputs.searchServiceName.value)
    Write-Host ("  Project Name:          {0}" -f $outputs.projectName.value)
    Write-Ok "================================================="
  }
}

# ── Step 3: Retrieve Search admin key ────────────────────────────────────────

Write-Explain "Step 3 — Search Admin Key" @(
  "Retrieves the admin key for Azure AI Search.",
  "This key is used by the RAG lab to create indexes and upload documents."
)

Write-Info "== Retrieving Search admin key =="
$searchKeys = az search admin-key show `
  --resource-group $ResourceGroup `
  --service-name ($outputs.searchServiceName.value) `
  --subscription $SubscriptionId `
  -o json | ConvertFrom-Json

$searchAdminKey = $searchKeys.primaryKey

# ── Step 4: Build project endpoint ───────────────────────────────────────────

$aiName = $outputs.aiServicesName.value
$projName = $outputs.projectName.value
# Azure returns child-resource names as "parent/child"; keep only the project segment
if ($projName -match '/') { $projName = $projName.Split('/')[-1] }
$projectEndpoint = "https://${aiName}.services.ai.azure.com/api/projects/${projName}"

# ── Step 5: Assign current user RBAC ─────────────────────────────────────────

Write-Explain "Step 5 — RBAC Role Assignment" @(
  "Assigns the current user 'Cognitive Services User' on the AI Foundry account.",
  "This lets you authenticate with DefaultAzureCredential in the lab scripts."
)

Write-Info "== Assigning 'Cognitive Services User' role to current user =="
$currentUser = az ad signed-in-user show --query id -o tsv 2>$null
if ($currentUser) {
  $aiServiceId = $outputs.aiServicesId.value 2>$null
  if (-not $aiServiceId) {
    $aiServiceId = (az cognitiveservices account show --name $aiName --resource-group $ResourceGroup --query id -o tsv)
  }
  az role assignment create `
    --assignee $currentUser `
    --role "Cognitive Services User" `
    --scope $aiServiceId `
    --subscription $SubscriptionId `
    -o none 2>$null
  Write-Ok "RBAC assignment complete."
} else {
  Write-Warn "Could not determine current user — assign 'Cognitive Services User' manually."
}

# ── Summary ──────────────────────────────────────────────────────────────────

Write-Host ""
Write-Ok "==================== .env VALUES ===================="
Write-Host "AZURE_SUBSCRIPTION_ID=$SubscriptionId"
Write-Host "AZURE_TENANT_ID=$TenantId"
Write-Host "AZURE_RESOURCE_GROUP=$ResourceGroup"
Write-Host "AZURE_LOCATION=$Location"
Write-Host "AZURE_AI_FOUNDRY_ACCOUNT_NAME=$aiName"
Write-Host "AZURE_AI_PROJECT_NAME=$projName"
Write-Host "AZURE_AI_PROJECT_ENDPOINT=$projectEndpoint"
Write-Host "AZURE_SEARCH_SERVICE_NAME=$($outputs.searchServiceName.value)"
Write-Host "AZURE_SEARCH_ENDPOINT=$($outputs.searchEndpoint.value)"
Write-Host "AZURE_SEARCH_ADMIN_KEY=$searchAdminKey"
Write-Ok "====================================================="
# ── Step 6: Write .env file ──────────────────────────────────────────────────

$envFile = Join-Path $PSScriptRoot ".env"
Write-Info "== Writing .env file to $envFile =="
@"
AZURE_SUBSCRIPTION_ID=$SubscriptionId
AZURE_TENANT_ID=$TenantId
AZURE_RESOURCE_GROUP=$ResourceGroup
AZURE_LOCATION=$Location
AZURE_AI_FOUNDRY_ACCOUNT_NAME=$aiName
AZURE_AI_PROJECT_NAME=$projName
AZURE_AI_PROJECT_ENDPOINT=$projectEndpoint
AZURE_SEARCH_SERVICE_NAME=$($outputs.searchServiceName.value)
AZURE_SEARCH_ENDPOINT=$($outputs.searchEndpoint.value)
AZURE_SEARCH_ADMIN_KEY=$searchAdminKey
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
DISABLE_CODE_INTERPRETER_LAB=$(if ($SkipCodeInterpreterLab) { "true" } else { "" })
MCP_WORKSHOP_LABNUM=$LabNum
"@ | Set-Content -Path $envFile -Encoding utf8
Write-Ok ".env file written."

# ── Step 7: Install Python dependencies ──────────────────────────────────────

Write-Info "== Installing Python dependencies =="
Push-Location $PSScriptRoot
pip install -r requirements.txt --quiet --user
Pop-Location
Write-Ok "Python dependencies installed."

# ── Step 8: Lab Runner Menu ──────────────────────────────────────────────────

Show-LabMenu
