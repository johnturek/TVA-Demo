"""
Lab 07 — AI Foundry Agent API (FastAPI + OBO)
==============================================
Builds a FastAPI Python API that wraps any hosted AI Foundry agent
(declarative YAML-based or portal-developed) behind simple REST endpoints.

This is the **escape hatch** — Copilot Studio or any HTTP client can call
into AI Foundry agents via ``POST /chat`` or ``POST /chat/stream`` with
optional On-Behalf-Of (OBO) authentication.

Covers:
  - Connecting to a hosted agent via the Responses API with agent_reference
  - Building FastAPI endpoints with Pydantic request/response models
  - Server-Sent Events (SSE) streaming for real-time token delivery
  - OBO authentication (MSAL) with DefaultAzureCredential fallback
  - Container App deployment and Copilot Studio integration

Prerequisites:
  pip install --user -r requirements.txt          # foundry-lab root
  pip install --user -r labs/lab07-aifoundry-agent-api/requirements.txt
  cp example.env .env   # fill in your values

Usage:
  # Guided walkthrough (exercises)
  python labs/lab07-aifoundry-agent-api/lab07_agent_api.py

  # Run only one exercise
  python labs/lab07-aifoundry-agent-api/lab07_agent_api.py --exercise 2

  # Run the FastAPI server directly
  uvicorn labs.lab07-aifoundry-agent-api.lab07_agent_api:app --reload
"""

import sys, os, json, asyncio, logging, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from dotenv import load_dotenv

load_dotenv()

console = Console()


# ── Inlined config helpers (from shared.config) ─────────────────────────────
# Keeps this lab fully self-contained for containerised deployment.

def get_project_endpoint() -> str:
    """Return the Foundry project endpoint or exit with guidance."""
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        print(
            "ERROR: AZURE_AI_PROJECT_ENDPOINT is not set.\n"
            "Run the infrastructure deployment first, then copy the endpoint to .env.\n"
            "  Format: https://<account>.services.ai.azure.com/api/projects/<project>"
        )
        sys.exit(1)
    return endpoint


def get_project_client():
    """Return an authenticated AIProjectClient using DefaultAzureCredential."""
    from azure.identity import DefaultAzureCredential
    from azure.ai.projects import AIProjectClient

    return AIProjectClient(
        endpoint=get_project_endpoint(),
        credential=DefaultAzureCredential(),
    )


def get_model_name() -> str:
    """Return the default model deployment name."""
    return os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

# ── Environment ──────────────────────────────────────────────────────────────

AGENT_NAME = os.environ.get("AZURE_AGENT_NAME", "TvaDamSafetyInspector")
AGENT_VERSION = os.environ.get("AZURE_AGENT_VERSION", "1")

# OBO configuration (mirrors root mcp_server.py pattern)
_OBO_CLIENT_ID = os.environ.get("OBO_CLIENT_ID", "").strip()
_OBO_CLIENT_SECRET = os.environ.get("OBO_CLIENT_SECRET", "").strip()
_OBO_TENANT_ID = os.environ.get("OBO_TENANT_ID", "").strip()
_OBO_SCOPE = os.environ.get("OBO_SCOPE", "https://cognitiveservices.azure.com/.default").strip()
_OBO_ENABLED = bool(_OBO_CLIENT_ID and _OBO_CLIENT_SECRET and _OBO_TENANT_ID)


def section(title: str):
    console.print(f"\n[bold cyan]{'─' * 60}[/]")
    console.print(f"[bold cyan]  {title}[/]")
    console.print(f"[bold cyan]{'─' * 60}[/]\n")


# ── Lab Introduction ─────────────────────────────────────────────────────────

def show_lab_intro(wait_for_input=True):
    """Display an introduction explaining why this lab matters."""
    console.print(Panel(
        "[bold]Why This Lab?[/]\n\n"
        "Lab 03 taught you to deploy agents as hosted, portal-visible resources.\n"
        "But how do you [cyan]call[/] those agents from external systems like "
        "[bold]Copilot Studio[/], a mobile app, or a custom UI?\n\n"
        "This lab builds a [cyan]FastAPI[/] REST API that acts as an "
        "[bold]escape hatch[/] — any HTTP client can chat with any hosted "
        "AI Foundry agent via simple ``POST /chat`` requests.\n\n"
        "[bold]Concepts Covered[/]\n\n"
        "  • [cyan]Agent selection via environment variables[/] — configure which "
        "agent to call per deployment\n"
        "  • [cyan]FastAPI + Pydantic[/] — type-safe request/response models\n"
        "  • [cyan]SSE streaming[/] — real-time token delivery via "
        "Server-Sent Events\n"
        "  • [cyan]OBO authentication[/] — MSAL On-Behalf-Of flow so the API "
        "calls Foundry as the end user\n"
        "  • [cyan]Container App deployment[/] — Dockerfile and env var "
        "configuration\n\n"
        "[bold]How This Differs from Lab 03[/]\n\n"
        "Lab 03 ran agents from a local Python script. Here we wrap the same "
        "agent behind an HTTP API with production-grade auth, streaming, and "
        "containerization — ready for Copilot Studio or any client to call.",
        title="🎓 Lab 07 — AI Foundry Agent API (FastAPI + OBO)",
        border_style="bright_blue",
    ))
    if wait_for_input:
        console.input("\n[dim]Press Enter to continue...[/]")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_openai_client_default():
    """Return an OpenAI client using DefaultAzureCredential (local dev)."""
    client = get_project_client()
    return client.get_openai_client()


_logger = logging.getLogger("lab07")

_RESOLVE_MAX_RETRIES = int(os.environ.get("RESOLVE_AGENT_RETRIES", "3"))
_RESOLVE_RETRY_DELAY = float(os.environ.get("RESOLVE_AGENT_RETRY_DELAY", "2.0"))


def _resolve_agent():
    """Look up the hosted agent by AZURE_AGENT_NAME and return (name, version).

    Retries on transient failures (common on Container App cold start when
    credential tokens or network connections aren't ready yet).
    """
    project_client = get_project_client()
    agent = None
    last_err = None

    for attempt in range(1, _RESOLVE_MAX_RETRIES + 1):
        try:
            for a in project_client.agents.list():
                if a.name == AGENT_NAME:
                    agent = a
                    break
            last_err = None
            break  # success (even if agent wasn't found by name)
        except Exception as exc:
            last_err = exc
            _logger.warning(
                "Agent lookup attempt %d/%d failed: %s",
                attempt, _RESOLVE_MAX_RETRIES, exc,
            )
            if attempt < _RESOLVE_MAX_RETRIES:
                time.sleep(_RESOLVE_RETRY_DELAY)

    if last_err is not None:
        _logger.error("All %d agent lookup attempts failed: %s", _RESOLVE_MAX_RETRIES, last_err)

    if agent is None:
        console.print(f"[bold red]Agent '{AGENT_NAME}' not found.[/]")
        console.print("[dim]Deploy it first via Lab 03 Exercise 5, or set AZURE_AGENT_NAME.[/]")
        return None, None

    version = AGENT_VERSION
    if not version and agent.id and ":" in agent.id:
        version = agent.id.split(":")[-1]
    version = version or "1"

    return agent.name, version


def _build_agent_reference(name: str, version: str) -> dict:
    """Build the agent_reference dict for Responses API extra_body."""
    return {
        "agent_reference": {
            "name": name,
            "version": version,
            "type": "agent_reference",
        }
    }


# ── OBO Token Exchange (MSAL — mirrors root mcp_server.py) ──────────────────

_OBO_APP = None

def _get_obo_app():
    """Lazily initialise the MSAL ConfidentialClientApplication for OBO."""
    global _OBO_APP
    if _OBO_APP is None and _OBO_ENABLED:
        import msal
        _OBO_APP = msal.ConfidentialClientApplication(
            client_id=_OBO_CLIENT_ID,
            client_credential=_OBO_CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{_OBO_TENANT_ID}",
        )
    return _OBO_APP


def _acquire_obo_token(bearer_token: str) -> str:
    """Exchange a caller's bearer token for a Cognitive Services token via OBO.

    Uses MSAL ConfidentialClientApplication.acquire_token_on_behalf_of().
    Raises RuntimeError on failure.
    """
    app = _get_obo_app()
    if app is None:
        raise RuntimeError(
            "OBO is not configured. Set OBO_CLIENT_ID, OBO_CLIENT_SECRET, and OBO_TENANT_ID."
        )

    result = app.acquire_token_on_behalf_of(
        user_assertion=bearer_token,
        scopes=[_OBO_SCOPE],
    )

    if "access_token" in result:
        return result["access_token"]

    error = result.get("error", "unknown_error")
    error_desc = result.get("error_description", "No description")
    raise RuntimeError(f"OBO token exchange failed: {error} — {error_desc}")


def _get_openai_client_obo(bearer_token: str):
    """Build an OpenAI client using an OBO-acquired token."""
    import openai as _openai

    obo_token = _acquire_obo_token(bearer_token)

    project_endpoint = get_project_endpoint()
    account_endpoint = project_endpoint.split("/api/projects")[0]

    return _openai.AzureOpenAI(
        azure_endpoint=account_endpoint,
        api_key=obo_token,
        api_version="2025-04-01-preview",
    )


def _get_openai_client(bearer_token: str = None):
    """Return the appropriate OpenAI client.

    - If a bearer_token is provided and OBO is configured → OBO flow.
    - Otherwise → DefaultAzureCredential (local dev).
    """
    if bearer_token and _OBO_ENABLED:
        return _get_openai_client_obo(bearer_token)
    return _get_openai_client_default()


# ══════════════════════════════════════════════════════════════════════════════
#  FastAPI Application  (importable as: uvicorn lab07_agent_api:app)
# ══════════════════════════════════════════════════════════════════════════════

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(
    title="AI Foundry Agent API",
    description="REST API wrapping a hosted AI Foundry agent with OBO authentication.",
    version="1.0.0",
)


# ── Pydantic Models ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for /chat and /chat/stream."""
    message: str = Field(..., description="The user's message to send to the agent.")
    conversation_history: list[dict] = Field(
        default_factory=list,
        description="Optional conversation history as a list of {role, content} dicts.",
    )

class ChatResponse(BaseModel):
    """Response body for /chat."""
    response: str = Field(..., description="The agent's response text.")
    conversation_history: list[dict] = Field(
        ..., description="Updated conversation history including the latest exchange.",
    )


# ── FastAPI dependency: extract optional Bearer token ────────────────────────

def _extract_bearer(request: Request) -> Optional[str]:
    """Extract a Bearer token from the Authorization header, or return None."""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check — returns agent config and OBO status."""
    return {
        "status": "healthy",
        "agent_name": AGENT_NAME,
        "agent_version": AGENT_VERSION,
        "obo_enabled": _OBO_ENABLED,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    """Send a message to the hosted agent and return the response."""
    bearer = _extract_bearer(request)
    openai_client = _get_openai_client(bearer)
    agent_name, agent_version = _resolve_agent()
    if not agent_name:
        raise HTTPException(status_code=503, detail=f"Agent '{AGENT_NAME}' not found.")

    # Build input: history + new message
    input_messages = list(body.conversation_history)
    input_messages.append({"role": "user", "content": body.message})

    response = openai_client.responses.create(
        input=input_messages,
        extra_body=_build_agent_reference(agent_name, agent_version),
    )

    # Build updated history
    updated_history = list(input_messages)
    updated_history.append({"role": "assistant", "content": response.output_text})

    return ChatResponse(
        response=response.output_text,
        conversation_history=updated_history,
    )


@app.post("/chat/stream")
async def chat_stream(body: ChatRequest, request: Request):
    """Send a message to the hosted agent and stream the response via SSE."""
    bearer = _extract_bearer(request)
    openai_client = _get_openai_client(bearer)
    agent_name, agent_version = _resolve_agent()
    if not agent_name:
        raise HTTPException(status_code=503, detail=f"Agent '{AGENT_NAME}' not found.")

    input_messages = list(body.conversation_history)
    input_messages.append({"role": "user", "content": body.message})

    async def event_generator():
        stream = openai_client.responses.create(
            input=input_messages,
            extra_body=_build_agent_reference(agent_name, agent_version),
            stream=True,
        )
        for event in stream:
            if event.type == "response.output_text.delta":
                data = json.dumps({"type": "delta", "content": event.delta})
                yield f"data: {data}\n\n"
            elif event.type == "response.completed":
                full_text = ""
                if hasattr(event, "response") and hasattr(event.response, "output_text"):
                    full_text = event.response.output_text
                done_data = json.dumps({"type": "done", "content": full_text})
                yield f"data: {done_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Guided Exercises (walkthrough mode)
# ══════════════════════════════════════════════════════════════════════════════

# ── Exercise 1: Connect to the Hosted Agent ──────────────────────────────────

def exercise_1_connect_to_agent():
    """Resolve the hosted agent by name and send a test message."""
    section("Exercise 1 — Connect to the Hosted Agent")

    console.print(f"[bold]Looking up agent:[/] [cyan]{AGENT_NAME}[/] (version {AGENT_VERSION})")
    console.print(f"[dim]Set AZURE_AGENT_NAME and AZURE_AGENT_VERSION to change the target agent.[/]\n")

    agent_name, agent_version = _resolve_agent()
    if not agent_name:
        return

    console.print(f"[green]✓ Found agent:[/] {agent_name} (version {agent_version})\n")

    # Send a test message
    openai_client = _get_openai_client_default()
    user_question = "What is your area of expertise? Give a one-sentence answer."

    console.print(Panel(user_question, title="👤 Test Message", border_style="cyan"))

    response = openai_client.responses.create(
        input=[{"role": "user", "content": user_question}],
        extra_body=_build_agent_reference(agent_name, agent_version),
    )

    console.print(Panel(
        response.output_text,
        title=f"🤖 {agent_name} Response",
        border_style="green",
    ))

    # Show the code pattern
    code = (
        '# Resolve agent and chat via Responses API\n'
        'project_client = get_project_client()\n'
        'openai_client = project_client.get_openai_client()\n\n'
        'response = openai_client.responses.create(\n'
        '    input=[{"role": "user", "content": "Your question here"}],\n'
        '    extra_body={"agent_reference": {\n'
        f'        "name": "{agent_name}",\n'
        f'        "version": "{agent_version}",\n'
        '        "type": "agent_reference",\n'
        '    }},\n'
        ')\n'
        'print(response.output_text)'
    )
    console.print(Panel(
        Syntax(code, "python", theme="monokai", word_wrap=True),
        title="📋 Code Pattern",
        border_style="dim",
    ))


# ── Exercise 2: Build the FastAPI App ────────────────────────────────────────

def exercise_2_fastapi_app():
    """Show the FastAPI app structure and test the /chat endpoint."""
    section("Exercise 2 — Build the FastAPI App")

    # Show the Pydantic models
    models_code = (
        'from pydantic import BaseModel, Field\n\n'
        'class ChatRequest(BaseModel):\n'
        '    message: str = Field(..., description="The user\'s message.")\n'
        '    conversation_history: list[dict] = Field(default_factory=list)\n\n'
        'class ChatResponse(BaseModel):\n'
        '    response: str = Field(..., description="The agent\'s response.")\n'
        '    conversation_history: list[dict] = Field(...)'
    )
    console.print(Panel(
        Syntax(models_code, "python", theme="monokai", word_wrap=True),
        title="📋 Pydantic Request/Response Models",
        border_style="dim",
    ))

    # Show the /chat endpoint
    chat_code = (
        '@app.post("/chat", response_model=ChatResponse)\n'
        'async def chat(body: ChatRequest, request: Request):\n'
        '    bearer = _extract_bearer(request)\n'
        '    openai_client = _get_openai_client(bearer)\n'
        '    agent_name, agent_version = _resolve_agent()\n\n'
        '    input_messages = list(body.conversation_history)\n'
        '    input_messages.append({"role": "user", "content": body.message})\n\n'
        '    response = openai_client.responses.create(\n'
        '        input=input_messages,\n'
        '        extra_body=_build_agent_reference(agent_name, agent_version),\n'
        '    )\n\n'
        '    return ChatResponse(\n'
        '        response=response.output_text,\n'
        '        conversation_history=[...updated history...],\n'
        '    )'
    )
    console.print(Panel(
        Syntax(chat_code, "python", theme="monokai", word_wrap=True),
        title="📋 POST /chat Endpoint",
        border_style="dim",
    ))

    # Simulate a request
    console.print("[bold]Simulating a /chat request…[/]\n")

    agent_name, agent_version = _resolve_agent()
    if not agent_name:
        return

    openai_client = _get_openai_client_default()
    test_message = "What types of inspections do you recommend for concrete gravity dams?"

    console.print(Panel(
        json.dumps({"message": test_message, "conversation_history": []}, indent=2),
        title="📤 Request Body",
        border_style="cyan",
    ))

    input_messages = [{"role": "user", "content": test_message}]
    response = openai_client.responses.create(
        input=input_messages,
        extra_body=_build_agent_reference(agent_name, agent_version),
    )

    updated_history = list(input_messages)
    updated_history.append({"role": "assistant", "content": response.output_text})

    response_body = {
        "response": response.output_text,
        "conversation_history": updated_history,
    }

    console.print(Panel(
        response.output_text,
        title="📥 Response (response field)",
        border_style="green",
    ))
    console.print(f"[dim]conversation_history now has {len(updated_history)} messages "
                  f"(pass it back in the next request for multi-turn).[/]")

    # Show how to run
    console.print(Panel(
        "[bold]Run the API server:[/]\n\n"
        "  [cyan]uvicorn lab07_agent_api:app --reload --port 8000[/]\n\n"
        "[bold]Test with curl:[/]\n\n"
        '  [cyan]curl -X POST http://localhost:8000/chat \\\n'
        '    -H "Content-Type: application/json" \\\n'
        '    -d \'{"message": "What inspections are needed?"}\'[/]\n\n'
        "[bold]Health check:[/]\n\n"
        "  [cyan]curl http://localhost:8000/health[/]",
        title="🚀 Running the API",
        border_style="bright_green",
    ))


# ── Exercise 3: Add Streaming ────────────────────────────────────────────────

def exercise_3_streaming():
    """Demonstrate the /chat/stream SSE endpoint."""
    section("Exercise 3 — Add Streaming (SSE)")

    # Show the streaming endpoint code
    stream_code = (
        '@app.post("/chat/stream")\n'
        'async def chat_stream(body: ChatRequest, request: Request):\n'
        '    openai_client = _get_openai_client(_extract_bearer(request))\n'
        '    agent_name, agent_version = _resolve_agent()\n\n'
        '    input_messages = [...history + new message...]\n\n'
        '    async def event_generator():\n'
        '        stream = openai_client.responses.create(\n'
        '            input=input_messages,\n'
        '            extra_body=_build_agent_reference(agent_name, agent_version),\n'
        '            stream=True,\n'
        '        )\n'
        '        for event in stream:\n'
        '            if event.type == "response.output_text.delta":\n'
        '                data = json.dumps({"type": "delta", "content": event.delta})\n'
        '                yield f"data: {data}\\n\\n"\n'
        '            elif event.type == "response.completed":\n'
        '                yield f"data: {json.dumps({\"type\": \"done\"})}\\n\\n"\n\n'
        '    return StreamingResponse(event_generator(), media_type="text/event-stream")'
    )
    console.print(Panel(
        Syntax(stream_code, "python", theme="monokai", word_wrap=True),
        title="📋 POST /chat/stream Endpoint (SSE)",
        border_style="dim",
    ))

    # Demonstrate streaming live
    console.print("[bold]Demonstrating streaming (live tokens)…[/]\n")

    agent_name, agent_version = _resolve_agent()
    if not agent_name:
        return

    openai_client = _get_openai_client_default()
    test_message = "List three key safety checks for embankment dams."

    console.print(Panel(test_message, title="👤 Streaming Request", border_style="cyan"))
    console.print("[bold green]Streaming response:[/] ", end="")

    stream = openai_client.responses.create(
        input=[{"role": "user", "content": test_message}],
        extra_body=_build_agent_reference(agent_name, agent_version),
        stream=True,
    )

    for event in stream:
        if event.type == "response.output_text.delta":
            console.print(event.delta, end="")
    console.print()  # newline

    console.print(Panel(
        "[bold]Each SSE event is a JSON line:[/]\n\n"
        '  [cyan]data: {"type": "delta", "content": "Three key"}[/]\n'
        '  [cyan]data: {"type": "delta", "content": " safety checks"}[/]\n'
        '  [cyan]data: {"type": "done", "content": "...full text..."}[/]\n\n'
        "[bold]Test with curl:[/]\n\n"
        '  [cyan]curl -N -X POST http://localhost:8000/chat/stream \\\n'
        '    -H "Content-Type: application/json" \\\n'
        '    -d \'{"message": "List safety checks"}\'[/]',
        title="📡 SSE Event Format",
        border_style="bright_green",
    ))


# ── Exercise 4: Add OBO Authentication ───────────────────────────────────────

def exercise_4_obo_auth():
    """Explain and demonstrate the OBO authentication flow."""
    section("Exercise 4 — OBO Authentication")

    # Show the OBO flow
    console.print(Panel(
        "[bold]On-Behalf-Of (OBO) Flow[/]\n\n"
        "  1. Copilot Studio authenticates the user → gets a Bearer JWT\n"
        "  2. Copilot Studio calls [cyan]POST /chat[/] with "
        "[cyan]Authorization: Bearer <token>[/]\n"
        "  3. FastAPI extracts the token and exchanges it via MSAL OBO\n"
        "     for a [cyan]Cognitive Services[/] token\n"
        "  4. FastAPI calls the Foundry Responses API [bold]as the user[/]\n\n"
        "  If no Bearer token is present → falls back to DefaultAzureCredential\n"
        "  (your ``az login`` identity — perfect for local dev).",
        title="🔐 Auth Architecture",
        border_style="bright_yellow",
    ))

    # Show the OBO code
    obo_code = (
        'import msal\n\n'
        '# MSAL Confidential Client (same pattern as root mcp_server.py)\n'
        '_OBO_APP = msal.ConfidentialClientApplication(\n'
        '    client_id=OBO_CLIENT_ID,\n'
        '    client_credential=OBO_CLIENT_SECRET,\n'
        '    authority=f"https://login.microsoftonline.com/{OBO_TENANT_ID}",\n'
        ')\n\n'
        'def _acquire_obo_token(bearer_token: str) -> str:\n'
        '    result = _OBO_APP.acquire_token_on_behalf_of(\n'
        '        user_assertion=bearer_token,\n'
        '        scopes=["https://cognitiveservices.azure.com/.default"],\n'
        '    )\n'
        '    if "access_token" in result:\n'
        '        return result["access_token"]\n'
        '    raise RuntimeError(f"OBO failed: {result.get(\'error\')}")\n\n'
        'def _get_openai_client(bearer_token=None):\n'
        '    if bearer_token and _OBO_ENABLED:\n'
        '        obo_token = _acquire_obo_token(bearer_token)\n'
        '        return AzureOpenAI(azure_endpoint=..., api_key=obo_token)\n'
        '    return project_client.get_openai_client()  # DefaultAzureCredential'
    )
    console.print(Panel(
        Syntax(obo_code, "python", theme="monokai", word_wrap=True),
        title="📋 OBO Token Exchange (MSAL)",
        border_style="dim",
    ))

    # Show current status
    if _OBO_ENABLED:
        console.print(f"[green]✓ OBO is configured:[/] client_id={_OBO_CLIENT_ID[:8]}…")
        console.print(f"  scope={_OBO_SCOPE}")
    else:
        console.print("[yellow]⚠ OBO is not configured (running in local dev mode).[/]")
        console.print("[dim]Set OBO_CLIENT_ID, OBO_CLIENT_SECRET, OBO_TENANT_ID to enable.[/]")

    # Show env vars
    console.print(Panel(
        "[bold]Environment Variables (same as root MCP server):[/]\n\n"
        "  [cyan]OBO_CLIENT_ID[/]     — Entra app registration client ID\n"
        "  [cyan]OBO_CLIENT_SECRET[/] — App client secret\n"
        "  [cyan]OBO_TENANT_ID[/]     — Entra tenant ID\n"
        "  [cyan]OBO_SCOPE[/]         — Downstream scope "
        "(default: [dim]https://cognitiveservices.azure.com/.default[/])\n\n"
        "[bold]The app registration must have:[/]\n\n"
        "  • API permission for [cyan]Azure AI Services[/] (Cognitive Services)\n"
        "  • A client secret\n"
        "  • Users with [cyan]Cognitive Services User[/] RBAC on the Foundry project",
        title="🔧 OBO Configuration",
        border_style="bright_green",
    ))


# ── Exercise 5: Container App Deployment ─────────────────────────────────────

def exercise_5_container_deployment():
    """Show Dockerfile, env var config, and Copilot Studio integration."""
    section("Exercise 5 — Run as Container App")

    # Show Dockerfile
    dockerfile = (
        'FROM python:3.11-slim\n\n'
        'WORKDIR /app\n\n'
        'COPY requirements.txt ./\n'
        'RUN pip install --no-cache-dir -r requirements.txt\n\n'
        'COPY . .\n\n'
        'ENV PYTHONUNBUFFERED=1\n\n'
        'EXPOSE 8000\n\n'
        'CMD ["uvicorn", "lab07_agent_api:app", "--host", "0.0.0.0", "--port", "8000"]'
    )
    console.print(Panel(
        Syntax(dockerfile, "dockerfile", theme="monokai", word_wrap=True),
        title="🐳 Dockerfile",
        border_style="dim",
    ))

    # Show env vars for Container App
    console.print(Panel(
        "[bold]Container App Environment Variables:[/]\n\n"
        "  [bold cyan]Agent Selection[/]\n"
        "  [cyan]AZURE_AGENT_NAME[/]              = TvaDamSafetyInspector\n"
        "  [cyan]AZURE_AGENT_VERSION[/]           = 1\n"
        "  [cyan]AZURE_AI_PROJECT_ENDPOINT[/]     = https://…\n"
        "  [cyan]AZURE_OPENAI_DEPLOYMENT_NAME[/]  = gpt-4.1\n\n"
        "  [bold cyan]OBO Authentication[/]\n"
        "  [cyan]OBO_CLIENT_ID[/]                 = <app-client-id>\n"
        "  [cyan]OBO_CLIENT_SECRET[/]             = <app-secret>\n"
        "  [cyan]OBO_TENANT_ID[/]                 = <tenant-id>\n"
        "  [cyan]OBO_SCOPE[/]                     = https://cognitiveservices.azure.com/.default\n\n"
        "[bold]To switch agents[/], just update [cyan]AZURE_AGENT_NAME[/] — no code changes.\n"
        "This is the [bold]escape hatch[/]: any YAML-based or portal-developed agent\n"
        "becomes callable via the same REST API.",
        title="⚙️ Environment Configuration",
        border_style="bright_green",
    ))

    # Show Copilot Studio integration
    console.print(Panel(
        "[bold]Copilot Studio Integration (HTTP Connector):[/]\n\n"
        "  1. Deploy the Container App and note the FQDN\n"
        "  2. In Copilot Studio → [bold]Connectors[/] → [bold]HTTP[/]\n"
        "  3. Configure:\n\n"
        "     [cyan]POST[/]  https://<FQDN>/chat\n"
        "     [cyan]Headers:[/]  Authorization: Bearer {{token}}\n"
        "     [cyan]Body:[/]\n"
        '     {\n'
        '       "message": "{{user_message}}",\n'
        '       "conversation_history": {{history}}\n'
        '     }\n\n'
        "  4. For streaming, use [cyan]POST /chat/stream[/] (SSE)\n\n"
        "  The OBO flow ensures the agent runs [bold]as the user[/],\n"
        "  inheriting their RBAC permissions on the Foundry project.",
        title="🤖 Copilot Studio Setup",
        border_style="bright_blue",
    ))

    console.print(Panel(
        "[bold yellow]What Changed?[/]\n\n"
        "Lab 03 Exercise 5 deployed an agent and chatted with it from a script.\n\n"
        "This lab wraps the [bold]same agent[/] behind a production-ready HTTP API:\n"
        "  • [cyan]FastAPI[/] with Pydantic validation\n"
        "  • [cyan]SSE streaming[/] for real-time responses\n"
        "  • [cyan]OBO auth[/] so requests run as the end user\n"
        "  • [cyan]Env-var-driven agent selection[/] — swap agents without code changes\n"
        "  • [cyan]Container App deployment[/] — the same Docker/env pattern as the MCP server\n\n"
        "Any hosted AI Foundry agent — YAML-based or portal-developed — is now\n"
        "accessible via [cyan]POST /chat[/] from Copilot Studio or any HTTP client.",
        title="🚀 From Agent to API — The Escape Hatch",
        border_style="bright_blue",
    ))


# ── Exercise 6: Build, Deploy, Test & Export OpenAPI ─────────────────────────

def exercise_6_build_deploy_test():
    """Build the container in ACR, deploy to Container Apps, run tests, and write the Copilot Studio OpenAPI spec."""
    import subprocess, time, shutil, textwrap

    section("Exercise 6 — Build, Deploy, Test & Export OpenAPI")

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    FOUNDRY_LAB_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
    ENV_FILE = os.path.join(FOUNDRY_LAB_DIR, ".env")
    DEPLOY_SCRIPT = os.path.join(SCRIPT_DIR, "deploy-lab07.sh")
    TEST_SCRIPT = os.path.join(SCRIPT_DIR, "test_lab07_api.py")
    OPENAPI_TEMPLATE = os.path.join(SCRIPT_DIR, "openapi.yaml")
    OPENAPI_OUTPUT = os.path.join(SCRIPT_DIR, "openapi-copilot-studio.yaml")

    # ── Step 1: Preflight checks ─────────────────────────────────────────────
    console.print(Panel(
        "[bold]Step 1 — Preflight Checks[/]\n\n"
        "Verifying that the deploy script, test script, and .env file exist\n"
        "and that required Azure CLI tools are available.",
        title="🔍 Preflight",
        border_style="dim",
    ))

    missing = []
    if not os.path.isfile(ENV_FILE):
        missing.append(f".env not found at {ENV_FILE}")
    if not os.path.isfile(DEPLOY_SCRIPT):
        missing.append(f"deploy-lab07.sh not found at {DEPLOY_SCRIPT}")
    if not shutil.which("az"):
        missing.append("Azure CLI (az) not found on PATH")

    if missing:
        for m in missing:
            console.print(f"  [red]✗[/] {m}")
        console.print("\n[bold red]Cannot proceed — fix the above issues first.[/]")
        return

    console.print("  [green]✓[/] .env found")
    console.print("  [green]✓[/] deploy-lab07.sh found")
    console.print("  [green]✓[/] Azure CLI available")

    # Read env vars we'll need later for OpenAPI templating
    env_vars = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()

    console.print()

    # ── Step 2: ACR Build + Deploy ───────────────────────────────────────────
    console.print(Panel(
        "[bold]Step 2 — Build & Deploy[/]\n\n"
        "Running [cyan]deploy-lab07.sh[/] which will:\n"
        "  1. Build the Docker image via [cyan]az acr build[/]\n"
        "  2. Deploy (or update) the Container App via Azure REST API\n"
        "  3. Enable system-assigned Managed Identity\n"
        "  4. Assign [cyan]Azure AI User[/] role on the AI Foundry account + project\n"
        "  5. Wait for the FQDN to become available\n\n"
        "[dim]This typically takes 2–4 minutes.[/]",
        title="🚀 Build & Deploy",
        border_style="bright_blue",
    ))

    console.print("[bold]Running deploy-lab07.sh...[/]\n")

    # Stream output in real-time instead of buffering until completion
    deploy_proc = subprocess.Popen(
        ["bash", DEPLOY_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=FOUNDRY_LAB_DIR,
        bufsize=1,
    )

    deploy_output_lines: list[str] = []
    try:
        for line in deploy_proc.stdout:
            line_stripped = line.rstrip("\n")
            deploy_output_lines.append(line_stripped)
            console.print(f"  [dim]{line_stripped}[/]")
        deploy_proc.wait(timeout=600)
    except subprocess.TimeoutExpired:
        deploy_proc.kill()
        deploy_proc.wait()
        console.print("\n[bold red]✗ Deploy timed out after 10 minutes.[/]")
        return

    if deploy_proc.returncode != 0:
        console.print(f"\n[bold red]✗ Deploy failed (exit code {deploy_proc.returncode}).[/]")
        console.print("[dim]Check the output above for details.[/]")
        return

    # Extract FQDN from deploy output
    app_fqdn = ""
    for line in deploy_output_lines:
        if "FQDN:" in line:
            app_fqdn = line.split("FQDN:")[-1].strip()
            break

    if not app_fqdn:
        # Fallback: query Azure for the FQDN
        container_app_name = env_vars.get("LAB07_CONTAINER_APP_NAME", "foundry-lab07-agent-api")
        try:
            fqdn_result = subprocess.run(
                ["az", "containerapp", "show",
                 "--name", container_app_name,
                 "--query", "properties.configuration.ingress.fqdn",
                 "-o", "tsv"],
                capture_output=True, text=True, timeout=30,
            )
            app_fqdn = fqdn_result.stdout.strip()
        except Exception:
            pass

    if not app_fqdn:
        console.print("[bold red]✗ Could not determine FQDN from deployment.[/]")
        return

    app_url = f"https://{app_fqdn}"
    console.print(f"\n[bold green]✓ Deployed:[/] {app_url}")

    # ── Step 3: Wait for container to become healthy ─────────────────────────
    console.print(Panel(
        "[bold]Step 3 — Health Check[/]\n\n"
        f"Waiting for [cyan]{app_url}/health[/] to respond...\n"
        "[dim]New container revisions can take 30–90 seconds to start.[/]",
        title="💚 Health Check",
        border_style="bright_green",
    ))

    import urllib.request, urllib.error

    healthy = False
    for attempt in range(12):
        try:
            req = urllib.request.Request(f"{app_url}/health")
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode())
                if body.get("status") == "healthy":
                    agent = body.get("agent_name", "?")
                    ver = body.get("agent_version", "?")
                    obo = body.get("obo_enabled", False)
                    console.print(f"  [green]✓[/] Healthy — agent={agent} v{ver}  obo={obo}")
                    healthy = True
                    break
        except Exception:
            pass
        console.print(f"  [dim]Attempt {attempt + 1}/12 — waiting 15s...[/]")
        time.sleep(15)

    if not healthy:
        console.print("[bold red]✗ Container App did not become healthy within 3 minutes.[/]")
        console.print(f"[dim]Try manually: curl {app_url}/health[/]")
        return

    # ── Step 4: Run test suite ───────────────────────────────────────────────
    console.print(Panel(
        "[bold]Step 4 — Run Tests[/]\n\n"
        f"Running [cyan]test_lab07_api.py[/] against [cyan]{app_url}[/]\n"
        "Tests: GET /health, GET /docs, POST /chat, POST /chat/stream",
        title="🧪 Test Suite",
        border_style="bright_yellow",
    ))

    test_proc = subprocess.Popen(
        [sys.executable, TEST_SCRIPT, app_url],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        for line in test_proc.stdout:
            console.print(f"  {line.rstrip()}")
        test_proc.wait(timeout=180)
    except subprocess.TimeoutExpired:
        test_proc.kill()
        test_proc.wait()

    if test_proc.returncode != 0:
        console.print("\n[bold red]✗ Some tests failed.[/]")
        console.print("[dim]The API is deployed but may need troubleshooting. Continuing to export OpenAPI spec.[/]")
    else:
        console.print("\n[bold green]✓ All tests passed![/]")

    # ── Step 5: Write OpenAPI spec with real values ──────────────────────────
    console.print(Panel(
        "[bold]Step 5 — Export OpenAPI for Copilot Studio[/]\n\n"
        "Writing [cyan]openapi-copilot-studio.yaml[/] with your real FQDN,\n"
        "tenant ID, and client ID filled in — ready to import as a\n"
        "Custom Connector in Copilot Studio.",
        title="📄 OpenAPI Export",
        border_style="bright_magenta",
    ))

    tenant_id = env_vars.get("OBO_TENANT_ID") or env_vars.get("AZURE_TENANT_ID", "<TENANT_ID>")
    client_id = env_vars.get("OBO_CLIENT_ID", "<CLIENT_ID>")

    if os.path.isfile(OPENAPI_TEMPLATE):
        with open(OPENAPI_TEMPLATE) as f:
            spec_content = f.read()
    else:
        console.print("[yellow]⚠ openapi.yaml template not found — generating from scratch.[/]")
        spec_content = ""

    if spec_content:
        # Replace placeholders with real values
        spec_content = spec_content.replace("<CONTAINER_APP_FQDN>", app_fqdn)
        spec_content = spec_content.replace("<TENANT_ID>", tenant_id)
        spec_content = spec_content.replace("<CLIENT_ID>", client_id)
    else:
        # Generate a minimal spec if the template is missing
        spec_content = textwrap.dedent(f"""\
            # OpenAPI 3.0 spec for Lab 07 — AI Foundry Agent API
            # Generated by Exercise 6 — ready to import into Copilot Studio.

            openapi: "3.0.1"
            info:
              title: AI Foundry Agent API
              description: >
                REST API wrapping a hosted AI Foundry agent with OBO authentication.
                Supports non-streaming and SSE streaming chat endpoints.
              version: "1.0.0"

            servers:
              - url: https://{app_fqdn}
                description: Azure Container App deployment

            security:
              - oauth2: []

            paths:
              /health:
                get:
                  operationId: getHealth
                  summary: Health check
                  security: []
                  responses:
                    "200":
                      description: Healthy
                      content:
                        application/json:
                          schema:
                            type: object
                            properties:
                              status:
                                type: string
                              agent_name:
                                type: string
                              agent_version:
                                type: string
                              obo_enabled:
                                type: boolean
              /chat:
                post:
                  operationId: chat
                  summary: Chat with the hosted agent
                  requestBody:
                    required: true
                    content:
                      application/json:
                        schema:
                          $ref: "#/components/schemas/ChatRequest"
                  responses:
                    "200":
                      description: Agent response
                      content:
                        application/json:
                          schema:
                            $ref: "#/components/schemas/ChatResponse"
              /chat/stream:
                post:
                  operationId: chatStream
                  summary: Chat with streaming (SSE)
                  requestBody:
                    required: true
                    content:
                      application/json:
                        schema:
                          $ref: "#/components/schemas/ChatRequest"
                  responses:
                    "200":
                      description: SSE stream
                      content:
                        text/event-stream:
                          schema:
                            type: string

            components:
              schemas:
                ChatRequest:
                  type: object
                  required:
                    - message
                  properties:
                    message:
                      type: string
                    conversation_history:
                      type: array
                      default: []
                      items:
                        type: object
                        properties:
                          role:
                            type: string
                          content:
                            type: string
                ChatResponse:
                  type: object
                  properties:
                    response:
                      type: string
                    conversation_history:
                      type: array
                      items:
                        type: object
                        properties:
                          role:
                            type: string
                          content:
                            type: string

              securitySchemes:
                oauth2:
                  type: oauth2
                  flows:
                    authorizationCode:
                      authorizationUrl: https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize
                      tokenUrl: https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token
                      refreshUrl: https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token
                      scopes:
                        api://{client_id}/access_as_user: Access the AI Foundry Agent API on behalf of the user
        """)

    with open(OPENAPI_OUTPUT, "w") as f:
        f.write(spec_content)

    console.print(f"  [green]✓[/] Wrote [bold]{OPENAPI_OUTPUT}[/]\n")

    # Show what was substituted
    console.print(Panel(
        f"[bold]Substitutions made:[/]\n\n"
        f"  [cyan]FQDN[/]       → {app_fqdn}\n"
        f"  [cyan]TENANT_ID[/]  → {tenant_id}\n"
        f"  [cyan]CLIENT_ID[/]  → {client_id}\n\n"
        f"[bold]File:[/] {OPENAPI_OUTPUT}\n\n"
        "[bold]To import into Copilot Studio:[/]\n"
        "  1. Open [cyan]Copilot Studio[/] → your copilot → [bold]Settings[/]\n"
        "  2. Go to [bold]Generative AI[/] → [bold]Custom connectors[/]\n"
        "  3. Click [bold]Add a connector[/] → [bold]Upload an OpenAPI file[/]\n"
        f"  4. Select [cyan]openapi-copilot-studio.yaml[/]\n"
        "  5. Authenticate with your Entra credentials\n"
        "  6. Test by asking: [italic]\"What types of dam inspections are required?\"[/]",
        title="📋 Copilot Studio Import Instructions",
        border_style="bright_blue",
    ))

    # ── Summary panel ────────────────────────────────────────────────────────
    test_status = "[green]✓ All tests passed[/]" if test_proc.returncode == 0 else "[yellow]⚠ Some tests had warnings[/]"
    console.print(Panel(
        f"[bold]Deployment Summary[/]\n\n"
        f"  Container App URL:  [cyan]{app_url}[/]\n"
        f"  Health endpoint:    [cyan]{app_url}/health[/]\n"
        f"  Chat endpoint:      [cyan]{app_url}/chat[/]\n"
        f"  Stream endpoint:    [cyan]{app_url}/chat/stream[/]\n"
        f"  OpenAPI docs:       [cyan]{app_url}/docs[/]\n\n"
        f"  Test results:       {test_status}\n"
        f"  OpenAPI export:     [cyan]{OPENAPI_OUTPUT}[/]\n\n"
        "[dim]The Container App uses Managed Identity with Azure AI User role.\n"
        "OBO auth is enabled if OBO_CLIENT_ID/SECRET/TENANT_ID are set in .env.[/]",
        title="✅ Exercise 6 Complete",
        border_style="bold green",
    ))


# ── Exercise Metadata ────────────────────────────────────────────────────────

EXERCISES = [
    {
        "num": "1", "title": "Exercise 1 — Connect to the Hosted Agent",
        "short": "Resolve the hosted agent by name and send a test message via the Responses API.",
        "why": "Before building an API, you need to know how to find and call a hosted agent.\n"
               "Environment-variable-driven agent selection means the same code works for any agent.",
        "concepts": "• project_client.agents.list() to discover hosted agents\n"
                    "• AZURE_AGENT_NAME + AZURE_AGENT_VERSION as deployment-time configuration\n"
                    "• Responses API with agent_reference (extra_body)\n"
                    "• Difference between stateless Responses API and hosted Agent Service v2",
        "builds_on": "Lab 03 Exercise 5 — agent deployment and agent_reference chat.",
        "summary": "Resolved a hosted agent by name using environment variables and sent a test\n"
                   "message via the Responses API with agent_reference. The agent is selected at\n"
                   "deployment time — swap AZURE_AGENT_NAME to point at a different agent.",
        "key_functions": "• project_client.agents.list() — discover agents in the project\n"
                          "• openai.responses.create(input=..., extra_body={\"agent_reference\": ...})\n"
                          "• os.environ.get(\"AZURE_AGENT_NAME\") — deployment-time agent selection",
        "code_pattern": "agent_name = os.environ.get(\"AZURE_AGENT_NAME\")\n"
                        "response = openai.responses.create(\n"
                        "    input=[{\"role\": \"user\", \"content\": question}],\n"
                        "    extra_body={\"agent_reference\": {\n"
                        "        \"name\": agent_name, \"version\": \"1\",\n"
                        "        \"type\": \"agent_reference\"}})",
        "looking_ahead": "Next we wrap this in FastAPI with Pydantic models for a production-ready API.",
    },
    {
        "num": "2", "title": "Exercise 2 — Build the FastAPI App",
        "short": "Create POST /chat and GET /health endpoints with Pydantic request/response models.",
        "why": "A raw Python script can't serve external callers like Copilot Studio.\n"
               "FastAPI + Pydantic gives you type-safe, documented REST endpoints.",
        "concepts": "• FastAPI app with POST /chat and GET /health\n"
                    "• Pydantic BaseModel for request validation and response serialization\n"
                    "• Conversation history passthrough for multi-turn\n"
                    "• Running with uvicorn",
        "builds_on": "Exercise 1's agent connection — now wrapped behind HTTP endpoints.",
        "summary": "Built a FastAPI application with POST /chat (send message, get response)\n"
                   "and GET /health (check agent config). Pydantic models validate input and\n"
                   "serialize output. Conversation history is passed through for multi-turn.",
        "key_functions": "• FastAPI() + @app.post(\"/chat\")\n"
                          "• ChatRequest(message=..., conversation_history=[...])\n"
                          "• ChatResponse(response=..., conversation_history=[...])\n"
                          "• uvicorn lab07_agent_api:app --reload",
        "code_pattern": "@app.post(\"/chat\", response_model=ChatResponse)\n"
                        "async def chat(body: ChatRequest, request: Request):\n"
                        "    openai_client = _get_openai_client(_extract_bearer(request))\n"
                        "    response = openai_client.responses.create(\n"
                        "        input=[...history + new message...],\n"
                        "        extra_body=_build_agent_reference(name, version))\n"
                        "    return ChatResponse(response=response.output_text, ...)",
        "looking_ahead": "Next we add streaming so Copilot Studio gets tokens in real time.",
    },
    {
        "num": "3", "title": "Exercise 3 — Add Streaming (SSE)",
        "short": "Stream agent responses token-by-token via Server-Sent Events.",
        "why": "Agent responses can take several seconds. Streaming gives users immediate\n"
               "feedback — critical for chat UX in Copilot Studio or custom frontends.",
        "concepts": "• Server-Sent Events (SSE) via FastAPI StreamingResponse\n"
                    "• Responses API stream=True + event.type == 'response.output_text.delta'\n"
                    "• SSE data format: data: {JSON}\\n\\n\n"
                    "• Completion signal: {\"type\": \"done\"}",
        "builds_on": "Exercise 2's /chat endpoint — now with streaming variant.",
        "summary": "Added POST /chat/stream that yields SSE events as the agent generates\n"
                   "tokens. Each delta event contains a JSON payload with the text fragment.\n"
                   "A final 'done' event signals completion with the full response text.",
        "key_functions": "• StreamingResponse(event_generator(), media_type=\"text/event-stream\")\n"
                          "• openai.responses.create(..., stream=True)\n"
                          "• event.type == \"response.output_text.delta\" → yield SSE data\n"
                          "• event.type == \"response.completed\" → yield done signal",
        "code_pattern": "async def event_generator():\n"
                        "    stream = openai.responses.create(input=..., stream=True)\n"
                        "    for event in stream:\n"
                        "        if event.type == \"response.output_text.delta\":\n"
                        "            yield f\"data: {json.dumps({'content': event.delta})}\\n\\n\"",
        "looking_ahead": "Next we add OBO authentication so calls run as the end user.",
    },
    {
        "num": "4", "title": "Exercise 4 — OBO Authentication",
        "short": "Exchange the caller's Bearer token for a Foundry token via MSAL On-Behalf-Of.",
        "why": "When Copilot Studio sends a request, it includes a user token. OBO ensures\n"
               "the agent runs as that user — inheriting their RBAC permissions and audit trail.",
        "concepts": "• MSAL ConfidentialClientApplication.acquire_token_on_behalf_of()\n"
                    "• OBO_CLIENT_ID, OBO_CLIENT_SECRET, OBO_TENANT_ID env vars\n"
                    "• Dual mode: OBO when Bearer present, DefaultAzureCredential for local dev\n"
                    "• Cognitive Services scope: https://cognitiveservices.azure.com/.default",
        "builds_on": "Root MCP server's OBO pattern — same env vars, same MSAL flow.",
        "summary": "Added OBO authentication using the same MSAL pattern as the root MCP server.\n"
                   "When a Bearer token is present, it's exchanged for a Cognitive Services token\n"
                   "via acquire_token_on_behalf_of(). Without a Bearer token, the API falls back\n"
                   "to DefaultAzureCredential for local development.",
        "key_functions": "• msal.ConfidentialClientApplication(client_id, client_credential, authority)\n"
                          "• app.acquire_token_on_behalf_of(user_assertion=bearer, scopes=[...])\n"
                          "• AzureOpenAI(azure_endpoint=..., api_key=obo_token) — OBO client\n"
                          "• _extract_bearer(request) — FastAPI dependency",
        "code_pattern": "def _get_openai_client(bearer_token=None):\n"
                        "    if bearer_token and _OBO_ENABLED:\n"
                        "        obo_token = _acquire_obo_token(bearer_token)\n"
                        "        return AzureOpenAI(api_key=obo_token, ...)\n"
                        "    return project_client.get_openai_client()  # local dev",
        "looking_ahead": "Next we containerize and deploy — same Docker pattern as the MCP server.",
    },
    {
        "num": "5", "title": "Exercise 5 — Container App Deployment",
        "short": "Dockerize the API and configure it for Azure Container Apps + Copilot Studio.",
        "why": "A local script isn't reachable from Copilot Studio. Container Apps give you\n"
               "a public HTTPS endpoint with env-var-driven configuration — swap agents by\n"
               "changing AZURE_AGENT_NAME, no code changes needed.",
        "concepts": "• Dockerfile (python:3.11-slim + uvicorn)\n"
                    "• Container App env vars for agent selection and OBO\n"
                    "• Copilot Studio HTTP connector configuration\n"
                    "• The escape hatch pattern: any Foundry agent → REST API",
        "builds_on": "Root repo's Dockerfile + deploy-infrastructure.ps1 pattern.",
        "summary": "Showed how to containerize the API with a Dockerfile matching the root\n"
                   "MCP server pattern, configure Container App env vars for agent selection\n"
                   "and OBO auth, and wire up Copilot Studio via an HTTP connector.",
        "key_functions": "• Dockerfile: FROM python:3.11-slim, uvicorn CMD\n"
                          "• AZURE_AGENT_NAME / AZURE_AGENT_VERSION — agent selection\n"
                          "• OBO_CLIENT_ID / OBO_CLIENT_SECRET / OBO_TENANT_ID — auth\n"
                          "• Copilot Studio HTTP connector: POST /chat with Bearer token",
        "code_pattern": "# No code to run — deployment configuration\n"
                        "# Container App env vars:\n"
                        "AZURE_AGENT_NAME=TvaDamSafetyInspector\n"
                        "AZURE_AGENT_VERSION=1\n"
                        "OBO_CLIENT_ID=<client-id>\n"
                        "OBO_CLIENT_SECRET=<secret>\n"
                        "OBO_TENANT_ID=<tenant-id>",
        "looking_ahead": "Next we build, deploy, test, and export the OpenAPI spec end-to-end.",
    },
    {
        "num": "6", "title": "Exercise 6 — Build, Deploy, Test & Export OpenAPI",
        "short": "Build the container in ACR, deploy to Container Apps, run the test suite, and write the Copilot Studio OpenAPI spec.",
        "why": "Exercises 1–5 explained the pieces. This exercise puts them all together\n"
               "in a single end-to-end run: image build → deploy → verify → export.",
        "concepts": "• az acr build — cloud-side Docker build in Azure Container Registry\n"
                    "• Container App deployment via deploy-lab07.sh (ARM REST API)\n"
                    "• Managed Identity + Azure AI User RBAC assignment\n"
                    "• Automated health check + full test suite\n"
                    "• OpenAPI spec templating with real FQDN, tenant ID, and client ID",
        "builds_on": "Exercises 1–5 — combines agent connection, FastAPI, streaming, OBO, and containerization.",
        "summary": "Built the Docker image in ACR, deployed (or updated) the Container App,\n"
                   "ran the full test suite against the live endpoint, and wrote\n"
                   "openapi-copilot-studio.yaml with real Azure values — ready to import\n"
                   "into Copilot Studio as a Custom Connector.",
        "key_functions": "• deploy-lab07.sh — end-to-end build + deploy + RBAC\n"
                          "• test_lab07_api.py — health, docs, chat, and streaming tests\n"
                          "• openapi-copilot-studio.yaml — production OpenAPI with real values\n"
                          "• Copilot Studio Custom Connector import workflow",
        "code_pattern": "# Run the full pipeline:\n"
                        "bash labs/lab07-aifoundry-agent-api/deploy-lab07.sh\n"
                        "python labs/lab07-aifoundry-agent-api/test_lab07_api.py https://<FQDN>\n"
                        "# → openapi-copilot-studio.yaml written with real values",
    },
]

# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from shared.exercise_menu import show_exercise_menu, show_exercise_intro, show_exercise_summary

    EXERCISE_FUNCS = {
        1: exercise_1_connect_to_agent,
        2: exercise_2_fastapi_app,
        3: exercise_3_streaming,
        4: exercise_4_obo_auth,
        5: exercise_5_container_deployment,
        6: exercise_6_build_deploy_test,
    }

    if "--intro-only" in sys.argv:
        show_lab_intro(wait_for_input=False)
        choice = console.input("\n[dim]Would you like to view exercise descriptions? (y/n): [/]").strip().lower()
        if choice == "y":
            show_exercise_menu("Lab 07 — AI Foundry Agent API", EXERCISES)
        raise SystemExit(0)

    # --exercise N  → run only exercise N
    selected = None
    if "--exercise" in sys.argv:
        idx = sys.argv.index("--exercise")
        if idx + 1 < len(sys.argv):
            try:
                selected = int(sys.argv[idx + 1])
            except ValueError:
                pass
        if selected not in EXERCISE_FUNCS:
            console.print(f"[bold red]Invalid exercise number. Choose from: {list(EXERCISE_FUNCS.keys())}[/]")
            raise SystemExit(1)

    console.print(Panel(
        "[bold]Lab 07 — AI Foundry Agent API[/]\n"
        "FastAPI + OBO + Streaming · Azure AI Foundry",
        style="bold green",
    ))

    if selected:
        ex_meta = EXERCISES[selected - 1]
        show_exercise_intro(ex_meta, func=EXERCISE_FUNCS[selected])
        EXERCISE_FUNCS[selected]()
        show_exercise_summary(ex_meta)
    else:
        show_lab_intro()

        for i, (ex_meta, ex_func) in enumerate(zip(EXERCISES, EXERCISE_FUNCS.values())):
            show_exercise_intro(ex_meta, func=ex_func)
            ex_func()
            show_exercise_summary(ex_meta)
            if i < len(EXERCISES) - 1:
                console.input("\n[dim]Press Enter to continue...[/]")

    console.print("\n[bold green]✓ Lab 07 complete![/]\n")
