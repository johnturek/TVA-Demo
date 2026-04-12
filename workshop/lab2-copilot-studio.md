# Lab 2: Build the TVA Document Processor in Copilot Studio
**Duration:** 90 minutes | **Session:** 1 of 3 | **Presenter:** John

---

## Objectives
By the end of this lab, participants will have:
- A working Copilot Studio agent built from scratch
- Agent connected to Azure AI Foundry (not native Copilot knowledge)
- Configured authentication (maker vs OBO)
- File upload capability tested
- A passing end-to-end demo conversation

---

## Prerequisites
- Completed Lab 1 (Azure AI Foundry agent deployed and endpoint ready)
- Your saved values: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, `FOUNDRY_AGENT_ENDPOINT`, `FOUNDRY_AGENT_KEY`
- Access to https://copilotstudio.microsoft.us

---

## Part 1: Create the Agent (15 min)

### Step 1: Open Copilot Studio
1. Navigate to https://copilotstudio.microsoft.us
2. Sign in with demo tenant credentials

### Step 2: Create Your Agent

> **ℹ️ New Primary UX (as of early 2026):** The recommended way to create an agent is now **description-first from the Home page**. On the Home page, type a description of your agent in the prompt box and Copilot Studio will scaffold it for you automatically. The classic **+ Create → New agent** path (Agents page → top-left menu) still works as an alternative.

**Option A — Description-first (recommended):**
On the **Home** page, type in the description box:
> *"An agent for TVA engineers and compliance officers to search regulatory documents, NERC CIP compliance reports, and grid reliability data."*

Copilot Studio will generate a name and starting instructions. Review and adjust using the values below.

**Option B — Classic flow:**
1. Click **+ Create** → **New agent**
2. Proceed to name and configure manually.

### Step 3: Name and Describe Your Agent
- **Name:** `TVA Document Processor`
- **Description:** `Helps TVA engineers and compliance officers search regulatory documents, NERC CIP compliance reports, and grid reliability data.`
- **Instructions (system prompt):**

```
You are the TVA Document Processor, an AI assistant for Tennessee Valley Authority staff.

Your purpose:
- Answer questions about TVA regulatory documents and NERC CIP compliance
- Summarize uploaded compliance reports and policy documents
- Help engineers find specific requirements in TVA's document library
- Flag potential compliance gaps when asked

Always:
- Cite the source document when answering from the knowledge base
- Be precise with regulatory requirements — accuracy matters in energy compliance
- If a document is uploaded, prioritize its content over general knowledge
- If you don't know, say so clearly rather than guessing

TVA context: You support ~11,000 employees across power generation (nuclear, hydro, fossil, solar), river management operations, and grid reliability — serving 10 million people across the Tennessee Valley.
```

Click **Create**.

---

## Part 2: Connect to Azure AI Foundry Agent (25 min)

> ⚠️ **Important:** We are NOT using Copilot Studio's native knowledge feature. We're calling the **Foundry Agent Service** endpoint created in Lab 1 directly. This gives us richer RAG control and keeps all our AI logic in Azure AI Foundry.
>
> **Why not `data_sources` / Azure OpenAI On Your Data?** That pattern (sending `data_sources` with `type: azure_search` in the completions body) is deprecated and being retired. The current recommended pattern is to let the Foundry Agent handle grounding and call its conversation endpoint.

### Step 1: Add a Custom Connector Topic
1. In your agent, click **Topics** → **+ Add topic** → **From blank**
2. Name it: `Document Search`
3. Add a trigger phrase: `Search documents`

### Step 2: Add an HTTP Request Node
1. In the topic canvas, click **+** → **Add node** → **Advanced** → **Send HTTP request**

> ℹ️ **Terminology note:** Copilot Studio calls this a **node**, not an "action type." You'll find it under **Add node → Advanced → Send HTTP request**.

2. Configure:
   - **Method:** POST
   - **URL:** `https://YOUR_FOUNDRY_AGENT_ENDPOINT/invoke?api-version=2024-10-21`
   
   > Your facilitator has pre-configured a single-turn wrapper endpoint that accepts a user message and returns the agent's reply in one call. This is simpler than the multi-step conversation API.
   
   - **Headers:**
     - `Content-Type`: `application/json`
     - `api-key`: `[your Foundry Agent key]`

### Step 3: Build the Request Body
Use this JSON template in the body field. This calls the Foundry Agent Service directly — no `data_sources` needed; the agent handles grounding internally.

```json
{
  "message": "{System.LastMessage.Text}",
  "assistant_id": "YOUR_ASSISTANT_ID"
}
```

### Step 4: Parse and Display the Response
1. Add a **Parse value** node → parse `Topic.HTTPResponse.Body` as JSON
2. Add a **Send a message** node
3. Set message expression to:

```
Topic.ParsedResponse.choices.first().message.content
```

> ℹ️ **Power Fx note:** Use `.first()` — this is valid Power Fx. Array index syntax like `choices[0]` is **not** valid in Copilot Studio's expression editor.

### Step 5: Enable Knowledge on the Agent Overview Page
1. Navigate back to the agent **Overview** tab (the main agent page)
2. In the **Knowledge** section, click **+ Add knowledge**
3. Select **Azure AI Search** (or the appropriate connector for your index)
4. Enter your search endpoint and index details

> ℹ️ **UI update:** Knowledge is now configured directly on the agent **Overview** page, not via `Settings → Generative AI → toggle ON`. If you see a toggle under Settings → Generative AI, it controls whether generative answers are *enabled*, but the knowledge sources themselves are managed from the Overview page.

This ensures the agent uses your Foundry index for any question, not just the Document Search topic.

---

## Part 3: Authentication — Maker vs OBO (20 min)

This is one of the most important decisions in Copilot Studio development.

### The Two Models

| | Maker Credentials | User Credentials (OBO) |
|---|---|---|
| **Who authenticates** | The agent itself (service principal) | The end user |
| **Best for** | Internal tools, read-only data | Sensitive data, audit trails, user-specific data |
| **Setup complexity** | Low | Medium-High |
| **Government use** | Acceptable for demos | Required for production |
| **TVA use case** | Workshop demos | Production NERC CIP queries |

### Configure Maker Credentials (Workshop Default)
1. Go to **Settings** → **Security** → **Authentication**
2. Select **No authentication** (for workshop only)
3. This lets the agent call your API key directly

### Configure OBO (Production Pattern — Demo Only)
1. Go to **Settings** → **Security** → **Authentication**
2. Select **Authenticate manually**

> ℹ️ **Label update:** The option was previously labeled "Authenticate with Microsoft." It is now **"Authenticate manually"** in the current UI.

3. The **recommended production approach** is **Microsoft Entra ID V2** with **federated credentials** (secret-less) — no client secret stored in the agent config. This is the pattern supported for GCC and production workloads.
4. Enter your app registration details (from Lab 3's `setup-app-registration.ps1`)
5. Enable **Require users to sign in**

When OBO is enabled, the agent forwards the logged-in user's token to backend APIs — meaning your APIM layer knows exactly which TVA engineer made the request.

> ⚠️ **Vignette: GCC Tenants — Dataverse Connector Broken**
> If you're deploying to a GCC (Government Community Cloud) tenant, the Dataverse connector for Copilot Studio skills is currently broken. Aaron has a pending PR with the product group for GCC support. Workaround: use HTTP Request nodes directly (what we're doing in this lab) instead of Dataverse-backed skills. This is actually the more portable pattern anyway.

---

## Part 4: File Upload Capability (15 min)

One of Copilot Studio's most powerful features for document processing.

### Step 1: Enable File Upload
1. Go to **Settings** → **Generative AI**
2. Scroll to **File upload** → Toggle ON
3. Set max file size: 20MB
4. Allowed types: PDF, DOCX, TXT

### Step 2: Add Upload Topic
1. Create a new topic: `Analyze Document`
2. Trigger phrases:
   - `analyze this document`
   - `review this file`
   - `check this report`
3. Add a **File upload** action node
4. Store result in `Topic.UploadedFile`

### Step 3: Process the Upload
After the file upload node:

```
Send message: "I've received your document. Give me a moment to analyze it..."

Add HTTP Request node:
  POST https://YOUR_FOUNDRY_AGENT_ENDPOINT/invoke?api-version=2024-10-21
  Body: {
    "message": "Analyze this TVA document for compliance issues and key findings. Document content: {Topic.UploadedFile.Content}",
    "assistant_id": "YOUR_ASSISTANT_ID"
  }
```

### Test It
Upload one of the sample TVA documents from the `/docs` folder and ask:
- "What compliance gaps does this document identify?"
- "Summarize the key findings"
- "Are there any NERC CIP violations mentioned?"

---

## Part 5: Prompt-Based Development (10 min)

Instead of clicking through the UI for every topic, generate YAML directly.

### Step 1: Ask Copilot to Generate a Topic
In VS Code or any editor, prompt:

```
Generate a Copilot Studio topic YAML for an agent that:
- Triggers on "check compliance status"  
- Asks the user which NERC CIP standard they need (CIP-007, CIP-010, CIP-011)
- Calls a REST endpoint at https://api.example.com/compliance/{standard}
- Displays the result with a formatted message
```

### Step 2: Import the YAML
1. In Copilot Studio, go to **Topics**
2. Click the **...** menu → **Open code editor**

> ℹ️ **UI note:** The menu label for the YAML/code editor may vary in the live UI — look for "Open code editor," "Edit YAML," or similar. Verify the current label in your environment.

3. Paste the generated YAML
4. Fix any validation errors (usually just variable name formatting)

This approach is 5-10x faster than building topics in the canvas UI — especially for complex flows.

---

## Lab 2 Checkpoint ✅

Before break, verify:
- [ ] Agent created with TVA system prompt
- [ ] Document Search topic calls Azure AI Foundry Agent and returns cited answers
- [ ] Knowledge added via agent Overview page
- [ ] Authentication mode selected (maker for workshop, OBO pattern understood)
- [ ] File upload works — uploaded a sample doc and got a summary
- [ ] Tested at least 3 conversations in the Test panel

**Test your agent:** In the Test panel (right side), try:
1. "What are the NERC CIP-007 requirements for patch management?"
2. Upload `nerc-cip-007.txt` (from the `/docs` folder) and ask "What are the patch management requirements?"
3. "Who do I contact for a regulatory variance?"

---

## Executive Takeaway
What was just built: a virtual compliance expert that any TVA engineer can talk to in plain English. It reads the same documents your team uses, answers instantly, and cites exactly where the answer came from. This is what replaces 45-minute searches through SharePoint.
