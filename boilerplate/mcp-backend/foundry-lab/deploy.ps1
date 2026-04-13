<#
.SYNOPSIS
    Deploy Foundry Lab infrastructure — AI Foundry Account + Project + AI Search.

.PARAMETER LabNum
    Unique suffix for per-student resources (e.g. tvad01). Defaults to 'tvad01'.

.PARAMETER SearchLocation
    Azure region for AI Search (e.g. westus). Defaults to eastus.

.PARAMETER Walkthrough
    When set, pauses between steps for teaching mode.

.PARAMETER ResourceGroupOverride
    Use an existing resource group instead of creating one.

.PARAMETER Prefix
    Resource name prefix (default: foundry-lab).

.EXAMPLE
    LAB_NUM=tvad01 WALKTHROUGH=true SEARCH_LOCATION=westus npx just foundry:deploy
#>
param(
    [string]$LabNum              = $env:LAB_NUM,
    [string]$SearchLocation      = ($env:SEARCH_LOCATION ?? "eastus"),
    [switch]$Walkthrough,
    [string]$ResourceGroupOverride = $env:RESOURCE_GROUP_OVERRIDE,
    [string]$Prefix              = "foundry-lab"
)

if (-not $LabNum) { $LabNum = "tvad01" }

$ResourceGroup = if ($ResourceGroupOverride) { $ResourceGroupOverride } else { "mcp-workshop-rg-$LabNum" }

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   TVA Workshop — Foundry Lab Deployment                  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Lab Number     : $LabNum"
Write-Host "  Resource Group : $ResourceGroup"
Write-Host "  Search Region  : $SearchLocation"
Write-Host "  Walkthrough    : $($Walkthrough.IsPresent)"
Write-Host ""

# Verify az CLI is logged in
try {
    $account = az account show --query '{name:name,user:user.name}' -o json 2>$null | ConvertFrom-Json
    Write-Host "  ✅ Signed in as: $($account.user) ($($account.name))" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Not signed into Azure. Run: az login --use-device-code" -ForegroundColor Red
    exit 1
}

if ($Walkthrough) {
    Write-Host ""
    Write-Host "  📚 WALKTHROUGH MODE — press Enter to advance each step" -ForegroundColor Yellow
    Read-Host "     Press Enter to begin deployment"
}

# Step 1 — Resource group
Write-Host ""
Write-Host "  [1/4] Creating resource group '$ResourceGroup' in $SearchLocation..." -ForegroundColor Cyan
az group create --name $ResourceGroup --location $SearchLocation --output none
Write-Host "        ✅ Resource group ready" -ForegroundColor Green

if ($Walkthrough) { Read-Host "     Press Enter to continue" }

# Step 2 — AI Foundry Account
$FoundryAccount = "$Prefix-$LabNum"
Write-Host ""
Write-Host "  [2/4] Creating AI Foundry account '$FoundryAccount'..." -ForegroundColor Cyan
az cognitiveservices account create `
    --name $FoundryAccount `
    --resource-group $ResourceGroup `
    --kind AIServices `
    --sku S0 `
    --location $SearchLocation `
    --yes `
    --output none 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "        ⚠️  AI Foundry account creation skipped (may already exist)" -ForegroundColor Yellow
} else {
    Write-Host "        ✅ AI Foundry account created" -ForegroundColor Green
}

if ($Walkthrough) { Read-Host "     Press Enter to continue" }

# Step 3 — AI Search
$SearchService = "tva-search-$LabNum"
Write-Host ""
Write-Host "  [3/4] Creating AI Search service '$SearchService' in $SearchLocation..." -ForegroundColor Cyan
az search service create `
    --name $SearchService `
    --resource-group $ResourceGroup `
    --sku basic `
    --location $SearchLocation `
    --output none 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "        ⚠️  AI Search creation skipped (may already exist)" -ForegroundColor Yellow
} else {
    Write-Host "        ✅ AI Search service created" -ForegroundColor Green
}

if ($Walkthrough) { Read-Host "     Press Enter to continue" }

# Step 4 — Output .env values
Write-Host ""
Write-Host "  [4/4] Retrieving connection values..." -ForegroundColor Cyan

$searchKey = az search admin-key show --service-name $SearchService --resource-group $ResourceGroup --query primaryKey -o tsv 2>$null
$searchEndpoint = "https://$SearchService.search.windows.net"
$foundryEndpoint = az cognitiveservices account show --name $FoundryAccount --resource-group $ResourceGroup --query properties.endpoint -o tsv 2>$null

$envUpdates = @(
    "AZURE_SEARCH_SERVICE_NAME=$SearchService",
    "AZURE_SEARCH_ENDPOINT=$searchEndpoint",
    "AZURE_SEARCH_ADMIN_KEY=$searchKey",
    "AZURE_AI_PROJECT_ENDPOINT=$foundryEndpoint"
)

if (Test-Path "../../.env") {
    foreach ($kv in $envUpdates) {
        $key = $kv.Split('=')[0]
        $val = $kv.Substring($key.Length + 1)
        (Get-Content "../../.env") -replace "^$key=.*", "$key=$val" | Set-Content "../../.env"
    }
    Write-Host "        ✅ .env updated with deployment outputs" -ForegroundColor Green
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅  Foundry Lab infrastructure deployed                 ║" -ForegroundColor Green
Write-Host "║                                                          ║" -ForegroundColor Green
Write-Host "║  Next: Open workshop/lab1-azure-foundry.md               ║" -ForegroundColor Green
Write-Host "║        Run: FOUNDRY_LAB=01 npx just foundry:lab          ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
