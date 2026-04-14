#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup GCC Copilot Studio environment for agent management scripts.

.DESCRIPTION
    Full onboarding for managing Copilot Studio agents in GCC:
    1. Checks prerequisites (Node.js, PAC CLI)
    2. Creates PAC CLI auth for GCC if not present
    3. Selects a GCC environment
    4. Extracts tenant ID and environment URL
    5. Installs npm dependencies
    6. Validates connectivity by listing agents

.PARAMETER SelectEnv
    Re-select a different GCC environment from available PAC auth profiles

.PARAMETER ListEnvs
    List available GCC environments and select one interactively

.PARAMETER WriteEnvFile
    Write a .env file with the discovered config

.EXAMPLE
    .\setup.ps1
    .\setup.ps1 -WriteEnvFile
    .\setup.ps1 -SelectEnv
    .\setup.ps1 -ListEnvs
#>

param(
    [switch]$SelectEnv,
    [switch]$ListEnvs,
    [switch]$WriteEnvFile
)

$ErrorActionPreference = "Stop"
$scriptDir = $PSScriptRoot

# ─── Helper: list and select a GCC environment ──────────────────────────────

function Select-GccEnvironment {
    Write-Host ""
    Write-Host "    Fetching available environments..." -ForegroundColor Cyan
    $envListRaw = pac env list 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    ❌ 'pac env list' failed — you may need to authenticate first." -ForegroundColor Red
        $envListRaw | ForEach-Object { Write-Host "       $_" -ForegroundColor DarkGray }
        return $false
    }

    # Parse table: header row starts with "Environment" or "Active", data rows follow
    $lines = @($envListRaw | Where-Object { $_ -match '\S' })
    if ($lines.Count -lt 2) {
        Write-Host "    ❌ No environments found." -ForegroundColor Red
        return $false
    }

    Write-Host ""
    Write-Host "    Available environments:" -ForegroundColor Cyan
    Write-Host ""
    # Print the raw table so user sees names, URLs, types
    $lines | ForEach-Object { Write-Host "    $_" }

    Write-Host ""
    $envInput = Read-Host "    Enter the environment URL from the list above"
    $envInput = $envInput.Trim().TrimEnd('/')

    if (-not $envInput) {
        Write-Host "    ❌ No URL entered." -ForegroundColor Red
        return $false
    }

    # Select the environment via PAC CLI
    pac env select --environment $envInput 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    ❌ Failed to select environment: $envInput" -ForegroundColor Red
        return $false
    }

    Write-Host "    ✅ Selected environment: $envInput" -ForegroundColor Green
    return $true
}

Write-Host "`n╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  GCC Copilot Studio — Environment Setup              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# ─── 1. Check Node.js ───────────────────────────────────────────────────────

Write-Host "[1/8] Node.js" -ForegroundColor White -NoNewline
try {
    $nodeVersion = (node --version 2>$null)
} catch {
    $nodeVersion = $null
}

if (-not $nodeVersion) {
    Write-Host " ❌ not found" -ForegroundColor Red
    Write-Host "    Install from https://nodejs.org" -ForegroundColor Yellow
    exit 1
}
Write-Host " ✅ $nodeVersion" -ForegroundColor Green

# ─── 2. Check PAC CLI ───────────────────────────────────────────────────────

# Ensure dotnet global tools directory is in PATH
$dotnetToolsDir = Join-Path $HOME ".dotnet/tools"
if ($env:PATH -notlike "*$dotnetToolsDir*") {
    $env:PATH = "$dotnetToolsDir$([System.IO.Path]::PathSeparator)$env:PATH"
}

Write-Host "[2/8] PAC CLI" -ForegroundColor White -NoNewline
try {
    $pacOutput = pac help 2>&1 | Select-Object -First 3
    $pacVersion = ($pacOutput | Where-Object { $_ -match "Version:" }) -replace '.*Version:\s*', ''
} catch {
    $pacVersion = $null
}

if (-not $pacVersion) {
    Write-Host " ⚠️  not found — installing..." -ForegroundColor Yellow
    try {
        # Pin to 1.52.1 — latest 2.x versions have a broken NuGet package (missing DotnetToolSettings.xml)
        dotnet tool install --global Microsoft.PowerApps.CLI.Tool --version 1.52.1 2>&1 | Out-Null
        # Refresh PATH so the current session can find the newly installed tool
        $dotnetToolsDir = Join-Path $HOME ".dotnet/tools"
        if ($env:PATH -notlike "*$dotnetToolsDir*") {
            $env:PATH = "$dotnetToolsDir$([System.IO.Path]::PathSeparator)$env:PATH"
        }
        $pacOutput = pac help 2>&1 | Select-Object -First 3
        $pacVersion = ($pacOutput | Where-Object { $_ -match "Version:" }) -replace '.*Version:\s*', ''
    } catch {}

    if (-not $pacVersion) {
        Write-Host "    ❌ installation failed" -ForegroundColor Red
        Write-Host "    Try manually: dotnet tool install --global Microsoft.PowerApps.CLI.Tool" -ForegroundColor Yellow
        Write-Host "    Docs: https://aka.ms/PowerPlatformCLI" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "    ✅ installed v$pacVersion" -ForegroundColor Green
} else {
    Write-Host " ✅ v$pacVersion" -ForegroundColor Green
}

# ─── 3. PAC CLI authentication ──────────────────────────────────────────────

Write-Host "[3/8] GCC authentication" -ForegroundColor White

$authList = pac auth list 2>&1
$gccAuth = $authList | Where-Object { $_ -match '^\[' -and $_ -match 'UsGov' }
$activeAuth = $authList | Where-Object { $_ -match '^\[' -and $_ -match '\*' }

if ($SelectEnv) {
    Write-Host ""
    Write-Host "    Available auth profiles:" -ForegroundColor Cyan
    $authList | Where-Object { $_ -match '^\[|^Index' } | ForEach-Object { Write-Host "    $_" }
    $idx = Read-Host "`n    Select profile index"
    pac auth select --index $idx 2>&1 | Out-Null
    Write-Host "    Switched to profile [$idx]" -ForegroundColor Green
}
elseif (-not $gccAuth) {
    Write-Host ""
    Write-Host "    No GCC authentication found. Let's set one up." -ForegroundColor Yellow
    Write-Host ""

    if ($ListEnvs) {
        # Authenticate to GCC cloud first (no specific environment), then list and pick
        Write-Host "    First, authenticate to GCC cloud..." -ForegroundColor Cyan
        Write-Host "    A device code will be shown — sign in via browser." -ForegroundColor DarkGray
        pac auth create --name "GCC" --cloud UsGov --deviceCode
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    ❌ pac auth create failed" -ForegroundColor Red
            exit 1
        }
        Write-Host "    ✅ GCC auth profile created" -ForegroundColor Green

        $selected = Select-GccEnvironment
        if (-not $selected) { exit 1 }
    }
    else {
        Write-Host "    Tip: re-run with -ListEnvs to browse available environments" -ForegroundColor DarkGray
        Write-Host ""
        $gccEnvUrl = Read-Host "    GCC Dataverse URL (e.g. https://yourorg.crm9.dynamics.com)"
        $gccEnvUrl = $gccEnvUrl.TrimEnd('/')

        if ($gccEnvUrl -notmatch '\.crm9\.dynamics\.com') {
            Write-Host "    ⚠️  URL doesn't look like GCC (expected *.crm9.dynamics.com)" -ForegroundColor Yellow
            $continue = Read-Host "    Continue anyway? (y/N)"
            if ($continue -ne 'y') { exit 1 }
        }

        Write-Host "    Creating PAC auth for GCC..." -ForegroundColor Cyan
        Write-Host "    A device code will be shown — sign in via browser." -ForegroundColor DarkGray
        pac auth create --name "GCC" --cloud UsGov --environment $gccEnvUrl --deviceCode
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    ❌ pac auth create failed" -ForegroundColor Red
            exit 1
        }
        # Verify the profile actually exists
        $verifyAuth = pac auth list 2>&1
        $verifyGcc = $verifyAuth | Where-Object { $_ -match '^\[' -and $_ -match 'UsGov' }
        if (-not $verifyGcc) {
            Write-Host "    ❌ Auth profile was not created (sign-in may not have completed)" -ForegroundColor Red
            exit 1
        }
        Write-Host "    ✅ GCC auth profile created" -ForegroundColor Green
    }
}
elseif ($ListEnvs) {
    $selected = Select-GccEnvironment
    if (-not $selected) { exit 1 }
}
elseif (-not ($activeAuth -and $activeAuth -match 'UsGov')) {
    $gccIndex = ($gccAuth -replace '^\[(\d+)\].*', '$1') | Select-Object -First 1
    pac auth select --index $gccIndex 2>&1 | Out-Null
    Write-Host " ✅ selected GCC profile [$gccIndex]" -ForegroundColor Green
}
else {
    Write-Host " ✅ GCC profile active" -ForegroundColor Green
}

# ─── 4. Select GCC environment ──────────────────────────────────────────────

Write-Host "[4/8] GCC environment" -ForegroundColor White

$authWho = pac auth who 2>&1
$envWho = pac env who 2>&1

$tenantId = ($authWho | Where-Object { $_ -match 'Tenant\s*Id\s*:' }) -replace '.*Tenant\s*Id\s*:\s*', '' | ForEach-Object { $_.Trim() }
$cloud = ($authWho | Where-Object { $_ -match 'Cloud\s*:' }) -replace '.*Cloud\s*:\s*', '' | ForEach-Object { $_.Trim() }
# PAC CLI field name varies by version: "Org URL", "Organization URL", or "Environment URL"
$envUrl = ($envWho | Where-Object { $_ -match '(Org(anization)?\s+URL|Environment\s+URL)\s*:' }) -replace '.*(Org(anization)?\s+URL|Environment\s+URL)\s*:\s*', '' | ForEach-Object { $_.Trim().TrimEnd('/') }
$envId = ($envWho | Where-Object { $_ -match 'Environment\s*ID\s*:' }) -replace '.*Environment\s*ID\s*:\s*', '' | ForEach-Object { $_.Trim() }
$envFriendlyName = ($envWho | Where-Object { $_ -match 'Friendly\s+Name\s*:' }) -replace '.*Friendly\s+Name\s*:\s*', '' | ForEach-Object { $_.Trim() }
$userEmail = ($authWho | Where-Object { $_ -match 'User\s*:' }) -replace '.*User\s*:\s*', '' | ForEach-Object { $_.Trim() }

if (-not $tenantId -or -not $envUrl) {
    Write-Host " ❌ Could not read config from PAC CLI" -ForegroundColor Red
    Write-Host ""
    Write-Host "    'pac auth who' output:" -ForegroundColor DarkGray
    $authWho | ForEach-Object { Write-Host "      $_" -ForegroundColor DarkGray }
    Write-Host "    'pac env who' output:" -ForegroundColor DarkGray
    $envWho | ForEach-Object { Write-Host "      $_" -ForegroundColor DarkGray }
    Write-Host ""
    if (-not $tenantId) { Write-Host "    → Tenant ID not found in 'pac auth who' output" -ForegroundColor Yellow }
    if (-not $envUrl) { Write-Host "    → Environment URL not found in 'pac env who' output" -ForegroundColor Yellow }
    Write-Host "    Try: pac auth create --cloud UsGov --environment <url>" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "    Environment:  $envFriendlyName" -ForegroundColor White
Write-Host "    URL:          $envUrl" -ForegroundColor White
Write-Host "    Tenant:       $tenantId" -ForegroundColor White
Write-Host "    User:         $userEmail" -ForegroundColor White

# ─── 5. Set environment variables ────────────────────────────────────────────

Write-Host "`n[5/8] Environment variables" -ForegroundColor White
$env:CPS_TENANT_ID = $tenantId
$env:CPS_ENVIRONMENT_URL = $envUrl
Write-Host "    CPS_TENANT_ID=$tenantId" -ForegroundColor Green
Write-Host "    CPS_ENVIRONMENT_URL=$envUrl" -ForegroundColor Green

# ─── 6. Install npm dependencies ────────────────────────────────────────────

Write-Host "[6/8] npm install" -ForegroundColor White -NoNewline
Push-Location $scriptDir
try {
    npm install --quiet 2>&1 | Out-Null
    Write-Host " ✅" -ForegroundColor Green
} catch {
    Write-Host " ❌ npm install failed" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

# ─── 7. Seed MSAL token cache (device code) ─────────────────────────────────

Write-Host "[7/8] Seeding MSAL token cache" -ForegroundColor White
Write-Host "    This caches your GCC token so scripts won't prompt again." -ForegroundColor DarkGray

$seedScript = @"
const { getAccessToken } = require('./auth');
(async () => {
  await getAccessToken({
    tenantId: process.env.CPS_TENANT_ID,
    resource: process.env.CPS_ENVIRONMENT_URL,
    authMode: 'device',
  });
  console.log('Token cached successfully.');
})();
"@

Push-Location $scriptDir
$tmpSeed = Join-Path $scriptDir ".seed-cache.js"
Set-Content -Path $tmpSeed -Value $seedScript -Encoding UTF8
try {
    # Run without capturing so device-code prompts are visible to the user
    node $tmpSeed
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ Token cached — scripts will use silent auth" -ForegroundColor Green
    } else {
        Write-Host "    ⚠️  Token cache seeding may have failed" -ForegroundColor Yellow
    }
} finally {
    Remove-Item -Path $tmpSeed -ErrorAction SilentlyContinue
}
Pop-Location

# ─── 8. Validate ────────────────────────────────────────────────────────────

Write-Host "[8/8] Validating connection" -ForegroundColor White -NoNewline
try {
    $listScript = Join-Path $scriptDir "list-agents.js"
    $testOutput = node $listScript --auth device 2>&1
    $agentLine = $testOutput | Where-Object { $_ -match 'Found \d+ agent' }
    if ($agentLine) {
        $count = ($agentLine -replace '.*Found (\d+).*', '$1')
        Write-Host " ✅ $count agents found" -ForegroundColor Green
    } else {
        Write-Host " ✅ connected" -ForegroundColor Green
    }
} catch {
    Write-Host " ⚠️  validation skipped (may need to refresh auth)" -ForegroundColor Yellow
}

# ─── Write .env file ────────────────────────────────────────────────────────

if ($WriteEnvFile) {
    $envFile = Join-Path $scriptDir ".env"
    $envFile = Join-Path $scriptDir ".env"
    @"
# GCC Copilot Studio — $envFriendlyName ($userEmail)
CPS_TENANT_ID=$tenantId
CPS_ENVIRONMENT_URL=$envUrl
CPS_ENVIRONMENT_ID=$envId
"@ | Set-Content -Path $envFile -Encoding UTF8
    Write-Host "`n    Wrote $envFile" -ForegroundColor Green
}

# ─── Summary ─────────────────────────────────────────────────────────────────

Write-Host "`n╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ Setup complete!                                   ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Quick start:" -ForegroundColor Cyan
Write-Host "    node list-agents.js" -ForegroundColor White
Write-Host "    node clone-agent.js --agent-id <guid> --output-dir ..\MyAgent" -ForegroundColor White
Write-Host "    node push-agent.js --workspace ..\MyAgent" -ForegroundColor White
Write-Host "    node publish-agent.js --agent-id <guid>" -ForegroundColor White
Write-Host ""
