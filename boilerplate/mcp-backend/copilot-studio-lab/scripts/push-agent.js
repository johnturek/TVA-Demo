/**
 * push-agent.js — Push local Copilot Studio agent changes to GCC Dataverse
 *
 * Reads local YAML files and updates/creates bot components in Dataverse.
 *
 * Usage:
 *   node push-agent.js --workspace <path> [--tenant-id <tid>] [--environment-url <url>] [--auth <mode>]
 */

const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");
const { getAccessToken } = require("./auth");
const { httpGet, httpPatch, httpPost } = require("./dataverse");
const { parseArgs } = require("./args");

async function main() {
  const args = parseArgs(["workspace", "tenantId", "environmentUrl"]);

  if (args.help) {
    console.log(`Usage: node push-agent.js [options]

Options:
  --workspace <path>        Local agent workspace (required)
  --tenant-id <id>          Azure AD tenant ID (or CPS_TENANT_ID)
  --environment-url <url>   Dataverse URL (or CPS_ENVIRONMENT_URL)
  --auth <mode>             Auth mode: az-cli, device, msal (auto-detected)
  -h, --help                Show this help`);
    return;
  }

  // Read agent.yml
  const agentPath = path.join(args.workspace, "agent.yml");
  if (!fs.existsSync(agentPath)) {
    console.error("❌ agent.yml not found in workspace");
    process.exit(1);
  }
  const agentMeta = yaml.load(fs.readFileSync(agentPath, "utf8"));
  console.log(`Agent: ${agentMeta.displayName} (${agentMeta.id})`);

  // Read local topic files
  const topicsDir = path.join(args.workspace, "topics");
  const localTopics = [];
  if (fs.existsSync(topicsDir)) {
    fs.readdirSync(topicsDir)
      .filter((f) => f.endsWith(".mcs.yml"))
      .forEach((file) => {
        const content = fs.readFileSync(path.join(topicsDir, file), "utf8");
        const parsed = yaml.load(content);
        let displayName = file.replace(".mcs.yml", "");
        if (parsed?.beginDialog?.intent?.displayName) {
          displayName = parsed.beginDialog.intent.displayName;
        }
        localTopics.push({ displayName, fileName: file, content });
      });
  }
  console.log(`Found ${localTopics.length} local topic files`);

  // Authenticate
  const token = await getAccessToken({
    tenantId: args.tenantId,
    resource: args.environmentUrl,
    authMode: args.authMode,
  });

  // Fetch remote components
  const envUrl = args.environmentUrl;
  const url = `${envUrl}/api/data/v9.2/botcomponents?$filter=_parentbotid_value eq ${agentMeta.id}&$select=botcomponentid,name,schemaname,componenttype,content,data`;
  const response = await httpGet(url, token);
  const remoteComponents = response.value || [];
  console.log(`Found ${remoteComponents.length} remote components`);

  let updatedCount = 0;
  let createdCount = 0;
  let skippedCount = 0;

  for (const localTopic of localTopics) {
    const remoteComp = remoteComponents.find(
      (rc) => rc.name === localTopic.displayName
    );

    if (!remoteComp) {
      // Create new topic
      console.log(`➕ Creating new topic: ${localTopic.displayName}...`);
      const schemaName =
        "new_" +
        localTopic.displayName.replace(/[^a-zA-Z0-9]/g, "").toLowerCase();
      try {
        await httpPost(`${envUrl}/api/data/v9.2/botcomponents`, token, {
          name: localTopic.displayName,
          schemaname: schemaName,
          componenttype: 9,
          data: localTopic.content,
          statecode: 0,
          statuscode: 1,
          "parentbotid@odata.bind": `/bots(${agentMeta.id})`,
        });
        createdCount++;
        console.log("   ✅ Created successfully");
      } catch (error) {
        console.log(`   ❌ Failed to create: ${error.message}`);
        skippedCount++;
      }
      continue;
    }

    // Compare content
    let remoteContent = remoteComp.data || remoteComp.content;
    if (remoteContent) {
      try {
        const parsed = JSON.parse(remoteContent);
        remoteContent = parsed.yaml || parsed.content || remoteContent;
      } catch {}
    }

    if (remoteContent === localTopic.content) {
      console.log(`✓ ${localTopic.displayName} - no changes`);
      continue;
    }

    // Update
    console.log(`📤 Updating ${localTopic.displayName}...`);
    await httpPatch(
      `${envUrl}/api/data/v9.2/botcomponents(${remoteComp.botcomponentid})`,
      token,
      { data: localTopic.content }
    );
    updatedCount++;
    console.log("   ✅ Updated successfully");
  }

  console.log(`\n✅ Push complete!`);
  console.log(`   Created: ${createdCount}`);
  console.log(`   Updated: ${updatedCount}`);
  console.log(
    `   Unchanged: ${localTopics.length - updatedCount - createdCount - skippedCount}`
  );
  console.log(`   Skipped: ${skippedCount}`);
}

main().catch((err) => {
  console.error("❌ Error:", err.message);
  process.exit(1);
});
