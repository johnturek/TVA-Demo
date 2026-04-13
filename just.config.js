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
  // Attempt git submodule init (no-op if no submodules are configured)
  try {
    logger.info('Checking git submodules...');
    run('git submodule update --init --recursive');
    logger.info('✅ Submodules ready');
  } catch (_) {
    logger.info('ℹ️  No submodules to initialize (mcp-backend is bundled inline)');
  }

  // Detect python3 vs python and enforce 3.10+
  const python = (() => {
    for (const cmd of ['python3', 'python']) {
      try {
        const ver = execSync(`${cmd} -c "import sys; print(sys.version_info[:2])"`, { stdio: 'pipe' }).toString().trim();
        const match = ver.match(/(\d+),\s*(\d+)/);
        if (match) {
          const [major, minor] = [parseInt(match[1]), parseInt(match[2])];
          if (major === 3 && minor >= 10) return cmd;
          throw new Error(`Python 3.10+ required. Found ${major}.${minor} via '${cmd}'.\n` +
            '👉 On macOS with Homebrew: brew install python@3.12\n' +
            '   Then re-run: npx just setup');
        }
      } catch (e) {
        if (e.message.includes('required')) throw e;
      }
    }
    throw new Error('Python not found. Install Python 3.10+ from https://python.org');
  })();
  logger.info(`Using ${python} (3.10+) ✅`);

  // Create a venv in boilerplate/mcp-backend/.venv if it doesn't exist
  // This avoids PEP 668 "externally managed environment" errors on macOS Homebrew Python
  const venvDir = path.resolve('boilerplate/mcp-backend/.venv');
  if (!fs.existsSync(venvDir)) {
    logger.info('Creating Python virtual environment...');
    run(`${python} -m venv ${venvDir}`);
    logger.info('✅ Virtual environment created at boilerplate/mcp-backend/.venv');
  } else {
    logger.info('✅ Virtual environment already exists');
  }

  // Use absolute paths to the venv's pip and python
  const venvPip = process.platform === 'win32'
    ? path.join(venvDir, 'Scripts', 'pip.exe')
    : path.join(venvDir, 'bin', 'pip');
  const venvPython = process.platform === 'win32'
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : path.join(venvDir, 'bin', 'python');

  logger.info('Installing MCP server dependencies into venv...');
  const reqFile = path.resolve('boilerplate/mcp-backend/requirements.txt');
  run(`"${venvPip}" install -r "${reqFile}"`);
  logger.info('✅ Python dependencies installed');
  run(`"${venvPip}" install azure-search-documents azure-identity --quiet`);
  logger.info('✅ All dependencies installed');
  logger.info('');
  logger.info('💡 To activate the venv manually: source boilerplate/mcp-backend/.venv/bin/activate');
  // Write venv python path to a file so other tasks can use it
  fs.writeFileSync('.venv-python', venvPython);
});

// 2. Run MCP server locally (Python/FastMCP)
task('dev', () => {
  logger.info('Starting TVA MCP server locally (Python/FastMCP)...');
  logger.info('MCP endpoint:  http://localhost:8000/mcp');
  logger.info('PRM metadata:  http://localhost:8000/.well-known/oauth-protected-resource');
  logger.info('Press Ctrl+C to stop.');

  // Auto-copy workshop local env to .env if missing
  const envFile = path.resolve('boilerplate/mcp-backend/.env');
  const workshopEnv = path.resolve('boilerplate/.env.workshop-local');
  const exampleEnv = path.resolve('boilerplate/mcp-backend/example.env');
  if (!fs.existsSync(envFile)) {
    const source = fs.existsSync(workshopEnv) ? workshopEnv : exampleEnv;
    fs.copyFileSync(source, envFile);
    logger.info('ℹ️  Created boilerplate/mcp-backend/.env (auth disabled for local dev)');
    logger.info('   Edit this file to add your Entra ID credentials for production use.');
  }

  // Use venv python if available
  const venvPython = path.resolve('boilerplate/mcp-backend/.venv/bin/python');
  const python = fs.existsSync(venvPython) ? venvPython
    : fs.existsSync('.venv-python') ? fs.readFileSync('.venv-python', 'utf8').trim()
    : 'python3';
  run(`"${python}" mcp_server.py`, { cwd: 'boilerplate/mcp-backend' });
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
//    LAB_NUM must be unique per student for per-student resources (e.g. tvad01, tvad02).
//    For a shared environment, all students can use the same value (e.g. tva01).
task('provision', () => {
  const labNum = process.env.LAB_NUM || 'tvad01';
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
  const labNum = process.env.LAB_NUM || 'tvad01';
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
  // Hit the MCP endpoint — expect a 4xx (no session) or 2xx, not a connection error
  run('curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/mcp | grep -qE "^[245]" && echo "\u2705 MCP server is responding" || echo "\u26a0\ufe0f  Unexpected response"');
  logger.info('\u2705 MCP server reachable at http://localhost:8000/mcp');
});

// 11. (No-op) mcp-backend is now bundled inline — no submodule to sync
task('sync', () => {
  logger.info('ℹ️  mcp-backend is now bundled directly in this repo (no submodule).');
  logger.info('   To update the MCP server code, edit boilerplate/mcp-backend/ directly.');
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

// 17. Open workshop slides in default browser
task('slides', () => {
  const slidesPath = path.resolve('slides/index.html');
  if (!fs.existsSync(slidesPath)) {
    logger.error('slides/index.html not found');
    process.exit(1);
  }
  if (process.platform === 'darwin') {
    run(`open "${slidesPath}"`);
  } else if (process.platform === 'win32') {
    run(`start "" "${slidesPath}"`);
  } else {
    const slidesUrl = `file://${slidesPath}`;
    // In dev containers, xdg-open may not exist; prefer VS Code-provided browser command.
    if (process.env.BROWSER) {
      run(`${process.env.BROWSER} "${slidesUrl}"`);
    } else {
      run(`xdg-open "${slidesPath}"`);
    }
  }
  logger.info('✅ Slides opened in browser');
  logger.info('💡 Use arrow keys to navigate, F for fullscreen, S for speaker view');
});

// 18. Deploy Foundry Lab infrastructure (Aaron's 6 hands-on labs)
task('foundry:deploy', () => {
  logger.info('Deploying Foundry Lab infrastructure (AI Foundry Account + Project + AI Search)...');
  logger.info('⏱  First run takes ~5 minutes for Bicep deployment.');
  const labNum = process.env.LAB_NUM || '';
  const labNumFlag = labNum ? `-LabNum ${labNum}` : '';
  const searchLocation = process.env.SEARCH_LOCATION || '';
  const searchLocationFlag = searchLocation ? `-SearchLocation ${searchLocation}` : '';
  const walkthrough = process.env.WALKTHROUGH === 'true' ? '-Walkthrough' : '';
  const resourceGroupOverride = process.env.RESOURCE_GROUP_OVERRIDE || '';
  const resourceGroupOverrideFlag = resourceGroupOverride ? `-ResourceGroupOverride ${resourceGroupOverride}` : '';
  run(`pwsh -File deploy.ps1 -Prefix foundry-lab ${labNumFlag} ${searchLocationFlag} ${walkthrough} ${resourceGroupOverrideFlag}`, { cwd: 'boilerplate/mcp-backend/foundry-lab' });
});

// 19. Run a specific Foundry lab (e.g., FOUNDRY_LAB=01 npx just foundry:lab)
task('foundry:lab', () => {
  const labNum = process.env.FOUNDRY_LAB || '01';
  const labMap = {
    '01': 'lab01-prompts-completions/lab01_completions.py',
    '02': 'lab02-responses-api/lab02_responses.py',
    '03': 'lab03-agents/lab03_agents.py',
    '04': 'lab04-multi-agent/lab04_multi_agent.py',
    '05': 'lab05-rag/lab05_rag.py',
    '06': 'lab06-foundry-iq/lab06_foundry_iq.py',
  };
  const labFile = labMap[labNum];
  if (!labFile) {
    logger.error(`Unknown lab: ${labNum}. Use 01-06.`);
    process.exit(1);
  }
  logger.info(`Running Foundry Lab ${labNum}...`);
  const python = fs.existsSync('.venv-python') ? fs.readFileSync('.venv-python', 'utf8').trim() : 'python3';
  run(`"${python}" labs/${labFile}`, { cwd: 'boilerplate/mcp-backend/foundry-lab' });
});
