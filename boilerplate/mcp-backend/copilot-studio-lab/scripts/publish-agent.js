/**
 * publish-agent.js — Trigger publish on a Copilot Studio bot in GCC Dataverse
 *
 * Usage:
 *   node publish-agent.js --agent-id <guid> [--tenant-id <tid>] [--environment-url <url>] [--auth <mode>]
 */

const { getAccessToken } = require("./auth");
const { httpPost } = require("./dataverse");
const { parseArgs } = require("./args");

async function main() {
  const args = parseArgs(["agentId", "tenantId", "environmentUrl"]);

  if (args.help) {
    console.log(`Usage: node publish-agent.js [options]

Options:
  --agent-id <guid>         Bot ID to publish (required)
  --tenant-id <id>          Azure AD tenant ID (or CPS_TENANT_ID)
  --environment-url <url>   Dataverse URL (or CPS_ENVIRONMENT_URL)
  --auth <mode>             Auth mode: az-cli, device, msal (auto-detected)
  -h, --help                Show this help`);
    return;
  }

  const token = await getAccessToken({
    tenantId: args.tenantId,
    resource: args.environmentUrl,
    authMode: args.authMode,
  });

  console.log("Triggering publish...");
  const url = `${args.environmentUrl}/api/data/v9.2/bots(${args.agentId})/Microsoft.Dynamics.CRM.PublishAll`;

  try {
    await httpPost(url, token, {});
    console.log("✅ Publish triggered successfully!");
  } catch (err) {
    console.error("❌ Publish failed:", err.message);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("❌ Error:", err.message);
  process.exit(1);
});
