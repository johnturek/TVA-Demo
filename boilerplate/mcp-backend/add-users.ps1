<#
.SYNOPSIS
    Assign the MCP.User app role to one or more workshop participants.

.PARAMETER TenantId
    Entra ID tenant ID.

.PARAMETER AppClientId
    Client ID of the MCP server Entra ID app registration.

.PARAMETER Users
    Comma-separated list of user UPNs or object IDs.

.EXAMPLE
    USER_EMAIL=user@contoso.com npx just add-user
#>
param(
    [string]$TenantId    = $env:OBO_TENANT_ID,
    [string]$AppClientId = $env:OAUTH_CLIENT_ID,
    [string]$Users       = $env:USER_EMAIL
)

if (-not $TenantId -or -not $AppClientId -or -not $Users) {
    Write-Host "❌  Required: TenantId, AppClientId, Users" -ForegroundColor Red
    Write-Host "   Set OBO_TENANT_ID, OAUTH_CLIENT_ID, USER_EMAIL in .env or as env vars." -ForegroundColor Red
    exit 1
}

$userList = $Users -split '[,;\s]+' | Where-Object { $_ }

Write-Host ""
Write-Host "  Assigning MCP.User role to $($userList.Count) user(s)..." -ForegroundColor Cyan

# Find the service principal for the app
$sp = az ad sp show --id $AppClientId --query id -o tsv 2>$null
if (-not $sp) {
    Write-Host "  ❌  Service principal not found for AppClientId: $AppClientId" -ForegroundColor Red
    exit 1
}

# Find the MCP.User app role
$roles = az ad sp show --id $AppClientId --query appRoles -o json | ConvertFrom-Json
$mcpRole = $roles | Where-Object { $_.displayName -eq "MCP.User" -or $_.value -eq "MCP.User" } | Select-Object -First 1
if (-not $mcpRole) {
    Write-Host "  ❌  MCP.User app role not found on app registration." -ForegroundColor Red
    Write-Host "     Create it in Azure portal → App registrations → App roles." -ForegroundColor Red
    exit 1
}

foreach ($user in $userList) {
    $userId = az ad user show --id $user --query id -o tsv 2>$null
    if (-not $userId) {
        Write-Host "  ⚠️  User not found: $user" -ForegroundColor Yellow
        continue
    }

    $existing = az rest --method GET `
        --url "https://graph.microsoft.com/v1.0/users/$userId/appRoleAssignments" `
        --query "value[?appRoleId=='$($mcpRole.id)']" -o json 2>$null | ConvertFrom-Json
    if ($existing.Count -gt 0) {
        Write-Host "  ℹ️  $user already has MCP.User role" -ForegroundColor Yellow
        continue
    }

    $body = @{
        principalId = $userId
        resourceId  = $sp
        appRoleId   = $mcpRole.id
    } | ConvertTo-Json

    az rest --method POST `
        --url "https://graph.microsoft.com/v1.0/users/$userId/appRoleAssignments" `
        --body $body `
        --headers "Content-Type=application/json" `
        --output none

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Assigned MCP.User to: $user" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Failed to assign role to: $user" -ForegroundColor Red
    }
}

Write-Host ""
