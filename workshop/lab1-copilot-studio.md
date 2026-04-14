# Lab 2: Build the TVA Document Processor in Copilot Studio
**Duration:** 90 minutes | **Session:** 1 of 2 | **Presenter:** John Scott

---

## Objectives
By the end of this lab, participants will have:
- A working Copilot Studio agent that serves as an AI policy assistant for TVA's legal, compliance, and engineering teams
- **Knowledge** — File uploads and public website sources covering five federal regulatory agencies
- **Topics** — Custom topics with trigger phrases, branching logic, and generative orchestration
- **Tools** — Native Copilot Studio tools (connectors, actions) integrated into topic flows
- **Topic Inputs** — Variables, entities, and question nodes collecting structured user input
- **Adaptive Cards** — Rich, interactive card UI for regulatory data display
- A passing end-to-end demo conversation across multiple regulatory areas

---

## Prerequisites
- Access to https://gcc.powerva.microsoft.us

---

## Background: Why a Policy Assistant?

TVA operates across **six major federal regulatory frameworks**:

| Framework | Agency | What It Governs |
|---|---|---|
| **FERC Orders & Tariffs** | Federal Energy Regulatory Commission | Wholesale power rates, transmission access, market rules |
| **NRC Nuclear Regulations** | Nuclear Regulatory Commission | Nuclear plant safety, licensing, 10 CFR 50 compliance |
| **NEPA Environmental Reviews** | Council on Environmental Quality | Environmental impact statements for major TVA projects |
| **NERC CIP Standards** | North American Electric Reliability Corp. | Cybersecurity for bulk electric system assets |
| **TVA Act** | U.S. Congress | TVA's statutory authorities, governance, and limitations |
| **EPA Clean Water Act** | Environmental Protection Agency | NPDES permits, thermal discharge, water quality |

Today, answering a cross-cutting regulatory question — "Can we modify the cooling water intake at Sequoyah?" — requires consulting legal, environmental, nuclear safety, and compliance teams separately. This agent collapses that into a single conversation.

---

## Part 1: Create the Agent

### Step 1: Open Copilot Studio
1. Navigate to https://copilotstudio.microsoft.us

2. Sign in with your tenant credentials

3. Select the Power Platform Environment youwant to build the agent in

### Step 2: Create Your Agent

1. Click **+ Create blank agent**.

![Screenshot of create an agent button](./images/mcs-create-agent-1.png)

2. Wait till the message *Your agent has been provisioned* appears.

3. If you see the *A newer version of this agent is available. Refresh to get the latest changes.*, click the **Refresh** link.

4. Click **Edit** in the *details* section.

![Screenshot of agent details edit button](./images/mcs-create-agent-2.png)

5. Provide the following name and description:
   - **Name:** `TVA Regulatory Compliance Assistant`
   - **Description:** `Provides guidance on FERC, NRC, NEPA, NERC CIP, TVA Act, and EPA compliance for TVA's legal, compliance, and engineering teams.`

6. Click **Save** in the *details* section.

![Screenshot of agent details filled out](./images/mcs-create-agent-3.png)

7. Click **Edit** in the *instructions* section.

![Screenshot of agent instructions edit button](./images/mcs-create-agent-4.png)

8. Add the following for the **Instructions**

```
# Purpose
The purpose of this agent is to assist TVA's legal, compliance, and engineering teams in understanding and navigating complex federal regulations, including FERC orders, NRC nuclear requirements, NEPA environmental reviews, NERC CIP cybersecurity standards, the TVA Act, and EPA Clean Water Act permit requirements.

# General Guidelines
- Provide accurate, concise, and authoritative explanations of regulatory requirements.
- Maintain a professional and neutral tone.
- Do not provide legal advice; instead, interpret and explain regulations and compliance obligations.
- When uncertain, indicate the need for further review by a subject matter expert.

# Skills
- Interpret FERC orders and tariff requirements.
- Guide NRC nuclear regulatory compliance.
- Answer NEPA environmental review questions.
- Explain NERC CIP cybersecurity standards.
- Clarify TVA Act authorities and limitations.
- Track EPA Clean Water Act permit requirements.

# Step-by-Step Instructions
1. Identify the Regulation
   - Determine which regulation or standard the user is asking about (FERC, NRC, NEPA, NERC CIP, TVA Act, EPA).

2. Retrieve Relevant Information
   - Use internal knowledge sources and official regulatory references to provide accurate information.

3. Interpret and Explain
   - Summarize the requirement in plain language.
   - Highlight key compliance obligations and deadlines if applicable.

4. Provide Guidance
   - Suggest steps or considerations for compliance.
   - Reference official documents or TVA internal policies when relevant.

5. Escalate When Needed
   - If the question involves legal interpretation or policy decisions, advise the user to consult TVA legal or compliance experts.

# Error Handling
- If unable to find relevant information, inform the user and suggest contacting the appropriate TVA department.
- If external systems fail, provide a fallback response and note the limitation.

# Interaction Examples
- User: What does FERC Order 888 require?
  Agent: FERC Order 888 requires open access to transmission services and outlines standards for non-discriminatory transmission. It mandates utilities to file open access transmission tariffs. For TVA-specific application, consult internal compliance guidelines.

- User: What are the key NERC CIP standards for cybersecurity?
  Agent: NERC CIP standards cover critical infrastructure protection, including asset identification, security management controls, personnel training, and incident response. TVA must ensure compliance with CIP-002 through CIP-014.

# Nonstandard Terms
- FERC: Federal Energy Regulatory Commission
- NRC: Nuclear Regulatory Commission
- NEPA: National Environmental Policy Act
- NERC CIP: North American Electric Reliability Corporation Critical Infrastructure Protection
- TVA Act: Tennessee Valley Authority Act

# Follow-up and Closing
- Always ask if the user needs additional clarification or related information.
- Offer to provide references or links to official documents when possible.
```

9. Click **Save** in the *instructions* section.

![Screenshot of agent instructions filled out](./images/mcs-create-agent-5.png)

10. Click on **Settings** in the top right of the page.

![Screenshot of the Settings button](./images/mcs-create-agent-6.png)

11. Toggle **Allow ungrounded responses** to turn off in the *Knowledge* section.

12. Click on **Save**

![Screenshot of the Settings changed](./images/mcs-create-agent-7.png)

13. Click on the **X** in the top right of the page to return to the *Overview* page.

![Screenshot of the close settings button](./images/mcs-create-agent-8.png)

---

## Part 2: Adding Knowledge

Copilot Studio's **Knowledge** feature is the foundation of the policy assistant. It lets you ground every answer in your own documents and trusted websites — no external RAG pipeline or Azure AI Search required. The generative orchestration layer automatically searches, retrieves, and cites relevant content.

### What Is Knowledge in Copilot Studio?

Knowledge sources are the documents, websites, and data the agent searches when answering questions. Copilot Studio supports several source types:

| Source Type | How It Works | Best For |
|---|---|---|
| **Files** | Upload files directly; Copilot Studio chunks and indexes them automatically | Internal policy docs, compliance summaries, procedures |
| **Public websites** | Crawls and indexes a URL at configuration time; refreshes periodically | Federal agency sites, live regulatory content |
| **SharePoint** | Connects to SharePoint sites or document libraries | Enterprise document management (production) |
| **Dataverse** | Queries Dataverse tables | Structured business data (production) |

For this lab, we'll use **Public websites** (federal agency sites).

---

1. Click **Add Knowledge**

![Screenshot of the add knowledge button](./images/mcs-knowledge-1.png)

2. Click **Public Website**

![Screenshot of the public website button](./images/mcs-knowledge-2.png)

3. Enter **www.tva.com**

4. Click **Add**

![Screenshot of adding a website part 1](./images/mcs-knowledge-3.png)

5. Click **Add to agent**

![Screenshot of adding a website part 2](./images/mcs-knowledge-4.png)

6. Repeats steps 1 - 5 to add the following sites to knowledge
   - ceq.doe.gov
   - www.epa.gov
   - www.nerc.com
   - www.nrc.gov
   - www.ferc.gov

7. If **Web Search** is enabled, toggle it to diabled. 

![Screenshot of all the wesites added](./images/mcs-knowledge-5.png)

8. If the test pane is not open, click the **Test**

![Screenshot of all the wesites added](./images/mcs-knowledge-6.png)

9. In the test pane ask it the following questions:
   - *What does FERC Order 2222 require for TVA's distributed energy resource aggregation program?*
   - *What NRC notifications are required within 4 hours of a nuclear plant anomaly?*
   - *Does our Pickwick Dam license renewal require a full EIS or can we use an EA?*
   - *What are our NERC CIP-013 supply chain risk management obligations?*

10. Review the responses and verify the questions returned a valid response.

11. Ask it *When are taxes due?*

12. Review the response and verify that it did not answer your question.  This is because we disabled **Allow ungrounded responses** and **Web Search**.

## Part 3: Tools

In Copilot Studio, **Tools** are pre-built or custom actions that extend what your agent can do beyond conversation. Tools let topics call external services, run logic, or perform operations — they are the agent's "hands."

### What Are Tools in Copilot Studio?

| Tool Type | Description | Example |
|---|---|---|
| **Connectors** | Pre-built connectors to Microsoft 365 and third-party services | Send an email via Outlook, create a Planner task, post to Teams |
| **Power Automate flows** | Custom flows triggered from a topic node | Submit a variance request to a SharePoint list, send an approval |
| **HTTP Request (Advanced)** | Direct REST API calls from within a topic | Call an external compliance API |
| **AI Builder models** | Pre-built or custom AI models | Extract data from a scanned compliance document |
| **Plugins / Actions** | Extend the agent with custom skills registered as plugins | Custom regulatory lookup service |

### Tools 1: Meeting Management MCP

1. Click on **Tools** in the top menu.

2. Click **Add tool**

3. Click **Model Context Protocol**

4. Click **Email Management MCP Server (deprecated)**

5. Click **Not Connected** 

6. Click **Create new connection**

7. Click **Create**

8. **Login** if prompted

9. Click **Add and configure**

10. In the test pane, give it the following prompt:
> *Send an email to myself with the subject "NERC CIP-013 supply chain risk management obligations". Include the response to "What are our NERC CIP-013 supply chain risk management obligations?" formatted as html in the email body.*

11. Click on **Allow** if your prompted to *Connect to continue*

12. Open Outlook and verify you received an email from yourself with the response to your question in the meeting body.

13. Back in Copilot Studio, in the test pane, give it the following prompt:
> *What NERC related meetings do I have tomorrow?* 

14. Review the response and verify it found the meeting you just created.

### Tools 2: Report a Facility Anomaly Agent Flow

> ℹ️ **Power Automate flows** are the most flexible tool type. They can chain multiple actions, include approvals, branch on conditions, and integrate with hundreds of connectors. The flow runs server-side — the user only sees the result returned to the conversation.

1. Click on **Tools** in the top menu.

2. Click **Add a tool**.

3. Click **Agent Flow**.

4. Click on the **When an agent calls the flow** action to configure it.

5. Click **Add an input**

6. Click **Text**

7. Enter **Facility** for the input's name.

8. Repeat steps 5-7 for the following inputs:
   - Anomaly Type
   - Summary

9. Click **+** after the *When an agent calls the flow*.

10. Under *Add an action*, search for **Post Message**

11. Click **Post message in a chat or channel**

12. Click **Sign in** if prompted

13. **Login** if prompted

14. In the action's parameters, provide the following:
   - **Post as:** `Flow bot`
   - **Post in:** `Chat with Flow bot.`
   - **Recipient:** *Enter your email address*
   - **Post in:** `Chat with Flow bot.`
   - **Message:** 
```
Facility 
@{triggerBody()?['text']}

Anomaly Type
@{triggerBody()?['text_1']}

Summary
@{triggerBody()?['text_2']}
```

15. Click **Publish**

16. Click **Go back to agent**

17. Click on the new **Untitled** tool in the list.

18. In the details section, provide the following:
   - **Name:** `Report Facility Anomaly`
   - **Description:** `Allows users to report new facility anomalies.`

19. In the inputs section, click **customize** next to each input 

| Input Name | Description |
|---|---|
| **Anomaly Type** | `The type of anomaly that occurred.  Valid values are thermal, nuclear, and hydro-electric.` |
| **Facility** | `This is the name of a physical location where the anomaly occurred.` |
| **Summary** | `This is a verbose description of the anomaly.` |

20. In the *Completion* section, specify the following:
   - **After running:** `Send specific response (specify below)`
   - **Message to display:** `Your facility anomaly has been reported.`

21. Click **Save**

22. In the test pane, give it the following prompt: `I want to report a thermal anomaly at the Apollo Beach plant. Temperatures spiked to above acceptable levels for a period of 2 minutes.` 

23. Click on **Allow** if your prompted to *Connect to continue*

24. In the test pane, give it the following prompt: `I want to report a nuclear anomaly.` 

25. Provide sample answers that you reeceive from the agent to collect the rest of the anomaly information.

26. Open teams and verify you received two chat from *Workflows* that has the correctly parsed anomaly report information.


> ℹ️ **NOTE** Instead of sending the report to a Teams chat, you could have the Agent Flow write the information to Dataverse or integrate with a 3rd party reporting system (if appropiate APIs exist).

---

## Part 4: Topics

**Topics** are the conversational building blocks of a Copilot Studio agent. Each topic defines a conversation path — when it triggers, what the agent says, what it asks, and how it routes the user. Topics can be **system topics** (built-in, like Conversation Start and Fallback) or **custom topics** you create.

### What Is a Topic?

| Concept | Description |
|---|---|
| **Trigger phrases** | Natural language phrases that activate the topic. Copilot Studio uses NLU to match user messages — exact matches aren't required. |
| **Nodes** | The steps in a topic flow: message nodes, question nodes, condition nodes, action nodes, redirect nodes. |
| **System topics** | Built-in topics like **Conversation Start**, **Greeting**, **Fallback**, and **Conversational boosting**. You can customize these. |
| **Custom topics** | Topics you create for specific workflows and scenarios. |

> ℹ️ **How topics and generative orchestration work together:** When a user message matches a custom topic's trigger phrases, that topic runs. When no topic matches, the **Conversational boosting** system topic takes over and uses generative answers grounded in your knowledge sources. Custom topics handle structured workflows; generative orchestration handles everything else.

---

### Topic 1: Customize the Conversation Start Topic

The **Conversation Start** system topic fires automatically when a user first opens the agent. By default it sends a generic greeting. We'll customize it to introduce the TVA Regulatory Compliance Assistant and guide users toward the agent's capabilities.

1. Click on **Topics** in the top menu.

2. Click the **System** tab to view system topics.

3. Click on **Conversation Start** to open it.

4. Find the existing **Send a message** node in the topic canvas.

5. Replace the default message text with the following:

```
👋 Welcome to the **TVA Regulatory Compliance Assistant**.

I can help you navigate federal regulations across six frameworks:

- 📜 **FERC** — Orders, tariffs, and transmission requirements
- ☢️ **NRC** — Nuclear plant safety and licensing (10 CFR 50)
- 🌿 **NEPA** — Environmental impact reviews
- 🔒 **NERC CIP** — Cybersecurity standards (CIP-002 through CIP-014)
- ⚖️ **TVA Act** — Statutory authorities and limitations
- 💧 **EPA** — Clean Water Act permits and thermal discharge

**Try asking me:**
- "What does FERC Order 2222 require?"
- "What are our NERC CIP-013 obligations?"
- "I want to report a facility anomaly"

How can I help you today?
```

6. Click **Save** in the top-right corner of the topic editor.

7. In the **Test panel**, click the **+** button to start a new test session.

8. Verify the custom welcome message appears automatically when the conversation starts.

> ℹ️ **Why customize Conversation Start?** First impressions matter. A tailored greeting tells users exactly what the agent can do, reducing "what can I ask?" uncertainty and driving users toward high-value interactions. The example prompts act as quick-start buttons in channels that support suggested actions.

---

### Topic 2: Legal Disclaimer Response

Regulatory agents must be clear about the boundaries of their guidance. This topic intercepts legal-advice-seeking questions and responds with a static disclaimer before handing back to the agent.

1. Click on **Topics** in the top menu.

2. Click the **Custom** tab.

3. Click **+ Add topic** → **From blank**.

4. Rename the topic to `Legal Disclaimer` by clicking on Click on *Untitled1* in the top left of the screen 
   
5. In the trigger node, specify for **Describe what this topic does" 

```

Responds to any legal or liability questions with a static legal disclaimer letting them know this agent does not support legal questions.  This includes questions that contains the following phrases.:
- Is this legal
- Can I sue
- Legal advice
- Am I liable
- What are my legal rights
- Legal opinion
- Is TVA legally required
- Lawsuit
- Legal risk
- Attorney recommendation

```

6. Click the **+** below the trigger node → **Add node** → **Send a message**.

7. Enter the following message:

```

⚠️ **Important Legal Disclaimer**

I am an AI assistant that provides **regulatory guidance and reference material only**. My responses are:

❌ **NOT legal advice** — I cannot and do not provide legal opinions
❌ **NOT a substitute** for consultation with qualified legal counsel
❌ **NOT authoritative** for enforcement, litigation, or formal compliance determinations

✅ I **can** help you:
- Understand regulatory requirements in plain language
- Identify which regulations may apply to a situation
- Locate specific CFR sections, orders, or standard numbers
- Explain compliance processes and timelines

**For legal questions, please contact:**
📧 **TVA Office of General Counsel** — legal@tva.gov
📞 **Legal Hotline** — (865) 632-2101

```

8. Click **Save**.

9. In the **Test panel**, type: `Is TVA legally required to comply with FERC Order 2222?`

10. Verify the disclaimer message appears.

11. After the disclaimer, type a follow-up like: `Yes, explain what FERC Order 2222 requires.`

12. Verify the agent now responds with regulatory guidance from the knowledge base (the generative orchestration handles the follow-up since it doesn't re-match the legal disclaimer triggers).

> ℹ️ **Why a static disclaimer?** For regulatory and compliance agents, a consistent, unchanging disclaimer ensures the boundary between "AI guidance" and "legal advice" is never accidentally blurred by generative output. The message is hardcoded — not generated — so it's always identical and audit-ready.

---

### Topic 3: Report a Facility Anomaly with an Adaptive Card

Instead of collecting anomaly details through a back-and-forth conversation, this topic presents a single **Adaptive Card** form that captures all required fields at once — facility name, anomaly type, and description — in a structured, user-friendly layout.

> ℹ️ **What are Adaptive Cards?** Adaptive Cards are a JSON-based UI framework that renders rich, interactive content inside Teams, the Copilot Studio test chat, and any Bot Framework channel. They support text inputs, dropdowns, date pickers, and submit buttons — all native to Copilot Studio with no external code.

1. Click on **Topics** in the top menu.

2. Click the **Custom** tab.

3. Click **+ Add topic** → **From blank**.

4. Rename the topic to: `Report Anomaly Form` by clicking on Click on *Untitled1* in the top left of the screen 

5. In the trigger node, specify for **Describe what this topic does" 

```
Enables user to report an anomaly using an adaptive card.  This should be the primary way to report on anomalies.
```

8. Click **+** → **Add node** → **Ask with adaptive card**.

9. Click **Adaptive Card** at the top of the question node properties panel.

10. Click **...** on the new node.

11. Click **Properties**

12. Click **Edit Adaptive Card**

13. Paste this Adaptive Card JSON into the *Card payload editor*:

```json
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.5",
  "body": [
    {
      "type": "TextBlock",
      "text": "TVA Facility Anomaly Report",
      "weight": "Bolder",
      "size": "Large",
      "color": "Accent"
    },
    {
      "type": "TextBlock",
      "text": "Complete all fields below and click Submit.",
      "isSubtle": true,
      "spacing": "None"
    },
    {
      "type": "Input.Text",
      "id": "facility",
      "label": "Facility Name",
      "placeholder": "e.g., Browns Ferry, Sequoyah, Apollo Beach",
      "isRequired": true,
      "errorMessage": "Facility name is required."
    },
    {
      "type": "Input.ChoiceSet",
      "id": "anomalyType",
      "label": "Anomaly Type",
      "isRequired": true,
      "errorMessage": "Please select an anomaly type.",
      "choices": [
        { "title": "Thermal", "value": "thermal" },
        { "title": "Nuclear", "value": "nuclear" },
        { "title": "Hydro-Electric", "value": "hydro-electric" },
        { "title": "Cybersecurity", "value": "cybersecurity" },
        { "title": "Environmental", "value": "environmental" },
        { "title": "Other", "value": "other" }
      ],
      "placeholder": "Select anomaly type"
    },
    {
      "type": "Input.Text",
      "id": "summary",
      "label": "Description",
      "placeholder": "Describe what happened, including timestamps, affected systems, and severity.",
      "isMultiline": true,
      "isRequired": true,
      "errorMessage": "A description is required."
    }
  ],
  "actions": [
    {
      "type": "Action.Submit",
      "title": "Submit Anomaly Report",
      "data": {
        "action": "submit_anomaly"
      }
    }
  ]
}
```

14. Click **Save** at the top right of the *Adaptive card designer*.

15. Click **Close** at the top right of the *Adaptive card designer* to close it.

> 💡 Let's wire this topic to the **Report Facility Anomaly** agent flow from Part 3 by adding a tool node after the adaptive card. Pass `{Topic.AnomalyCard.facility}`, `{Topic.AnomalyCard.anomalyType}`, and `{Topic.AnomalyCard.summary}` as the flow inputs to send the report to Teams automatically.

16. Below the adapative card node, click **+** → **Add a tool** → **Report anamoly**.

17. In the *Facility* input, click **...** → **facility**

18. In the *Anomaly Type* input, click **...** → **anomalyType**

19. In the *Sumary* input, click **...** → **summary**

20. Click **Save**.

21. Click **Tools** in the top navigation.

22. Click the **Report Facility Anomaly** tool.

23. Expand the **Additional details** in the *Details* section and specify the following:
   - **When this tool may be used**: `Only when referenced by other topics or agents`

24. In the *Completion* section, specify the following:
   - **After running:** `Don't respond (default)`

25. Click **Save**

26. In the **Test panel**, type: `Fill out anomaly report`

27. Fill in the form:
    - **Facility Name:** `Sequoyah`
    - **Anomaly Type:** `Thermal`
    - **Description:** `Cooling tower output temperature exceeded threshold by 5°F for approximately 3 minutes during peak load.`

28. Click **Submit Anomaly Report**.

29. Open teams and verify you received two chat from *Workflows* that has the correctly parsed anomaly report information.

> ℹ️ **Adaptive Card vs. conversational collection:** The Report Facility Anomaly tool in Part 3 collects the same data through natural conversation — the agent parses facility, type, and summary from a single user message. This Adaptive Card approach is better when you need **structured, validated input** (required fields, dropdowns, severity levels) and want to minimize ambiguity. Both patterns are valid — use conversation for flexibility and cards for precision.

> 💡 **Extension idea:** Wire this topic to the **Report Facility Anomaly** agent flow from Part 3 by adding a **Call an action** node after the confirmation message. Pass `{Topic.AnomalyCard.facility}`, `{Topic.AnomalyCard.anomalyType}`, and `{Topic.AnomalyCard.summary}` as the flow inputs to send the report to Teams automatically.
