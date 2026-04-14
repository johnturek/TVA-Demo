# Lab 03 — Agents (Responses API + Foundry Agent v2)

## Objective

Build AI agents using the **OpenAI Responses API** and the **Azure AI Foundry
Agent v2** through the Foundry SDK v2.0. This lab covers both the
stateless Responses API pattern (exercises 1–4) and the full Foundry Agent v2
lifecycle with declarative YAML definitions, conversations, and the Responses
API (exercise 5).

## Architecture

```
Your Code (Foundry SDK v2.0)
    │
    ├── Exercises 1–4: Responses API (stateless)
    │   └── openai.responses.create(model, instructions, input, tools, ...)
    │
    └── Exercise 5: Foundry Agent v2 (stateful)
        │
        ├── YAML definition  → agents/dam-safety-inspector.yaml
        ├── agents.create_version()    → Push agent to new Foundry portal
        ├── conversations.create()     → Create conversation container
        ├── responses.create()         → Invoke agent via agent_reference
        ├── conversations.items.create() → Add follow-up messages
        └── conversations.delete()     → Cleanup
```

## Concepts Covered

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Basic Agent | Responses API with system instructions |
| 2 | Code Interpreter | Agent writes and executes Python in a sandbox |
| 3 | Function Calling | Agent invokes your custom tools via agentic loop |
| 4 | Streaming | Token-by-token agent output |
| 5 | Agent-as-Code | YAML → create_version → conversations + Responses API |

## Foundry Agent v2 Key Concepts

- **Agent**: Definition (model + instructions + tools) deployed to a Foundry project
  via `agents.create_version()` with a `PromptAgentDefinition`
- **Conversation**: Durable multi-turn container (v2 replacement for threads)
- **agent_reference**: Tells `responses.create()` which named agent to invoke
- **Publishing**: Promotes an agent to an Agent Application with a stable endpoint
  that consumers call via the **Responses API** (`POST /responses`)

## Agent-as-Code (Exercise 5)

Exercise 5 introduces a declarative workflow:

```
agents/dam-safety-inspector.yaml    ← Version-controlled definition
        │
        ▼
agents.create_version()             ← Push to new Foundry portal (AIProjectClient)
        │
        ▼
conversations + Responses API       ← Development interaction (agent_reference)
        │
        ▼
Publish → Agent Application         ← Production: Responses API endpoint
```

The YAML file defines the agent's name, model, instructions, and metadata.
The Python code loads it and creates the agent via the SDK — no portal clicks
required. When you're ready for production, publish the agent and consumers
use the same `responses.create()` pattern from exercises 1–4.

## Run

```bash
cd foundry-lab
python labs/lab03-agents/lab03_agents.py
```

## Challenges

- Add a `get_weather_forecast` tool that returns simulated 7-day Tennessee Valley weather data and have the agent correlate it with the load forecast
- Upload a CSV of hourly generation data and use File Search + Code Interpreter together to detect anomalies
- Extend the function calling loop to handle a scenario where Watts Bar is offline and the agent must recommend backup generation
- Implement tool call retry logic with exponential backoff for PI historian connectivity errors
- Create a second YAML agent definition with File Search tools and a vector store, then run both agents in the same conversation
- Publish the Dam Safety Inspector as an Agent Application and consume it via the Responses API
