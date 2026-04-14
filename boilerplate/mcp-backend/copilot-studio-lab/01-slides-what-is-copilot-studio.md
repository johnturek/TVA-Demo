# Part 1: What Is Microsoft Copilot Studio? (15 min)

---

## Slide 1 — Title

**Microsoft Copilot Studio**
*Build AI-Powered Agents — No Code Required*

Session 1 of 3: AI Agent Development Training Series

---

## Slide 2 — What Is Copilot Studio?

**Microsoft Copilot Studio** is a low-code platform for building AI-powered conversational agents (chatbots) that can:

- Answer questions using your organization's knowledge (SharePoint, websites, files)
- Automate multi-step business processes via topics and actions
- Connect to 1,000+ data sources through Power Platform connectors
- Leverage generative AI (GPT-based) to provide grounded, contextual answers

> **Key Point for the Audience:** Think of Copilot Studio as the *front door* for your AI — the place where users interact with intelligent automation.

---

## Slide 3 — Where Does It Fit?

```
┌─────────────────────────────────────────────────────┐
│                   User Interaction                    │
│              (Teams, Web, Custom Channels)            │
└──────────────────────┬──────────────────────────────┘
                       │
              ┌────────▼────────┐
              │  Copilot Studio │  ◄── You build here
              │   (GCC Mod)     │
              └────────┬────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐   ┌────▼────┐   ┌────▼─────┐
   │Knowledge│   │ Power   │   │AI Foundry│
   │ Sources │   │Platform │   │ (Azure   │
   │(SharePt,│   │Connectors│  │Commercial│
   │ Web)    │   │(Dataverse│  │  )       │
   └─────────┘   │ etc.)   │   └──────────┘
                  └─────────┘
```

---

## Slide 4 — Key Concepts

| Concept | What It Is | Example |
|---------|-----------|---------|
| **Agent** | A conversational AI bot | "IT Help Desk Agent" |
| **Topic** | A conversation flow triggered by user intent | "Password Reset" topic |
| **Trigger Phrases** | What the user says to activate a topic | "I forgot my password" |
| **Knowledge** | Data sources the agent searches for answers | SharePoint site, public URL |
| **Actions** | Integrations that do things (call APIs, update data) | Create a ServiceNow ticket |
| **Generative Answers** | AI-generated responses grounded in your knowledge | "Based on your HR policy..." |

---

## Slide 5 — Copilot Studio in GCC

### What's the Same
- Full agent-building experience (topics, knowledge, actions)
- Generative AI / GPT-powered answers
- Power Platform connector ecosystem
- Teams channel deployment

### GCC-Specific Considerations
- **Portal URL**: `gcc.powerva.microsoft.us` (not the commercial URL)
- **Data residency**: All conversation data stays in GCC boundary
- **AI processing**: Generative AI features use GCC-compliant endpoints
- **Cross-cloud**: Connecting to Azure Commercial (AI Foundry) requires explicit configuration
- **Feature parity**: Some features may arrive in GCC after commercial availability — check the [GCC release notes](https://learn.microsoft.com/en-us/microsoft-copilot-studio/requirements-licensing-gcc)

---

## Slide 6 — What Can You Build?

### Common Use Cases

1. **Employee Self-Service**
   - HR policy Q&A, benefits enrollment, onboarding guidance

2. **IT Help Desk**
   - Password resets, ticket creation, knowledge base search

3. **Field Operations**
   - Equipment manuals, safety procedures, compliance checklists

4. **Customer-Facing Support**
   - Product FAQ, order status, appointment scheduling

5. **Internal Productivity**
   - Meeting prep summaries, project status lookups, approval routing

> **Discussion Prompt:** *What repetitive questions or processes in your organization could an agent handle?*

---

## Slide 7 — Copilot Studio vs. AI Foundry — When to Use What

| Scenario | Use Copilot Studio | Use AI Foundry | Use Both |
|----------|-------------------|----------------|----------|
| Simple Q&A over documents | ✅ | | |
| Multi-step conversation with branching logic | ✅ | | |
| Custom ML model / fine-tuned LLM | | ✅ | |
| RAG with custom vector index | | ✅ | |
| Conversational UI + advanced AI backend | | | ✅ |
| Rapid prototype (hours, not days) | ✅ | | |
| Code-first agent with custom orchestration | | ✅ | |

> **Key Takeaway:** Copilot Studio is your *rapid, low-code path*. AI Foundry is your *code-first, advanced AI path*. Together, they cover the full spectrum.

---

*Next: Part 2 — Build Your First Agent (Hands-On Lab) →*
