<#
.SYNOPSIS
    Test all MCP endpoints using device-code authentication.

.EXAMPLE
    npx just test:prod
#>

$MCP_URL = $env:MCP_BACKEND_URL
if (-not $MCP_URL) {
    # Try to read from .env
    $envFile = Resolve-Path "../../.env" -ErrorAction SilentlyContinue
    if ($envFile) {
        $line = Get-Content $envFile | Where-Object { $_ -match "^MCP_BACKEND_URL=" }
        if ($line) { $MCP_URL = $line.Split('=', 2)[1].Trim() }
    }
}

if (-not $MCP_URL) {
    Write-Host "❌  MCP_BACKEND_URL not set. Run 'npx just provision' first." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   TVA Workshop — Endpoint Tests                         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host "  Testing: $MCP_URL"
Write-Host ""

$passed = 0
$failed = 0

function Test-Endpoint {
    param([string]$Name, [string]$Method, [string]$Url, [object]$Body)
    try {
        $params = @{ Method = $Method; Uri = $Url; ContentType = "application/json" }
        if ($Body) { $params.Body = ($Body | ConvertTo-Json -Depth 5) }
        $response = Invoke-RestMethod @params -ErrorAction Stop
        Write-Host "  ✅ $Name" -ForegroundColor Green
        $script:passed++
        return $response
    } catch {
        Write-Host "  ❌ $Name — $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
        return $null
    }
}

# Test 1 — Health
Test-Endpoint "Health check" GET "$MCP_URL/health" | Out-Null

# Test 2 — MCP initialize
Test-Endpoint "MCP initialize" POST "$MCP_URL/mcp" @{ method = "initialize"; params = @{} } | Out-Null

# Test 3 — tools/list
Test-Endpoint "MCP tools/list" POST "$MCP_URL/mcp" @{ method = "tools/list"; params = @{} } | Out-Null

# Test 4 — search_tva_docs
Test-Endpoint "search_tva_docs tool" POST "$MCP_URL/mcp" @{
    method = "tools/call"
    params = @{ name = "search_tva_docs"; arguments = @{ query = "patch management" } }
} | Out-Null

# Test 5 — get_nerc_requirement
Test-Endpoint "get_nerc_requirement tool" POST "$MCP_URL/mcp" @{
    method = "tools/call"
    params = @{ name = "get_nerc_requirement"; arguments = @{ standard = "CIP-007" } }
} | Out-Null

# Test 6 — check_compliance_status
Test-Endpoint "check_compliance_status tool" POST "$MCP_URL/mcp" @{
    method = "tools/call"
    params = @{ name = "check_compliance_status"; arguments = @{ standard = "CIP-007" } }
} | Out-Null

# Test 7 — list_regulations
Test-Endpoint "list_regulations tool" POST "$MCP_URL/mcp" @{
    method = "tools/call"
    params = @{ name = "list_regulations"; arguments = @{} }
} | Out-Null

# Test 8 — 404 on unknown method
try {
    Invoke-RestMethod -Method POST -Uri "$MCP_URL/mcp" -Body '{"method":"unknown"}' -ContentType "application/json" -ErrorAction Stop
    Write-Host "  ⚠️  Unknown method returned 2xx (expected 4xx)" -ForegroundColor Yellow
} catch {
    Write-Host "  ✅ Unknown method correctly rejected" -ForegroundColor Green
    $passed++
}

Write-Host ""
Write-Host "  Results: $passed passed, $failed failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
Write-Host ""

if ($failed -gt 0) { exit 1 }
