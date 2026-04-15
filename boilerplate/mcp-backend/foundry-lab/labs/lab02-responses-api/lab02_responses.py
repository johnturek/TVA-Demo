"""
Lab 02 — Responses API
=======================
Demonstrates the OpenAI Responses API through the Azure AI Foundry SDK v2.0.
The Responses API is a newer, stateless alternative to chat completions with
built-in tool-use, web search, and file search capabilities.

Covers:
  - Basic text responses via responses.create()
  - Structured output with JSON schema
  - Built-in web search tool
  - Multi-turn with previous_response_id
  - Streaming responses

Prerequisites:
  pip install -r requirements.txt
  cp example.env .env   # fill in your values

Usage:
  python labs/lab02-responses-api/lab02_responses.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from rich.console import Console
from rich.panel import Panel
from shared.config import get_project_client, get_model_name

console = Console()
MODEL = get_model_name()


def section(title: str):
    console.print(f"\n[bold cyan]{'─' * 60}[/]")
    console.print(f"[bold cyan]  {title}[/]")
    console.print(f"[bold cyan]{'─' * 60}[/]\n")


# ── Lab Introduction ──────────────────────────────────────────────────────────

def show_lab_intro(wait_for_input=True):
    """Display an introduction explaining why this lab matters and what we will learn."""
    console.print(Panel(
        "[bold]Why This Lab?[/]\n\n"
        "In Lab 01 we used the Chat Completions API — the workhorse behind most LLM "
        "applications. Now we step up to the [cyan]Responses API[/], a newer interface "
        "that treats every interaction as a stateless request with built-in support for "
        "tools, structured output, and chained multi-turn conversations without managing "
        "message arrays yourself.\n\n"
        "[bold]Concepts Covered[/]\n\n"
        "  • [cyan]responses.create()[/] — the new endpoint and how it differs from "
        "chat.completions.create()\n"
        "  • [cyan]Structured output[/] — forcing the model to return valid JSON that "
        "conforms to a strict schema\n"
        "  • [cyan]Built-in web search[/] — grounding answers in real-time internet data "
        "with a single tool declaration\n"
        "  • [cyan]Stateless multi-turn[/] — chaining turns via previous_response_id "
        "instead of manually appending messages\n"
        "  • [cyan]Streaming[/] — receiving delta events from the Responses API\n\n"
        "[bold]How This Differs from Lab 01[/]\n\n"
        "Lab 01 required you to build and maintain the messages array yourself. The "
        "Responses API handles conversation state server-side and adds native tool "
        "integration — no extra plumbing needed. This is the API surface every subsequent "
        "lab will use.",
        title="🎓 Lab 02 — Responses API",
        border_style="bright_blue",
    ))
    if wait_for_input:
        console.input("\n[dim]Press Enter to continue...[/]")


# ── Exercise 1: Basic Response ────────────────────────────────────────────────

def exercise_1_basic_response():
    """Use the Responses API for a simple text generation."""
    section("Exercise 1 — Basic Response")

    client = get_project_client()
    openai = client.get_openai_client()

    input_text = "Explain how anomaly detection differs from time-series forecasting in the context of power grid monitoring."
    console.print(Panel(
        f"[bold]Input:[/]\n{input_text}",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    response = openai.responses.create(
        model=MODEL,
        input=input_text,
    )

    console.print(Panel(response.output_text, title="Responses API"))
    console.print(f"[dim]Response ID: {response.id}[/]")


# ── Exercise 2: Structured Output (JSON Schema) ──────────────────────────────

def exercise_2_structured_output():
    """Force the model to return structured JSON conforming to a schema."""
    section("Exercise 2 — Structured Output (JSON Schema)")

    client = get_project_client()
    openai = client.get_openai_client()

    input_text = "List 3 TVA generation facilities with their type, capacity in MW, and current operational status."
    console.print(Panel(
        f"[bold]Input:[/]\n{input_text}\n\n"
        f"[bold]Output format:[/] JSON Schema (tva_generation_assets)\n"
        f"[bold]Schema fields:[/] name, type, capacity_mw, status  ·  [bold]Strict:[/] True",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    response = openai.responses.create(
        model=MODEL,
        input=input_text,
        text={
            "format": {
                "type": "json_schema",
                "name": "tva_generation_assets",
                "schema": {
                    "type": "object",
                    "properties": {
                        "plants": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "capacity_mw": {"type": "number"},
                                    "status": {"type": "string"},
                                },
                                "required": ["name", "type", "capacity_mw", "status"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["plants"],
                    "additionalProperties": False,
                },
                "strict": True,
            }
        },
    )

    parsed = json.loads(response.output_text)
    console.print_json(json.dumps(parsed, indent=2))


# ── Exercise 3: Built-in Web Search Tool ──────────────────────────────────────

def exercise_3_web_search():
    """Leverage the built-in web_search tool for grounded answers."""
    section("Exercise 3 — Built-in Web Search Tool")

    client = get_project_client()
    openai = client.get_openai_client()

    input_text = "What are the latest FERC regulations affecting renewable energy integration for large federal utilities?"
    console.print(Panel(
        f"[bold]Input:[/]\n{input_text}\n\n"
        f"[bold]Tools:[/] web_search_preview",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    response = openai.responses.create(
        model=MODEL,
        tools=[{"type": "web_search_preview"}],
        input=input_text,
    )

    console.print(Panel(response.output_text, title="Web-Grounded Response"))

    # Show citations if available
    for item in response.output:
        if hasattr(item, "type") and item.type == "web_search_call":
            console.print(f"[dim]  Search query: {item.id}[/]")


# ── Exercise 4: Multi-Turn with previous_response_id ─────────────────────────

def exercise_4_multi_turn():
    """Chain responses using previous_response_id for stateless multi-turn."""
    section("Exercise 4 — Multi-Turn Responses")

    client = get_project_client()
    openai = client.get_openai_client()

    turn1_input = "What is intra-hour load forecasting?"
    turn2_input = "What machine learning models work best for 15-minute interval prediction?"
    turn3_input = "How do utilities account for behind-the-meter solar generation in these forecasts?"
    console.print(Panel(
        f"[bold]Turn 1:[/] {turn1_input}\n"
        f"[bold]Turn 2:[/] {turn2_input}\n"
        f"[bold]Turn 3:[/] {turn3_input}\n\n"
        f"[bold]Chaining:[/] Each turn references the previous via previous_response_id",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    # Turn 1
    r1 = openai.responses.create(
        model=MODEL,
        input=turn1_input,
    )
    console.print(Panel(r1.output_text, title="Turn 1"))

    # Turn 2 — references Turn 1
    r2 = openai.responses.create(
        model=MODEL,
        input=turn2_input,
        previous_response_id=r1.id,
    )
    console.print(Panel(r2.output_text, title="Turn 2 (follow-up)"))

    # Turn 3 — references Turn 2 (which chains to Turn 1)
    r3 = openai.responses.create(
        model=MODEL,
        input=turn3_input,
        previous_response_id=r2.id,
    )
    console.print(Panel(r3.output_text, title="Turn 3 (follow-up)"))


# ── Exercise 5: Streaming Responses ───────────────────────────────────────────

def exercise_5_streaming():
    """Stream a Responses API result token by token."""
    section("Exercise 5 — Streaming Responses")

    client = get_project_client()
    openai = client.get_openai_client()

    input_text = (
        "Write a detailed explanation of how a hydroelectric dam on the Tennessee River "
        "converts water flow into electricity. Cover the journey from reservoir to turbine "
        "to generator to transmission line, and explain why hydroelectric power is valuable "
        "for grid reliability. Use about 200 words."
    )
    console.print(Panel(
        f"[bold]Input:[/]\n{input_text}\n\n"
        f"[bold]Streaming:[/] enabled",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    console.print("[dim]Streaming:[/] ", end="")

    stream = openai.responses.create(
        model=MODEL,
        input=input_text,
        stream=True,
    )

    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)

    print()


# ── Exercise Metadata ─────────────────────────────────────────────────────────

EXERCISES = [
    {
        "num": "1", "title": "Exercise 1 — Basic Response",
        "short": "Your first Responses API call — the newer, more capable interface.",
        "why": "The Responses API is OpenAI's modern interface, designed for tool-use,\n"
               "structured output, and stateless multi-turn from the start.",
        "concepts": "• responses.create() vs. chat.completions.create()\n"
                    "• Response object structure (output, usage, id)\n"
                    "• Stateless design philosophy\n"
                    "• When to choose Responses API over Chat Completions",
        "builds_on": "Lab 01's completions foundation — introduces the newer API surface.",
        "summary": "Made a basic call to the Responses API — a simpler, more modern\n"
                   "alternative to Chat Completions. Instead of a messages array, you pass\n"
                   "a single 'input' string and get back 'output_text' directly.",
        "key_functions": "• openai.responses.create(model, input) — the new API call\n"
                         "• response.output_text — direct text output (no choices[0] nesting)\n"
                         "• response.id — unique response ID for chaining turns later",
        "code_pattern": "response = openai.responses.create(\n"
                        "    model=MODEL,\n"
                        "    input=\"Your question here\",\n"
                        ")\n"
                        "print(response.output_text)",
        "looking_ahead": "Next we force the model to return structured JSON with a strict schema.",
    },
    {
        "num": "2", "title": "Exercise 2 — Structured Output (JSON Schema)",
        "short": "Guarantee valid JSON output that matches your schema every time.",
        "why": "Downstream systems need reliable, parseable output. Structured output\n"
               "eliminates format errors and makes LLM responses machine-readable.",
        "concepts": "• JSON Schema as a response constraint\n"
                    "• response_format and text.format configuration\n"
                    "• Type-safe outputs for application integration\n"
                    "• Handling schema validation and edge cases",
        "builds_on": "Exercise 1's basic response — adds output structure constraints.",
        "summary": "Used the text.format parameter with a JSON schema to guarantee the\n"
                   "model returns valid, parseable JSON matching a defined structure. The\n"
                   "strict=True setting ensures 100% schema compliance — no parsing failures.",
        "key_functions": "• text={\"format\": {\"type\": \"json_schema\", ...}} — schema enforcement\n"
                         "• \"strict\": True — guarantees exact schema conformance\n"
                         "• json.loads(response.output_text) — safe JSON parsing\n"
                         "• \"additionalProperties\": False — prevents extra fields",
        "code_pattern": "response = openai.responses.create(\n"
                        "    model=MODEL, input=prompt,\n"
                        "    text={\"format\": {\n"
                        "        \"type\": \"json_schema\",\n"
                        "        \"name\": \"my_schema\",\n"
                        "        \"schema\": {...},\n"
                        "        \"strict\": True,\n"
                        "    }}\n"
                        ")",
        "looking_ahead": "Next we add a built-in web search tool for real-time information.",
    },
    {
        "num": "3", "title": "Exercise 3 — Built-in Web Search Tool",
        "short": "Extend the model beyond its training data with real-time web search.",
        "why": "Models have a knowledge cutoff. Web search grounds answers in current\n"
               "information — essential for news, pricing, docs, and live data.",
        "concepts": "• Built-in tool types (web_search_preview)\n"
                    "• Tool configuration and invocation\n"
                    "• Grounding: citations and source attribution\n"
                    "• tool_choice for controlling when tools are used",
        "builds_on": "Exercises 1-2's response handling — introduces tool usage.",
        "summary": "Added tools=[{\"type\": \"web_search_preview\"}] to the Responses API call,\n"
                   "enabling the model to search the web and ground answers in live data.\n"
                   "One line of configuration — no custom tool code needed.",
        "key_functions": "• tools=[{\"type\": \"web_search_preview\"}] — built-in web search\n"
                         "• response.output — inspect output items for tool call details\n"
                         "• item.type == \"web_search_call\" — search invocation metadata",
        "code_pattern": "response = openai.responses.create(\n"
                        "    model=MODEL,\n"
                        "    tools=[{\"type\": \"web_search_preview\"}],\n"
                        "    input=\"What are the latest...?\",\n"
                        ")",
        "looking_ahead": "Next we chain multiple turns statelessly using previous_response_id.",
    },
    {
        "num": "4", "title": "Exercise 4 — Multi-Turn Responses",
        "short": "Chain responses statelessly using previous_response_id.",
        "why": "Multi-turn is critical for assistants and copilots. The Responses API\n"
               "handles it statelessly — no conversation array management needed.",
        "concepts": "• previous_response_id for turn chaining\n"
                    "• Stateless multi-turn vs. stateful conversation arrays\n"
                    "• Server-side context management\n"
                    "• Conversation branching and forking",
        "builds_on": "Lab 01 Ex.5's multi-turn concept, reimagined with stateless chaining.",
        "summary": "Chained 3 conversation turns using previous_response_id — the Responses\n"
                   "API handles context server-side, so you never build or manage a messages\n"
                   "array. Each call references the prior response and the server fills in\n"
                   "the conversation history automatically.",
        "key_functions": "• previous_response_id=r1.id — chain to previous turn\n"
                         "• Server-side state: no messages array to manage\n"
                         "• Each response.id becomes the link for the next turn",
        "code_pattern": "r1 = openai.responses.create(model=MODEL, input=\"Turn 1\")\n"
                        "r2 = openai.responses.create(\n"
                        "    model=MODEL, input=\"Turn 2\",\n"
                        "    previous_response_id=r1.id,  # chains context\n"
                        ")",
        "looking_ahead": "Next we add streaming to the Responses API with typed events.",
    },
    {
        "num": "5", "title": "Exercise 5 — Streaming Responses",
        "short": "Stream Responses API output with richer event types.",
        "why": "Streaming in the Responses API includes structured events for tool calls,\n"
               "content deltas, and completion — enabling richer real-time UIs.",
        "concepts": "• Response streaming event types and structure\n"
                    "• Content delta handling and reassembly\n"
                    "• Tool-call events in the stream\n"
                    "• Differences from Chat Completions streaming",
        "builds_on": "Lab 01 Ex.4's streaming + all Responses API patterns from this lab.",
        "summary": "Streamed Responses API output using typed events. Unlike Chat Completions\n"
                   "(which uses delta.content), the Responses API emits structured event types\n"
                   "like 'response.output_text.delta' — enabling richer real-time UIs with\n"
                   "tool-call events, content deltas, and completion signals.",
        "key_functions": "• stream=True — enables streaming on responses.create()\n"
                         "• event.type == \"response.output_text.delta\" — text chunks\n"
                         "• event.delta — the incremental text content\n"
                         "• Typed events vs. Chat Completions' generic chunks",
        "code_pattern": "stream = openai.responses.create(model=MODEL, input=..., stream=True)\n"
                        "for event in stream:\n"
                        "    if event.type == \"response.output_text.delta\":\n"
                        "        print(event.delta, end=\"\", flush=True)",
    },
]

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from shared.exercise_menu import show_exercise_menu, show_exercise_intro, show_exercise_summary

    EXERCISE_FUNCS = {
        1: exercise_1_basic_response,
        2: exercise_2_structured_output,
        3: exercise_3_web_search,
        4: exercise_4_multi_turn,
        5: exercise_5_streaming,
    }

    if "--intro-only" in sys.argv:
        show_lab_intro(wait_for_input=False)
        choice = console.input("\n[dim]Would you like to view exercise descriptions? (y/n): [/]").strip().lower()
        if choice == "y":
            show_exercise_menu("Lab 02 — Responses API", EXERCISES)
        raise SystemExit(0)

    # --exercise N  → run only exercise N (e.g. --exercise 2)
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

    console.print(Panel("[bold]Lab 02 — Responses API[/]\n"
                        "Azure AI Foundry SDK v2.0 · OpenAI Responses API",
                        style="bold green"))

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

    console.print("\n[bold green]✓ Lab 02 complete![/]\n")
