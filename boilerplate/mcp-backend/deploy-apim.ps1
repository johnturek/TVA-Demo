# deploy-apim.ps1
# Creates APIM Basic v2, configures an API that proxies the MCP Container App,
# and applies a validate-jwt inbound policy.
# Uses Azure CLI.  -WhatIf shows commands without executing.

[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]
param(
  [Parameter(Mandatory=$true)]
  [string] $SubscriptionId,

  [Parameter(Mandatory=$true)]
  [string] $ResourceGroup,

  [string] $Location = "eastus2",

  [Parameter(Mandatory=$true)]
  [string] $ApimName,

  [Parameter(Mandatory=$true)]
  [string] $ContainerAppName,

  [Parameter(Mandatory=$true)]
  [string] $TenantId,

  # Entra API app registration name — used to look up the audience (client ID)
  [Parameter(Mandatory=$true)]
  [string] $ApiAppName,

  [string] $ApimApiName = "mcp-api",
  [string] $ApimApiDisplayName = "MCP Server API",
  [string] $ApimApiPath = "/",
  [string] $PublisherEmail = "admin@contoso.com",
  [string] $PublisherName = "MCP Workshop",
  [string] $ApimSku = "Consumption"
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

# ── Subscription ─────────────────────────────────────────────────────────────

Write-Info "== Setting subscription to $SubscriptionId =="
Invoke-AzCli -Command "az account set --subscription '$SubscriptionId'" | Out-Null

# ── Look up Container App FQDN ──────────────────────────────────────────────

Write-Info "== Looking up Container App FQDN =="
$containerAppResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.App/containerApps/$ContainerAppName"
$appFqdn = Invoke-AzCli -ReadOnly -AllowFailure -Command "az resource show --ids '$containerAppResourceId' --query properties.configuration.ingress.fqdn -o tsv"
if (-not $appFqdn) {
  Write-Warn "Container App '$ContainerAppName' not found. Run deploy-infrastructure.ps1 first."
  Write-Warn "WhatIf: would create APIM '$ApimName' with backend https://<container-app-fqdn>"
  return
}
$appFqdn = $appFqdn.Trim()
$backendUrl = "https://$appFqdn"
Write-Ok "Container App FQDN: $appFqdn"
Write-Ok "Backend URL: $backendUrl"

# ── Look up API app registration audience ────────────────────────────────────

Write-Info "== Looking up API app registration: $ApiAppName =="
$apiApps = Invoke-AzCli -ReadOnly -Command "az ad app list --display-name '$ApiAppName' --query ""[].{appId:appId,displayName:displayName}"" -o json" -AsJson
if (-not $apiApps -or $apiApps.Count -eq 0) {
  Write-Warn "API app registration '$ApiAppName' not found. Run setup-entra-apps.ps1 first."
  return
}
$apiClientId = $apiApps[0].appId
$audience = "api://$apiClientId"
Write-Ok "API audience: $audience"

# ── Create APIM instance (Basic v2) ─────────────────────────────────────────

Write-Info "== Creating/locating APIM: $ApimName ($ApimSku) =="
$apimExists = Invoke-AzCli -ReadOnly -AllowFailure -Command "az apim show --name '$ApimName' --resource-group '$ResourceGroup' -o json" -AsJson
if (-not $apimExists) {
  Write-Info "Creating APIM instance (this can take several minutes)..."
  $apimResult = Invoke-AzCli -Command "az apim create --name '$ApimName' --resource-group '$ResourceGroup' --location '$Location' --publisher-email '$PublisherEmail' --publisher-name '$PublisherName' --sku-name '$ApimSku' --sku-capacity 1 -o json" -AsJson
  if (-not $apimResult) {
    Write-Warn "WhatIf: would create APIM '$ApimName' ($ApimSku) in '$ResourceGroup'"
    Write-Warn "WhatIf: would create API '$ApimApiDisplayName' with backend $backendUrl and validate-jwt policy"
    return
  }
  Write-Ok "Created APIM: $ApimName"
} else {
  Write-Ok "APIM exists: $ApimName"
}

$apimGatewayUrl = Invoke-AzCli -ReadOnly -Command "az apim show --name '$ApimName' --resource-group '$ResourceGroup' --query gatewayUrl -o tsv"
Write-Ok "APIM Gateway: $apimGatewayUrl"

# ── Create API ───────────────────────────────────────────────────────────────

Write-Info "== Creating/locating API: $ApimApiName =="
$apiExists = Invoke-AzCli -ReadOnly -AllowFailure -Command "az apim api show --api-id '$ApimApiName' --service-name '$ApimName' --resource-group '$ResourceGroup' -o json" -AsJson
if (-not $apiExists) {
  Invoke-AzCli -Command "az apim api create --api-id '$ApimApiName' --service-name '$ApimName' --resource-group '$ResourceGroup' --display-name '$ApimApiDisplayName' --path '$ApimApiPath' --service-url '$backendUrl' --protocols https --subscription-required false -o json" | Out-Null
  Write-Ok "Created API: $ApimApiName"
} else {
  # Update backend URL in case it changed
  Invoke-AzCli -Command "az apim api update --api-id '$ApimApiName' --service-name '$ApimName' --resource-group '$ResourceGroup' --service-url '$backendUrl'" | Out-Null
  Write-Ok "API exists, updated backend URL: $backendUrl"
}

# ── Create API operations ───────────────────────────────────────────────────

Write-Info "== Creating API operations =="

# MCP endpoint (POST /mcp) — streamable HTTP transport
$mcpOpExists = Invoke-AzCli -ReadOnly -AllowFailure -Command "az apim api operation show --api-id '$ApimApiName' --operation-id 'mcp-post' --service-name '$ApimName' --resource-group '$ResourceGroup' -o json" -AsJson
if (-not $mcpOpExists) {
  Invoke-AzCli -Command "az apim api operation create --api-id '$ApimApiName' --operation-id 'mcp-post' --service-name '$ApimName' --resource-group '$ResourceGroup' --display-name 'MCP Streamable HTTP' --method POST --url-template '/mcp'" | Out-Null
  Write-Ok "Created operation: POST /mcp"
} else {
  Write-Ok "Operation exists: POST /mcp"
}

# MCP endpoint (GET /mcp) — SSE stream
$mcpGetExists = Invoke-AzCli -ReadOnly -AllowFailure -Command "az apim api operation show --api-id '$ApimApiName' --operation-id 'mcp-get' --service-name '$ApimName' --resource-group '$ResourceGroup' -o json" -AsJson
if (-not $mcpGetExists) {
  Invoke-AzCli -Command "az apim api operation create --api-id '$ApimApiName' --operation-id 'mcp-get' --service-name '$ApimName' --resource-group '$ResourceGroup' --display-name 'MCP SSE Stream' --method GET --url-template '/mcp'" | Out-Null
  Write-Ok "Created operation: GET /mcp"
} else {
  Write-Ok "Operation exists: GET /mcp"
}

# MCP endpoint (DELETE /mcp) — session termination
$mcpDeleteExists = Invoke-AzCli -ReadOnly -AllowFailure -Command "az apim api operation show --api-id '$ApimApiName' --operation-id 'mcp-delete' --service-name '$ApimName' --resource-group '$ResourceGroup' -o json" -AsJson
if (-not $mcpDeleteExists) {
  Invoke-AzCli -Command "az apim api operation create --api-id '$ApimApiName' --operation-id 'mcp-delete' --service-name '$ApimName' --resource-group '$ResourceGroup' --display-name 'MCP Session Delete' --method DELETE --url-template '/mcp'" | Out-Null
  Write-Ok "Created operation: DELETE /mcp"
} else {
  Write-Ok "Operation exists: DELETE /mcp"
}

# PRM metadata (GET /.well-known/oauth-protected-resource) — no auth required
$prmOpExists = Invoke-AzCli -ReadOnly -AllowFailure -Command "az apim api operation show --api-id '$ApimApiName' --operation-id 'prm-metadata' --service-name '$ApimName' --resource-group '$ResourceGroup' -o json" -AsJson
if (-not $prmOpExists) {
  Invoke-AzCli -Command "az apim api operation create --api-id '$ApimApiName' --operation-id 'prm-metadata' --service-name '$ApimName' --resource-group '$ResourceGroup' --display-name 'PRM Metadata' --method GET --url-template '/.well-known/oauth-protected-resource'" | Out-Null
  Write-Ok "Created operation: GET /.well-known/oauth-protected-resource"
} else {
  Write-Ok "Operation exists: GET /.well-known/oauth-protected-resource"
}

# ── Apply validate-jwt policy ───────────────────────────────────────────────

Write-Info "== Applying validate-jwt inbound policy to API =="

$openIdConfigUrl = "https://login.microsoftonline.com/$TenantId/v2.0/.well-known/openid-configuration"

$policyXml = @"
<policies>
  <inbound>
    <base />
    <choose>
      <when condition="@(context.Operation.Id == &quot;prm-metadata&quot;)">
        <!-- PRM metadata endpoint: no auth required -->
      </when>
      <otherwise>
        <validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized. Valid bearer token required.">
          <openid-config url="$openIdConfigUrl" />
          <audiences>
            <audience>$audience</audience>
            <audience>$apiClientId</audience>
          </audiences>
          <issuers>
            <issuer>https://login.microsoftonline.com/$TenantId/v2.0</issuer>
            <issuer>https://sts.windows.net/$TenantId/</issuer>
          </issuers>
        </validate-jwt>
      </otherwise>
    </choose>
  </inbound>
  <backend>
    <base />
  </backend>
  <outbound>
    <base />
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>
"@

# Apply policy via ARM REST API (az apim api policy not available in all CLI versions)
$policyBody = @{
  properties = @{
    format = "xml"
    value  = $policyXml
  }
} | ConvertTo-Json -Depth 5 -Compress

$tempDir = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
$policyFile = Join-Path $tempDir "apim-mcp-policy-$ApimName.json"
$policyResponseFile = Join-Path $tempDir "apim-mcp-policy-response-$ApimName.xml"
Set-Content -Path $policyFile -Value $policyBody -Encoding UTF8

$policyUrl = "https://management.azure.com/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.ApiManagement/service/$ApimName/apis/$ApimApiName/policies/policy?api-version=2022-08-01"
Invoke-AzCli -Command "az rest --method PUT --url '$policyUrl' --body '@$policyFile' --output-file '$policyResponseFile'" | Out-Null

if (Test-Path $policyFile) { Remove-Item $policyFile -Force }
if (Test-Path $policyResponseFile) { Remove-Item $policyResponseFile -Force }

Write-Ok "Applied validate-jwt policy."

# ── Output ───────────────────────────────────────────────────────────────────

Write-Host ""
Write-Ok "==================== APIM OUTPUTS ===================="
Write-Host ("APIM_NAME:          {0}" -f $ApimName)
Write-Host ("APIM_GATEWAY:       {0}" -f $apimGatewayUrl)
Write-Host ("MCP_ENDPOINT:       {0}/mcp" -f $apimGatewayUrl)
Write-Host ("PRM_METADATA:       {0}/.well-known/oauth-protected-resource" -f $apimGatewayUrl)
Write-Host ("BACKEND_URL:        {0}" -f $backendUrl)
Write-Host ("JWT_AUDIENCE:       {0}" -f $audience)
Write-Host ("JWT_ISSUER:         https://login.microsoftonline.com/{0}/v2.0" -f $TenantId)
Write-Ok "======================================================="
Write-Host ""
Write-Info "MCP clients should connect to: $apimGatewayUrl/mcp"
Write-Info "PRM metadata served at: $apimGatewayUrl/.well-known/oauth-protected-resource"
