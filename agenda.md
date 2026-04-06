# TVA Workshop: Microsoft Copilot Studio + Azure AI
## Master Agenda — April 15, 2026 | TVA HQ

**Total Duration:** 8 hours  
**Goal:** Every participant leaves with a **production-ready, Entra ID–secured, live Azure deployment** of the TVA Document Processor agent — not just a local demo, but a real URL they can hand to TVA stakeholders tomorrow

---

## Schedule at a Glance

| Time | Block | Format | Presenter |
|------|-------|--------|-----------|
| 8:00 – 8:30 | Arrival & Setup | Setup/Check-in | All |
| 8:30 – 9:00 | Kickoff & Executive Framing | Presentation | JT |
| 9:00 – 9:30 | Session 1 Intro: Azure AI Foundry | Presentation | Kevin |
| 9:30 – 11:00 | Lab 1: Azure AI Foundry Setup | Hands-On Lab | Kevin |
| 11:00 – 11:15 | Break | — | — |
| 11:15 – 11:45 | Session 2 Intro: Copilot Studio | Presentation | Aaron |
| 11:45 – 1:15 | Lab 2: Build the Document Processor Agent | Hands-On Lab | Aaron |
| 1:15 – 2:00 | Lunch | — | — |
| 2:00 – 2:30 | Session 3 Intro: APIM + MCP + Secure Auth | Presentation | JT |
| 2:30 – 4:00 | Lab 3: APIM Integration + MCP Server | Hands-On Lab | JT |
| 4:00 – 4:15 | Break | — | — |
| 4:15 – 4:45 | Demo Showcase & What You Built | Demo/Discussion | All |
| 4:45 – 5:00 | Closing: Next Steps & TVA Roadmap | Presentation | JT |

---

## Detailed Schedule

---

### 8:00 AM – 8:30 AM | Arrival & Environment Setup
**Format:** Self-service setup  
**Facilitator:** All presenters circulate

**Objectives:**
- Participants verify access to the demo tenant
- Azure portal and Copilot Studio portals open and authenticated
- Docker Desktop running (devs only)
- Pre-provisioned Azure AI Foundry project confirmed

**What facilitators are doing:**
- Confirming laptop connectivity to demo tenant
- Handing out quick-reference cards with tenant URLs, app registration IDs, and endpoint URLs
- Flagging GCC-tenant participants for Aaron's track notes

---

### 8:30 AM – 9:00 AM | Kickoff & Executive Framing
**Format:** Presentation  
**Presenter:** JT  
**Audience:** Everyone (exec + dev)

**Objectives:**
- Set the vision: what AI-assisted document processing means for TVA's mission
- Frame the day — what participants will build, why it matters
- Business case for Copilot Studio + Azure AI at TVA scale
- Address "why not just use SharePoint Copilot?" directly

**Key talking points:**
- TVA manages 49 dams, 3 nuclear plants, 11,000+ miles of transmission lines — and a compliance document mountain to match
- Today's agent will accept a regulatory or compliance document, extract key obligations, and flag potential issues — in seconds
- ROI framing: 30 min/doc × 500 docs/year × 50 engineers = 12,500 hours reclaimed
- Path from today's demo tenant to GCC production is real and documented

**Exec-specific segment (8:30–8:45):**
- Show the finished agent running (2-minute live demo of end state)
- Confirm exec buy-in questions: security, licensing, deployment path

**Dev-specific segment (8:45–9:00):**
- Architecture overview: Copilot Studio → Power Platform connector → APIM → Azure AI Foundry
- Auth model: OAuth OBO flow explained at 30,000 feet
- What boilerplate code is provided

---

### 9:00 AM – 9:30 AM | Session 1 Intro: Azure AI Foundry
**Format:** Presentation  
**Presenter:** Kevin  
**Audience:** Everyone

**Objectives:**
- Understand what Azure AI Foundry is and why it's the right backend for document RAG
- Understand the knowledge base / vector index architecture
- Know what gets deployed at the end of Lab 1

**Topics covered:**
- Azure AI Foundry vs Azure OpenAI Service vs Azure AI Search — when to use what
- Project structure: hub → project → deployments
- RAG architecture: chunk → embed → index → retrieve → augment → generate
- TVA use case: ingesting NERC reliability standards, NRC regulatory guides, TVA environmental compliance docs
- Model selection for this lab: GPT-4o (stable, available in demo tenant)
- What "deployment endpoint" means and how Copilot Studio will call it

---

### 9:30 AM – 11:00 AM | Lab 1: Azure AI Foundry Setup
**Format:** Hands-On Lab (90 min)  
**Presenter/Facilitator:** Kevin  
**See:** `lab1-azure-foundry.md`

**What participants build:**
- Azure AI Foundry project (pre-provisioned hub, participants create project)
- Knowledge base with 5 sample TVA regulatory documents
- GPT-4o deployment
- A working chat endpoint they can test via playground

**Milestones (time-boxed):**
- 0–20 min: Create project, confirm model deployments
- 20–45 min: Upload TVA documents, create vector index
- 45–75 min: Test RAG in Foundry playground
- 75–90 min: Copy endpoint URL + API key for Lab 2

**Exec track during lab:**
- Separate breakout (Kevin designates an exec host)
- Exec participants view pre-built version of Foundry project
- Kevin or JT walks through "how the knowledge base works" at business level
- Optional: Execs run 3 test prompts against the pre-built playground

---

### 11:00 AM – 11:15 AM | Break

---

### 11:15 AM – 11:45 AM | Session 2 Intro: Copilot Studio
**Format:** Presentation  
**Presenter:** Aaron  
**Audience:** Everyone

**Objectives:**
- Understand Copilot Studio's architecture: topics, actions, knowledge, triggers
- Know the difference between native knowledge vs custom connector vs generative actions
- Auth models: maker credentials vs end-user credentials (OBO)
- GCC vs commercial tenant differences (Aaron's specialty)

**Topics covered:**
- Copilot Studio agent anatomy
- Why we're NOT using native SharePoint knowledge for this use case (control, auth, structured output)
- Custom connector to call APIM → Azure AI Foundry
- OBO token flow: what it is, why TVA needs it, how to configure it without losing your mind
- Stable features only — what to avoid in the current release
- File upload capability: how to pass document content through the agent

---

### 11:45 AM – 1:15 PM | Lab 2: Build the TVA Document Processor Agent
**Format:** Hands-On Lab (90 min)  
**Presenter/Facilitator:** Aaron  
**See:** `lab2-copilot-studio.md`

**What participants build:**
- A new Copilot Studio agent: "TVA Document Processor"
- Topics: document upload intake, analysis trigger, result display
- Custom connector pointing to Lab 1 Azure AI Foundry endpoint
- Authentication configured (maker credentials for lab; OBO path documented)
- End-to-end test: upload a PDF excerpt → get structured analysis back

**Milestones:**
- 0–15 min: Create agent, configure basic settings
- 15–35 min: Build intake topic + file upload flow
- 35–60 min: Create custom connector to Foundry endpoint
- 60–80 min: Wire connector into agent action
- 80–90 min: End-to-end test + debug

**Exec track during lab:**
- Aaron or JT demo of the finished agent
- Discussion: "What documents at TVA would you run through this first?"
- Optional exec exercise: configure a test prompt on the pre-built agent

---

### 1:15 PM – 2:00 PM | Lunch
Catered lunch. Presenters available for informal Q&A.  
Encourage participants to leave the agent running — Lab 3 builds on it.

---

### 2:00 PM – 2:30 PM | Session 3 Intro: APIM + MCP + Secure Auth
**Format:** Presentation  
**Presenter:** JT  
**Audience:** Everyone

**Objectives:**
- Understand why APIM is the right gateway layer for enterprise AI integrations
- Understand what MCP (Model Context Protocol) is and when to use it
- Understand OBO token flow end-to-end
- Know when to use MCP vs agent actions vs sub-agent orchestration

**Topics covered:**
- APIM as the enterprise security layer: rate limiting, auth validation, backend abstraction
- MCP: what it is, why it matters for agent interoperability, TVA-specific use cases
- OBO token flow: Azure AD → Copilot Studio → APIM → backend service, all with the user's identity
- Agent SDK: deploying the same agent to multiple channels (Teams, web, M365 Copilot)
- Decision framework: MCP vs native actions vs sub-agents — when each wins
- Docker microservice: simulating TVA's backend compliance system

---

### 2:30 PM – 4:00 PM | Lab 3: APIM Integration + MCP Server
**Format:** Hands-On Lab (90 min)  
**Presenter/Facilitator:** JT  
**See:** `lab3-apim-mcp.md`

**What participants build:**
- APIM policy that validates OAuth tokens and proxies to Azure AI Foundry
- A running MCP server (Docker) with TVA regulatory document tooling
- Copilot Studio agent updated to call the APIM-protected endpoint
- OBO token flow configured and tested
- (Stretch) Agent published to Teams channel

**Milestones:**
- 0–20 min: Deploy Docker MCP server, confirm it's running
- 20–40 min: Configure APIM: create API, import backend, add JWT validation policy
- 40–65 min: Update Copilot Studio connector to use APIM endpoint + OAuth
- 65–80 min: Test OBO flow end-to-end
- 80–90 min: (Stretch) Publish agent to Teams

**Exec track during lab:**
- JT or Kevin: "What does secure AI integration look like in your current architecture?"
- Discussion: deployment paths, governance, who owns the agent
- Optional: live demonstration of the completed secure agent

---

### 4:00 PM – 4:15 PM | Break

---

### 4:15 PM – 4:45 PM | Demo Showcase & What You Built
**Format:** Demo + Discussion  
**Presenter:** All  
**Audience:** Everyone

**Structure:**
- 3–4 participant volunteers demo their running agents (5 min each)
- Presenters highlight what's notable in each build
- Open discussion: what surprised you, what would you extend

**Exec engagement:**
- Ask execs: "Which TVA use case would you prioritize deploying this for first?"
- Capture answers — these become the follow-up roadmap conversation

---

### 4:45 PM – 5:00 PM | Closing: Next Steps & TVA Roadmap
**Format:** Presentation  
**Presenter:** JT  
**Audience:** Everyone

**Content:**
- Path from demo tenant → GCC production (key steps, timeline estimate)
- Resources: Microsoft Learn paths, Copilot Studio docs, this workshop package repo
- What JT/Kevin/Aaron are available to help with post-workshop
- Next engagement options: deeper architecture review, production pilot, CoE setup
- Thank you + survey link

---

## Presenter Responsibilities Summary

| Presenter | Session | Lab | Other |
|-----------|---------|-----|-------|
| JT | Kickoff, Session 3 Intro, Closing | Lab 3 facilitator | Exec engagement throughout |
| Kevin | Session 1 Intro | Lab 1 facilitator | Exec track during Lab 1 |
| Aaron | Session 2 Intro | Lab 2 facilitator | GCC guidance throughout |

---

## Room Setup Requirements
- Projector / large display (dual screens preferred: presentation + live demo)
- Whiteboard for architecture diagrams
- Power strips at every table
- Wi-Fi: ensure Azure portal and Copilot Studio portal are not blocked
- Printed: Quick-reference cards with tenant URLs, credentials, endpoint URLs
- Catered lunch confirmed for ~[N] participants
