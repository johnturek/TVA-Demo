# Part 2b: The Three Pillars — Knowledge, Tools & Agents (Slides)

Every Copilot Studio agent is built on three foundational pillars. Understanding these is the key to building agents that are genuinely useful.

---

## Slide 1 — The Three Pillars

```
                    ┌─────────────────┐
                    │   Your Agent    │
                    │  (Copilot Studio)│
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
     ┌──────▼──────┐  ┌─────▼──────┐  ┌──────▼──────┐
     │  KNOWLEDGE  │  │   TOOLS    │  │   AGENTS   │
     │             │  │ (Actions)  │  │  (Child /  │
     │ What the    │  │            │  │ Connected) │
     │ agent KNOWS │  │ What the   │  │            │
     │             │  │ agent DOES │  │ Who the    │
     │             │  │            │  │ agent ASKS │
     └─────────────┘  └────────────┘  └────────────┘
```

| Pillar | Purpose | Example |
|--------|---------|---------|
| **Knowledge** | Gives the agent information to answer questions | SharePoint site, public URL, uploaded files |
| **Tools (Actions)** | Lets the agent take actions in external systems | Create a ticket, send an email, look up a record |
| **Child/Connected Agents** | Delegates specialized tasks to other agents | "Ask the HR Agent" or "Route to the IT Agent" |

---

## Slide 2 — Pillar 1: Knowledge

### What Is Knowledge?

Knowledge sources are the **data** your agent searches to generate grounded answers. The AI reads and indexes your content, then uses it to answer user questions with citations.

### Knowledge Source Types

| Type | What It Is | Best For | GCC Available? |
|------|-----------|----------|----------------|
| **Public websites** | URLs the agent crawls and indexes | Public documentation, external FAQs | ✅ Yes |
| **SharePoint** | SharePoint Online sites and document libraries | Internal policies, procedures, org content | ✅ Yes |
| **Uploaded files** | PDF, Word, Excel, etc. uploaded directly | Manuals, guides, reference docs | ✅ Yes |
| **Dataverse** | Structured data in Dataverse tables | CRM records, case history, product catalogs | ✅ Yes |
| **Microsoft Graph** | Content from M365 (emails, Teams, OneDrive) | Personalized, user-specific answers | ⚠️ Check availability |

### How Knowledge Works Under the Hood

```
User asks: "What's our PTO policy?"
         │
         ▼
┌─────────────────┐
│  AI Orchestrator │ ── Searches all knowledge sources
└────────┬────────┘
         │
    ┌────▼─────┐     ┌──────────────┐
    │ Retrieved │────▶│ AI generates │────▶ "Based on your HR
    │ chunks   │     │ a grounded   │      policy document,
    │ from     │     │ answer with  │      employees receive
    │ SharePt  │     │ citations    │      15 days PTO..."
    └──────────┘     └──────────────┘
```

### Best Practices for Knowledge

1. **Be specific** — Add targeted URLs, not entire site root domains
2. **Keep content current** — Stale knowledge = wrong answers
3. **Test with real questions** — Verify the agent finds and cites the right sources
4. **Layer sources** — Combine SharePoint (internal) + websites (external) for comprehensive coverage
5. **Use descriptions** — Add a description to each knowledge source so the AI knows *when* to use it

---

## Slide 3 — Pillar 2: Tools (Actions)

### What Are Tools?

Tools (called **Actions** in Copilot Studio) let your agent **do things** — not just answer questions. They connect to external systems, run workflows, and retrieve or update data.

### Types of Tools/Actions

| Type | What It Does | Example | Complexity | License |
|------|-------------|---------|------------|---------|
| **Connector actions** | Call a pre-built Power Platform connector | Get items from SharePoint, create a Planner task | Low | Included |
| **Agent Flows** | Run a Power Automate flow built right from Copilot Studio | Multi-step approval, send Teams notification, call APIs | Medium | ✅ **No Premium license required!** |
| **HTTP requests** | Call any REST API directly | Call AI Foundry, query a custom API | Medium-High | Included |
| **Custom connectors** | Call your own API through a defined connector | Internal LOB system, custom microservice | High | Premium |
| **MCP (Model Context Protocol)** | Connect to any MCP-compatible tool server | Dev tools, databases, GitHub, custom MCP servers | Medium | Included |

### 🆕 Agent Flows — The Game-Changer

**Agent Flows** are Power Automate flows that you create *directly from within Copilot Studio*. Key benefits:

- **No Premium licensing required** — unlike standalone Power Automate cloud flows
- Built-in **Copilot Studio connector** — seamless input/output mapping
- Full Power Automate capability: conditions, loops, connectors, error handling
- Flows are **scoped to the agent** — easier to manage than standalone flows

```
┌──────────────────────────────────────────────────────────┐
│                    Copilot Studio                         │
│                                                          │
│  User says: "Book a meeting room for tomorrow at 2pm"    │
│         │                                                │
│         ▼                                                │
│  ┌─────────────┐                                         │
│  │ Agent Flow  │  ← Built right here, no Premium needed  │
│  │             │                                         │
│  │ 1. Check    │                                         │
│  │    calendar │                                         │
│  │ 2. Find room│                                         │
│  │ 3. Book it  │                                         │
│  │ 4. Send     │                                         │
│  │    invite   │                                         │
│  └──────┬──────┘                                         │
│         ▼                                                │
│  Agent: "Done! Room 301 is booked for tomorrow 2-3pm."  │
└──────────────────────────────────────────────────────────┘
```

> 💡 **For GCC audiences:** This removes one of the biggest adoption barriers. Previously, connecting an agent to Power Automate required Premium connectors. Agent Flows change that.

### 🆕 MCP — Model Context Protocol

**MCP (Model Context Protocol)** is an open standard that lets AI agents connect to external tools and data sources through a universal interface. Think of it as **USB-C for AI agents** — one standard plug that works with everything.

```
                    ┌─────────────────┐
                    │  Copilot Studio │
                    │     Agent       │
                    └────────┬────────┘
                             │ MCP Protocol
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
       │  MCP Server │ │MCP Server│ │  MCP Server │
       │  (Database) │ │(GitHub)  │ │ (Custom API)│
       └─────────────┘ └──────────┘ └─────────────┘
```

| MCP Concept | What It Is | Analogy |
|-------------|-----------|---------|
| **MCP Server** | A tool/data provider that exposes capabilities via MCP | Like a USB device |
| **MCP Client** | The agent that connects to MCP servers | Like a laptop with USB ports |
| **Tools** | Actions the server exposes (functions the agent can call) | Like printer commands |
| **Resources** | Data the server provides (context for the agent) | Like files on a USB drive |

**Why MCP matters for GCC:**
- **Standard protocol** — build once, connect to any MCP-compatible agent (Copilot Studio, GitHub Copilot, Claude, etc.)
- **On-premises bridge** — MCP servers can run inside your network, giving agents access to internal systems without exposing APIs publicly
- **Escape hatch complement** — While AI Foundry is the escape hatch for *models*, MCP is the escape hatch for *tools and data*
- **Growing ecosystem** — hundreds of pre-built MCP servers for databases, APIs, dev tools, and more

> ⚠️ **GCC Note:** MCP support in Copilot Studio is evolving. Check current availability for your GCC environment. Even if not yet natively supported, you can use MCP servers via HTTP actions or Agent Flows as an intermediary.

### Custom Connectors — Your Own APIs

When pre-built connectors don't cover your needs, **custom connectors** let you wrap any REST API into a Power Platform connector:

| Step | What You Do |
|------|------------|
| 1. Define | Create an OpenAPI/Swagger definition for your API |
| 2. Register | Register the custom connector in Power Platform (GCC) |
| 3. Authenticate | Configure auth (API key, OAuth, certificate) |
| 4. Use | The connector appears alongside built-in connectors in Copilot Studio |

**Common GCC custom connector scenarios:**
- Internal ticketing system (ServiceNow, Remedy, custom)
- HR/ERP systems behind your network
- Custom Azure Functions or APIs in Azure Commercial (another escape hatch!)
- Legacy SOAP services wrapped in a REST facade

> 💡 **Pro Tip:** If you're already using custom connectors in Power Apps or Power Automate, those *same connectors* are available to your Copilot Studio agents.

### How the AI Decides to Use a Tool

The AI orchestrator reads the **tool description** you provide and decides when to invoke it:

```
User: "Create a support ticket for my broken laptop"
         │
         ▼
┌─────────────────────────────────────────┐
│  AI Orchestrator reads tool descriptions │
│                                         │
│  📋 "Create ServiceNow ticket" tool     │
│     Description: "Use this tool when    │
│     the user wants to create a new      │
│     support ticket or report an issue"  │
│                                         │
│  ✅ MATCH — invoke this tool            │
└────────────────┬────────────────────────┘
                 │
         ┌───────▼────────┐
         │ Tool executes  │
         │ (creates ticket)│
         │ Returns: TKT-  │
         │ 2024-0042      │
         └───────┬────────┘
                 │
         ┌───────▼──────────────────────────┐
         │ Agent: "I've created ticket      │
         │ TKT-2024-0042 for your broken    │
         │ laptop. The IT team will follow  │
         │ up within 24 hours."             │
         └──────────────────────────────────┘
```

> 💡 **Key Insight:** The description is critical — for ALL tool types (connector actions, Agent Flows, HTTP, MCP, custom connectors). A vague description = the AI won't know when to use the tool. A clear description = reliable automation.

### Tools + Generative Actions

When **Generative Actions** (also called "Dynamic Chaining") is enabled in your agent settings, the AI orchestrator can:

- Automatically decide which tools to call based on the user's intent
- Chain multiple tools together in sequence
- Combine tool results with knowledge for a comprehensive response

Without Generative Actions, tools only run when explicitly called from a topic node.

### Slide: The Complete Tools Landscape

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR COPILOT STUDIO AGENT                 │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │Connector │ │  Agent   │ │   HTTP   │ │    Custom     │  │
│  │ Actions  │ │  Flows   │ │ Requests │ │  Connectors   │  │
│  │          │ │          │ │          │ │               │  │
│  │ 1,000+   │ │ No       │ │ Any REST │ │ Your own APIs │  │
│  │ pre-built│ │ Premium! │ │ endpoint │ │ via Swagger   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───────┬───────┘  │
│       │            │            │               │           │
│  ┌────▼────────────▼────────────▼───────────────▼────────┐  │
│  │              MCP (Model Context Protocol)              │  │
│  │         Universal standard for tool connectivity       │  │
│  │        (emerging — growing ecosystem of servers)       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Slide 4 — Pillar 3: Child & Connected Agents

### Why Multiple Agents?

As your agent grows, you may find it handles too many domains — HR, IT, Facilities, Finance. Instead of one massive agent, you can **modularize**:

```
                    ┌───────────────────┐
                    │   Parent Agent    │
                    │ (Main entry point)│
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
       │  HR Agent   │ │ IT Agent │ │Facilities  │
       │  (Child)    │ │ (Child)  │ │Agent (Child)│
       │             │ │          │ │             │
       │ • PTO policy│ │ • Tickets│ │ • Room book │
       │ • Benefits  │ │ • VPN    │ │ • Maint.    │
       │ • Onboard   │ │ • Equip  │ │ • Parking   │
       └─────────────┘ └──────────┘ └─────────────┘
```

### Child Agents vs. Connected Agents

| Feature | Child Agent | Connected Agent |
|---------|-------------|-----------------|
| **Relationship** | Built and managed within same environment | Independent agent, possibly in another environment |
| **Routing** | Parent agent routes to child via topic | Orchestrator matches user intent to connected agent |
| **Use case** | Modular domains within one team's ownership | Cross-team or cross-org collaboration |
| **Autonomy** | Shares parent's channels and settings | Has its own settings, channels, knowledge |
| **GCC** | ✅ Available | ✅ Available |

### When to Use Multi-Agent Patterns

| Scenario | Pattern |
|----------|---------|
| One team, multiple domains (HR + IT + Facilities) | **Child agents** under a single parent |
| Different teams own different agent capabilities | **Connected agents** — each team builds their own |
| Specialized AI (e.g., legal review vs. general Q&A) | **Child agent** with tailored instructions + knowledge |
| Cross-organization agent federation | **Connected agents** across environments |

> 💡 **Think of it like a call center:** The parent agent is the receptionist who routes your call. Child agents are the specialists who actually handle your request.

---

*Next: Part 2c — Hands-On Lab: Knowledge, Tools & Child Agents →*
