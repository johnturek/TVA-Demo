# test-endpoints.ps1
# End-to-end OAuth + MCP test against both APIM and Container App.
# Acquires a token via device-code flow, then checks:
#   1. PRM metadata (no auth)
#   2. MCP POST /mcp without token (expect 401)
#   3. MCP POST /mcp with valid Bearer token (MCP initialize + tools/list)
#   4. MCP tools/call get_my_profile (OBO → Graph /me)
#   5. MCP DELETE without session (expect 4xx)
# Reports pass/fail for each test.

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [string] $TenantId,

  [Parameter(Mandatory=$true)]
  [string] $ApiClientId,

  [Parameter(Mandatory=$true)]
  [string] $ApimGateway,

  [Parameter(Mandatory=$true)]
  [string] $ContainerAppUrl,

  [string] $Scope = ""
)

$ErrorActionPreference = 'Stop'

# Derive scope from ApiClientId if not specified
if (-not $Scope) { $Scope = "api://$ApiClientId/mcp.invoke" }

function Write-Pass($label, $detail) { Write-Host "  PASS  " -ForegroundColor Green -NoNewline; Write-Host " $label" -NoNewline; if ($detail) { Write-Host " — $detail" -ForegroundColor DarkGray } else { Write-Host "" } }
function Write-Fail($label, $detail) { Write-Host "  FAIL  " -ForegroundColor Red   -NoNewline; Write-Host " $label" -NoNewline; if ($detail) { Write-Host " — $detail" -ForegroundColor DarkGray } else { Write-Host "" } }
function Write-Skip($label, $detail) { Write-Host "  SKIP  " -ForegroundColor Yellow -NoNewline; Write-Host " $label" -NoNewline; if ($detail) { Write-Host " — $detail" -ForegroundColor DarkGray } else { Write-Host "" } }

$results = @()  # collect {Target, Test, Status, Detail}

function Add-Result($target, $test, $status, $detail) {
  $script:results += [PSCustomObject]@{ Target=$target; Test=$test; Status=$status; Detail=$detail }
  Write-Host ""  # newline after progress indicator
  switch ($status) {
    "PASS" { Write-Pass "$target | $test" $detail }
    "FAIL" { Write-Fail "$target | $test" $detail }
    "SKIP" { Write-Skip "$target | $test" $detail }
  }
}

# ── SSE response parser ─────────────────────────────────────────────────────
# FastMCP returns SSE (event: message\ndata: {...}) — extract the JSON payload.
function Parse-SseContent($content) {
  if ($content -match "^event:") {
    $dataLine = ($content -split "`n" | Where-Object { $_ -match "^data:\s*" }) | Select-Object -First 1
    if ($dataLine) { return ($dataLine -replace "^data:\s*", "") }
  }
  return $content
}

# ── MCP initialize payload ──────────────────────────────────────────────────

$mcpInitBody = @{
  jsonrpc = "2.0"
  id      = 1
  method  = "initialize"
  params  = @{
    protocolVersion = "2025-03-26"
    capabilities    = @{}
    clientInfo      = @{ name = "test-endpoints.ps1"; version = "1.0" }
  }
} | ConvertTo-Json -Depth 5 -Compress

# ── Step 1: Acquire token via device-code flow ──────────────────────────────

Write-Host ""
Write-Host "== Acquiring token via device-code flow ==" -ForegroundColor Cyan
Write-Host "   Client ID : $ApiClientId"
Write-Host "   Scope     : $Scope"
Write-Host ""

$deviceCodeUrl = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/devicecode"
$tokenUrl      = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"

$dcResponse = Invoke-RestMethod -Method POST -Uri $deviceCodeUrl -Body @{
  client_id = $ApiClientId
  scope     = "$Scope openid profile"
}

Write-Host $dcResponse.message -ForegroundColor Yellow
Write-Host ""

# Poll for token
$interval   = [int]$dcResponse.interval
if ($interval -lt 1) { $interval = 5 }
$expiresAt  = (Get-Date).AddSeconds([int]$dcResponse.expires_in)
$accessToken = $null

$prevEAP = $ErrorActionPreference
$ErrorActionPreference = 'Continue'

while ((Get-Date) -lt $expiresAt) {
  Start-Sleep -Seconds $interval
  try {
    $tokenResp = Invoke-RestMethod -Method POST -Uri $tokenUrl -Body @{
      client_id   = $ApiClientId
      grant_type  = "urn:ietf:params:oauth:grant-type:device_code"
      device_code = $dcResponse.device_code
    }
    $accessToken = $tokenResp.access_token
    break
  } catch {
    $errBody = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($errBody.error -eq "authorization_pending") {
      Write-Host "." -NoNewline
      continue
    }
    if ($errBody.error -eq "slow_down") {
      $interval += 5
      continue
    }
    Write-Host ""
    Write-Host "Token error: $($errBody.error) — $($errBody.error_description)" -ForegroundColor Red
    break
  }
}

$ErrorActionPreference = $prevEAP

if (-not $accessToken) {
  Write-Host ""
  Write-Host "Could not acquire token. Aborting." -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "Token acquired." -ForegroundColor Green

# Decode token claims (without validation) for display
$tokenParts = $accessToken.Split(".")
$claimsJson = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($tokenParts[1].PadRight(($tokenParts[1].Length + 3) -band -bnot 3, '=')))
$claims = $claimsJson | ConvertFrom-Json
Write-Host "   sub  : $($claims.sub)"
Write-Host "   upn  : $($claims.upn)"
Write-Host "   aud  : $($claims.aud)"
Write-Host "   iss  : $($claims.iss)"
Write-Host "   roles: $($claims.roles -join ', ')"
Write-Host ""

$authHeader = @{ Authorization = "Bearer $accessToken"; "Content-Type" = "application/json"; Accept = "application/json, text/event-stream" }
$noAuthHeader = @{ "Content-Type" = "application/json"; Accept = "application/json, text/event-stream" }

# ── Step 2: Run tests ───────────────────────────────────────────────────────

$targets = @(
  @{ Name = "ContainerApp"; Base = $ContainerAppUrl },
  @{ Name = "APIM";         Base = $ApimGateway }
)

foreach ($target in $targets) {
  $name = $target.Name
  $base = $target.Base

  Write-Host ""
  Write-Host "== Testing $name ($base) ==" -ForegroundColor Cyan

  # ── Test: PRM metadata (no auth) ──────────────────────────────────────
  $prmUrl = "$base/.well-known/oauth-protected-resource"
  Write-Host "  Testing PRM metadata..." -NoNewline
  try {
    $prmResp = Invoke-WebRequest -Uri $prmUrl -Method GET -UseBasicParsing -TimeoutSec 60 -ErrorAction Stop
    if ($prmResp.StatusCode -eq 200) {
      $prmBody = $prmResp.Content | ConvertFrom-Json
      if ($prmBody.resource) {
        Add-Result $name "PRM metadata (GET, no auth)" "PASS" "resource=$($prmBody.resource)"
      } else {
        Add-Result $name "PRM metadata (GET, no auth)" "FAIL" "200 but no 'resource' field"
      }
    } else {
      Add-Result $name "PRM metadata (GET, no auth)" "FAIL" "HTTP $($prmResp.StatusCode)"
    }
  } catch {
    $status = $_.Exception.Response.StatusCode.value__
    Add-Result $name "PRM metadata (GET, no auth)" "FAIL" "HTTP $status — $($_.Exception.Message)"
  }

  # ── Test: MCP POST without token (expect 401) ─────────────────────────
  $mcpUrl = "$base/mcp"
  Write-Host "  Testing MCP POST without token..." -NoNewline
  try {
    $resp = Invoke-WebRequest -Uri $mcpUrl -Method POST -Body $mcpInitBody -Headers $noAuthHeader -UseBasicParsing -TimeoutSec 60 -ErrorAction Stop
    # If we get here, it means no auth was enforced — that's a fail
    Add-Result $name "MCP POST without token (expect 401)" "FAIL" "Got HTTP $($resp.StatusCode) — expected 401"
  } catch {
    $status = 0
    if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
    if ($status -eq 401) {
      Add-Result $name "MCP POST without token (expect 401)" "PASS" "401 Unauthorized"
    } else {
      Add-Result $name "MCP POST without token (expect 401)" "FAIL" "HTTP $status — $($_.Exception.Message)"
    }
  }

  # ── Test: MCP POST with Bearer token (initialize) ─────────────────────
  Write-Host "  Testing MCP initialize with Bearer..." -NoNewline
  $resp = $null
  try {
    $resp = Invoke-WebRequest -Uri $mcpUrl -Method POST -Body $mcpInitBody -Headers $authHeader -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
    if ($resp.StatusCode -eq 200) {
      $body = (Parse-SseContent $resp.Content) | ConvertFrom-Json -ErrorAction SilentlyContinue
      if ($body.result.protocolVersion) {
        Add-Result $name "MCP initialize (POST, Bearer)" "PASS" "protocolVersion=$($body.result.protocolVersion), serverName=$($body.result.serverInfo.name)"
      } else {
        Add-Result $name "MCP initialize (POST, Bearer)" "PASS" "HTTP 200 (response: $($resp.Content.Substring(0, [Math]::Min(120, $resp.Content.Length))))"
      }
    } else {
      Add-Result $name "MCP initialize (POST, Bearer)" "FAIL" "HTTP $($resp.StatusCode)"
    }
  } catch {
    $status = 0
    $detail = $_.Exception.Message
    if ($_.Exception.Response) {
      $status = [int]$_.Exception.Response.StatusCode
      try {
        $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
        $detail = $reader.ReadToEnd()
        $reader.Close()
      } catch {}
    }
    Add-Result $name "MCP initialize (POST, Bearer)" "FAIL" "HTTP $status — $detail"
  }

  # ── Test: MCP tools/list (POST, Bearer) ────────────────────────────────
  # Extract Mcp-Session-Id from initialize response to send follow-up
  $sessionId = $null
  if ($resp -and $resp.Headers) {
    # Headers may be Dictionary<string, string[]> — handle both cases
    $raw = $resp.Headers["Mcp-Session-Id"]
    if ($raw -is [array]) { $sessionId = $raw[0] } elseif ($raw) { $sessionId = "$raw" }
  }

  if ($sessionId) {
    $toolsListBody = @{
      jsonrpc = "2.0"
      id      = 2
      method  = "tools/list"
      params  = @{}
    } | ConvertTo-Json -Depth 5 -Compress

    $sessionHeader = @{ Authorization = "Bearer $accessToken"; "Content-Type" = "application/json"; Accept = "application/json, text/event-stream"; "Mcp-Session-Id" = $sessionId }
    Write-Host "  Testing MCP tools/list with session..." -NoNewline
    try {
      $tlResp = Invoke-WebRequest -Uri $mcpUrl -Method POST -Body $toolsListBody -Headers $sessionHeader -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
      if ($tlResp.StatusCode -eq 200) {
        $tlBody = (Parse-SseContent $tlResp.Content) | ConvertFrom-Json -ErrorAction SilentlyContinue
        $toolNames = ($tlBody.result.tools | ForEach-Object { $_.name }) -join ", "
        if ($toolNames) {
          Add-Result $name "MCP tools/list (POST, Bearer)" "PASS" "tools: $toolNames"
        } else {
          Add-Result $name "MCP tools/list (POST, Bearer)" "PASS" "HTTP 200 (no tools listed)"
        }
      } else {
        Add-Result $name "MCP tools/list (POST, Bearer)" "FAIL" "HTTP $($tlResp.StatusCode)"
      }
    } catch {
      $status = 0; $detail = $_.Exception.Message
      if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
      Add-Result $name "MCP tools/list (POST, Bearer)" "FAIL" "HTTP $status — $detail"
    }
  } else {
    Write-Host "  Testing MCP tools/list with session..." -NoNewline
    Add-Result $name "MCP tools/list (POST, Bearer)" "SKIP" "No Mcp-Session-Id from initialize"
  }

  # ── Test: MCP tools/call get_my_profile (OBO → Graph /me) ──────────────
  if ($sessionId) {
    $oboCallBody = @{
      jsonrpc = "2.0"
      id      = 3
      method  = "tools/call"
      params  = @{ name = "get_my_profile"; arguments = @{} }
    } | ConvertTo-Json -Depth 5 -Compress

    Write-Host "  Testing get_my_profile (OBO)..." -NoNewline
    try {
      $oboResp = Invoke-WebRequest -Uri $mcpUrl -Method POST -Body $oboCallBody -Headers $sessionHeader -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
      if ($oboResp.StatusCode -eq 200) {
        $oboBody = (Parse-SseContent $oboResp.Content) | ConvertFrom-Json -ErrorAction SilentlyContinue
        # tools/call result is in .result.content[0].text (JSON-encoded)
        $toolResult = $null
        if ($oboBody.result.content) {
          $toolResult = $oboBody.result.content[0].text | ConvertFrom-Json -ErrorAction SilentlyContinue
        }
        if ($toolResult.success -eq $true) {
          $displayName = $toolResult.displayName
          $upn = $toolResult.userPrincipalName
          Add-Result $name "get_my_profile OBO (tools/call)" "PASS" "$displayName ($upn)"
        } elseif ($toolResult.error) {
          Add-Result $name "get_my_profile OBO (tools/call)" "FAIL" "$($toolResult.error): $($toolResult.message)"
        } else {
          Add-Result $name "get_my_profile OBO (tools/call)" "PASS" "HTTP 200 (response: $($oboResp.Content.Substring(0, [Math]::Min(150, $oboResp.Content.Length))))"
        }
      } else {
        Add-Result $name "get_my_profile OBO (tools/call)" "FAIL" "HTTP $($oboResp.StatusCode)"
      }
    } catch {
      $status = 0; $detail = $_.Exception.Message
      if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
      Add-Result $name "get_my_profile OBO (tools/call)" "FAIL" "HTTP $status — $detail"
    }
  } else {
    Write-Host "  Testing get_my_profile (OBO)..." -NoNewline
    Add-Result $name "get_my_profile OBO (tools/call)" "SKIP" "No session from initialize"
  }

  # ── Test: MCP tools/call help ──────────────────────────────────────────
  if ($sessionId) {
    $helpCallBody = @{
      jsonrpc = "2.0"
      id      = 4
      method  = "tools/call"
      params  = @{ name = "help"; arguments = @{} }
    } | ConvertTo-Json -Depth 5 -Compress

    Write-Host "  Testing help (tools/call)..." -NoNewline
    try {
      $helpResp = Invoke-WebRequest -Uri $mcpUrl -Method POST -Body $helpCallBody -Headers $sessionHeader -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
      if ($helpResp.StatusCode -eq 200) {
        $helpBody = (Parse-SseContent $helpResp.Content) | ConvertFrom-Json -ErrorAction SilentlyContinue
        $helpResult = $null
        if ($helpBody.result.content) {
          $helpResult = $helpBody.result.content[0].text | ConvertFrom-Json -ErrorAction SilentlyContinue
        }
        if ($helpResult.total_tools -gt 0) {
          $cats = ($helpResult.categories.PSObject.Properties.Name) -join ", "
          Add-Result $name "help (tools/call)" "PASS" "$($helpResult.total_tools) tools, categories: $cats"
        } elseif ($helpResult) {
          Add-Result $name "help (tools/call)" "PASS" "HTTP 200"
        } else {
          Add-Result $name "help (tools/call)" "FAIL" "Could not parse help response"
        }
      } else {
        Add-Result $name "help (tools/call)" "FAIL" "HTTP $($helpResp.StatusCode)"
      }
    } catch {
      $status = 0; $detail = $_.Exception.Message
      if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
      Add-Result $name "help (tools/call)" "FAIL" "HTTP $status — $detail"
    }
  } else {
    Write-Host "  Testing help (tools/call)..." -NoNewline
    Add-Result $name "help (tools/call)" "SKIP" "No session from initialize"
  }

  # ── Test: MCP tools/call analyze_policy ────────────────────────────────
  if ($sessionId) {
    $policyCallBody = @{
      jsonrpc = "2.0"
      id      = 5
      method  = "tools/call"
      params  = @{ name = "analyze_policy"; arguments = @{ query = "What is FedRAMP?" } }
    } | ConvertTo-Json -Depth 5 -Compress

    Write-Host "  Testing analyze_policy (tools/call)..." -NoNewline
    try {
      $policyResp = Invoke-WebRequest -Uri $mcpUrl -Method POST -Body $policyCallBody -Headers $sessionHeader -UseBasicParsing -TimeoutSec 120 -ErrorAction Stop
      if ($policyResp.StatusCode -eq 200) {
        $policyBody = (Parse-SseContent $policyResp.Content) | ConvertFrom-Json -ErrorAction SilentlyContinue
        $policyResult = $null
        if ($policyBody.result.content) {
          $policyResult = $policyBody.result.content[0].text | ConvertFrom-Json -ErrorAction SilentlyContinue
        }
        if ($policyResult.success -eq $true) {
          $snippet = $policyResult.result
          if ($snippet.Length -gt 80) { $snippet = $snippet.Substring(0, 80) + "..." }
          Add-Result $name "analyze_policy (tools/call)" "PASS" $snippet
        } elseif ($policyResult.error) {
          Add-Result $name "analyze_policy (tools/call)" "FAIL" "$($policyResult.error): $($policyResult.message)"
        } else {
          Add-Result $name "analyze_policy (tools/call)" "PASS" "HTTP 200 (response received)"
        }
      } else {
        Add-Result $name "analyze_policy (tools/call)" "FAIL" "HTTP $($policyResp.StatusCode)"
      }
    } catch {
      $status = 0; $detail = $_.Exception.Message
      if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
      Add-Result $name "analyze_policy (tools/call)" "FAIL" "HTTP $status — $detail"
    }
  } else {
    Write-Host "  Testing analyze_policy (tools/call)..." -NoNewline
    Add-Result $name "analyze_policy (tools/call)" "SKIP" "No session from initialize"
  }

  # ── Test: MCP DELETE without session (expect 400/405) ──────────────────
  Write-Host "  Testing MCP DELETE without session..." -NoNewline
  try {
    $resp = Invoke-WebRequest -Uri $mcpUrl -Method DELETE -Headers $authHeader -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
    Add-Result $name "MCP DELETE no session (expect 4xx)" "FAIL" "Got HTTP $($resp.StatusCode) — expected 4xx"
  } catch {
    $status = 0
    if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
    if ($status -ge 400 -and $status -lt 500) {
      Add-Result $name "MCP DELETE no session (expect 4xx)" "PASS" "HTTP $status"
    } else {
      Add-Result $name "MCP DELETE no session (expect 4xx)" "FAIL" "HTTP $status — $($_.Exception.Message)"
    }
  }
}

# ── Summary ──────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "== Test Summary ==" -ForegroundColor Cyan
Write-Host ""
Write-Host ("{0,-14} {1,-42} {2,-6} {3}" -f "TARGET", "TEST", "RESULT", "DETAIL") -ForegroundColor White
Write-Host ("{0,-14} {1,-42} {2,-6} {3}" -f "------", "----", "------", "------")

foreach ($r in $results) {
  $color = switch ($r.Status) { "PASS" { "Green" } "FAIL" { "Red" } "SKIP" { "Yellow" } }
  Write-Host ("{0,-14} {1,-42} " -f $r.Target, $r.Test) -NoNewline
  Write-Host ("{0,-6}" -f $r.Status) -ForegroundColor $color -NoNewline
  Write-Host " $($r.Detail)"
}

$passCount = ($results | Where-Object Status -eq "PASS").Count
$failCount = ($results | Where-Object Status -eq "FAIL").Count
$total     = $results.Count

Write-Host ""
if ($failCount -eq 0) {
  Write-Host "All $passCount/$total tests passed." -ForegroundColor Green
} else {
  Write-Host "$passCount/$total passed, $failCount/$total FAILED." -ForegroundColor Red
}
Write-Host ""
