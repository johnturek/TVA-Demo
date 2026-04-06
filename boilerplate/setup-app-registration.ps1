# Setup Azure App Registration for TVA Document Processor (OBO Flow)
# Prerequisites: az cli installed and logged in to correct tenant
# Usage: .\setup-app-registration.ps1 -TenantId "your-tenant-id"

param(
    [string]$AppName  = "tva-doc-processor",
    [string]$TenantId = $env:AZURE_TENANT_ID
)

if (-not $TenantId) {
    Write-Error "TenantId is required. Pass -TenantId or set AZURE_TENANT_ID env var."
    exit 1
}

Write-Host "🔧 Creating app registration: $AppName" -ForegroundColor Cyan

# Create the app registration
$app = az ad app create `
    --display-name $AppName `
    --sign-in-audience "AzureADMyOrg" `
    --output json | ConvertFrom-Json

$appId = $app.appId
Write-Host "✅ App registered — Client ID: $appId"

# Expose an API scope (required for OBO)
$scopeId = [guid]::NewGuid().ToString()
az ad app update --id $appId --identifier-uris "api://$appId"
az ad app update --id $appId --set "api={`"oauth2PermissionScopes`":[{`"adminConsentDescription`":`"Access TVA Document Processor`",`"adminConsentDisplayName`":`"Access TVA Doc Processor`",`"id`":`"$scopeId`",`"isEnabled`":true,`"type`":`"User`",`"userConsentDescription`":`"Access TVA Document Processor`",`"userConsentDisplayName`":`"Access TVA Doc Processor`",`"value`":`"access_as_user`"}]}"
Write-Host "✅ API scope configured: api://$appId/access_as_user"

# Add Microsoft Graph permissions (openid, profile, User.Read)
az ad app permission add `
    --id $appId `
    --api "00000003-0000-0000-c000-000000000000" `
    --api-permissions `
        "37f7f235-527c-4136-accd-4a02d197296e=Scope" `
        "14dad69e-099b-42c9-810b-d002981feec1=Scope" `
        "e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope"
Write-Host "✅ Graph permissions added (openid, profile, User.Read)"

# Create service principal
az ad sp create --id $appId | Out-Null
Write-Host "✅ Service principal created"

# Create client secret (90-day expiry for workshop)
$secret = az ad app credential reset `
    --id $appId `
    --years 1 `
    --output json | ConvertFrom-Json

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SAVE THESE VALUES" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  AZURE_TENANT_ID    = $TenantId"
Write-Host "  AZURE_CLIENT_ID    = $appId"
Write-Host "  AZURE_CLIENT_SECRET= $($secret.password)"
Write-Host "  APP_URI            = api://$appId"
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next: Grant admin consent at https://portal.azure.com"
Write-Host "  Azure AD → App registrations → $AppName → API permissions → Grant admin consent"
