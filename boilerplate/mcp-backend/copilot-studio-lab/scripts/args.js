/**
 * args.js — Shared argument parser for GCC Copilot Studio scripts
 *
 * Reads CLI args and env vars, returns a normalized config object.
 */

function parseArgs(requiredFields = []) {
  const args = process.argv.slice(2);
  const parsed = {
    agentId: null,
    workspace: null,
    outputDir: null,
    environmentId: null,
    tenantId: process.env.CPS_TENANT_ID,
    environmentUrl: process.env.CPS_ENVIRONMENT_URL,
    authMode: process.env.CPS_AUTH_MODE || null,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case "--agent-id":
        parsed.agentId = args[++i];
        break;
      case "--workspace":
        parsed.workspace = args[++i];
        break;
      case "--output-dir":
        parsed.outputDir = args[++i];
        break;
      case "--environment-id":
        parsed.environmentId = args[++i];
        break;
      case "--tenant-id":
        parsed.tenantId = args[++i];
        break;
      case "--environment-url":
        parsed.environmentUrl = args[++i];
        break;
      case "--auth":
        parsed.authMode = args[++i];
        break;
      case "--help":
      case "-h":
        parsed.help = true;
        break;
    }
  }

  if (parsed.environmentUrl) {
    parsed.environmentUrl = parsed.environmentUrl.replace(/\/+$/, "");
  }

  if (!parsed.help) {
    const missing = requiredFields.filter((f) => !parsed[f]);
    if (missing.length > 0) {
      const envHints = {
        tenantId: "CPS_TENANT_ID",
        environmentUrl: "CPS_ENVIRONMENT_URL",
      };
      const hints = missing
        .map((f) => {
          const flag = "--" + f.replace(/([A-Z])/g, "-$1").toLowerCase();
          const env = envHints[f] ? ` or ${envHints[f]}` : "";
          return `  ${flag}${env}`;
        })
        .join("\n");
      console.error(`❌ Missing required arguments:\n${hints}`);
      process.exit(1);
    }
  }

  return parsed;
}

module.exports = { parseArgs };
