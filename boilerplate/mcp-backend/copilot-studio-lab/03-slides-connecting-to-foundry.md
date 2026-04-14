# Part 3: The GCC Escape Hatch — AI Foundry (20 min)

## The Problem: GCC Has Boundaries

You've now seen how powerful Copilot Studio is in GCC — knowledge, tools, child agents. But GCC has real constraints:

- **Model availability** — Not every AI model ships to GCC on day one
- **Feature lag** — Some Copilot Studio features arrive in GCC months after commercial
- **Advanced AI capabilities** — Fine-tuned models, custom RAG pipelines, and code-first agents aren't available natively in GCC Copilot Studio

## The Escape Hatch: Azure Commercial AI Foundry

When you hit a wall in GCC, you don't have to stop. You **reach out** to Azure Commercial through a controlled, auditable connection:

- **Custom models** (fine-tuned, domain-specific)
- **Advanced RAG** with custom vector indexes and retrieval pipelines
- **Multi-model orchestration** (routing to different models based on intent)
- **Code-first agents** with custom Python/C# logic
- **Evaluation and optimization** pipelines
- **Models not yet in GCC** — access GPT-4o, GPT-4.1, and other models immediately in Commercial

> 🔑 **Key Framing:** Copilot Studio in GCC is your **front door** — it handles user interaction, channels, and compliance. AI Foundry in Azure Commercial is the **back room** — where the heavy AI lifting happens when GCC's built-in capabilities aren't enough.

The combination gives you the best of both: **GCC compliance for the user experience** + **Azure Commercial's full AI catalog for the brains.**

---

## Architecture: GCC Copilot Studio + Azure Commercial AI Foundry

```
┌──────────────────────────────────────────────────────────────┐
│                    GCC (Moderate) Boundary                    │
│                                                              │
│  ┌──────────┐    ┌──────────────────┐                        │
│  │  User in  │───▶│  Copilot Studio  │                        │
│  │  Teams    │◀───│  Agent (GCC)     │                        │
│  └──────────┘    └────────┬─────────┘                        │
│                           │                                  │
│                           │ HTTP Action / Power Automate     │
│                           │ (outbound to Azure Commercial)   │
└───────────────────────────┼──────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │   Azure Comml.  │
                   │   ┌───────────┐ │
                   │   │AI Foundry │ │
                   │   │  Agent    │ │
                   │   │ Endpoint  │ │
                   │   └───────────┘ │
                   │   ┌───────────┐ │
                   │   │ Azure AI  │ │
                   │   │ Search    │ │
                   │   └───────────┘ │
                   │   ┌───────────┐ │
                   │   │  GPT-4o / │ │
                   │   │  Custom   │ │
                   │   │  Model    │ │
                   │   └───────────┘ │
                   └─────────────────┘
```

### How the Connection Works

1. **Copilot Studio** handles the user conversation (Teams, Web)
2. When advanced AI is needed, it calls an **HTTP action** (or Power Automate flow)
3. The HTTP action calls the **AI Foundry agent endpoint** in Azure Commercial
4. The Foundry agent processes the request (custom model, RAG, etc.)
5. The response flows back to Copilot Studio, which presents it to the user

---

## Slide: Cross-Cloud Considerations (GCC → Azure Commercial)

### What You Need

| Component | Cloud | Details |
|-----------|-------|---------|
| Copilot Studio agent | GCC Moderate | Built and published in `gcc.powerva.microsoft.us` |
| AI Foundry project | Azure Commercial | Hosts models, agents, evaluations |
| API endpoint | Azure Commercial | REST API exposed by the Foundry agent |
| Authentication | Cross-cloud | API key or Managed Identity with cross-tenant config |

### Security & Compliance Notes

- ⚠️ **Data flow awareness**: When Copilot Studio calls Azure Commercial, data leaves the GCC boundary for processing
- Ensure your **ATO (Authority to Operate)** covers this cross-cloud pattern
- Use **API keys** stored in Power Platform environment variables (not hardcoded)
- Consider a **Power Automate flow** as the intermediary for better logging and error handling
- All responses returned to Copilot Studio are displayed within the GCC boundary

---

## Demo: Connecting the Dots (Instructor-Led)

> This section is instructor-led. Attendees observe while the instructor demonstrates.

### Step 1: Show the AI Foundry Agent Endpoint

1. Open [Azure AI Foundry portal](https://ai.azure.com)
2. Navigate to an existing Foundry project
3. Show a deployed agent with its REST endpoint:
   ```
   POST https://<your-foundry-resource>.services.ai.azure.com/agents/v1.0/threads/{thread_id}/runs
   ```
4. Highlight the API key in the deployment settings

### Step 2: Create an HTTP Action in Copilot Studio

1. Back in Copilot Studio (GCC), open the agent
2. Go to **Actions** → **+ Add an action**
3. Choose **"HTTP request"** (or create via Power Automate)
4. Configure:

   | Field | Value |
   |-------|-------|
   | **Method** | POST |
   | **URL** | `https://<your-foundry-resource>.services.ai.azure.com/agents/v1.0/...` |
   | **Headers** | `api-key: <your-key>`, `Content-Type: application/json` |
   | **Body** | `{ "message": "{user_question}" }` |

5. Map the response back to a Copilot Studio variable
6. Display the result in a message node

### Step 3: Test the End-to-End Flow

1. In the test panel, ask a question that triggers the Foundry-connected topic
2. Show the response coming back from AI Foundry
3. Point out the latency difference (cross-cloud call adds ~1-3 seconds)

---

## Slide: Integration Patterns

### Pattern 1: Direct HTTP Action (Simple)
```
User → Copilot Studio → HTTP Action → AI Foundry → Response
```
- **Pros**: Simple, fast to set up
- **Cons**: Limited error handling, API key management in Copilot Studio

### Pattern 2: Power Automate Intermediary (Recommended)
```
User → Copilot Studio → Power Automate Flow → AI Foundry → Response
```
- **Pros**: Better error handling, logging, retry logic, secret management via Azure Key Vault connector
- **Cons**: Slightly more setup, additional latency

### Pattern 3: Azure API Management Gateway (Enterprise)
```
User → Copilot Studio → APIM (GCC) → AI Foundry → Response
```
- **Pros**: Rate limiting, caching, monitoring, policy enforcement
- **Cons**: Requires APIM infrastructure, more complex setup

> 💡 **Recommendation for GCC:** Start with Pattern 2 (Power Automate). It gives you the best balance of control, security, and simplicity.

---

## Slide: When to Use What — Decision Framework

```
                    ┌─────────────────────┐
                    │ Do you need custom   │
                    │ models or advanced   │
                    │ RAG?                 │
                    └──────┬──────────────┘
                           │
                    ┌──────▼──────┐
                    │     No      │──────▶ Use Copilot Studio alone
                    └──────┬──────┘        (built-in generative AI)
                           │ Yes
                    ┌──────▼──────────────┐
                    │ Do users need a      │
                    │ conversational UI    │
                    │ (Teams, Web)?        │
                    └──────┬──────────────┘
                           │
                    ┌──────▼──────┐
                    │     No      │──────▶ Use AI Foundry alone
                    └──────┬──────┘        (API / playground)
                           │ Yes
                    ┌──────▼──────────────┐
                    │ Use BOTH:            │
                    │ Copilot Studio (UI)  │
                    │ + AI Foundry (brain) │
                    └─────────────────────┘
```

---

*Next: Wrap-Up & Next Steps →*
