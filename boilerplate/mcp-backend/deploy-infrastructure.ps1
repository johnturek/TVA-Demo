# deploy-infrastructure.ps1
# Creates Resource Group, ACR, Container Apps Environment, builds and deploys the MCP container app.
# Uses Azure CLI for all operations.  -WhatIf shows commands without executing.

[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]
param(
  [Parameter(Mandatory=$true)]
  [string] $SubscriptionId,

  [Parameter(Mandatory=$true)]
  [string] $ResourceGroup,

  [string] $Location = "eastus2",

  [string] $AcrName = "",

  [string] $ContainerAppsEnvName = "",

  [string] $ContainerAppName = "mcp-server",

  [string] $ImageName = "mcp-server",

  [string] $ImageTag = "",

  [string] $Cpu = "0.5",

  [string] $Memory = "1.0Gi"
)

$ErrorActionPreference = "Stop"

# ── Helpers ──────────────────────────────────────────────────────────────────

function Write-Info($msg)  { Write-Host $msg -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host $msg -ForegroundColor Magenta }
function Write-Err($msg)   { Write-Host $msg -ForegroundColor Red }
function Write-AzCmd($msg) { Write-Host $msg -ForegroundColor Yellow }

function Invoke-AzCli {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory=$true)]
    [string] $Command,
    [switch] $AsJson,
    [switch] $ReadOnly,
    [switch] $AllowFailure
  )

  Write-AzCmd "AZ> $Command"

  if (-not $ReadOnly -and -not $PSCmdlet.ShouldProcess($Command, "Run Azure CLI command")) {
    return $null
  }

  $stdoutLines = @()
  $stderrLines = @()
  $prevEAP = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  $output = Invoke-Expression $Command 2>&1
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $prevEAP

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

# ── Defaults ─────────────────────────────────────────────────────────────────

# Derive names from resource group if not provided
$rgSlug = $ResourceGroup -replace '[^a-zA-Z0-9]', ''
if (-not $AcrName)             { $AcrName = "${rgSlug}acr".ToLower() }
if (-not $ContainerAppsEnvName) { $ContainerAppsEnvName = "${ResourceGroup}-env" }
if (-not $ImageTag)            { $ImageTag = "v" + (Get-Date -Format "yyyyMMdd-HHmmss") }

# ── Login & Subscription ────────────────────────────────────────────────────

Write-Info "== Validating Azure CLI login =="
$acct = Invoke-AzCli -ReadOnly -Command "az account show -o json" -AsJson
if (-not $acct) { throw "Not logged in. Run: az login" }

Write-Info "== Setting subscription to $SubscriptionId =="
Invoke-AzCli -Command "az account set --subscription '$SubscriptionId'" | Out-Null

# ── Resource Group ───────────────────────────────────────────────────────────

Write-Info "== Creating resource group: $ResourceGroup =="
$rgExists = Invoke-AzCli -ReadOnly -AllowFailure -Command "az group show --name '$ResourceGroup' -o json" -AsJson
if (-not $rgExists) {
  $rgResult = Invoke-AzCli -Command "az group create --name '$ResourceGroup' --location '$Location' -o json" -AsJson
  if (-not $rgResult) {
    Write-Warn "WhatIf: would create resource group '$ResourceGroup' in '$Location'"
    Write-Warn "WhatIf: would create ACR '$AcrName', Container Apps Environment '$ContainerAppsEnvName', build and deploy Container App '$ContainerAppName'"
    return
  }
  Write-Ok "Created resource group: $ResourceGroup"
} else {
  $Location = $rgExists.location
  Write-Ok "Resource group exists: $ResourceGroup (location=$Location)"
}

# ── Azure Container Registry ────────────────────────────────────────────────

Write-Info "== Creating ACR: $AcrName =="
$acrExists = Invoke-AzCli -ReadOnly -AllowFailure -Command "az acr show --name '$AcrName' --resource-group '$ResourceGroup' -o json" -AsJson
if (-not $acrExists) {
  Invoke-AzCli -Command "az acr create --name '$AcrName' --resource-group '$ResourceGroup' --location '$Location' --sku Basic --admin-enabled true -o json" -AsJson | Out-Null
  Write-Ok "Created ACR: $AcrName"
} else {
  Write-Ok "ACR exists: $AcrName"
}

# ── Container Apps Environment ───────────────────────────────────────────────

# NOTE: Uses az resource / az rest instead of az containerapp to avoid the
#       slow-to-install containerapp CLI extension.

$managedEnvResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.App/managedEnvironments/$ContainerAppsEnvName"

Write-Info "== Creating Container Apps Environment: $ContainerAppsEnvName =="
$envExists = Invoke-AzCli -ReadOnly -AllowFailure -Command "az resource show --ids '$managedEnvResourceId' -o json" -AsJson
if (-not $envExists) {
  Invoke-AzCli -Command "az resource create --resource-group '$ResourceGroup' --resource-type Microsoft.App/managedEnvironments --name '$ContainerAppsEnvName' --location '$Location' --properties '{}' -o json" -AsJson | Out-Null
  Write-Ok "Created Container Apps Environment: $ContainerAppsEnvName"
} else {
  Write-Ok "Container Apps Environment exists: $ContainerAppsEnvName"
}

# ── Build image in ACR ───────────────────────────────────────────────────────

$imageRef = "${ImageName}:${ImageTag}"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check if an image already exists in the registry
$existingTags = Invoke-AzCli -ReadOnly -AllowFailure -Command "az acr repository show-tags --name '$AcrName' --repository '$ImageName' --orderby time_desc --top 1 -o tsv"
if ($existingTags) {
  $latestTag = ($existingTags -split "`n" | Select-Object -First 1).Trim()
  Write-Ok "Found existing image: ${ImageName}:${latestTag}"
  $isWhatIf = -not $PSCmdlet.ShouldProcess("check", "Rebuild prompt")
  if ($isWhatIf) {
    $rebuild = "n"
    Write-Warn "WhatIf: skipping rebuild prompt, reusing existing image"
  } else {
    $rebuild = Read-Host "Rebuild image with az acr build? (y/n, default=n)"
  }
  if ($rebuild -notmatch '^[yY]') {
    $imageRef = "${ImageName}:${latestTag}"
    Write-Info "Reusing existing image: $imageRef"
  } else {
    Write-Info "== Building image in ACR: $imageRef =="

    if (-not $PSCmdlet.ShouldProcess("az acr build --image '$imageRef'", "Run Azure CLI command")) {
      Write-Warn "WhatIf: would build image '$imageRef' in ACR '$AcrName' and deploy Container App '$ContainerAppName'"
      return
    }

    # Work around Azure CLI 'charmap' encoding bug on Windows (colorama/cp1252)
    $prevEncoding = $env:PYTHONIOENCODING
    $env:PYTHONIOENCODING = "utf-8"

    # Run build as a background job so we can show progress dots
    $buildCmd = "az acr build --registry '$AcrName' --resource-group '$ResourceGroup' --image '$imageRef' '$scriptDir' --no-logs 2>&1"
    Write-AzCmd "AZ> $buildCmd"
    $buildJob = Start-Job -ScriptBlock {
      param($cmd, $enc)
      $env:PYTHONIOENCODING = $enc
      Invoke-Expression $cmd
    } -ArgumentList $buildCmd, "utf-8"

    Write-Host -NoNewline "  Building"

    # Poll the job for completion, showing dots
    while ($buildJob.State -eq 'Running') {
      Start-Sleep -Seconds 5
      Write-Host -NoNewline "."
    }

    $buildOutput = Receive-Job $buildJob
    $buildHadError = $buildJob.State -eq 'Failed'
    Remove-Job $buildJob

    $env:PYTHONIOENCODING = $prevEncoding

    Write-Host ""

    # Extract run ID from output
    $runId = $null
    foreach ($line in $buildOutput) {
      $lineStr = "$line"
      if ($lineStr -match 'ID:\s*(\S+)') {
        $runId = $Matches[1]
        break
      }
    }
    if (-not $runId) {
      $runId = (Invoke-AzCli -ReadOnly -Command "az acr task list-runs --registry '$AcrName' --resource-group '$ResourceGroup' --top 1 --query '[0].runId' -o tsv" 2>$null)
      if ($runId) { $runId = $runId.Trim() }
    }

    $runIdMsg = if ($runId) { " (run ID: $runId)" } else { "" }

    if ($buildHadError) {
      Write-Err "ACR build failed$runIdMsg"
      $tail = ($buildOutput | ForEach-Object { "$_" }) | Select-Object -Last 10
      $tail | ForEach-Object { Write-Err $_ }
      if ($runId) {
        Write-Err "Full logs: az acr task logs --registry '$AcrName' --resource-group '$ResourceGroup' --run-id '$runId'"
      }
      throw "ACR build failed$runIdMsg"
    }

    # Verify image tag exists in registry
    $verifyTag = Invoke-AzCli -ReadOnly -AllowFailure -Command "az acr repository show-tags --name '$AcrName' --repository '$ImageName' --query ""[?contains(@, '$ImageTag')]"" -o tsv"
    if (-not $verifyTag) {
      Write-Err "ACR build completed but image tag '$ImageTag' not found in registry$runIdMsg"
      if ($runId) {
        Write-Err "Check logs: az acr task logs --registry '$AcrName' --resource-group '$ResourceGroup' --run-id '$runId'"
      }
      throw "ACR build verification failed$runIdMsg"
    }

    Write-Ok "ACR build confirmed: $imageRef$runIdMsg"
  }
} else {
  # No existing image — must build
  Write-Info "== Building image in ACR: $imageRef =="

  if (-not $PSCmdlet.ShouldProcess("az acr build --image '$imageRef'", "Run Azure CLI command")) {
    Write-Warn "WhatIf: would build image '$imageRef' in ACR '$AcrName' and deploy Container App '$ContainerAppName'"
    return
  }

  $prevEncoding = $env:PYTHONIOENCODING
  $env:PYTHONIOENCODING = "utf-8"

  $buildCmd = "az acr build --registry '$AcrName' --resource-group '$ResourceGroup' --image '$imageRef' '$scriptDir' --no-logs 2>&1"
  Write-AzCmd "AZ> $buildCmd"
  $buildJob = Start-Job -ScriptBlock {
    param($cmd, $enc)
    $env:PYTHONIOENCODING = $enc
    Invoke-Expression $cmd
  } -ArgumentList $buildCmd, "utf-8"

  Write-Host -NoNewline "  Building"
  while ($buildJob.State -eq 'Running') {
    Start-Sleep -Seconds 5
    Write-Host -NoNewline "."
  }

  $buildOutput = Receive-Job $buildJob
  $buildHadError = $buildJob.State -eq 'Failed'
  Remove-Job $buildJob

  $env:PYTHONIOENCODING = $prevEncoding
  Write-Host ""

  $runId = $null
  foreach ($line in $buildOutput) {
    $lineStr = "$line"
    if ($lineStr -match 'ID:\s*(\S+)') {
      $runId = $Matches[1]
      break
    }
  }
  if (-not $runId) {
    $runId = (Invoke-AzCli -ReadOnly -Command "az acr task list-runs --registry '$AcrName' --resource-group '$ResourceGroup' --top 1 --query '[0].runId' -o tsv" 2>$null)
    if ($runId) { $runId = $runId.Trim() }
  }

  $runIdMsg = if ($runId) { " (run ID: $runId)" } else { "" }

  if ($buildHadError) {
    Write-Err "ACR build failed$runIdMsg"
    $tail = ($buildOutput | ForEach-Object { "$_" }) | Select-Object -Last 10
    $tail | ForEach-Object { Write-Err $_ }
    if ($runId) {
      Write-Err "Full logs: az acr task logs --registry '$AcrName' --resource-group '$ResourceGroup' --run-id '$runId'"
    }
    throw "ACR build failed$runIdMsg"
  }

  $verifyTag = Invoke-AzCli -ReadOnly -AllowFailure -Command "az acr repository show-tags --name '$AcrName' --repository '$ImageName' --query ""[?contains(@, '$ImageTag')]"" -o tsv"
  if (-not $verifyTag) {
    Write-Err "ACR build completed but image tag '$ImageTag' not found in registry$runIdMsg"
    if ($runId) {
      Write-Err "Check logs: az acr task logs --registry '$AcrName' --resource-group '$ResourceGroup' --run-id '$runId'"
    }
    throw "ACR build verification failed$runIdMsg"
  }

  Write-Ok "ACR build confirmed: $imageRef$runIdMsg"
}

# ── Deploy Container App ─────────────────────────────────────────────────────

$acrLoginServer = Invoke-AzCli -ReadOnly -Command "az acr show --name '$AcrName' --resource-group '$ResourceGroup' --query loginServer -o tsv"
$containerImage = "$acrLoginServer/$imageRef"

# Read env settings from .env file
$envFilePath = Join-Path $scriptDir ".env"
if (-not (Test-Path $envFilePath)) {
  Write-Warn "No .env file found at $envFilePath - container app will need env vars configured manually."
  $envSettings = @{}
} else {
  $envSettings = @{}
  foreach ($line in (Get-Content $envFilePath)) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
    $parts = $trimmed.Split("=", 2)
    if ($parts.Count -eq 2 -and $parts[0].Trim()) {
      $envSettings[$parts[0].Trim()] = $parts[1].Trim()
    }
  }
}

# Build secrets and env-var arrays (skip empty values — Container Apps rejects empty secrets)
$secrets = @()
$envVars = @()
foreach ($entry in $envSettings.GetEnumerator()) {
  if ([string]::IsNullOrWhiteSpace($entry.Value)) { continue }
  $secretName = $entry.Key.ToLower().Replace("_", "-")
  $secrets += "{0}={1}" -f $secretName, $entry.Value
  $envVars += "{0}=secretref:{1}" -f $entry.Key, $secretName
}
if (-not $envSettings.ContainsKey("FASTMCP_HOST")) {
  $envVars += "FASTMCP_HOST=0.0.0.0"
}
if (-not $envSettings.ContainsKey("FASTMCP_PORT")) {
  $envVars += "FASTMCP_PORT=8000"
}

# Get ACR credentials
$acrCreds = Invoke-AzCli -ReadOnly -Command "az acr credential show --name '$AcrName' --query ""{username:username,password:passwords[0].value}"" -o json" -AsJson

Write-Info "== Deploying Container App: $ContainerAppName =="
$containerAppResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.App/containerApps/$ContainerAppName"
$appExists = Invoke-AzCli -ReadOnly -AllowFailure -Command "az resource show --ids '$containerAppResourceId' -o json" -AsJson

# Build container env vars and secrets for ARM template (skip empty values)
$armSecrets = @()
$armEnvVars = @()
foreach ($entry in $envSettings.GetEnumerator()) {
  if ([string]::IsNullOrWhiteSpace($entry.Value)) { continue }
  $secretName = $entry.Key.ToLower().Replace("_", "-")
  $armSecrets += @{ name = $secretName; value = $entry.Value }
  $armEnvVars += @{ name = $entry.Key; secretRef = $secretName }
}
if (-not $envSettings.ContainsKey("FASTMCP_HOST")) {
  $armEnvVars += @{ name = "FASTMCP_HOST"; value = "0.0.0.0" }
}
if (-not $envSettings.ContainsKey("FASTMCP_PORT")) {
  $armEnvVars += @{ name = "FASTMCP_PORT"; value = "8000" }
}

$containerAppBody = @{
  location = $Location
  properties = @{
    managedEnvironmentId = $managedEnvResourceId
    configuration = @{
      ingress = @{
        external = $true
        targetPort = 8000
        transport = "auto"
      }
      registries = @(
        @{
          server = $acrLoginServer
          username = $acrCreds.username
          passwordSecretRef = "acr-password"
        }
      )
      secrets = @(@{ name = "acr-password"; value = $acrCreds.password }) + $armSecrets
    }
    template = @{
      containers = @(
        @{
          name = "mcp-server"
          image = $containerImage
          env = $armEnvVars
          resources = @{
            cpu = [double]$Cpu
            memory = $Memory
          }
        }
      )
      scale = @{
        minReplicas = 1
        maxReplicas = 1
      }
    }
  }
} | ConvertTo-Json -Depth 20 -Compress

# Write body to temp file to avoid shell quoting issues
$tempDir = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
$bodyFile = Join-Path $tempDir "containerapp-$ContainerAppName.json"
$containerAppBody | Set-Content -Path $bodyFile -Encoding utf8

$apiVersion = "2024-03-01"
$responseFile = Join-Path $tempDir "containerapp-response-$ContainerAppName.json"
if (-not $appExists) {
  Invoke-AzCli -Command "az rest --method PUT --url 'https://management.azure.com${containerAppResourceId}?api-version=$apiVersion' --body '@$bodyFile' --output-file '$responseFile'" | Out-Null
  Write-Ok "Created Container App: $ContainerAppName"
} else {
  Invoke-AzCli -Command "az rest --method PUT --url 'https://management.azure.com${containerAppResourceId}?api-version=$apiVersion' --body '@$bodyFile' --output-file '$responseFile'" | Out-Null
  Write-Ok "Updated Container App: $ContainerAppName"

  # Restart the active revision so it picks up changed secrets/env vars
  $activeRevision = Invoke-AzCli -ReadOnly -Command "az containerapp revision list --name '$ContainerAppName' --resource-group '$ResourceGroup' --query `"[0].name`" -o tsv"
  if ($activeRevision) {
    $activeRevision = $activeRevision.Trim()
    Write-Info "Restarting revision $activeRevision to apply updated secrets..."
    Invoke-AzCli -Command "az containerapp revision restart --name '$ContainerAppName' --resource-group '$ResourceGroup' --revision '$activeRevision'" | Out-Null
    Write-Ok "Revision restarted."
  }
}

Remove-Item $bodyFile -ErrorAction SilentlyContinue
Remove-Item $responseFile -ErrorAction SilentlyContinue

# ── Wait for FQDN ───────────────────────────────────────────────────────────

# The PUT is async — Azure may still be provisioning ingress.  Poll until the
# FQDN appears, bail early on terminal provisioning states.
$appFqdn = $null
$maxAttempts = 18          # 18 × 10 s = 3 minutes
$pollInterval = 10
for ($attempt = 0; $attempt -lt $maxAttempts; $attempt++) {
  $appResource = Invoke-AzCli -ReadOnly -AllowFailure `
    -Command "az resource show --ids '$containerAppResourceId' -o json" -AsJson

  if ($appResource) {
    $provState = $appResource.properties.provisioningState
    $appFqdn   = $appResource.properties.configuration.ingress.fqdn

    if ($appFqdn) { $appFqdn = $appFqdn.Trim() }
    if ($appFqdn) { break }

    # Bail early on terminal failure states
    if ($provState -and $provState -notin @('Succeeded','InProgress','Waiting')) {
      Write-Err "Container App provisioning entered terminal state: $provState"
      throw "Container App provisioning failed (state=$provState)"
    }

    # Provisioning succeeded but no FQDN — ingress misconfiguration
    if ($provState -eq 'Succeeded') {
      Write-Err "Provisioning succeeded but no FQDN assigned. Check ingress configuration."
      throw "Container App has no FQDN (provisioningState=Succeeded but ingress.fqdn is empty)"
    }
  }

  if ($attempt -eq 0) { Write-Host -NoNewline "  Waiting for FQDN" }
  Write-Host -NoNewline "."
  Start-Sleep -Seconds $pollInterval
}
if ($attempt -gt 0 -and $attempt -lt $maxAttempts) { Write-Host "" }

if (-not $appFqdn) {
  $elapsed = $maxAttempts * $pollInterval
  Write-Err "Container App created but FQDN not available after ${elapsed}s."
  Write-Err "Check provisioning status in the Azure portal."
  throw "Timed out waiting for Container App FQDN"
}

# ── Output ───────────────────────────────────────────────────────────────────

Write-Host ""
Write-Ok "==================== OUTPUTS ===================="
Write-Host ("RESOURCE_GROUP:     {0}" -f $ResourceGroup)
Write-Host ("ACR:                {0}" -f $AcrName)
Write-Host ("CONTAINER_ENV:      {0}" -f $ContainerAppsEnvName)
Write-Host ("CONTAINER_APP:      {0}" -f $ContainerAppName)
Write-Host ("APP_URL:            https://{0}" -f $appFqdn)
Write-Host ("MCP_ENDPOINT:       https://{0}/mcp" -f $appFqdn)
Write-Host ("PRM_METADATA:       https://{0}/.well-known/oauth-protected-resource" -f $appFqdn)
Write-Ok "================================================="
Write-Host ""
Write-Info "Next: run deploy-apim.ps1 to put APIM in front of this endpoint."
