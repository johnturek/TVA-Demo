# deploy.ps1
# Orchestrates the full deployment: Entra app registrations, Azure infrastructure, and APIM.
# Uses Azure CLI.  -WhatIf is passed through to all child scripts.

[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]
param(
  # Optional overrides — if omitted, pulled from current az login context
  [string] $TenantId = "",
  [string] $SubscriptionId = "",

  # All resource names derived from this prefix
  [string] $Prefix = "mcp-workshop",

  # Lab number — appended to resource names for multi-deployment in one RG (e.g. "l03")
  [string] $LabNum = "",

  [string] $Location = "eastus2",

  # Override the resource group name (skip "$Prefix-rg" derivation)
  [string] $ResourceGroupOverride = "",

  # Steps to run (default: all)
  [switch] $SkipEntra,
  [switch] $SkipInfrastructure,
  [switch] $SkipApim,
  [switch] $SkipTests,

  # Walkthrough mode: pause at each step with detailed explanations
  [Alias("Explain")]
  [switch] $Walkthrough
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
  foreach ($line in $Lines) {
    Write-Host "  $line" -ForegroundColor Gray
  }
  Write-Host ""
  Write-Host "  Press ENTER to continue, or Ctrl+C to stop..." -ForegroundColor DarkYellow -NoNewline
  Read-Host
  Write-Host ""
}

# ── Login & resolve tenant/subscription from az context ──────────────────────

Write-Info "== Checking Azure CLI login =="
$acct = az account show -o json 2>$null | ConvertFrom-Json
if (-not $acct) {
  Write-Info "Not logged in — running az login..."
  az login | Out-Null
  $acct = az account show -o json | ConvertFrom-Json
}

if (-not $TenantId)       { $TenantId = $acct.tenantId }
if (-not $SubscriptionId) { $SubscriptionId = $acct.id }

Write-AzCmd "AZ> Using tenant=$TenantId  subscription=$SubscriptionId"

# ── Derived names ────────────────────────────────────────────────────────────

$labSuffix           = if ($LabNum) { "-$LabNum" } else { "" }

$ResourceGroup       = if ($ResourceGroupOverride) { $ResourceGroupOverride } else { "$Prefix-rg" }
$AcrName             = (($Prefix -replace '[^a-zA-Z0-9]', '') + ($LabNum -replace '[^a-zA-Z0-9]', '') + "acr").ToLower()
$ContainerAppsEnv    = "$Prefix$labSuffix-env".ToLower()
$ContainerAppName    = "$Prefix$labSuffix-mcp".ToLower()
$ApiAppName          = "$Prefix$labSuffix-api".ToLower()
$ApimName            = "$Prefix$labSuffix-apim".ToLower()

Write-Info "== Deployment Plan =="
Write-Host "  Prefix:              $Prefix"
if ($LabNum) { Write-Host "  Lab Number:          $LabNum" }
Write-Host "  Tenant:              $TenantId"
Write-Host "  Subscription:        $SubscriptionId"
Write-Host "  Resource Group:      $ResourceGroup"
Write-Host "  ACR:                 $AcrName"
Write-Host "  Container Env:       $ContainerAppsEnv"
Write-Host "  Container App:       $ContainerAppName"
Write-Host "  App Registration:    $ApiAppName"
Write-Host "  APIM:                $ApimName"
Write-Host "  Location:            $Location"
Write-Host ""

if ($Walkthrough) {
  Write-Explain "WORKSHOP OVERVIEW — What Are We Building?" @(
    "This workshop deploys a remote MCP (Model Context Protocol) server that"
    "AI clients (VS Code, Copilot Studio, Claude Desktop) can connect to."
    ""
    "The architecture has four layers:"
    ""
    "  1. ENTRA ID — Identity: Who is calling? (OAuth 2.0 / JWT tokens)"
    "  2. APIM — Gateway: Is the caller allowed in? (validate-jwt policy)"
    "  3. CONTAINER APP — Server: The FastMCP server that runs the tools"
    "  4. OBO — Downstream: Call Microsoft Graph AS the user (On-Behalf-Of)"
    ""
    "Key concepts you'll see:"
    ""
    "  PRM (Protected Resource Metadata)"
    "    The server publishes /.well-known/oauth-protected-resource so clients"
    "    can auto-discover WHERE to get tokens and WHAT scopes to request."
    "    This is how VS Code and Copilot Studio know how to authenticate."
    ""
    "  Streamable HTTP Transport"
    "    MCP over HTTP POST to /mcp — not WebSockets, not SSE-only."
    "    The client sends JSON-RPC messages, the server responds with SSE."
    ""
    "  On-Behalf-Of (OBO) Flow"
    "    The MCP server exchanges the user's token for a Microsoft Graph"
    "    token, then calls Graph AS that user. The user never gives their"
    "    password to the MCP server."
  )
}

# ── Build -WhatIf passthrough ────────────────────────────────────────────────

$isWhatIf = $WhatIfPreference -or $PSBoundParameters.ContainsKey('WhatIf')

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$envFile = Join-Path $scriptDir ".env"
$tempDir = if ($env:TEMP) { $env:TEMP } elseif ($env:TMPDIR) { $env:TMPDIR } else { "/tmp" }
$entraOutputFile = Join-Path $tempDir "entra-outputs-$ContainerAppName.json"

# ── Step 1: Entra app registrations ──────────────────────────────────────────

if (-not $SkipEntra) {
  Write-Explain "STEP 1 — Entra ID App Registration" @(
    "WHY: Every secured API needs an identity. An Entra app registration is"
    "     the 'passport' that defines WHO can call our MCP server and HOW."
    ""
    "WHAT THIS CREATES:"
    ""
    "  App Registration ('$ApiAppName')"
    "    - The single identity for our MCP server"
    "    - Client ID: a GUID that identifies this app to Entra ID"
    "    - Identifier URI: api://<client-id> — the 'audience' in JWT tokens"
    ""
    "  OAuth2 Scope: 'mcp.invoke'"
    "    - A permission that clients must request to call our MCP tools"
    "    - Appears in the token's 'scp' claim"
    ""
    "  App Role: 'MCP.User'"
    "    - Only users assigned this role can call our server"
    "    - APIM's validate-jwt policy checks for this role in the JWT"
    ""
    "  Client Secret (for OBO)"
    "    - The MCP server needs a secret to exchange user tokens for Graph tokens"
    "    - Only used server-side — never sent to clients"
    ""
    "  isFallbackPublicClient = true"
    "    - Allows device-code flow (for testing from terminal scripts)"
    "    - Without this, device-code auth fails with AADSTS7000218"
    ""
    "  Pre-authorized Client: VS Code (aebc6443-996d-45c2-90f0-388ff96faa56)"
    "    - Lets VS Code acquire tokens for our API without extra admin consent"
    "    - VS Code uses the Windows broker (WAM) to get tokens silently"
    ""
    "  Redirect URIs (for WAM broker + Copilot Studio)"
    "    - WAM: ms-appx-web://microsoft.aad.brokerplugin/<client-id>"
    "    - Native: https://login.microsoftonline.com/common/oauth2/nativeclient"
    "    - Copilot Studio: added separately via add-reply-url.ps1"
    ""
    "  Graph User.Read permission + admin consent"
    "    - Allows OBO to call Graph /me on behalf of the user"
    ""
    "PORTAL EQUIVALENT: Entra ID > App registrations > New registration"
    "TROUBLESHOOTING:"
    "  - AADSTS500131: audience mismatch — check that OBO_CLIENT_ID matches OAUTH_CLIENT_ID"
    "  - AADSTS7000218: app not configured as public client — check isFallbackPublicClient"
    "  - AADSTS65001: user hasn't consented — check admin consent was granted"
  )
  Write-Info "== Step 1: Entra App Registrations =="
  & "$scriptDir\setup-entra-apps.ps1" `
    -TenantId $TenantId `
    -ApiAppName $ApiAppName `
    -UseApiUri `
    -OutputFile $entraOutputFile `
    -WhatIf:$isWhatIf

  # ── Auto-update .env with Entra outputs ──────────────────────────────────
  if (Test-Path $entraOutputFile) {
    $entraOut = Get-Content $entraOutputFile -Raw | ConvertFrom-Json
    $cid  = $entraOut.ClientId
    $csec = $entraOut.ClientSecret
    $tid  = $entraOut.TenantId
    $uri  = $entraOut.IdentifierUri
    $scope = $entraOut.ScopeValue

    if (Test-Path $envFile) {
      $lines = Get-Content $envFile
    } else {
      $lines = Get-Content (Join-Path $scriptDir "example.env")
    }

    # Helper: set a key=value line in .env (add if missing)
    function Set-EnvLine([string[]]$lines, [string]$key, [string]$val) {
      $found = $false
      $result = @()
      foreach ($l in $lines) {
        if ($l -match "^${key}=") {
          $result += "$key=$val"
          $found = $true
        } else {
          $result += $l
        }
      }
      if (-not $found) { $result += "$key=$val" }
      return $result
    }

    $lines = Set-EnvLine $lines "OAUTH_AUTHORIZATION_URL" "https://login.microsoftonline.com/$tid/oauth2/v2.0/authorize"
    $lines = Set-EnvLine $lines "OAUTH_TOKEN_URL"         "https://login.microsoftonline.com/$tid/oauth2/v2.0/token"
    $lines = Set-EnvLine $lines "OAUTH_DEVICE_CODE_URL"   "https://login.microsoftonline.com/$tid/oauth2/v2.0/devicecode"
    $lines = Set-EnvLine $lines "OAUTH_CLIENT_ID"         $cid
    $lines = Set-EnvLine $lines "OAUTH_SCOPES"            "$uri/$scope"
    $lines = Set-EnvLine $lines "OBO_CLIENT_ID"           $cid
    $lines = Set-EnvLine $lines "OBO_CLIENT_SECRET"       $csec
    $lines = Set-EnvLine $lines "OBO_TENANT_ID"           $tid

    $lines | Set-Content -Path $envFile -Encoding UTF8
    Write-Ok "Updated .env with Entra outputs (CLIENT_ID=$cid)"
    Remove-Item $entraOutputFile -Force -ErrorAction SilentlyContinue
  }
} else {
  Write-Info "== Step 1: Skipped (Entra) =="
}

# ── Step 2: Infrastructure (RG, ACR, Container Apps Env, Container App) ─────

if (-not $SkipInfrastructure) {
  Write-Explain "STEP 2 — Azure Infrastructure (Container App)" @(
    "WHY: The MCP server needs to run somewhere publicly accessible."
    "     Azure Container Apps gives us a serverless container host with"
    "     HTTPS, auto-scaling, and a public FQDN — no VM management."
    ""
    "WHAT THIS CREATES:"
    ""
    "  Resource Group ('$ResourceGroup')"
    "    - A logical container for all Azure resources in this workshop"
    ""
    "  Azure Container Registry ('$AcrName')"
    "    - Private Docker registry to store our MCP server container image"
    "    - The image is built from mcp_server.py + Dockerfile + requirements.txt"
    "    - 'az acr build' builds the image in the cloud (no local Docker needed)"
    ""
    "  Container Apps Environment ('$ContainerAppsEnv')"
    "    - Shared hosting environment (networking, logging) for container apps"
    ""
    "  Container App ('$ContainerAppName')"
    "    - Runs our FastMCP server on port 8000"
    "    - Env vars from .env are injected as Container App secrets"
    "    - Public FQDN: https://<app-name>.<random>.azurecontainerapps.io"
    "    - Exposes two endpoints:"
    "        /mcp — MCP Streamable HTTP (requires Bearer token)"
    "        /.well-known/oauth-protected-resource — PRM metadata (no auth)"
    ""
    "HOW THE SERVER WORKS:"
    "  - FastMCP library handles the MCP protocol (JSON-RPC over HTTP)"
    "  - PRM middleware intercepts /.well-known/oauth-protected-resource"
    "  - Auth middleware checks for Bearer token on /mcp requests"
    "  - Tools are Python functions decorated with @_mcp.tool()"
    ""
    "TROUBLESHOOTING:"
    "  - Container App returns 401: check MCP_REQUIRE_AUTH and OAUTH_* env vars"
    "  - Container App not responding: check env vars aren't empty (rejects empty secrets)"
    "  - PRM metadata wrong: check OAUTH_TOKEN_URL and OAUTH_CLIENT_ID env vars"
  )
  Write-Info "== Step 2: Azure Infrastructure =="
  & "$scriptDir\deploy-infrastructure.ps1" `
    -SubscriptionId $SubscriptionId `
    -ResourceGroup $ResourceGroup `
    -Location $Location `
    -AcrName $AcrName `
    -ContainerAppsEnvName $ContainerAppsEnv `
    -ContainerAppName $ContainerAppName `
    -WhatIf:$isWhatIf
} else {
  Write-Info "== Step 2: Skipped (Infrastructure) =="
}

# ── Step 3: APIM ────────────────────────────────────────────────────────────

if (-not $SkipApim) {
  $apimScript = Join-Path $scriptDir "deploy-apim.ps1"
  if (Test-Path $apimScript) {
    Write-Explain "STEP 3 — Azure API Management (APIM)" @(
      "WHY: The MCP server itself doesn't validate JWT tokens — that's APIM's job."
      "     APIM sits in front of the Container App as a security gateway."
      "     This is the 'zero trust' pattern: the network layer enforces auth."
      ""
      "WHAT THIS CREATES:"
      ""
      "  APIM Instance ('$ApimName') — Consumption tier"
      "    - Serverless API gateway (scales to zero, pay-per-call)"
      "    - First request after idle may take 30-60s (cold start)"
      ""
      "  API with 4 operations:"
      "    POST   /mcp    — MCP messages (initialize, tools/list, tools/call)"
      "    GET    /mcp    — MCP session polling"
      "    DELETE /mcp    — MCP session cleanup"
      "    GET    /.well-known/oauth-protected-resource — PRM metadata"
      ""
      "  validate-jwt Inbound Policy:"
      "    - Checks every request for a valid Bearer token from your Entra tenant"
      "    - Validates: issuer, audience (api://<client-id>), signature, expiry"
      "    - Requires the 'MCP.User' role in the token's 'roles' claim"
      "    - EXCEPTION: PRM metadata endpoint skips auth (via <choose> block)"
      "      because clients need PRM to DISCOVER how to authenticate"
      ""
      "  Backend URL:"
      "    - APIM proxies to https://<container-app-fqdn>"
      "    - The Container App also has its own auth middleware as defense-in-depth"
      ""
      "THE AUTH FLOW (end to end):"
      "    1. Client reads PRM at /.well-known/oauth-protected-resource"
      "    2. PRM tells client: get a token from Entra for scope mcp.invoke"
      "    3. Client gets a token (WAM broker, device-code, or auth-code flow)"
      "    4. Client sends POST /mcp with 'Authorization: Bearer <token>'"
      "    5. APIM validate-jwt checks the token — rejects if invalid"
      "    6. If valid, APIM forwards to Container App"
      "    7. Container App processes the MCP request"
      "    8. For OBO tools: server exchanges the token for a Graph token"
      ""
      "TROUBLESHOOTING:"
      "  - 401 from APIM: token audience doesn't match api://<client-id>"
      "  - 403 from APIM: user doesn't have MCP.User role assigned"
      "  - Timeout on first call: APIM Consumption cold start (wait 60s)"
      "  - 404: API operations not created — re-run deploy-apim.ps1"
    )
    Write-Info "== Step 3: APIM =="
    & $apimScript `
      -SubscriptionId $SubscriptionId `
      -ResourceGroup $ResourceGroup `
      -Location $Location `
      -ApimName $ApimName `
      -ContainerAppName $ContainerAppName `
      -TenantId $TenantId `
      -ApiAppName $ApiAppName `
      -WhatIf:$isWhatIf
  } else {
    Write-Warn "== Step 3: deploy-apim.ps1 not found, skipping =="
  }
} else {
  Write-Info "== Step 3: Skipped (APIM) =="
}

# ── Step 4: Test endpoints ──────────────────────────────────────────────────

if (-not $SkipTests) {
  # Only run tests if at least one deployment step ran — otherwise the user
  # can run test-endpoints.ps1 directly.
  $testScript = Join-Path $scriptDir "test-endpoints.ps1"
  if (Test-Path $testScript) {
    # Resolve values needed for tests
    $containerAppResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.App/containerApps/$ContainerAppName"
    $fqdn = az resource show --ids $containerAppResourceId --query properties.configuration.ingress.fqdn -o tsv 2>$null
    if ($fqdn) { $fqdn = $fqdn.Trim() }
    $containerAppTestUrl = "https://$fqdn"

    $apiClientIdResult = az ad app list --display-name $ApiAppName --query "[0].appId" -o tsv 2>$null
    if ($apiClientIdResult) { $apiClientIdResult = $apiClientIdResult.Trim() }

    $apimGatewayResult = az apim show --name $ApimName --resource-group $ResourceGroup --query gatewayUrl -o tsv 2>$null
    if ($apimGatewayResult) { $apimGatewayResult = $apimGatewayResult.Trim() }

    if ($fqdn -and $apiClientIdResult -and $apimGatewayResult) {
      Write-Explain "STEP 4 — End-to-End Testing" @(
        "WHY: Verify the full stack works — Entra tokens, APIM validation,"
        "     MCP protocol, tool execution, and OBO token exchange."
        ""
        "WHAT THE TESTS DO:"
        ""
        "  1. Acquire a token via device-code flow"
        "     - You'll see a code to enter at https://login.microsoft.com/device"
        "     - This proves the Entra app is configured correctly"
        "     - The token will have audience=api://<client-id> and role=MCP.User"
        ""
        "  2. Test against BOTH Container App (direct) and APIM (gateway)"
        "     - This validates auth works at both layers"
        ""
        "  Tests per target (8 tests x 2 targets = 16 total):"
        ""
        "    PRM metadata (GET, no auth)"
        "      — Confirms /.well-known/oauth-protected-resource is accessible"
        "      — Returns authorization_servers, scopes_supported, resource"
        ""
        "    MCP POST without token (expect 401)"
        "      — Confirms unauthenticated requests are rejected"
        ""
        "    MCP initialize (POST, Bearer)"
        "      — First MCP protocol message; establishes a session"
        "      — Returns protocolVersion and Mcp-Session-Id header"
        ""
        "    MCP tools/list (POST, Bearer + session)"
        "      — Lists available tools: get_my_profile, analyze_policy, help"
        ""
        "    get_my_profile (tools/call) — OBO test"
        "      — Server exchanges your token for a Graph token (OBO flow)"
        "      — Calls GET https://graph.microsoft.com/v1.0/me"
        "      — Returns your displayName and userPrincipalName"
        ""
        "    help (tools/call)"
        "      — Calls the help tool to verify tool metadata"
        ""
        "    analyze_policy (tools/call)"
        "      — Calls the Federal Policy Analyst external API"
        "      — Proves the MCP server can call external services"
        ""
        "    MCP DELETE without session (expect 400)"
        "      — Confirms bad session cleanup requests are rejected"
        ""
        "TROUBLESHOOTING:"
        "  - AADSTS500131 on OBO: check OBO_CLIENT_ID and OBO_CLIENT_SECRET in .env"
        "  - Timeout on APIM: first call after cold start takes 30-60s"
        "  - 406 Not Acceptable: FastMCP needs Accept: application/json, text/event-stream"
      )
      Write-Info "== Step 4: Test Endpoints =="
      & $testScript `
        -TenantId $TenantId `
        -ApiClientId $apiClientIdResult `
        -ApimGateway $apimGatewayResult `
        -ContainerAppUrl $containerAppTestUrl
    } else {
      Write-Warn "== Step 4: Skipped (could not resolve test parameters) =="
      if (-not $fqdn) { Write-Warn "  Missing: Container App FQDN" }
      if (-not $apiClientIdResult) { Write-Warn "  Missing: API app client ID" }
      if (-not $apimGatewayResult) { Write-Warn "  Missing: APIM gateway URL" }
    }
  }
}

Write-Host ""
if ($Walkthrough) {
  Write-Explain "DEPLOYMENT COMPLETE — What's Next?" @(
    "Your MCP server is deployed and tested. Here's what you can do now:"
    ""
    "CONNECT FROM VS CODE:"
    "  Add to .vscode/mcp.json:"
    "    { ""servers"": { ""workshop-mcp"": {"
    "        ""url"": ""https://<CONTAINER_APP_FQDN>/mcp"","
    "        ""type"": ""http"" } } }"
    "  VS Code discovers PRM, gets a token via WAM, and connects automatically."
    ""
    "CONNECT FROM COPILOT STUDIO:"
    "  Tools > + Add a tool > Model Context Protocol > Manual"
    "  Fill in Client ID, Secret, Auth URL, Token URL, Scopes"
    "  Add the generated redirect URL with: .\add-reply-url.ps1"
    ""
    "ADD USERS:"
    "  .\add-users.ps1 -TenantId <tid> -AppClientId <cid> -Users 'a@contoso.com,b@contoso.com'"
    ""
    "KEY FILES TO EXPLORE:"
    "  mcp_server.py          — The MCP server (tools, PRM, auth, OBO)"
    "  prm_metadata.json      — PRM metadata template"
    "  setup-entra-apps.ps1   — Entra app registration (identity layer)"
    "  deploy-infrastructure.ps1 — Container App deployment"
    "  deploy-apim.ps1        — APIM gateway with validate-jwt"
    "  test-endpoints.ps1     — End-to-end test suite"
    ""
    "ARCHITECTURE RECAP:"
    "  Client --> APIM (validate-jwt) --> Container App (FastMCP)"
    "                                          |"
    "                                          +--> OBO --> Graph /me"
    "                                          +--> HTTP --> Policy Analyst API"
  )
}
Write-Ok "== Deployment complete =="