// just.config.js — TVA Workshop task runner
// Run tasks: npx just <taskname>
// List tasks: npx just --list
//
// Microsoft Learn: https://microsoft.github.io/just/
// Repo: https://github.com/microsoft/just

const { task, series, condition, logger } = require('just-task');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// ── Helpers ──────────────────────────────────────────────────────────────────

function run(cmd, opts = {}) {
  logger.info(`> ${cmd}`);
  execSync(cmd, { stdio: 'inherit', ...opts });
}

function loadEnv(file = '.workshop-outputs.env') {
  if (!fs.existsSync(file)) return {};
  return Object.fromEntries(
    fs.readFileSync(file, 'utf8')
      .split('\n')
      .filter(l => l.includes('='))
      .map(l => l.split('='))
  );
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

// 1. Install all dependencies (Python MCP server + local Node tools)
task('install', () => {
  // Ensure git submodule (mcp-backend) is initialized
  logger.info('Initializing git submodules...');
  run('git submodule update --init --recursive');
  logger.info('✅ Submodules ready');

  // Detect python3 vs python and enforce 3.10+
  const python = (() => {
    for (const cmd of ['python3', 'python']) {
      try {
        const ver = execSync(`${cmd} -c "import sys; print(sys.version_info[:2])"`, { stdio: 'pipe' }).toString().trim();
        // ver looks like "(3, 12)"
        const match = ver.match(/(\d+),\s*(\d+)/);
        if (match) {
          const [major, minor] = [parseInt(match[1]), parseInt(match[2])];
          if (major === 3 && minor >= 10) return cmd;
          throw new Error(`Python 3.10+ required. Found ${major}.${minor} via '${cmd}'.\n` +
            '👉 Install Python 3.10+ from https://python.org\n' +
            '   On macOS with Homebrew: brew install python@3.12\n' +
            '   Then re-run: npx just setup');
        }
      } catch (e) {
        if (e.message.includes('required')) throw e;
      }
    }
    throw new Error('Python not found. Install Python 3.10+ from https://python.org');
  })();
  logger.info(`Using ${python} (3.10+) ✅`);

  // Detect pip3 vs pip
  const pip = (() => {
    try { execSync('pip3 --version', { stdio: 'ignore' }); return 'pip3'; } catch (_) {}
    try { execSync('pip --version', { stdio: 'ignore' }); return 'pip'; } catch (_) {}
    throw new Error('pip not found. Install Python 3.10+ from https://python.org');
  })();
  logger.info(`Using ${pip} to install Python dependencies...`);
  run(`${pip} install -r requirements.txt`, { cwd: 'boilerplate/mcp-backend' });
  logger.info('✅ Python dependencies installed');
  run(`${pip} install azure-search-documents azure-identity --quiet`);
  logger.info('✅ All dependencies installed');
});

// 2. Run MCP server locally (Python/FastMCP)
task('dev', () => {
  logger.info('Starting TVA MCP server locally (Python/FastMCP)...');
  logger.info('MCP endpoint:  http://localhost:8000/mcp');
  logger.info('PRM metadata:  http://localhost:8000/.well-known/oauth-protected-resource');
  logger.info('Press Ctrl+C to stop.');
  const python = (() => {
    try { execSync('python3 --version', { stdio: 'ignore' }); return 'python3'; } catch (_) {}
    try { execSync('python --version', { stdio: 'ignore' }); return 'python'; } catch (_) {}
    throw new Error('Python 3.9+ not found. Install from https://python.org');
  })();
  run(`${python} mcp_server.py`, { cwd: 'boilerplate/mcp-backend' });
});

// 3. Run MCP server via PowerShell script (Windows-friendly)
task('dev:ps', () => {
  run('pwsh -File run_mcp_server.ps1', { cwd: 'boilerplate/mcp-backend' });
});

// 4. Stop local MCP server
task('dev:stop', () => {
  run('docker compose down', { cwd: 'boilerplate' });
});

// 5. Run MCP server in Docker locally (port 8000)
task('dev:docker', () => {
  logger.info('Building and starting MCP server in Docker...');
  logger.info('MCP endpoint: http://localhost:8000/mcp');
  run('docker compose up -d --build', { cwd: 'boilerplate' });
  logger.info('✅ MCP server running. Run `npx just test:local` to verify.');
});

// 6. Upload TVA docs to Azure AI Search (optional — Lab 1 uses Foundry File Search instead)
// Run this only if you need a separate AI Search index for custom connectors.
task('upload-docs', () => {
  logger.info('Uploading TVA documents to Azure AI Search index...');
  logger.info('NOTE: Lab 1 uses Foundry Agent File Search (upload via Foundry portal).');
  logger.info('This task populates a separate AI Search index for custom connector use.');
  const python = (() => {
    try { execSync('python3 --version', { stdio: 'ignore' }); return 'python3'; } catch (_) {}
    try { execSync('python --version', { stdio: 'ignore' }); return 'python'; } catch (_) {}
    throw new Error('Python 3.9+ not found.');
  })();
  run(`${python} boilerplate/upload-docs.py`);
  logger.info('✅ Docs uploaded to tva-knowledge-base index');
});

// 7. Provision full Azure stack — uses Aaron's deploy.ps1 with -Walkthrough for workshop
//    Requires PowerShell 7+ (pwsh). Pass LAB_NUM env var to set participant suffix.
task('provision', () => {
  const labNum = process.env.LAB_NUM || 'l01';
  const walkthrough = process.env.WALKTHROUGH === 'true' ? '-Walkthrough' : '';
  logger.info(`Provisioning Azure resources for lab: ${labNum}`);
  logger.info('⏱  APIM takes ~15 minutes. Grab coffee.');
  logger.info('📚 MS Learn: https://learn.microsoft.com/en-us/azure/api-management/');
  run(`pwsh -File deploy.ps1 -LabNum ${labNum} ${walkthrough}`, { cwd: 'boilerplate/mcp-backend' });
  logger.info('✅ Azure stack provisioned. Check .env for APIM outputs.');
});

// 8. Provision with walkthrough mode (teaching mode — pauses at each step)
task('provision:teach', () => {
  process.env.WALKTHROUGH = 'true';
  const labNum = process.env.LAB_NUM || 'l01';
  logger.info(`Provisioning in WALKTHROUGH mode for lab: ${labNum}`);
  run(`pwsh -File deploy.ps1 -LabNum ${labNum} -Walkthrough`, { cwd: 'boilerplate/mcp-backend' });
});

// 9. Test all endpoints (uses Aaron's test-endpoints.ps1 — device-code auth + 8 tests)
task('test:prod', () => {
  logger.info('Running endpoint tests (device-code auth required)...');
  run('pwsh -File test-endpoints.ps1', { cwd: 'boilerplate/mcp-backend' });
});

// 10. Test local MCP server (runs on port 8000)
task('test:local', () => {
  logger.info('Testing local MCP server on http://localhost:8000/mcp ...');
  run('curl -sf http://localhost:8000/.well-known/oauth-protected-resource | python3 -m json.tool');
  logger.info('✅ PRM metadata accessible');
});

// 11. Sync Aaron's mcp-backend submodule to latest
task('sync', () => {
  logger.info('Syncing mcp-backend submodule to latest...');
  run('git submodule update --remote boilerplate/mcp-backend');
  logger.info('✅ mcp-backend updated to latest commit from Aaron\'s repo');
  logger.info('Run `git add boilerplate/mcp-backend && git commit -m "chore: sync mcp-backend"` to save the update');
});

// 12. Add a user to the MCP.User app role
task('add-user', () => {
  const user = process.env.USER_EMAIL;
  if (!user) { logger.error('Set USER_EMAIL env var first'); process.exit(1); }
  const env = loadEnv('.env');
  run(`pwsh -File add-users.ps1 -TenantId "${env.OBO_TENANT_ID}" -AppClientId "${env.OAUTH_CLIENT_ID}" -Users "${user}"`,
    { cwd: 'boilerplate/mcp-backend' });
});

// 13. Full local setup (install only — Lab 1 doc upload done via Foundry portal)
task('setup', series('install'));

// 14. Full workshop flow: install → start local server → test
task('workshop:start', series('install', 'dev:docker', 'test:local'));

// 15. End of workshop: provision Azure (walkthrough) + test prod
task('workshop:ship', series('provision:teach', 'test:prod'));

// 16. Clean up local (stop Docker)
task('clean', () => {
  run('docker compose down --volumes', { cwd: 'boilerplate' });
  logger.info('Local containers stopped.');
  logger.info('To delete ALL Azure resources: az group delete --name mcp-workshop-rg --yes');
});
