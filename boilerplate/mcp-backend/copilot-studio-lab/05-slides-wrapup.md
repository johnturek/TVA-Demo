# Part 4: Wrap-Up & Next Steps (5 min)

---

## Slide: What We Covered Today

| Section | Key Takeaway |
|---------|-------------|
| **What Is Copilot Studio?** | A low-code platform for building AI-powered conversational agents, available in GCC |
| **Build Your First Agent** | You can go from zero to a working AI agent in under 30 minutes |
| **Connecting to AI Foundry** | Copilot Studio (GCC) can call Azure Commercial AI Foundry for advanced AI capabilities |

---

## Slide: Key Takeaways

1. **Copilot Studio is the user interface layer** — it handles conversations, channels (Teams, Web), and basic AI
2. **Knowledge sources + generative answers** = instant Q&A without writing code
3. **Topics** give you precise control when you need structured conversation flows
4. **AI Foundry extends Copilot Studio** when you need custom models, advanced RAG, or code-first agents
5. **GCC works** — the platform is available in GCC Moderate with some considerations for cross-cloud connectivity

---

## Slide: What's Coming Next

### Session 2: Build the TVA Document Processor (Copilot Studio)
- Build a TVA Regulatory Compliance Assistant from scratch
- Deep dive into Knowledge — 6 federal agency website sources
- Tools — MCP connectors and Power Automate Agent Flows
- Topics — System topic customization, custom triggers, Adaptive Cards
- End-to-end anomaly reporting workflow

### Session 3: Microsoft AI Foundry
- Deep dive into Azure AI Foundry in Azure Commercial
- Deploying models (GPT-4o, custom fine-tuned models)
- Building Foundry agents with code
- Evaluation pipelines and prompt optimization
- How Foundry agents serve as the "brain" behind Copilot Studio

### Session 4: AI Use Case Development
- Hands-on ideation workshop
- Identifying high-value AI use cases in your organization
- Rapid prototyping with GitHub Copilot
- From idea → working prototype in one session

---

## Slide: Resources

### Copilot Studio
| Resource | Link |
|----------|------|
| GCC Portal | [gcc.powerva.microsoft.us](https://gcc.powerva.microsoft.us) |
| Documentation | [learn.microsoft.com/microsoft-copilot-studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/) |
| GCC Licensing & Requirements | [GCC Requirements](https://learn.microsoft.com/en-us/microsoft-copilot-studio/requirements-licensing-gcc) |
| What's New | [Release Notes](https://learn.microsoft.com/en-us/microsoft-copilot-studio/fundamentals-whats-new) |

### AI Foundry
| Resource | Link |
|----------|------|
| Azure AI Foundry Portal | [ai.azure.com](https://ai.azure.com) |
| Documentation | [learn.microsoft.com/azure/ai-studio](https://learn.microsoft.com/en-us/azure/ai-studio/) |

### GitHub Copilot
| Resource | Link |
|----------|------|
| GitHub Copilot | [github.com/features/copilot](https://github.com/features/copilot) |

---

## Slide: Homework (Optional)

Before Session 2, try these on your own:

1. **Build an agent** for a real use case in your team (even a small one!)
2. **Add 2-3 knowledge sources** (SharePoint sites, documentation URLs)
3. **Create a custom topic** with at least one question node (ask the user for input)
4. **Share the agent** with a colleague via Teams and get their feedback
5. **Write down 3 questions** you encountered — bring them to Session 2

---

## Q&A

*Open the floor for questions.*

**Common questions to be prepared for:**

- *"How is data handled in GCC?"* → All conversation data stays in GCC. Cross-cloud calls to Foundry send only the specific query, not full conversation history.
- *"Can we use this with external users?"* → Yes, via the Web channel or custom Direct Line integration.
- *"What's the cost?"* → Copilot Studio is licensed per-tenant. Check with your Microsoft account team for GCC-specific pricing.
- *"How long until features from commercial reach GCC?"* → Typically 2-6 months, but varies. Check the GCC release notes.

---

*Thank you! See you at Session 2: Build the TVA Document Processor →*
