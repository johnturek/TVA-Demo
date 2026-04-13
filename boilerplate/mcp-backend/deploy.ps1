<#
.SYNOPSIS
    Provision the full Azure MCP stack — Entra ID apps, Container Registry,
    Container App, and APIM for the TVA Workshop.

.PARAMETER LabNum
    Unique suffix for per-student resources (e.g. tvad01). Required.

.PARAMETER Walkthrough
    Pauses between steps for teaching/demo mode.

.EXAMPLE
    LAB_NUM=tvad01 npx just provision
    LAB_NUM=tvad01 npx just provision:teach
#>
param(
    [string]$LabNum     = $env:LAB_NUM,
    [switch]$Walkthrough
)

if (-not $LabNum) {
    Write-Host "❌  LAB_NUM is required. Example: LAB_NUM=tvad01 npx just provision" -ForegroundColor Red
    exit 1
}

$ResourceGroup = "mcp-workshop-rg-$LabNum"
$AcrName       = "tvacr$($LabNum -replace '[^a-z0-9]', '')"
$AppName       = "tva-mcp-$LabNum"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   TVA Workshop — Full Azure Stack Provisioning          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Lab Number     : $LabNum"
Write-Host "  Resource Group : $ResourceGroup"
Write-Host "  ACR Name       : $AcrName"
Write-Host "  App Name       : $AppName"
Write-Host "  Walkthrough    : $($Walkthrough.IsPresent)"
Write-Host ""
Write-Host "  ⏱  APIM provisioning takes ~15 minutes. Grab coffee." -ForegroundColor Yellow
Write-Host ""

# Verify az CLI login
try {
    $account = az account show --query '{name:name,user:user.name}' -o json 2>$null | ConvertFrom-Json
    Write-Host "  ✅ Signed in as: $($account.user) ($($account.name))" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Not signed in. Run: az login --use-device-code" -ForegroundColor Red
    exit 1
}

if ($Walkthrough) {
    Write-Host ""
    Write-Host "  📚 WALKTHROUGH MODE" -ForegroundColor Yellow
    Read-Host "     Press Enter to begin"
}

# Step 1 — Resource group
Write-Host ""
Write-Host "  [1/5] Creating resource group '$ResourceGroup'..." -ForegroundColor Cyan
az group create --name $ResourceGroup --location eastus --output none
Write-Host "        ✅ Resource group ready" -ForegroundColor Green
if ($Walkthrough) { Read-Host "     Press Enter to continue" }

# Step 2 — Container Registry
Write-Host ""
Write-Host "  [2/5] Creating Container Registry '$AcrName'..." -ForegroundColor Cyan
az acr create --name $AcrName --resource-group $ResourceGroup --sku Basic --admin-enabled true --output none
$AcrLoginServer = az acr show --name $AcrName --query loginServer -o tsv
Write-Host "        ✅ ACR ready: $AcrLoginServer" -ForegroundColor Green
if ($Walkthrough) { Read-Host "     Press Enter to continue" }

# Step 3 — Build and push Docker image
Write-Host ""
Write-Host "  [3/5] Building and pushing MCP server Docker image..." -ForegroundColor Cyan
$ScriptDir = Split-Path -Parent $PSScriptRoot
az acr build --registry $AcrName --image "tva-mcp-server:latest" "$ScriptDir/.." --file "$ScriptDir/../Dockerfile.mcp" --output none
Write-Host "        ✅ Image pushed to $AcrLoginServer/tva-mcp-server:latest" -ForegroundColor Green
if ($Walkthrough) { Read-Host "     Press Enter to continue" }

# Step 4 — Container App
Write-Host ""
Write-Host "  [4/5] Deploying Container App '$AppName'..." -ForegroundColor Cyan
$AcrPassword = az acr credential show --name $AcrName --query passwords[0].value -o tsv

az containerapp env create `
    --name "tva-env-$LabNum" `
    --resource-group $ResourceGroup `
    --location eastus `
    --output none 2>$null

az containerapp create `
    --name $AppName `
    --resource-group $ResourceGroup `
    --environment "tva-env-$LabNum" `
    --image "$AcrLoginServer/tva-mcp-server:latest" `
    --registry-server $AcrLoginServer `
    --registry-username $AcrName `
    --registry-password $AcrPassword `
    --target-port 8000 `
    --ingress external `
    --output none

$AppUrl = az containerapp show --name $AppName --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv
Write-Host "        ✅ Container App live: https://$AppUrl" -ForegroundColor Green
if ($Walkthrough) { Read-Host "     Press Enter to continue" }

# Step 5 — Write outputs to .env
Write-Host ""
Write-Host "  [5/5] Writing outputs to ../../.env..." -ForegroundColor Cyan
$envFile = Resolve-Path "../../.env" -ErrorAction SilentlyContinue
if ($envFile) {
    (Get-Content $envFile) -replace "^MCP_BACKEND_URL=.*", "MCP_BACKEND_URL=https://$AppUrl" | Set-Content $envFile
    Write-Host "        ✅ MCP_BACKEND_URL updated in .env" -ForegroundColor Green
} else {
    Write-Host "        ℹ️  Add to .env: MCP_BACKEND_URL=https://$AppUrl"
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅  Azure stack provisioned!                            ║" -ForegroundColor Green
Write-Host "║                                                          ║" -ForegroundColor Green
Write-Host "║  MCP Server: https://$AppUrl" -ForegroundColor Green
Write-Host "║  Next: LAB_NUM=$LabNum npx just test:prod                ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
