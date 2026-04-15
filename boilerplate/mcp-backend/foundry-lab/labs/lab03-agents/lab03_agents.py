"""
Lab 03 — Agents (Responses API + Agent Service v2)
====================================================
Demonstrates building AI agents using the OpenAI Responses API through the
Azure AI Foundry SDK v2.0, then graduates to the Agent Service v2 with
declarative YAML agent definitions deployed as hosted agents.

Covers:
  - Agent with system instructions (responses.create + instructions)
  - Tool integration (Code Interpreter)
  - Function calling with custom tools and agentic loop
  - Streaming agent responses
  - Agent-as-Code: Declarative YAML → Agent Service v2 (hosted, portal-visible)

Prerequisites:
  pip install --user -r requirements.txt
  cp example.env .env   # fill in your values

Usage:
  python labs/lab03-agents/lab03_agents.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
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
        "So far we have sent prompts and received answers — a request-response pattern. "
        "Real-world tasks are rarely one-shot. An [cyan]agent[/] can reason about a "
        "problem, decide which tools to invoke, execute code, and loop until it arrives "
        "at a complete answer. This lab teaches you to build that loop — and then "
        "graduate to deploying agents as durable, version-controlled resources.\n\n"
        "[bold]Concepts Covered[/]\n\n"
        "  • [cyan]Agent instructions[/] — persistent system-level guidance that shapes "
        "agent behavior across turns\n"
        "  • [cyan]Code Interpreter[/] — letting the agent write and execute Python in a "
        "sandboxed container to compute answers\n"
        "  • [cyan]Custom tool (function) calling[/] — defining your own tools and wiring "
        "them into an agentic loop\n"
        "  • [cyan]The agentic loop[/] — the resolve-and-continue pattern where the agent "
        "calls tools, receives results, and decides its next step\n"
        "  • [cyan]Streaming agent runs[/] — watching the agent think in real time\n"
        "  • [cyan]Agent-as-Code[/] — declarative YAML definitions pushed to Foundry "
        "Agent v2 via the SDK, with conversations + Responses API\n\n"
        "[bold]How This Differs from Labs 01–02[/]\n\n"
        "Labs 01 and 02 were purely conversational — ask a question, get text back. Here "
        "the model becomes an [bold]actor[/]: it can call functions, run code, and iterate "
        "until the task is done. In Exercise 5, we go further — the agent becomes a "
        "[bold]managed resource[/] in your Foundry project, with durable conversations "
        "and a path to production via the Responses API.",
        title="🎓 Lab 03 — Agents (Responses API + Foundry Agent v2)",
        border_style="bright_blue",
    ))
    if wait_for_input:
        console.input("\n[dim]Press Enter to continue...[/]")


# ── Exercise 1: Basic Agent with Instructions ────────────────────────────────

def exercise_1_basic_agent():
    """Use the Responses API with system instructions as an agent."""
    section("Exercise 1 — Basic Agent")

    client = get_project_client()
    openai = client.get_openai_client()

    instructions = (
        "You are a TVA power systems data scientist. "
        "Provide clear, concise explanations with practical examples from energy operations. "
        "When discussing algorithms, include time complexity."
    )
    input_text = "Compare ARIMA and Prophet for weekly hydro generation forecasting at a dam like Chickamauga. When should I use each?"
    console.print(Panel(
        f"[bold]Instructions:[/]\n{instructions}\n\n"
        f"[bold]Input:[/]\n{input_text}",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    response = openai.responses.create(
        model=MODEL,
        instructions=instructions,
        input=input_text,
    )

    console.print(f"[green]Response ID:[/] {response.id}")
    console.print(Panel(response.output_text, title="Agent Response"))


# ── Exercise 2: Agent with Code Interpreter ───────────────────────────────────

def exercise_2_code_interpreter():
    """Agent that writes and executes Python code to solve problems."""
    section("Exercise 2 — Agent with Code Interpreter")

    if os.environ.get("DISABLE_CODE_INTERPRETER_LAB", "").lower() in ("true", "1", "yes"):
        console.print(Panel(
            "[yellow]⚠ Skipped:[/] DISABLE_CODE_INTERPRETER_LAB is set.\n\n"
            "Code Interpreter containers may not be available in your region or project.\n"
            "Unset the variable or set it to false to try this exercise.",
            title="Exercise 2 — Skipped", border_style="yellow",
        ))
        return

    client = get_project_client()
    openai = client.get_openai_client()

    instructions = (
        "You are a TVA energy analyst. When asked questions, "
        "write and execute Python code to compute the answer. "
        "Always show your work and interpret the results."
    )
    input_text = (
        "Generate a dataset of 8760 hourly load samples for a year "
        "(mean=2800 MW, std=400), compute monthly descriptive statistics, perform "
        "an ADF stationarity test, and identify the top 5 peak demand hours. Report the results."
    )
    console.print(Panel(
        f"[bold]Instructions:[/]\n{instructions}\n\n"
        f"[bold]Input:[/]\n{input_text}\n\n"
        f"[bold]Tools:[/] code_interpreter (container: auto)",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    console.print("[dim]Streaming response (container may take a moment to start)…[/]")

    stream = openai.responses.create(
        model=MODEL,
        instructions=instructions,
        input=input_text,
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        include=["code_interpreter_call.outputs"],
        stream=True,
    )

    # Collect streamed events and display progress incrementally
    code_buffer = ""
    text_buffer = ""
    in_code = False

    for event in stream:
        etype = event.type

        # Code interpreter starts writing code
        if etype == "response.code_interpreter_call.code.delta":
            if not in_code:
                in_code = True
                code_buffer = ""
                console.print("[dim]  🖥️  Code Interpreter writing code…[/]")
            code_buffer += event.delta

        # Code finished — show it
        if etype == "response.code_interpreter_call.code.done":
            in_code = False
            if code_buffer:
                console.print(Panel(
                    Syntax(code_buffer, "python", theme="monokai"),
                    title="🐍 Generated Python Code",
                    border_style="green",
                ))
                code_buffer = ""

        # Execution output from the sandbox
        if etype == "response.code_interpreter_call.output":
            if hasattr(event, "text") and event.text:
                console.print(Panel(event.text, title="📊 Execution Output", border_style="yellow"))
            elif hasattr(event, "logs") and event.logs:
                console.print(Panel(event.logs, title="📊 Execution Output", border_style="yellow"))

        # Streamed assistant text
        if etype == "response.output_text.delta":
            print(event.delta, end="", flush=True)
            text_buffer += event.delta

        if etype == "response.output_text.done":
            if text_buffer:
                print()
                text_buffer = ""


# ── Exercise 3: Agent with Tool Calling ────────────────────────────────────────

def exercise_3_function_calling():
    """Agent that calls user-defined functions in an agentic loop."""
    section("Exercise 3 — Agent with Tool Calling")

    client = get_project_client()
    openai = client.get_openai_client()

    # Define custom tool functions
    tools = [
        {
            "type": "function",
            "name": "get_plant_status",
            "description": "Returns real-time status of a TVA generation plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "Name of the TVA plant (e.g., 'Watts Bar', 'Chickamauga').",
                    }
                },
                "required": ["plant_name"],
            },
        },
        {
            "type": "function",
            "name": "query_load_forecast",
            "description": "Query the load forecast for a TVA service area.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "TVA region (e.g., 'Eastern', 'Western', 'Middle').",
                    },
                    "hours_ahead": {
                        "type": "integer",
                        "description": "Forecast horizon in hours.",
                    },
                },
                "required": ["region", "hours_ahead"],
            },
        },
    ]

    INSTRUCTIONS = (
        "You are a TVA grid operations analyst. Use the available tools to check plant status "
        "and load forecasts. Summarize findings clearly for the operations center."
    )

    # Simulated function implementations
    def handle_tool_call(name: str, arguments: dict) -> str:
        if name == "get_plant_status":
            return json.dumps({
                "name": arguments["plant_name"],
                "type": "nuclear",
                "capacity_mw": 2330,
                "current_output_mw": 2285,
                "status": "online",
                "fuel_type": "uranium",
            })
        elif name == "query_load_forecast":
            return json.dumps({
                "region": arguments["region"],
                "hours_ahead": arguments["hours_ahead"],
                "forecast": [
                    {"hour": 1, "load_mw": 14200, "temperature_f": 28},
                    {"hour": 12, "load_mw": 17800, "temperature_f": 24},
                    {"hour": 24, "load_mw": 16500, "temperature_f": 26},
                    {"hour": 48, "load_mw": 18400, "temperature_f": 22},
                ],
                "peak_load_mw": 18400,
                "available_capacity_mw": 20100,
                "reserve_margin_pct": 9.2,
            })
        return json.dumps({"error": f"Unknown function: {name}"})

    # Initial request
    input_text = (
        "What's the current status of the Watts Bar plant? Also get the 48-hour load forecast "
        "for the Eastern region and advise if we need additional generation capacity."
    )
    tool_names = ", ".join(t["name"] for t in tools)
    console.print(Panel(
        f"[bold]Instructions:[/]\n{INSTRUCTIONS}\n\n"
        f"[bold]Input:[/]\n{input_text}\n\n"
        f"[bold]Tools:[/] {tool_names}",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    response = openai.responses.create(
        model=MODEL,
        instructions=INSTRUCTIONS,
        input=input_text,
        tools=tools,
    )

    # Agentic loop: keep resolving function calls until the model produces text
    while any(item.type == "function_call" for item in response.output):
        tool_outputs = []
        for item in response.output:
            if item.type == "function_call":
                args = json.loads(item.arguments)
                result = handle_tool_call(item.name, args)
                console.print(f"[yellow]  Tool call: {item.name}({args})[/]")
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result,
                })

        response = openai.responses.create(
            model=MODEL,
            instructions=INSTRUCTIONS,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=tools,
        )

    console.print(Panel(response.output_text, title="Data Analyst Response"))


# ── Exercise 4: Streaming Agent Run ───────────────────────────────────────────

def exercise_4_streaming():
    """Stream agent responses token by token."""
    section("Exercise 4 — Streaming Agent Run")

    client = get_project_client()
    openai = client.get_openai_client()

    instructions = "You are a concise, helpful assistant."
    input_text = "Write a step-by-step guide for deploying a real-time vegetation encroachment detection model to edge devices on TVA transmission line inspection drones."
    console.print(Panel(
        f"[bold]Instructions:[/]\n{instructions}\n\n"
        f"[bold]Input:[/]\n{input_text}\n\n"
        f"[bold]Streaming:[/] enabled",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    console.print("[dim]Streaming agent response:[/]")

    stream = openai.responses.create(
        model=MODEL,
        instructions=instructions,
        input=input_text,
        stream=True,
    )

    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)

    print()


# ── Exercise 5: Agent-as-Code — YAML → Agent Service v2 (Portal-Visible) ─────

def exercise_5_agent_as_code():
    """Define an agent in YAML, deploy it to Agent Service v2 (visible in portal)."""
    section("Exercise 5 — Agent-as-Code: YAML → Agent Service v2 (Hosted)")

    import re
    import yaml

    # ── Step 1: Load the YAML agent definition ────────────────────────────
    yaml_path = os.path.join(os.path.dirname(__file__), "agents", "dam-safety-inspector.yaml")
    console.print(f"[dim]Loading agent definition from:[/] {yaml_path}\n")

    with open(yaml_path) as f:
        yaml_str = f.read()

    # Resolve =Env.VAR_NAME references to actual environment variable values.
    def _resolve_env_refs(raw: str) -> str:
        return re.sub(
            r"=Env\.(\w+)",
            lambda m: os.environ.get(m.group(1), m.group(0)),
            raw,
        )

    yaml_str = _resolve_env_refs(yaml_str)
    agent_def = yaml.safe_load(yaml_str)

    agent_name = agent_def["name"]
    agent_model = agent_def["model"]["id"]
    agent_instructions = agent_def.get("instructions", "You are a helpful assistant.")
    agent_description = agent_def.get("description", "").strip()

    from rich.syntax import Syntax
    console.print(Panel(
        Syntax(yaml_str, "yaml", theme="monokai", word_wrap=True),
        title="📄 YAML Agent Definition", border_style="bright_magenta",
    ))

    # ── Step 2: Deploy agent to Agent Service v2 ─────────────────────────
    console.print("[bold]Deploying agent to Agent Service v2 (hosted)…[/]")

    project_client = get_project_client()

    # Check if the agent already exists; reuse it if so.
    existing_agent = None
    try:
        for a in project_client.agents.list():
            if a.name == agent_name:
                existing_agent = a
                break
    except Exception:
        pass

    if existing_agent:
        console.print(f"[yellow]Agent '{agent_name}' already exists — reusing (id={existing_agent.id}).[/]")
        agent = existing_agent
    else:
        agent = project_client.agents.create_version(
            agent_name=agent_name,
            body={
                "definition": {
                    "kind": "prompt",
                    "model": agent_model,
                    "instructions": agent_instructions,
                    "description": agent_description,
                },
            }
        )
        console.print(f"[green]✓ Agent created in Agent Service v2:[/] name={agent.name}  id={agent.id}")

    console.print(
        "[dim]This agent is now visible in the AI Foundry portal under your project's Agents tab.[/]\n"
    )

    # ── Step 3: Chat with the hosted agent via Responses API ─────────────
    openai_client = project_client.get_openai_client()

    # Extract version from agent id (e.g. "TvaDamSafetyInspector:1" → "1")
    agent_version = agent.id.split(":")[-1] if ":" in agent.id else "1"

    user_question = (
        "What are the different types of dam inspections TVA performs, "
        "and how often is each type required?"
    )
    console.print("[bold]Chatting with hosted agent via Responses API…[/]")
    console.print(Panel(user_question, title="👤 User Message", border_style="cyan"))

    response = openai_client.responses.create(
        input=[{"role": "user", "content": user_question}],
        extra_body={"agent_reference": {"name": agent.name, "version": agent_version, "type": "agent_reference"}},
    )

    console.print(Panel(
        response.output_text,
        title="🏗️ Dam Safety Inspector Response",
        border_style="green",
    ))

    # ── Step 4: Multi-turn — follow-up using conversation history ────────
    followup = "What instrumentation is required, and what triggers a Red action level?"
    console.print(Panel(followup, title="👤 Follow-up Message", border_style="cyan"))

    conversation = [
        {"role": "user", "content": user_question},
        {"role": "assistant", "content": response.output_text},
        {"role": "user", "content": followup},
    ]

    response2 = openai_client.responses.create(
        input=conversation,
        extra_body={"agent_reference": {"name": agent.name, "version": agent_version, "type": "agent_reference"}},
    )

    console.print(Panel(
        response2.output_text,
        title="🏗️ Dam Safety Inspector Follow-up",
        border_style="green",
    ))

    # ── Step 5: Cleanup prompt ───────────────────────────────────────────
    console.print(Panel(
        f"[bold]The agent '[cyan]{agent_name}[/cyan]' is now a hosted resource in your "
        "Foundry project.[/]\n\n"
        "You can see it at [link=https://ai.azure.com]ai.azure.com[/link] → your project → Agents.\n\n"
        "To delete it later:\n"
        f"  [dim]project_client.agents.delete(agent_name='{agent_name}')[/dim]",
        title="🌐 Agent Visible in Portal",
        border_style="bright_green",
    ))

    console.print(Panel(
        "[bold yellow]What Changed?[/]\n\n"
        "Exercises 1–4 used the [cyan]Responses API[/] directly — stateless, "
        "ephemeral, defined entirely in code.\n\n"
        "This exercise reads a [cyan]declarative YAML definition[/] and deploys it "
        "as a [bold]hosted agent[/] via the [bold]Agent Service v2 API[/] "
        "([cyan]project_client.agents.create_version()[/cyan]).\n\n"
        "  • The agent is [bold]registered in your Foundry project[/] and visible in the portal\n"
        "  • Chat uses the [bold]Responses API[/] with an [cyan]agent_reference[/] — the hosted "
        "agent's instructions and model are resolved server-side\n"
        "  • Multi-turn history is managed via conversation arrays\n\n"
        "The same YAML file can be version-controlled in Git, deployed via CI/CD, "
        "and managed programmatically through the SDK.",
        title="🚀 Declarative Agents — From Code to Hosted Service",
        border_style="bright_blue",
    ))


# ── Exercise Metadata ─────────────────────────────────────────────────────────

EXERCISES = [
    {
        "num": "1", "title": "Exercise 1 — Basic Agent",
        "short": "Create an agent with system instructions — the foundation of autonomy.",
        "why": "Agents are the building block of autonomous AI. Defining clear instructions\n"
               "turns a generic model into a specialized, goal-oriented assistant.",
        "concepts": "• Agent = instructions + model + tools\n"
                    "• System instructions as agent identity and constraints\n"
                    "• Agent lifecycle: create → invoke → inspect output\n"
                    "• Difference between agents and raw completions",
        "builds_on": "Lab 02's Responses API — adds the agent abstraction layer.",
        "summary": "Created an agent by adding the 'instructions' parameter to responses.create().\n"
                   "Unlike system messages in Chat Completions, instructions are a first-class\n"
                   "agent concept — they define persistent behavior across turns and tool calls.",
        "key_functions": "• instructions parameter — persistent agent-level guidance\n"
                         "• responses.create(model, instructions, input) — agent invocation\n"
                         "• response.id — for chaining with previous_response_id",
        "code_pattern": "response = openai.responses.create(\n"
                        "    model=MODEL,\n"
                        "    instructions=\"You are a specialist...\",\n"
                        "    input=\"Your question here\",\n"
                        ")",
        "looking_ahead": "Next we give the agent a Code Interpreter tool to write and execute code.",
    },
    {
        "num": "2", "title": "Exercise 2 — Agent with Code Interpreter",
        "short": "Give agents the power to write and execute code in a sandbox.",
        "why": "Code Interpreter lets agents do math, analyze data, and create files —\n"
               "capabilities that pure text generation cannot reliably provide.",
        "concepts": "• Code Interpreter tool and sandboxed execution\n"
                    "• Input/output file handling\n"
                    "• When the model decides to write code vs. answer directly\n"
                    "• Security boundaries of the sandbox",
        "builds_on": "Exercise 1's agent setup — adds a powerful built-in tool.",
        "summary": "Added Code Interpreter as a tool — the agent autonomously wrote Python\n"
                   "code, executed it in a sandboxed container, and interpreted the results.\n"
                   "The model decides when to write code vs. answer directly.",
        "key_functions": "• tools=[{\"type\": \"code_interpreter\", \"container\": {\"type\": \"auto\"}}]\n"
                         "• include=[\"code_interpreter_call.outputs\"] — get execution output\n"
                         "• item.type == \"code_interpreter_call\" — detect code execution\n"
                         "• item.code / item.results — inspect generated code and output",
        "code_pattern": "response = openai.responses.create(\n"
                        "    model=MODEL, instructions=..., input=...,\n"
                        "    tools=[{\"type\": \"code_interpreter\",\n"
                        "            \"container\": {\"type\": \"auto\"}}],\n"
                        "    include=[\"code_interpreter_call.outputs\"],\n"
                        ")",
        "looking_ahead": "Next we define custom tools and build the core agentic loop pattern.",
    },
    {
        "num": "3", "title": "Exercise 3 — Agent with Tool Calling",
        "short": "Define custom functions the agent can call — connect AI to your systems.",
        "why": "Custom tools are how agents interact with databases, APIs, and business\n"
               "logic. This is the bridge between AI reasoning and real-world action.",
        "concepts": "• Function tool definitions (name, description, parameters JSON schema)\n"
                    "• The agentic loop: model calls tool → you execute → return result\n"
                    "• Tool choice and when the model decides to call a function\n"
                    "• Handling multiple sequential tool calls",
        "builds_on": "Exercise 2's tool concept — moves from built-in to custom-defined tools.",
        "summary": "Defined custom function tools with JSON Schema parameters and implemented\n"
                   "the agentic loop — the foundational pattern where: (1) the model requests\n"
                   "tool calls, (2) you execute them locally, (3) you return results, and\n"
                   "(4) the model either calls more tools or produces a final answer.",
        "key_functions": "• tools=[{\"type\": \"function\", \"name\": ..., \"parameters\": ...}]\n"
                         "• item.type == \"function_call\" — detect tool call requests\n"
                         "• json.loads(item.arguments) — parse tool call arguments\n"
                         "• {\"type\": \"function_call_output\", \"call_id\": ..., \"output\": ...}\n"
                         "• previous_response_id — chain tool results back to the agent",
        "code_pattern": "while any(item.type == \"function_call\" for item in response.output):\n"
                        "    tool_outputs = []\n"
                        "    for item in response.output:\n"
                        "        if item.type == \"function_call\":\n"
                        "            result = execute_tool(item.name, item.arguments)\n"
                        "            tool_outputs.append({\"type\": \"function_call_output\",\n"
                        "                \"call_id\": item.call_id, \"output\": result})\n"
                        "    response = openai.responses.create(\n"
                        "        previous_response_id=response.id, input=tool_outputs, ...)",
        "looking_ahead": "Next we add streaming to watch agent execution in real time.",
    },
    {
        "num": "4", "title": "Exercise 4 — Streaming Agent Run",
        "short": "Stream agent execution for real-time visibility into long-running tasks.",
        "why": "Agent runs can take many seconds as the model reasons and calls tools.\n"
               "Streaming gives users immediate feedback and progress visibility.",
        "concepts": "• Streaming agent runs with event-driven processing\n"
                    "• Event types: text deltas, tool calls, tool results\n"
                    "• Real-time progress display during agentic loops\n"
                    "• Combining streaming with tool execution",
        "builds_on": "All previous agent exercises + Lab 01-02 streaming concepts.",
        "summary": "Combined agent instructions with stream=True to stream an agent's\n"
                   "response token-by-token. The event types are the same as Lab 02's\n"
                   "streaming — 'response.output_text.delta' — but now with agent context.",
        "key_functions": "• responses.create(instructions=..., input=..., stream=True)\n"
                         "• event.type == \"response.output_text.delta\" — streaming text\n"
                         "• Combines: instructions + streaming in one call",
        "code_pattern": "stream = openai.responses.create(\n"
                        "    model=MODEL, instructions=..., input=..., stream=True)\n"
                        "for event in stream:\n"
                        "    if event.type == \"response.output_text.delta\":\n"
                        "        print(event.delta, end=\"\", flush=True)",
        "looking_ahead": "Next we graduate from stateless Responses API to the Agent Service v2:\n"
                         "define an agent in YAML and deploy it as a hosted, portal-visible agent.",
    },
    {
        "num": "5", "title": "Exercise 5 — Agent-as-Code: YAML → Agent Service v2 (Hosted)",
        "short": "Define an agent in YAML, deploy it to Agent Service v2 — visible in the portal.",
        "why": "Exercises 1–4 used the Responses API — stateless, ephemeral, defined in code.\n"
               "Production agents need to be version-controlled, reviewable, and discoverable.\n"
               "Agent-as-Code + Agent Service v2 makes your agent a hosted, portal-visible resource.",
        "concepts": "• Declarative YAML agent definition (kind, name, model, instructions)\n"
                    "• Agent Service v2 — project_client.agents.create_version() registers a hosted agent\n"
                    "• Responses API with agent_reference — chat with hosted agents\n"
                    "• Conversation history arrays for multi-turn\n"
                    "• Environment variable references (=Env.VAR) in YAML",
        "builds_on": "All previous exercises — now we move from ad-hoc to hosted, portal-visible agents.",
        "summary": "Loaded an agent definition from a declarative YAML file, deployed it to\n"
                   "Agent Service v2 via project_client.agents.create_version(), and chatted with it\n"
                   "using the Responses API with an agent_reference. The agent is now visible\n"
                   "in the AI Foundry portal under your project's Agents tab.",
        "key_functions": "• project_client.agents.create_version(agent_name=..., body={...}) — register hosted agent\n"
                          "• project_client.agents.list() — discover existing agents\n"
                          "• openai.responses.create(input=..., extra_body={\"agent\": ...}) — chat\n"
                          "• Conversation history arrays for multi-turn context\n"
                          "• project_client.agents.delete(agent_name=...) — cleanup",
        "code_pattern": "# Load YAML → deploy to Agent Service v2\n"
                        "agent_def = yaml.safe_load(yaml_str)\n"
                        "agent = project_client.agents.create_version(\n"
                        "    agent_name=agent_def['name'],\n"
                        "    body={'definition': {'kind': 'prompt',\n"
                        "        'model': agent_def['model']['id'],\n"
                        "        'instructions': agent_def['instructions']}}\n"
                        ")\n"
                        "# Chat via Responses API with agent reference\n"
                        "response = openai.responses.create(\n"
                        "    input=[{'role': 'user', 'content': '...'}],\n"
                        "    extra_body={'agent_reference': {'name': agent.name,\n"
                        "        'version': version, 'type': 'agent_reference'}})",
    },
]

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from shared.exercise_menu import show_exercise_menu, show_exercise_intro, show_exercise_summary

    EXERCISE_FUNCS = {
        1: exercise_1_basic_agent,
        2: exercise_2_code_interpreter,
        3: exercise_3_function_calling,
        4: exercise_4_streaming,
        5: exercise_5_agent_as_code,
    }

    if "--intro-only" in sys.argv:
        show_lab_intro(wait_for_input=False)
        choice = console.input("\n[dim]Would you like to view exercise descriptions? (y/n): [/]").strip().lower()
        if choice == "y":
            show_exercise_menu("Lab 03 — Agents", EXERCISES)
        raise SystemExit(0)

    # --exercise N  → run only exercise N (e.g. --exercise 5)
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
        "[bold]Lab 03 — Agents[/]\n"
        "Responses API + Agent Service v2 · Azure AI Foundry",
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

    console.print("\n[bold green]✓ Lab 03 complete![/]\n")
