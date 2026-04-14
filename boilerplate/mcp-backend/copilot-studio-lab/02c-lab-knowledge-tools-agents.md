# Part 2c: Hands-On Lab — Knowledge, Tools & Child Agents (25 min)

Building on the agent you created in Part 2, you'll now extend it with additional knowledge sources, a tool/action, and a child agent.

---

## Lab A: Expand Your Knowledge Sources (8 min)

### A1: Add a SharePoint Knowledge Source (4 min)

> If you don't have a SharePoint site available, follow along with the instructor and skip to A2.

1. In your agent, click **"Knowledge"** in the left panel
2. Click **"+ Add knowledge"**
3. Select **"SharePoint"**
4. Enter a SharePoint site URL from your organization:
   ```
   https://yourtenant.sharepoint.us/sites/YourSiteName
   ```
5. Select specific document libraries or pages to index
6. Click **"Add"**

> 📝 **Why SharePoint?** Most GCC organizations store policies, procedures, and documentation in SharePoint. This is typically your most valuable knowledge source.

### A2: Add an Uploaded File (4 min)

1. Click **"+ Add knowledge"** again
2. Select **"Files"**
3. Upload a sample document (PDF, Word, or Excel):
   - Use any document you have, or download a sample from the instructor
   - Good candidates: an FAQ document, a policy manual, or a procedures guide
4. Click **"Upload"** and wait for indexing

### A3: Test Multi-Source Knowledge

In the **Test panel**, try questions that span both sources:

| Prompt | Expected Behavior |
|--------|-------------------|
| Question about the website content | Answer cites the public URL |
| Question about the uploaded file | Answer cites the uploaded document |
| Question that combines both | Answer may synthesize from multiple sources |

> ✅ **Checkpoint:** Your agent now pulls from multiple knowledge sources. Notice how the AI automatically selects the most relevant source based on the question.

### A4: Add a Knowledge Description

1. Click on one of your knowledge sources
2. Find the **Description** field
3. Add a clear description, e.g.:
   ```
   This knowledge source contains the official Microsoft Copilot Studio documentation.
   Use it when users ask about Copilot Studio features, setup, or capabilities.
   ```

> 💡 **Why descriptions matter:** When you have multiple knowledge sources, the AI uses descriptions to decide *which* source to search. Without descriptions, it searches everything — which can be slower and less accurate.

---

## Lab B: Add Tools to Your Agent (12 min)

### B1: Add a Pre-Built Connector Action (3 min)

We'll start with the simplest tool type — a pre-built connector.

1. In your agent, click **"Actions"** in the left panel
2. Click **"+ Add an action"**
3. Browse the available connectors. For this lab, choose one of these:

   **Option A — MSN Weather (simple, no auth required):**
   - Search for **"MSN Weather"**
   - Select **"Get current weather"**
   - The action is pre-configured with inputs (location) and outputs (temperature, conditions)

   **Option B — Office 365 Outlook (if available in your GCC tenant):**
   - Search for **"Office 365 Outlook"**
   - Select **"Send an email (V2)"**
   - You may need to authenticate the connector

   **Option C — SharePoint (if you have a list):**
   - Search for **"SharePoint"**
   - Select **"Get items"**
   - Configure with a SharePoint site and list URL

4. After adding the action, note the **description** field — this is what the AI reads to decide when to use it
5. Edit the description to be clear and specific:
   ```
   Use this action when the user asks about the current weather
   for a specific location or city.
   ```
6. Click **"Save"**

### B2: Create an Agent Flow (5 min)

Now let's create an **Agent Flow** — a Power Automate flow built directly in Copilot Studio, **no Premium license required**.

1. In your agent, click **"Actions"** in the left panel
2. Click **"+ Add an action"**
3. Select **"New agent flow"** (or **"Create a flow"**)
4. The Power Automate designer opens *within* Copilot Studio
5. Your flow starts with a **"When Copilot Studio calls a flow"** trigger — this is pre-configured
6. Add a simple action to the flow:

   **Example: Send a Teams notification**
   - Click **"+ New step"**
   - Search for **"Microsoft Teams"**
   - Select **"Post message in a chat or channel"**
   - Configure:
     | Field | Value |
     |-------|-------|
     | Post as | Flow bot |
     | Post in | Channel |
     | Team | *(select your team)* |
     | Channel | *(select a channel)* |
     | Message | `New request from agent: {triggerBody()['text']}` |

7. Add a **"Return value(s) to Copilot Studio"** step at the end
   - Add an output: `confirmation` = `"Notification sent successfully"`
8. **Save** the flow
9. Back in Copilot Studio, update the action **description**:
   ```
   Use this flow when the user wants to notify the team about
   something or send a message to the team channel.
   ```

> 🆕 **Why this matters:** This flow runs without Premium licensing. Previously, calling Power Automate from Copilot Studio required Premium connectors — Agent Flows remove that barrier entirely.

### B3: Enable Generative Actions (2 min)

For the AI to automatically use your new tools, enable Generative Actions:

1. Click **Settings** (gear icon) → **Generative AI**
2. Find the **"Generative actions"** or **"Dynamic chaining"** toggle
3. **Enable** it
4. Click **"Save"**

> ⚠️ **What this does:** With Generative Actions ON, the AI orchestrator automatically decides when to call your tools based on the user's message. Without it, tools only execute when explicitly called from a topic flow.

### B4: Test Your Tools

In the **Test panel**, try:

| Prompt | Expected Behavior |
|--------|-------------------|
| `What's the weather in Washington DC?` | Agent calls the connector action and returns current conditions |
| `Notify my team that the training lab is complete` | Agent calls the Agent Flow and sends a Teams message |
| `What is Copilot Studio?` | Agent uses knowledge (NOT any tool) — correct routing! |

> ✅ **Checkpoint:** Your agent now has two types of tools: a connector action AND an Agent Flow. Notice how the AI routes to the right one based on the user's intent.

### B5: Discussion — MCP and Custom Connectors (2 min)

While we won't build these in the lab, be aware of two additional tool types:

**MCP (Model Context Protocol):**
- An open standard — "USB-C for AI agents"
- Lets your agent connect to *any* MCP-compatible tool server (databases, GitHub, dev tools)
- Growing ecosystem of pre-built MCP servers
- Especially useful as a bridge to on-premises systems in GCC

**Custom Connectors:**
- Wrap any REST API into a Power Platform connector using an OpenAPI/Swagger definition
- If you already use custom connectors in Power Apps or Power Automate, they're available here too
- Great for internal LOB systems, HR/ERP, or custom Azure Functions

> ✅ **Checkpoint:** Your agent now both *knows things* (knowledge) and *does things* (tools). The AI orchestrator routes to the right capability automatically.

---

## Lab C: Create a Child Agent (7 min)

### C1: Create the Child Agent (4 min)

1. Go back to the **Copilot Studio home page** (`gcc.powerva.microsoft.us`)
2. Click **"+ Create"** → **"New agent"**
3. Fill in:

| Field | Value |
|-------|-------|
| **Name** | `Training FAQ Agent` |
| **Description** | `Specialized agent that answers questions about the AI training series` |
| **Instructions** | `You are a specialist agent that answers questions about the AI Agent Development Training Series. There are 3 sessions: Session 1 is Copilot Studio, Session 2 is Microsoft AI Foundry, and Session 3 is AI Use Case Development with GitHub Copilot. Be concise and helpful.` |

4. Click **"Create"**
5. Optionally add a knowledge source specific to this child agent's domain

### C2: Connect the Child Agent to Your Parent Agent (3 min)

1. Go back to your **Training Demo Agent** (the original agent from Part 2)
2. Click **"Agents"** in the left panel (or **"Actions"** → **"Add"** → look for agent options)
3. Click **"+ Add an agent"**
4. Select the **"Training FAQ Agent"** you just created
5. Review the agent's description — this is how the parent decides when to route to it
6. Click **"Add"**

### C3: Test the Multi-Agent Flow

In the **Test panel** of your parent agent, try:

| Prompt | Expected Behavior |
|--------|-------------------|
| `Tell me about the training sessions` | Routes to the Training FAQ child agent |
| `What's the weather?` | Uses the weather tool (stays in parent) |
| `What is Copilot Studio?` | Uses knowledge source (stays in parent) |

> ✅ **Checkpoint:** Your parent agent now routes to a specialized child agent. This is the foundation for building modular, enterprise-scale agent architectures.

---

## Summary: The Three Pillars in Action

You've now built an agent with all three pillars:

```
          ┌──────────────────────────┐
          │   Training Demo Agent    │
          │      (Your Agent)        │
          └────────────┬─────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
  ┌─────▼─────┐  ┌────▼────┐  ┌─────▼──────┐
  │ KNOWLEDGE │  │  TOOLS  │  │   AGENTS   │
  │           │  │         │  │            │
  │ • Website │  │ • Conn. │  │ • Training │
  │ • SharePt │  │   action │  │   FAQ Agent│
  │ • File    │  │ • Agent │  │   (child)  │
  │           │  │   Flow  │  │            │
  └───────────┘  └─────────┘  └────────────┘
```

| Pillar | What You Did | What You Learned |
|--------|-------------|-----------------|
| **Knowledge** | Added website, SharePoint, and file sources | Multiple sources with descriptions for smart routing |
| **Tools** | Added a connector action + Agent Flow (no Premium!) | AI decides when to use tools based on descriptions; MCP and custom connectors extend reach |
| **Agents** | Created a child agent and connected it | Modular architecture for scaling agent capabilities |

> 🎯 **Key Takeaway:** A well-built agent combines all three pillars. Knowledge for answering, Tools for doing, and Agents for delegating.

---

*Next: Part 3 — Connecting to Microsoft AI Foundry →*
