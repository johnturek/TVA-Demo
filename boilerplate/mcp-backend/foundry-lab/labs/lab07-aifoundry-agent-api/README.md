# Lab 07 — AI Foundry Agent API (FastAPI + OBO)

A **FastAPI REST API** that wraps any hosted AI Foundry agent — YAML-based
or portal-developed — behind simple `/chat` and `/chat/stream` endpoints.

This is the **escape hatch**: Copilot Studio (or any HTTP client) can call
into AI Foundry agents via a standard REST contract with On-Behalf-Of (OBO)
authentication.

## Architecture

```
Copilot Studio  ──Bearer──▶  FastAPI (Lab 07)  ──OBO──▶  Azure AI Foundry
  (Custom Connector)            │                         Responses API
                                │                         (agent_reference)
                                ├── POST /chat            ↕
                                ├── POST /chat/stream     Hosted Agent
                                └── GET  /health          (YAML or portal)
```

**Auth flow:**
1. Copilot Studio authenticates the user → acquires a Bearer JWT
2. Sends `POST /chat` with `Authorization: Bearer <token>`
3. FastAPI extracts the token and exchanges it via MSAL OBO for a Cognitive Services token
4. FastAPI calls the Foundry Responses API **as the user** with `agent_reference`

**Local dev:** No Bearer token → falls back to `DefaultAzureCredential` (your `az login` identity).

## Prerequisites

- **Lab 03 Exercise 5** completed (or any hosted agent deployed in your Foundry project)
- Python 3.11+
- Azure CLI logged in (`az login`)
- For OBO: An Entra ID app registration with a client secret and Cognitive Services permissions

## Setup

```bash
# From foundry-lab/ directory
pip install --user -r requirements.txt
pip install --user -r labs/lab07-aifoundry-agent-api/requirements.txt
cp example.env .env   # fill in your values
```

## Exercises

| # | Title | What You Build |
|---|-------|----------------|
| 1 | Connect to the Hosted Agent | Resolve agent by env var, call via `agent_reference` |
| 2 | Build the FastAPI App | `POST /chat` + `GET /health` with Pydantic models |
| 3 | Add Streaming (SSE) | `POST /chat/stream` with Server-Sent Events |
| 4 | OBO Authentication | MSAL OBO + DefaultAzureCredential fallback |
| 5 | Container App Deployment | Dockerfile, env vars, Copilot Studio integration |
| 6 | Build, Deploy, Test & Export | ACR build → deploy → test suite → `openapi-copilot-studio.yaml` |

### Run the walkthrough

```bash
# All exercises
python labs/lab07-aifoundry-agent-api/lab07_agent_api.py

# Single exercise
python labs/lab07-aifoundry-agent-api/lab07_agent_api.py --exercise 2

# View exercise descriptions only
python labs/lab07-aifoundry-agent-api/lab07_agent_api.py --intro-only
```

### Run the API server

```bash
cd labs/lab07-aifoundry-agent-api
uvicorn lab07_agent_api:app --reload --port 8000
```

### Test

```bash
# Health check
curl http://localhost:8000/health

# Chat (non-streaming)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What inspections are needed for concrete gravity dams?"}'

# Chat (streaming)
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "List three key safety checks."}'

# Multi-turn (pass conversation_history from previous response)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me more about the first one.",
    "conversation_history": [
      {"role": "user", "content": "What inspections are needed?"},
      {"role": "assistant", "content": "...previous response..."}
    ]
  }'
```

## Environment Variables

### Agent Selection
| Variable | Description | Default |
|----------|-------------|---------|
| `AZURE_AGENT_NAME` | Name of the hosted agent to call | `TvaDamSafetyInspector` |
| `AZURE_AGENT_VERSION` | Agent version | `1` |
| `AZURE_AI_PROJECT_ENDPOINT` | AI Foundry project endpoint | *(required)* |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment name | `gpt-4.1` |

### OBO Authentication (same as root MCP server)
| Variable | Description |
|----------|-------------|
| `OBO_CLIENT_ID` | Entra app registration client ID |
| `OBO_CLIENT_SECRET` | App client secret |
| `OBO_TENANT_ID` | Entra tenant ID |
| `OBO_SCOPE` | Downstream scope (default: `https://cognitiveservices.azure.com/.default`) |

When all three `OBO_*` variables are set, OBO is enabled. Without them, the API
falls back to `DefaultAzureCredential`.

## Container App Deployment

The Dockerfile mirrors the root MCP server pattern:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "lab07_agent_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Set the environment variables in your Container App configuration to select the
agent and configure OBO. To switch agents, update `AZURE_AGENT_NAME` — no code
changes needed.

## Copilot Studio Integration

### Custom Connector (OpenAPI)

1. Import `openapi.yaml` as a Custom Connector in Copilot Studio
2. Replace the placeholders in the spec:
   - `<CONTAINER_APP_FQDN>` → your Container App FQDN
   - `<TENANT_ID>` → your Entra tenant ID
   - `<CLIENT_ID>` → your Entra app registration client ID
3. Configure the OAuth2 connection in Copilot Studio
4. Add the Copilot Studio redirect URL to your app registration

### OAuth Security Scheme

The `openapi.yaml` defines an OAuth2 authorization code flow:
- **Authorization URL**: `https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/authorize`
- **Token URL**: `https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/token`
- **Scope**: `api://<CLIENT_ID>/access_as_user`

The Bearer token from Copilot Studio is exchanged server-side via OBO for a
Cognitive Services token, so the agent runs as the authenticated user.

## API Reference

### `GET /health`
Returns agent configuration and OBO status. No authentication required.

### `POST /chat`
Send a message to the hosted agent. Returns the full response.

**Request:** `ChatRequest` — `message` (required), `conversation_history` (optional)
**Response:** `ChatResponse` — `response` (agent text), `conversation_history` (updated)

### `POST /chat/stream`
Same input as `/chat`, but returns a Server-Sent Events stream:
```
data: {"type": "delta", "content": "Three key"}
data: {"type": "delta", "content": " safety checks"}
data: {"type": "done", "content": "...full response text..."}
```
