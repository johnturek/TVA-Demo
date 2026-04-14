/**
 * clone-agent.js — Clone a Copilot Studio agent from GCC Dataverse
 *
 * Queries Dataverse directly to extract bot components and create
 * the proper directory structure for VS Code Copilot Studio extension.
 *
 * Usage:
 *   node clone-agent.js --agent-id <guid> --output-dir <path> [--tenant-id <tid>] [--environment-url <url>] [--auth <mode>]
 */

const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");
const { getAccessToken } = require("./auth");
const { httpGet } = require("./dataverse");
const { parseArgs } = require("./args");

async function main() {
  const args = parseArgs(["agentId", "outputDir", "tenantId", "environmentUrl"]);

  if (args.help) {
    console.log(`Usage: node clone-agent.js [options]

Options:
  --agent-id <guid>         Bot ID to clone (required)
  --output-dir <path>       Output directory (required)
  --tenant-id <id>          Azure AD tenant ID (or CPS_TENANT_ID)
  --environment-url <url>   Dataverse URL (or CPS_ENVIRONMENT_URL)
  --auth <mode>             Auth mode: az-cli, device, msal (auto-detected)
  -h, --help                Show this help`);
    return;
  }

  console.log(`Cloning agent ${args.agentId} to ${args.outputDir}`);

  const token = await getAccessToken({
    tenantId: args.tenantId,
    resource: args.environmentUrl,
    authMode: args.authMode,
  });

  // Fetch bot metadata
  console.log("Fetching bot metadata...");
  const botUrl = `${args.environmentUrl}/api/data/v9.2/bots(${args.agentId})?$select=botid,name,schemaname,iconbase64,authenticationmode,authenticationtrigger`;
  const bot = await httpGet(botUrl, token);
  console.log(`Agent: ${bot.name}`);

  // Fetch components
  console.log("Fetching bot components...");
  const compUrl = `${args.environmentUrl}/api/data/v9.2/botcomponents?$filter=_parentbotid_value eq ${args.agentId}&$select=botcomponentid,name,schemaname,componenttype,content,data`;
  const compResponse = await httpGet(compUrl, token);
  const components = compResponse.value || [];
  console.log(`Found ${components.length} components`);

  // Create directory structure
  const dirs = ["topics", "actions", "entities"].map((d) =>
    path.join(args.outputDir, d)
  );
  [args.outputDir, ...dirs].forEach((dir) => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });

  // Create agent.yml
  const agentYaml = {
    kind: "Agent",
    version: "1.0",
    name: bot.schemaname || bot.name,
    displayName: bot.name,
    id: bot.botid,
  };
  fs.writeFileSync(
    path.join(args.outputDir, "agent.yml"),
    yaml.dump(agentYaml),
    "utf8"
  );
  console.log("Created agent.yml");

  // Process components
  components.forEach((comp) => {
    let content = comp.data || comp.content;
    if (!content) {
      console.log(`  Skipping ${comp.name} - no content`);
      return;
    }

    // Unwrap JSON envelope if present
    try {
      const parsed = JSON.parse(content);
      content = parsed.yaml || parsed.content || content;
    } catch {}

    // Extract display name from YAML
    let displayName = comp.name;
    try {
      const yamlContent = yaml.load(content);
      if (yamlContent?.beginDialog?.intent?.displayName) {
        displayName = yamlContent.beginDialog.intent.displayName;
      }
    } catch {
      console.log(`  Could not parse YAML for ${comp.name}, using component name`);
    }

    // Determine output path based on component type
    const fileName = `${displayName}.mcs.yml`;
    let filePath;
    if (comp.componenttype === 1 || comp.componenttype === 9) {
      filePath = path.join(args.outputDir, "topics", fileName);
    } else if (comp.componenttype === 2) {
      filePath = path.join(args.outputDir, "actions", fileName);
    } else {
      filePath = path.join(args.outputDir, "topics", fileName);
    }

    fs.writeFileSync(filePath, content, "utf8");
    console.log(`  Wrote: ${path.relative(args.outputDir, filePath)}`);
  });

  console.log(`\n✅ Successfully cloned agent to ${args.outputDir}`);
}

main().catch((err) => {
  console.error("❌ Error:", err.message);
  process.exit(1);
});
