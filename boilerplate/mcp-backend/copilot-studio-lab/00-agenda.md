# Microsoft Copilot Studio Training

---

## Session 1: Introduction to Copilot Studio (90 Minutes)

| Time | Section | Type | Description |
|------|---------|------|-------------|
| 0:00 – 0:15 | **What Is Copilot Studio?** | Presentation | Key concepts, architecture, GCC landscape |
| 0:15 – 0:35 | **Build Your First Agent** | Hands-On Lab | Create, configure, and test a basic agent |
| 0:35 – 1:00 | **The Three Pillars: Knowledge, Tools & Agents** | Slides + Hands-On | Deep dive into knowledge sources, tools/actions, and child/connected agents |
| 1:00 – 1:20 | **The GCC Escape Hatch: AI Foundry** | Presentation + Demo | When GCC isn't enough — reach into Azure Commercial AI Foundry |
| 1:20 – 1:30 | **Wrap-Up & Next Steps** | Discussion | Q&A, preview of Session 2 |

### Learning Objectives — Session 1

1. Explain what Microsoft Copilot Studio is and how it fits into the Microsoft AI stack
2. Navigate the Copilot Studio portal in GCC and identify key components (agents, topics, knowledge, actions)
3. Build a simple agent with trigger phrases, topics, and a knowledge source
4. Configure multiple knowledge source types (websites, SharePoint, files) and understand how grounding works
5. Add tools (actions) to an agent — connector actions, Power Automate flows, and HTTP requests
6. Understand the child agent / connected agent pattern for modular, multi-agent architectures
7. Understand how Copilot Studio agents in GCC can connect to Azure Commercial AI Foundry for advanced AI capabilities
8. Identify when to use Copilot Studio alone vs. when to extend with AI Foundry

---

## Session 2: Build the TVA Document Processor (90 Minutes)

| Time | Section | Type | Description |
|------|---------|------|-------------|
| 0:00 – 0:05 | **Introduction & Background** | Presentation | Why a regulatory policy assistant? Six federal frameworks |
| 0:05 – 0:15 | **Create the Agent** | Hands-On Lab | Build and configure the TVA Regulatory Compliance Assistant |
| 0:15 – 0:30 | **Knowledge: Federal Regulatory Sources** | Hands-On Lab | Add 6 public website knowledge sources (FERC, NRC, NEPA, NERC, TVA, EPA) |
| 0:30 – 0:55 | **Tools: MCP & Agent Flows** | Hands-On Lab | Connect MCP email tool + build a Power Automate anomaly reporting flow |
| 0:55 – 1:20 | **Topics: Conversation Start, Legal Disclaimer & Adaptive Cards** | Hands-On Lab | Customize system topics, create custom topics, build an Adaptive Card form |
| 1:20 – 1:30 | **Wrap-Up & Demo** | Discussion | End-to-end demo conversation, Q&A |

### Learning Objectives — Session 2

1. Build a domain-specific Copilot Studio agent grounded in real federal regulatory content
2. Configure multiple public website knowledge sources and test grounded answers
3. Disable ungrounded responses and web search to enforce compliance guardrails
4. Integrate MCP connectors as agent tools for email workflows
5. Build a Power Automate Agent Flow triggered from conversation to report anomalies to Teams
6. Customize the Conversation Start system topic for a tailored first impression
7. Create custom topics with trigger phrases and static responses (legal disclaimer pattern)
8. Use Adaptive Cards to collect structured, validated input within a conversation
9. Wire Adaptive Card output to an Agent Flow for end-to-end automation

### Presenter

John Scott

---

## Prerequisites (Both Sessions)

- Microsoft 365 GCC account with Copilot Studio license
- Access to [https://gcc.powerva.microsoft.us](https://gcc.powerva.microsoft.us)
- Azure Commercial subscription (for Foundry demo — instructor-led)
