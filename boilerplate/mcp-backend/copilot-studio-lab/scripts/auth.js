/**
 * auth.js — Portable authentication for GCC Dataverse
 *
 * Supports three auth modes:
 *   1. az-cli   — Uses `az account get-access-token` (Cloud Shell, local with Azure CLI)
 *   2. device   — MSAL device code flow (Codespaces, headless, no browser)
 *                 Tokens are cached to ~/.cps-msal-cache.json so subsequent
 *                 calls use silent acquisition until the refresh token expires.
 *   3. msal     — MSAL cached tokens from VS Code extension (local dev with extension)
 *
 * Auto-detection order: az-cli → msal → device
 */

const { execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const CACHE_FILE = path.join(
  process.env.HOME || process.env.USERPROFILE,
  ".cps-msal-cache.json"
);

const CLIENT_ID = "51f81489-12ee-4a9e-aaae-a2591f45987d"; // VS Code first-party

/**
 * Get an access token for the given resource.
 * @param {object} opts
 * @param {string} opts.tenantId   - Azure AD tenant ID
 * @param {string} opts.resource   - Resource URL (e.g. https://org.crm9.dynamics.com)
 * @param {string} [opts.authMode] - Force auth mode: "az-cli", "device", "msal"
 * @returns {Promise<string>} Access token
 */
async function getAccessToken({ tenantId, resource, authMode }) {
  const mode = authMode || detectAuthMode();
  console.error(`Auth mode: ${mode}`);

  switch (mode) {
    case "az-cli":
      return getTokenFromAzCli(resource, tenantId);
    case "device":
      return getTokenFromDeviceCode(tenantId, resource);
    case "msal":
      return getTokenFromMsalCache(tenantId, resource);
    default:
      throw new Error(`Unknown auth mode: ${mode}. Use: az-cli, device, msal`);
  }
}

/** Detect best available auth mode */
function detectAuthMode() {
  // Try Azure CLI first (works in Cloud Shell, local, Codespaces with az login)
  try {
    execSync("az account show", { stdio: "pipe" });
    return "az-cli";
  } catch {}

  // Try MSAL cache (local dev with VS Code extension)
  const scriptsPath = getMsalScriptsPath();
  if (scriptsPath) return "msal";

  // Fall back to device code
  return "device";
}

/** Azure CLI token acquisition */
function getTokenFromAzCli(resource, tenantId) {
  try {
    const tenantArg = tenantId ? ` --tenant "${tenantId}"` : "";
    const output = execSync(
      `az account get-access-token --resource "${resource}"${tenantArg} --query accessToken -o tsv`,
      { encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] }
    );
    return output.trim();
  } catch (e) {
    throw new Error(
      `Azure CLI token failed. Run 'az login' first.\n${e.stderr || e.message}`
    );
  }
}

/** Build an MSAL app with file-based token cache */
function buildMsalApp(tenantId) {
  const msal = require("@azure/msal-node");

  const beforeCacheAccess = async (cacheContext) => {
    if (fs.existsSync(CACHE_FILE)) {
      cacheContext.tokenCache.deserialize(fs.readFileSync(CACHE_FILE, "utf8"));
    }
  };

  const afterCacheAccess = async (cacheContext) => {
    if (cacheContext.cacheHasChanged) {
      fs.writeFileSync(CACHE_FILE, cacheContext.tokenCache.serialize(), { mode: 0o600 });
    }
  };

  return new msal.PublicClientApplication({
    auth: {
      clientId: CLIENT_ID,
      authority: `https://login.microsoftonline.com/${tenantId}`,
    },
    cache: {
      cachePlugin: { beforeCacheAccess, afterCacheAccess },
    },
  });
}

/** MSAL device code flow with persistent token cache */
async function getTokenFromDeviceCode(tenantId, resource) {
  const app = buildMsalApp(tenantId);
  const scope = resource.endsWith("/.default") ? resource : `${resource}/.default`;

  // Try silent acquisition from cache first
  const accounts = await app.getTokenCache().getAllAccounts();
  if (accounts.length > 0) {
    try {
      const result = await app.acquireTokenSilent({
        scopes: [scope],
        account: accounts[0],
      });
      console.error("Using cached token (silent refresh)");
      return result.accessToken;
    } catch {
      // Cache miss or expired refresh token — fall through to device code
    }
  }

  const result = await app.acquireTokenByDeviceCode({
    scopes: [scope],
    deviceCodeCallback: (response) => {
      console.error(`\n${response.message}\n`);
    },
  });

  return result.accessToken;
}

/** MSAL cached token from VS Code Copilot Studio extension */
async function getTokenFromMsalCache(tenantId, resource) {
  const scriptsPath = getMsalScriptsPath();
  if (!scriptsPath) {
    throw new Error(
      "VS Code Copilot Studio extension not found. Use --auth az-cli or --auth device instead."
    );
  }

  const msal = require(path.join(scriptsPath, "node_modules", "@azure/msal-node"));
  const { createCachePlugin } = require(path.join(scriptsPath, "src", "msal-cache.js"));

  const cachePlugin = await createCachePlugin("manage-agent");
  const app = new msal.PublicClientApplication({
    auth: {
      clientId: CLIENT_ID,
      authority: `https://login.microsoftonline.com/${tenantId}`,
    },
    cache: { cachePlugin },
  });

  const accounts = await app.getTokenCache().getAllAccounts();
  if (accounts.length === 0) {
    throw new Error(
      "No cached MSAL account. Run manage-agent list-agents first, or use --auth az-cli."
    );
  }

  const scope = resource.endsWith("/.default") ? resource : `${resource}/.default`;
  const result = await app.acquireTokenSilent({
    scopes: [scope],
    account: accounts[0],
  });

  return result.accessToken;
}

/** Find VS Code extension scripts path, or null */
function getMsalScriptsPath() {
  const home = process.env.USERPROFILE || process.env.HOME;
  const candidate = path.join(
    home,
    ".copilot",
    "installed-plugins",
    "skills-for-copilot-studio",
    "copilot-studio",
    "scripts"
  );
  if (fs.existsSync(path.join(candidate, "src", "msal-cache.js"))) {
    return candidate;
  }
  return null;
}

module.exports = { getAccessToken, detectAuthMode };
