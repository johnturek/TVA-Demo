# add-users.ps1
# Assigns one or more users to the MCP.User app role on an Entra app registration.
# Users are specified as a comma-separated list of UPNs.
# Uses Azure CLI.  -WhatIf shows commands without executing.

[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]
param(
  [Parameter(Mandatory=$true)]
  [string] $TenantId,

  # Identify the app by client ID or display name (one required)
  [string] $AppClientId = "",
  [string] $AppDisplayName = "",

  # Comma-separated list of user UPNs to assign
  [Parameter(Mandatory=$true)]
  [string] $Users,

  # App role value to assign (default: MCP.User)
  [string] $RoleName = "MCP.User"
)

$ErrorActionPreference = "Stop"

function Write-Info($msg)  { Write-Host $msg -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host $msg -ForegroundColor Green }
function Write-Err($msg)   { Write-Host $msg -ForegroundColor Red }
function Write-AzCmd($msg) { Write-Host $msg -ForegroundColor Yellow }

function Invoke-AzCli {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory=$true)]
    [string] $Command,
    [switch] $AsJson,
    [switch] $ReadOnly
  )

  Write-AzCmd "AZ> $Command"

  if (-not $ReadOnly -and -not $PSCmdlet.ShouldProcess($Command, "Run Azure CLI command")) {
    return $null
  }

  $stdoutLines = @()
  $stderrLines = @()
  $output = Invoke-Expression $Command 2>&1
  $exitCode = $LASTEXITCODE

  foreach ($line in $output) {
    if ($line -is [System.Management.Automation.ErrorRecord]) {
      $stderrLines += $line.ToString()
    } else {
      $stdoutLines += "$line"
    }
  }

  if ($exitCode -ne 0) {
    Write-Err "Azure CLI command failed (exit=$exitCode):"
    if ($stderrLines.Count -gt 0) {
      $stderrLines | ForEach-Object { Write-Err "  $_" }
    } elseif ($stdoutLines.Count -gt 0) {
      $stdoutLines | Select-Object -Last 10 | ForEach-Object { Write-Err "  $_" }
    }
    throw "az command failed (exit=$exitCode)"
  }

  $text = ($stdoutLines -join "`n")
  if ($AsJson) {
    if ([string]::IsNullOrWhiteSpace($text)) { return $null }
    return $text | ConvertFrom-Json
  }

  return $text
}

function Graph-Get($url) {
  return Invoke-AzCli -ReadOnly -Command "az rest --method GET --url '$url'"
}

function Graph-Post($url, [hashtable]$body) {
  $bodyJson = ($body | ConvertTo-Json -Depth 10 -Compress)
  $tempDir = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
  $bodyFile = Join-Path $tempDir "add-users-post-$([guid]::NewGuid().ToString('N').Substring(0,8)).json"
  $bodyJson | Out-File -FilePath $bodyFile -Encoding utf8
  try {
    return Invoke-AzCli -Command "az rest --method POST --url '$url' --body '@$bodyFile'"
  } finally {
    Remove-Item -Path $bodyFile -ErrorAction SilentlyContinue
  }
}

# ── Validate params ──────────────────────────────────────────────────────────

if (-not $AppClientId -and -not $AppDisplayName) {
  throw "Provide either -AppClientId or -AppDisplayName to identify the app registration."
}

# ── Login check ──────────────────────────────────────────────────────────────

Write-Info "== Validating Azure CLI login =="
$acct = Invoke-AzCli -ReadOnly -Command "az account show -o json" -AsJson
if (-not $acct) { throw "Not logged in. Run: az login" }

# ── Find the app ─────────────────────────────────────────────────────────────

if ($AppClientId) {
  Write-Info "== Looking up app by client ID: $AppClientId =="
  $app = Invoke-AzCli -ReadOnly -Command "az ad app show --id '$AppClientId' -o json" -AsJson
  if (-not $app) { throw "App not found with client ID '$AppClientId'." }
} else {
  Write-Info "== Looking up app by display name: $AppDisplayName =="
  $apps = Invoke-AzCli -ReadOnly -Command "az ad app list --display-name '$AppDisplayName' --query ""[].{appId:appId,id:id,displayName:displayName}"" -o json" -AsJson
  if (-not $apps -or $apps.Count -eq 0) { throw "No app found with display name '$AppDisplayName'." }
  if ($apps.Count -gt 1) { throw "Multiple apps found with display name '$AppDisplayName'. Use -AppClientId instead." }
  $AppClientId = $apps[0].appId
  $app = Invoke-AzCli -ReadOnly -Command "az ad app show --id '$AppClientId' -o json" -AsJson
}

$objectId = $app.id
Write-Ok "Found app: $($app.displayName) (appId=$($app.appId), objectId=$objectId)"

# ── Find the service principal ───────────────────────────────────────────────

Write-Info "== Looking up service principal =="
$spList = Invoke-AzCli -ReadOnly -Command "az ad sp list --filter ""appId eq '$AppClientId'"" -o json" -AsJson
if (-not $spList -or $spList.Count -eq 0) {
  throw "No service principal found for app '$AppClientId'. Run setup-entra-apps.ps1 first."
}
$sp = $spList | Select-Object -First 1
$spId = $sp.id
Write-Ok "Service principal: $spId"

# ── Find the app role ────────────────────────────────────────────────────────

Write-Info "== Looking up app role '$RoleName' =="
$appRolesRaw = Graph-Get "https://graph.microsoft.com/v1.0/applications/$objectId"
$appRoles = ($appRolesRaw | ConvertFrom-Json).appRoles
$roleObj = $appRoles | Where-Object { $_.value -eq $RoleName } | Select-Object -First 1
if (-not $roleObj) {
  throw "App role '$RoleName' not found on app '$($app.displayName)'. Available roles: $(($appRoles | ForEach-Object { $_.value }) -join ', ')"
}
$roleId = $roleObj.id
Write-Ok "Found role '$RoleName' (id=$roleId)"

# ── Get existing role assignments ────────────────────────────────────────────

Write-Info "== Loading existing role assignments =="
$existingRaw = Graph-Get "https://graph.microsoft.com/v1.0/servicePrincipals/$spId/appRoleAssignedTo"
$existingAssignments = ($existingRaw | ConvertFrom-Json).value

# ── Parse user list and assign ───────────────────────────────────────────────

$userList = $Users -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }

if ($userList.Count -eq 0) {
  throw "No users specified. Provide a comma-separated list of UPNs."
}

Write-Info "== Assigning $($userList.Count) user(s) to '$RoleName' role =="

$assigned = 0
$skipped = 0
$failed = 0

foreach ($upn in $userList) {
  Write-Host ""
  Write-Info "Processing: $upn"

  # Look up the user
  try {
    $userObj = Invoke-AzCli -ReadOnly -Command "az ad user show --id '$upn' -o json" -AsJson
  } catch {
    Write-Err "  Could not find user '$upn' — skipping."
    $failed++
    continue
  }

  if (-not $userObj) {
    Write-Err "  User '$upn' not found — skipping."
    $failed++
    continue
  }

  $userId = $userObj.id

  # Check if already assigned
  $existing = $existingAssignments | Where-Object {
    $_.principalId -eq $userId -and $_.appRoleId -eq $roleId
  } | Select-Object -First 1

  if ($existing) {
    Write-Ok "  '$upn' already has '$RoleName' role — skipping."
    $skipped++
    continue
  }

  # Assign the role
  try {
    Graph-Post "https://graph.microsoft.com/v1.0/servicePrincipals/$spId/appRoleAssignedTo" @{
      principalId = $userId
      resourceId  = $spId
      appRoleId   = $roleId
    } | Out-Null
    Write-Ok "  Assigned '$upn' to '$RoleName' role."
    $assigned++
  } catch {
    Write-Err "  Failed to assign '$upn': $_"
    $failed++
  }
}

# ── Summary ──────────────────────────────────────────────────────────────────

Write-Host ""
Write-Ok "==================== SUMMARY ===================="
Write-Host "  App:       $($app.displayName) ($AppClientId)"
Write-Host "  Role:      $RoleName"
Write-Host "  Assigned:  $assigned"
Write-Host "  Skipped:   $skipped (already assigned)"
Write-Host "  Failed:    $failed"
Write-Host "  Total:     $($userList.Count)"
Write-Ok "================================================="
