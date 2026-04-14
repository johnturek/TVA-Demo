# add-reply-url.ps1
# Adds a redirect URI to an existing Entra app registration.
# Uses Azure CLI.  -WhatIf shows commands without executing.

[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]
param(
  [Parameter(Mandatory=$true)]
  [string] $TenantId,

  # Identify the app by client ID or display name (one required)
  [string] $AppClientId = "",
  [string] $AppDisplayName = "",

  [Parameter(Mandatory=$true)]
  [string] $ReplyUrl
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
    if ($AllowFailure) { return $null }
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

# ── Read current redirect URIs ───────────────────────────────────────────────

Write-Info "== Reading current redirect URIs =="
$appRaw = Invoke-AzCli -ReadOnly -Command "az rest --method GET --url 'https://graph.microsoft.com/v1.0/applications/$objectId'"
$appObj = $appRaw | ConvertFrom-Json

$currentUris = @()
if ($appObj.web -and $appObj.web.redirectUris) {
  $currentUris = @($appObj.web.redirectUris)
}

Write-Info "Current redirect URIs ($($currentUris.Count)):"
foreach ($uri in $currentUris) { Write-Host "  $uri" }

# ── Add if not already present ───────────────────────────────────────────────

if ($currentUris -contains $ReplyUrl) {
  Write-Ok "Reply URL already present: $ReplyUrl"
  return
}

$updatedUris = @($currentUris + $ReplyUrl)

Write-Info "== Adding reply URL: $ReplyUrl =="
$body = @{ web = @{ redirectUris = $updatedUris } } | ConvertTo-Json -Depth 10 -Compress
$tempDir = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
$bodyFile = Join-Path $tempDir "reply-url-patch-$objectId.json"
$body | Out-File -FilePath $bodyFile -Encoding utf8
Invoke-AzCli -Command "az rest --method PATCH --url 'https://graph.microsoft.com/v1.0/applications/$objectId' --body '@$bodyFile'" | Out-Null
Remove-Item -Path $bodyFile -ErrorAction SilentlyContinue

Write-Ok "Added reply URL: $ReplyUrl"
Write-Ok "Total redirect URIs: $($updatedUris.Count)"
