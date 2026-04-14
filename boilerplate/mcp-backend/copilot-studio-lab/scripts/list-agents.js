/**
 * list-agents.js — List Copilot Studio agents in a GCC Dataverse environment
 *
 * Usage:
 *   node list-agents.js [--tenant-id <tid>] [--environment-url <url>] [--auth <mode>]
 *
 * Auth modes: az-cli (default in Cloud Shell), device (Codespaces), msal (local VS Code)
 */

const { getAccessToken } = require("./auth");
const { httpGet } = require("./dataverse");
const { parseArgs } = require("./args");

async function main() {
  const args = parseArgs(["tenantId", "environmentUrl"]);

  if (args.help) {
    console.log(`Usage: node list-agents.js [options]

Options:
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

  // WhoAmI check
  const whoAmI = await httpGet(`${args.environmentUrl}/api/data/v9.2/WhoAmI`, token);
  console.log(`Signed in as user: ${whoAmI.UserId}\n`);

  // List bots
  const url = `${args.environmentUrl}/api/data/v9.2/bots?$select=botid,name,schemaname&$orderby=name`;
  const response = await httpGet(url, token);
  const bots = response.value || [];

  if (bots.length === 0) {
    console.log("No agents found.");
    return;
  }

  console.log(`Found ${bots.length} agent(s):\n`);
  const maxName = Math.max(...bots.map((b) => b.name.length), 4);
  console.log(`${"Name".padEnd(maxName)}  Agent ID`);
  console.log(`${"─".repeat(maxName)}  ${"─".repeat(36)}`);
  bots.forEach((bot) => {
    console.log(`${bot.name.padEnd(maxName)}  ${bot.botid}`);
  });
}

main().catch((err) => {
  console.error("❌ Error:", err.message);
  process.exit(1);
});
