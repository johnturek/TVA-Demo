[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]
param(
  [Parameter(Mandatory=$true)]
  [string] $TenantId,

  # Display name for the single Entra app (audience + OBO client)
  [string] $ApiAppName = "mcp-workshop-server",

  # Scope to expose on the API app
  [string] $ScopeValue = "mcp.invoke",
  [string] $ScopeAdminConsentDisplayName = "Invoke MCP tools",
  [string] $ScopeAdminConsentDescription = "Allows the app to invoke MCP tools.",
  [string] $ScopeUserConsentDisplayName = "Invoke MCP tools",
  [string] $ScopeUserConsentDescription = "Allows you to invoke MCP tools.",

  # Optional: set identifier URI = api://<api-app-client-id>
  [switch] $UseApiUri,

  # OBO downstream (Graph) delegated permission to add to the server app
  [string] $GraphDelegatedPermission = "User.Read",

  # Secret lifetime
  [int] $SecretYears = 1,

  # Optional: write key outputs to a JSON file (for deploy.ps1 automation)
  [string] $OutputFile = ""
)

$ErrorActionPreference = "Stop"

function Write-Info($msg)  { Write-Host $msg -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host $msg -ForegroundColor Magenta }
function Write-Err($msg)   { Write-Host $msg -ForegroundColor Red }
function Write-AzCmd($msg) { Write-Host $msg -ForegroundColor Yellow }

function Require-Cmd($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Required command not found: $name"
  }
}

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

function New-Guid() { [guid]::NewGuid().ToString() }

Require-Cmd az

Write-Info "== Validating Azure CLI login & tenant =="
$acct = Invoke-AzCli -ReadOnly -Command "az account show -o json" -AsJson
if (-not $acct) { throw "Not logged in. Run: az login" }

# az rest auto-authenticates for graph.microsoft.com URLs using the logged-in account.
# No need to manually pass Authorization headers.
# On Windows, az rest --body requires backslash-escaped double quotes inside the JSON.

function _Escape-JsonForAzRest($jsonString) {
  # On Windows, Invoke-Expression + native commands need escaped quotes.
  # On Linux/macOS, single-quoted strings pass through correctly without escaping.
  if ($IsWindows) {
    return $jsonString.Replace('"', '\"')
  }
  return $jsonString
}

function Graph-Get($url) {
  $escapedUrl = $url.Replace("'", "''")
  Invoke-AzCli -ReadOnly -Command "az rest --method GET --url '$escapedUrl'"
}

function Graph-Post($url, $bodyObj) {
  $body = ($bodyObj | ConvertTo-Json -Depth 30 -Compress)
  $escaped = _Escape-JsonForAzRest $body
  Invoke-AzCli -Command "az rest --method POST --url '$url' --body '$escaped'"
}

function Graph-Patch($url, $bodyObj) {
  $body = ($bodyObj | ConvertTo-Json -Depth 30 -Compress)
  $escaped = _Escape-JsonForAzRest $body
  Invoke-AzCli -Command "az rest --method PATCH --url '$url' --body '$escaped'"
}

function Get-OAuth2PermissionGrant([string]$clientSpId, [string]$resourceSpId) {
  $url = "https://graph.microsoft.com/v1.0/oauth2PermissionGrants?`$filter=clientId eq '$clientSpId' and resourceId eq '$resourceSpId'"
  $raw = Graph-Get $url
  ($raw | ConvertFrom-Json).value | Select-Object -First 1
}

function Upsert-OAuth2PermissionGrant(
  [string]$clientSpId,
  [string]$resourceSpId,
  [string]$scopeString
) {
  $existing = Get-OAuth2PermissionGrant -clientSpId $clientSpId -resourceSpId $resourceSpId

  if (-not $existing) {
    Write-Info "Creating oauth2PermissionGrant (client=$clientSpId, resource=$resourceSpId, scopes='$scopeString')"
    Graph-Post "https://graph.microsoft.com/v1.0/oauth2PermissionGrants" @{
      clientId    = $clientSpId
      consentType = "AllPrincipals"
      resourceId  = $resourceSpId
      scope       = $scopeString
    } | Out-Null
    Write-Ok "Created oauth2PermissionGrant."
    return
  }

  $existingScopes = @()
  if ($existing.scope) { $existingScopes = $existing.scope.Trim().Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries) }

  $desiredScopes = $scopeString.Trim().Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)
  $merged = @($existingScopes + $desiredScopes) | Select-Object -Unique
  $mergedScopeString = ($merged -join " ").Trim()

  $existingScopeNormalized = (($existingScopes | Select-Object -Unique) -join " ").Trim()

  if ($mergedScopeString -ne $existingScopeNormalized) {
    Write-Info "Updating oauth2PermissionGrant $($existing.id) scopes to '$mergedScopeString'"
    Graph-Patch "https://graph.microsoft.com/v1.0/oauth2PermissionGrants/$($existing.id)" @{
      scope = $mergedScopeString
    } | Out-Null
    Write-Ok "Updated oauth2PermissionGrant."
  } else {
    Write-Ok "oauth2PermissionGrant already contains required scopes."
  }
}

function Find-AppByName($displayName) {
  $apps = Invoke-AzCli -ReadOnly -Command "az ad app list --display-name '$displayName' --query ""[].{appId:appId,id:id,displayName:displayName}"" -o json" -AsJson
  if (-not $apps) { return $null }
  if ($apps.Count -gt 1) { throw "Multiple apps found with display name '$displayName'. Use unique names." }
  return $apps | Select-Object -First 1
}

# ── Portal UI: Entra ID > App registrations > + New registration
#    Name: mcp-workshop-l01-api (or your ApiAppName)
#    Supported account types: Accounts in this organizational directory only
#    Click "Register"
#
#    Single-app model: this app is both the JWT audience (APIM validates-jwt)
#    and the confidential client for OBO token exchange to Microsoft Graph.
Write-Info "== Creating/locating app registration =="
$apiApp = Find-AppByName $ApiAppName
if (-not $apiApp) {
  $apiApp = Invoke-AzCli -Command "az ad app create --display-name '$ApiAppName' --sign-in-audience AzureADMyOrg -o json" -AsJson
  if (-not $apiApp) {
    Write-Warn "WhatIf: would create app '$ApiAppName', add scope '$ScopeValue', create secret, configure Graph permissions, grant admin consent."
    return
  }
  Write-Ok "Created API app: $($apiApp.appId)"
} else {
  Write-Ok "Found API app: $($apiApp.appId)"
}

$apiAppObj = Invoke-AzCli -ReadOnly -Command "az ad app show --id '$($apiApp.appId)' -o json" -AsJson
$apiObjectId = $apiAppObj.id
$apiClientId = $apiAppObj.appId

# ── Portal UI: App registration > Authentication > Allow public client flows = Yes
#    Required for device-code flow without a client secret
Write-Info "== Enabling public client flows (isFallbackPublicClient) =="
Graph-Patch "https://graph.microsoft.com/v1.0/applications/$apiObjectId" @{
  isFallbackPublicClient = $true
} | Out-Null

# ── Portal UI: App registration > Expose an API > Set (Application ID URI)
#    Set to: api://<client-id>
# Identifier URI
if ($UseApiUri) {
  $identifierUri = "api://$apiClientId"
  Write-Info "== Setting identifier URI on API app: $identifierUri =="
  Graph-Patch "https://graph.microsoft.com/v1.0/applications/$apiObjectId" @{
    identifierUris = @($identifierUri)
  } | Out-Null
} else {
  $identifierUri = ($apiAppObj.identifierUris | Select-Object -First 1)
  if (-not $identifierUri) {
    $identifierUri = "api://$apiClientId"
    Write-Warn "No identifierUri found; setting default: $identifierUri"
    Graph-Patch "https://graph.microsoft.com/v1.0/applications/$apiObjectId" @{
      identifierUris = @($identifierUri)
    } | Out-Null
  }
}

# ── Portal UI: App registration > Expose an API > + Add a scope
#    Scope name: mcp.invoke
#    Who can consent: Admins and users
#    Admin consent display name: Invoke MCP tools
#    Admin consent description: Allows the app to invoke MCP tools.
#    State: Enabled
Write-Info "== Ensuring API app has an OAuth2 permission scope '$ScopeValue' =="
$apiAppObj2Raw = Graph-Get "https://graph.microsoft.com/v1.0/applications/$apiObjectId"
$apiAppObj2 = $apiAppObj2Raw | ConvertFrom-Json

$currentScopes = @()
if ($apiAppObj2.api -and $apiAppObj2.api.oauth2PermissionScopes) {
  $currentScopes = @($apiAppObj2.api.oauth2PermissionScopes)
}

$scope = $currentScopes | Where-Object { $_.value -eq $ScopeValue } | Select-Object -First 1
if (-not $scope) {
  $scopeId = New-Guid
  $newScope = @{
    id = $scopeId
    adminConsentDisplayName = $ScopeAdminConsentDisplayName
    adminConsentDescription = $ScopeAdminConsentDescription
    userConsentDisplayName = $ScopeUserConsentDisplayName
    userConsentDescription = $ScopeUserConsentDescription
    isEnabled = $true
    type = "User"
    value = $ScopeValue
  }

  $updatedScopes = @($currentScopes + $newScope)

  Graph-Patch "https://graph.microsoft.com/v1.0/applications/$apiObjectId" @{
    api = @{
      oauth2PermissionScopes = $updatedScopes
    }
  } | Out-Null

  Write-Ok "Added scope '$ScopeValue' (id=$scopeId) to API app."
} else {
  $scopeId = $scope.id
  Write-Ok "Scope '$ScopeValue' already exists (id=$scopeId)."
}

# ── Portal UI: App registration > App roles > + Create app role
#    Display name: MCP User
#    Allowed member types: Users/Groups
#    Value: MCP.User
#    Description: Can invoke MCP tools on this server.
#    Enable this app role: checked
Write-Info "== Ensuring API app has 'MCP.User' app role =="
$apiAppObj2bRaw = Graph-Get "https://graph.microsoft.com/v1.0/applications/$apiObjectId"
$apiAppObj2b = $apiAppObj2bRaw | ConvertFrom-Json

$currentRoles = @()
if ($apiAppObj2b.appRoles) {
  $currentRoles = @($apiAppObj2b.appRoles)
}

$mcpUserRole = $currentRoles | Where-Object { $_.value -eq "MCP.User" } | Select-Object -First 1
if (-not $mcpUserRole) {
  $mcpUserRoleId = New-Guid
  $newRole = @{
    id = $mcpUserRoleId
    allowedMemberTypes = @("User")
    displayName = "MCP User"
    description = "Can invoke MCP tools on this server."
    isEnabled = $true
    value = "MCP.User"
  }
  $updatedRoles = @($currentRoles + $newRole)

  Graph-Patch "https://graph.microsoft.com/v1.0/applications/$apiObjectId" @{
    appRoles = $updatedRoles
  } | Out-Null
  Write-Ok "Added app role 'MCP.User' (id=$mcpUserRoleId)."
} else {
  $mcpUserRoleId = $mcpUserRole.id
  Write-Ok "App role 'MCP.User' already exists (id=$mcpUserRoleId)."
}

# ── Portal UI: This happens automatically when you create the app registration.
#    If the Enterprise Application (service principal) is missing:
#    Entra ID > Enterprise applications > + New application > Create your own > Register an application to integrate with Entra ID
Write-Info "== Creating/locating service principal for API app =="
$apiSp = Invoke-AzCli -ReadOnly -Command "az ad sp list --filter ""appId eq '$apiClientId'"" -o json" -AsJson | Select-Object -First 1
if (-not $apiSp) {
  $apiSp = Invoke-AzCli -Command "az ad sp create --id '$apiClientId' -o json" -AsJson
  if (-not $apiSp) {
    Write-Warn "WhatIf: would create API service principal, add secret, configure Graph permissions, grant admin consent."
    return
  }
  Write-Ok "Created API service principal: $($apiSp.id)"
} else {
  Write-Ok "Found API service principal: $($apiSp.id)"
}

# ── Portal UI: App registration > Certificates & secrets > + New client secret
#    Description: obo-secret
#    Expires: 12 months (or your SecretYears)
#    Copy the secret Value immediately (it won't be shown again)
#
#    Single-app model: the same app is the audience (validated by APIM) AND the
#    confidential client for OBO.  isFallbackPublicClient lets users obtain tokens
#    via device-code flow; the secret is used server-side for OBO only.
Write-Info "== Adding client secret to app (for OBO) =="
$endDate = (Get-Date).AddYears($SecretYears).ToString("yyyy-MM-dd")
$secretObj = Invoke-AzCli -Command "az ad app credential reset --id '$apiClientId' --append --display-name 'obo-secret' --end-date '$endDate' -o json" -AsJson
if (-not $secretObj) {
  Write-Warn "WhatIf: would create client secret, configure Graph permissions, grant admin consent."
  return
}
$clientSecret = $secretObj.password
Write-Ok "Created secret valid until $endDate"

# ── Portal UI: App registration > API permissions > + Add a permission
#    Tab "Microsoft Graph" > Delegated permissions > check "User.Read" > Add
Write-Info "== Configuring requiredResourceAccess (Graph delegated permission) =="

# Find Microsoft Graph SP and delegated scope id
$graphSp = Invoke-AzCli -ReadOnly -Command "az ad sp list --filter ""displayName eq 'Microsoft Graph'"" -o json" -AsJson | Select-Object -First 1
if (-not $graphSp) { throw "Could not find Microsoft Graph service principal in tenant." }

$graphAppId = $graphSp.appId
$graphScope = $graphSp.oauth2PermissionScopes | Where-Object { $_.value -eq $GraphDelegatedPermission } | Select-Object -First 1
if (-not $graphScope) { throw "Could not find Graph delegated permission '$GraphDelegatedPermission'." }
$graphScopeId = $graphScope.id

$requiredResourceAccess = @(
  @{
    resourceAppId = $graphAppId
    resourceAccess = @(
      @{ id = $graphScopeId; type = "Scope" }
    )
  }
)

Graph-Patch "https://graph.microsoft.com/v1.0/applications/$apiObjectId" @{
  requiredResourceAccess = $requiredResourceAccess
} | Out-Null
Write-Ok "Updated requiredResourceAccess (Graph $GraphDelegatedPermission)."

# ── Portal UI: App registration > API permissions
#    Click "Grant admin consent for <tenant>" button (requires Global Admin or Privileged Role Admin)
#    "User.Read" should show a green checkmark under "Status"
Write-Info "== Granting admin consent via Microsoft Graph oauth2PermissionGrants (requires admin) =="

# Delegated consent for Graph (User.Read)
Upsert-OAuth2PermissionGrant -clientSpId $apiSp.id -resourceSpId $graphSp.id -scopeString $GraphDelegatedPermission

Write-Ok "Graph-based admin consent complete."

# ── Portal UI: App registration > Authentication > + Add a platform > Mobile and desktop
#    Redirect URIs:
#      https://login.microsoftonline.com/common/oauth2/nativeclient
#      http://localhost
#      ms-appx-web://microsoft.aad.brokerplugin/<client-id>
Write-Info "== Adding public client redirect URIs (WAM broker, localhost, native client) =="
Invoke-AzCli -Command "az ad app update --id '$apiClientId' --public-client-redirect-uris 'https://login.microsoftonline.com/common/oauth2/nativeclient' 'http://localhost' 'ms-appx-web://microsoft.aad.brokerplugin/$apiClientId'"
Write-Ok "Public client redirect URIs configured."

# ── Portal UI: App registration > Expose an API > + Add a client application
#    Client ID: aebc6443-996d-45c2-90f0-388ff96faa56 (VS Code)
#    Authorized scopes: mcp.invoke
#    This pre-authorizes VS Code to acquire tokens for the mcp.invoke scope
#    without requiring additional admin consent.
Write-Info "== Pre-authorizing VS Code client for mcp.invoke scope =="
$vsCodeClientId = "aebc6443-996d-45c2-90f0-388ff96faa56"
$preAuthBody = @{
  api = @{
    knownClientApplications = @($vsCodeClientId)
    preAuthorizedApplications = @(
      @{
        appId = $vsCodeClientId
        delegatedPermissionIds = @($scopeId.ToString())
      }
    )
  }
}
Graph-Patch "https://graph.microsoft.com/v1.0/applications/$apiObjectId" $preAuthBody | Out-Null
Write-Ok "VS Code ($vsCodeClientId) pre-authorized for scope '$ScopeValue'."

Write-Host ""
Write-Ok "==================== OUTPUTS ===================="
Write-Host ("TENANT_ID:            {0}" -f $TenantId)
Write-Host ("CLIENT_ID:            {0}" -f $apiClientId)
Write-Host ("CLIENT_SECRET:        {0}" -f $clientSecret)
Write-Host ("AUDIENCE_URI:         {0}" -f $identifierUri)
Write-Host ("SCOPE:                {0}" -f $ScopeValue)
Write-Host ("OBO_SCOPE:            {0}" -f "https://graph.microsoft.com/.default")
Write-Ok "================================================="
Write-Host ""

Write-Info "Next steps — update .env:"
Write-Host "   OAUTH_CLIENT_ID=$apiClientId"
Write-Host "   OAUTH_SCOPES=$identifierUri/$ScopeValue"
Write-Host "   OBO_CLIENT_ID=$apiClientId"
Write-Host "   OBO_CLIENT_SECRET=$clientSecret"
Write-Host "   OBO_TENANT_ID=$TenantId"
Write-Host "   OBO_SCOPE=https://graph.microsoft.com/.default"

# Write machine-readable outputs if requested
if ($OutputFile) {
  @{
    TenantId     = $TenantId
    ClientId     = $apiClientId
    ClientSecret = $clientSecret
    IdentifierUri = $identifierUri
    ScopeValue   = $ScopeValue
  } | ConvertTo-Json | Set-Content -Path $OutputFile -Encoding UTF8
}

# ── Optional: assign current user to MCP.User role ──────────────────────────

# Get the current user's UPN from the az login context
$currentUserUpn = Invoke-AzCli -ReadOnly -Command "az ad signed-in-user show --query userPrincipalName -o tsv" 2>$null
if (-not $currentUserUpn) {
  $currentUserUpn = Invoke-AzCli -ReadOnly -Command "az account show --query user.name -o tsv"
}

if ($currentUserUpn) {
  Write-Host ""
  $answer = Read-Host "Add '$currentUserUpn' to the MCP.User role on '$ApiAppName'? (y/n)"
  if ($answer -match '^[yY]') {
    # ── Portal UI: Entra ID > Enterprise applications > find your API app > Users and groups
    #    + Add user/group > select the user > select role "MCP User" > Assign
    Write-Info "== Assigning '$currentUserUpn' to MCP.User role =="

    # Get the user's object id
    $userObj = Invoke-AzCli -ReadOnly -Command "az ad user show --id '$currentUserUpn' -o json" -AsJson
    if (-not $userObj) {
      Write-Err "Could not find user '$currentUserUpn' in Entra."
    } else {
      $userId = $userObj.id

      # Refresh the app role id (may have been created above)
      $apiAppRolesRaw = Graph-Get "https://graph.microsoft.com/v1.0/applications/$apiObjectId"
      $apiAppRoles = ($apiAppRolesRaw | ConvertFrom-Json).appRoles
      $roleObj = $apiAppRoles | Where-Object { $_.value -eq "MCP.User" } | Select-Object -First 1
      $roleId = $roleObj.id

      # Check if assignment already exists
      $existingAssignments = Graph-Get "https://graph.microsoft.com/v1.0/servicePrincipals/$($apiSp.id)/appRoleAssignedTo"
      $existing = ($existingAssignments | ConvertFrom-Json).value | Where-Object {
        $_.principalId -eq $userId -and $_.appRoleId -eq $roleId
      } | Select-Object -First 1

      if ($existing) {
        Write-Ok "'$currentUserUpn' already has MCP.User role."
      } else {
        Graph-Post "https://graph.microsoft.com/v1.0/servicePrincipals/$($apiSp.id)/appRoleAssignedTo" @{
          principalId = $userId
          resourceId  = $apiSp.id
          appRoleId   = $roleId
        } | Out-Null
        Write-Ok "Assigned '$currentUserUpn' to MCP.User role."
      }
    }
  } else {
    Write-Info "Skipped role assignment."
  }
}
