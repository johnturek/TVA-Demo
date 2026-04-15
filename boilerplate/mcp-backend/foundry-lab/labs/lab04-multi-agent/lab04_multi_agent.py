"""
Lab 04 — Multi-Agent Architectures
====================================
Demonstrates multi-agent orchestration patterns using the OpenAI Responses API
through the Azure AI Foundry SDK v2.0. Each "agent" is a stateless call to
responses.create with distinct instructions; orchestration is pure Python.

Patterns covered:
  - Sequential pipeline (output of agent A feeds agent B)
  - Parallel fan-out / fan-in
  - Supervisor / worker hierarchy
  - Critic / refinement loop
  - Foundry Workflow Agent (server-side orchestrated agent flow)

Prerequisites:
  pip install -r requirements.txt
  cp example.env .env

Usage:
  python labs/lab04-multi-agent/lab04_multi_agent.py
"""

import sys, os, json, re
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


def run_agent_turn(openai_client, instructions: str, user_message: str) -> str:
    """Helper: send a single turn to the Responses API and return text."""
    response = openai_client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=user_message,
    )
    return response.output_text


# ── Lab Introduction ──────────────────────────────────────────────────────────

def show_lab_intro(wait_for_input=True):
    """Display an introduction explaining why this lab matters and what we will learn."""
    console.print(Panel(
        "[bold]Why This Lab?[/]\n\n"
        "A single agent is powerful, but real enterprise workflows require [cyan]multiple "
        "specialized agents[/] working together — just like a team of human experts. "
        "This lab explores five orchestration patterns that let you compose agents into "
        "systems greater than the sum of their parts.\n\n"
        "[bold]Concepts Covered[/]\n\n"
        "  • [cyan]Sequential pipeline[/] — output of one agent feeds the next in a chain\n"
        "  • [cyan]Parallel fan-out / fan-in[/] — multiple specialists analyze independently, "
        "then a synthesizer merges their findings\n"
        "  • [cyan]Supervisor / worker[/] — a supervisor decomposes a task into sub-tasks "
        "and delegates to workers\n"
        "  • [cyan]Critic / refinement loop[/] — a generator produces work, a critic "
        "reviews it, and they iterate until approval\n"
        "  • [cyan]Foundry Workflow Agent[/] — server-side orchestrated agent flow using "
        "the Foundry conversations API\n\n"
        "[bold]How This Differs from Lab 03[/]\n\n"
        "Lab 03 built a [bold]single[/] agent with tools. Here we orchestrate [bold]"
        "multiple[/] agents — each with its own persona and instructions — using pure "
        "Python orchestration on the client side. The final pattern shows server-side "
        "orchestration via the Foundry Workflow API.",
        title="🎓 Lab 04 — Multi-Agent Architectures",
        border_style="bright_blue",
    ))
    if wait_for_input:
        console.input("\n[dim]Press Enter to continue...[/]")


# ── Pattern 1: Sequential Pipeline ───────────────────────────────────────────

def pattern_1_sequential_pipeline():
    """Agent A (data engineer) → Agent B (load forecaster) → Agent C (grid dispatcher)."""
    section("Pattern 1 — Sequential Pipeline: Data Engineer → Load Forecaster → Grid Dispatcher")

    client = get_project_client()
    openai = client.get_openai_client()

    researcher_instructions = (
        "You are a TVA data engineer in a public energy-policy planning exercise "
        "using only public-domain information. Given a topic, produce a structured "
        "outline of the historical load data, weather patterns, and generation "
        "assets relevant to a 48-hour dispatch plan. "
        "Output only the outline — no prose."
    )
    writer_instructions = (
        "You are a TVA load forecaster in a public energy-policy planning exercise "
        "using only public-domain information. Given a data outline, produce a "
        "well-structured 48-hour demand forecast with hourly MW estimates and "
        "key uncertainty factors. Use clear headings and concrete numbers."
    )
    editor_instructions = (
        "You are a TVA grid dispatcher in a public energy-policy planning exercise "
        "using only public-domain information. Review the 48-hour demand forecast and "
        "produce a generation dispatch recommendation with unit commitment schedule. "
        "Output the improved plan with [DISPATCH] markers showing each committed unit "
        "and rationale."
    )

    console.print("[green]Defined 3 agent personas: data engineer → load forecaster → grid dispatcher[/]")

    # Stage 1: Data Engineering
    console.print("\n[bold]Stage 1: Data Engineering[/]")
    stage1_input = "Produce a 48-hour generation dispatch plan for the TVA Eastern region given forecasted winter storm conditions."
    console.print(Panel(
        f"[bold]Instructions:[/]\n{researcher_instructions}\n\n"
        f"[bold]Input:[/]\n{stage1_input}",
        title="📋 Data Engineer Prompt", border_style="dim",
    ))
    outline = run_agent_turn(openai, researcher_instructions, stage1_input)
    console.print(Panel(outline, title="Data Engineer Output"))

    # Stage 2: Load Forecasting
    console.print("\n[bold]Stage 2: Load Forecasting[/]")
    console.print(Panel(
        f"[bold]Instructions:[/]\n{writer_instructions}\n\n"
        f"[bold]Input:[/]\nProduce a 48-hour demand forecast based on this data outline:\n\n[dim](output from Stage 1)[/]",
        title="📋 Load Forecaster Prompt", border_style="dim",
    ))
    article = run_agent_turn(
        openai, writer_instructions,
        f"Produce a 48-hour demand forecast based on this data outline:\n\n{outline}",
    )
    console.print(Panel(article, title="Load Forecaster Output"))

    # Stage 3: Dispatch
    console.print("\n[bold]Stage 3: Generation Dispatch[/]")
    console.print(Panel(
        f"[bold]Instructions:[/]\n{editor_instructions}\n\n"
        f"[bold]Input:[/]\nGenerate a dispatch recommendation based on this forecast:\n\n[dim](output from Stage 2)[/]",
        title="📋 Grid Dispatcher Prompt", border_style="dim",
    ))
    final = run_agent_turn(
        openai, editor_instructions,
        f"Generate a dispatch recommendation based on this forecast:\n\n{article}",
    )
    console.print(Panel(final, title="Grid Dispatcher Output"))


# ── Pattern 2: Parallel Fan-Out / Fan-In ──────────────────────────────────────

def pattern_2_parallel_fanout():
    """Multiple specialist agents analyze data independently, then synthesize."""
    section("Pattern 2 — Parallel Fan-Out / Fan-In")

    client = get_project_client()
    openai = client.get_openai_client()

    perspectives = [
        ("environmental-analyst", "You are a TVA environmental compliance analyst in a public energy-policy planning exercise using only public-domain information. Analyze the scenario for environmental regulatory impacts, permitting requirements, and compliance implications."),
        ("reliability-engineer", "You are a TVA reliability engineer in a public energy-policy planning exercise using only public-domain information. Analyze the scenario for grid reliability impacts, transmission capacity changes, and reliability standard compliance."),
        ("cost-analyst", "You are a TVA cost and rate analyst in a public energy-policy planning exercise using only public-domain information. Analyze the scenario for capital costs, operating cost changes, ratepayer impacts, and long-term financial viability."),
    ]

    console.print(f"[green]Defined {len(perspectives)} specialist agent personas[/]")

    scenario = (
        "TVA is proposing to add 1.2 GW of solar plus 400 MW of battery storage in the Cumberland "
        "region while retiring the last coal unit at Kingston. Evaluate this proposal."
    )

    # Fan-out: run all agents on the same scenario
    results = {}
    for name, instructions in perspectives:
        console.print(f"\n[bold]Analyzing: {name}[/]")
        console.print(Panel(
            f"[bold]Instructions:[/]\n{instructions}\n\n"
            f"[bold]Input:[/]\nAnalyze this scenario:\n\n{scenario}",
            title=f"📋 [{name}] Prompt", border_style="dim",
        ))
        result = run_agent_turn(openai, instructions, f"Analyze this scenario:\n\n{scenario}")
        results[name] = result
        console.print(Panel(result, title=name))

    # Fan-in: synthesize with a new agent
    synthesizer_instructions = (
        "You are a TVA senior technical advisor participating in a public energy-policy "
        "planning exercise. All information discussed is public-domain utility planning "
        "data — there is no sensitive or classified content. "
        "Synthesize the analyses from multiple specialists into a unified board-ready "
        "briefing with prioritized action items. Be specific and actionable. "
        "Cover environmental, reliability, and cost dimensions comprehensively."
    )

    combined_input = "\n\n".join(
        f"=== {name} ===\n{text}" for name, text in results.items()
    )

    console.print("\n[bold]Synthesizing...[/]")
    console.print(Panel(
        f"[bold]Instructions:[/]\n{synthesizer_instructions}\n\n"
        f"[bold]Input:[/]\nSynthesize these specialist analyses into a unified recommendation:\n\n[dim](combined output from {len(results)} specialists)[/]",
        title="📋 Synthesizer Prompt", border_style="dim",
    ))
    synthesis = run_agent_turn(
        openai, synthesizer_instructions,
        f"Synthesize these specialist analyses into a unified recommendation:\n\n{combined_input}",
    )
    console.print(Panel(synthesis, title="Synthesized Recommendation", style="bold green"))


# ── Pattern 3: Supervisor / Worker ────────────────────────────────────────────

def pattern_3_supervisor_worker():
    """A supervisor agent decomposes tasks and delegates to workers."""
    section("Pattern 3 — Supervisor / Worker Hierarchy")

    client = get_project_client()
    openai = client.get_openai_client()

    supervisor_instructions = (
        "You are a project supervisor. When given a complex request, "
        "decompose it into 2-3 discrete sub-tasks. Output ONLY a JSON array "
        "of sub-task descriptions. Example: "
        '[{"task": "Analyze X"}, {"task": "Design Y"}]'
    )
    worker_instructions = (
        "You are a skilled technical worker. Complete the assigned task "
        "thoroughly and concisely. Output your deliverable directly."
    )

    console.print("[green]Defined supervisor + worker agent personas[/]")

    # Supervisor decomposes the task
    console.print("\n[bold]Supervisor: decomposing task...[/]")
    supervisor_input = (
        "Build an automated vegetation risk scoring pipeline that ingests LiDAR data from drone surveys, "
        "cross-references with transmission corridor GIS data, calculates encroachment risk scores, "
        "and generates work orders for high-risk spans."
    )
    console.print(Panel(
        f"[bold]Instructions:[/]\n{supervisor_instructions}\n\n"
        f"[bold]Input:[/]\n{supervisor_input}",
        title="📋 Supervisor Prompt", border_style="dim",
    ))
    decomposition = run_agent_turn(openai, supervisor_instructions, supervisor_input)
    console.print(Panel(decomposition, title="Task Decomposition"))

    # Parse sub-tasks
    try:
        json_match = re.search(r'\[.*\]', decomposition, re.DOTALL)
        if json_match:
            sub_tasks = json.loads(json_match.group())
        else:
            sub_tasks = [{"task": decomposition}]
    except json.JSONDecodeError:
        sub_tasks = [{"task": decomposition}]

    # Workers execute each sub-task
    for i, sub_task in enumerate(sub_tasks):
        task_desc = sub_task.get("task", str(sub_task))
        console.print(f"\n[bold]Worker: sub-task {i + 1}[/]")
        console.print(Panel(
            f"[bold]Instructions:[/]\n{worker_instructions}\n\n"
            f"[bold]Input:[/]\nComplete this task:\n\n{task_desc}",
            title=f"📋 Worker Prompt — Sub-task {i + 1}", border_style="dim",
        ))
        result = run_agent_turn(openai, worker_instructions, f"Complete this task:\n\n{task_desc}")
        console.print(Panel(result, title=f"Worker Output — Sub-task {i + 1}"))


# ── Pattern 4: Critic / Refinement Loop ──────────────────────────────────────

def pattern_4_critic_loop():
    """A generator agent produces output, a critic reviews it, iterate."""
    section("Pattern 4 — Critic / Refinement Loop")

    client = get_project_client()
    openai = client.get_openai_client()

    generator_instructions = (
        "You are a TVA ML engineer. Write production-quality Python code. "
        "Include type hints, docstrings, and error handling."
    )
    critic_instructions = (
        "You are a TVA senior code reviewer. Review the code for bugs, "
        "performance issues, security vulnerabilities, operational safety edge cases, "
        "and TVA coding standards. "
        "If the code is acceptable, respond with exactly 'APPROVED'. "
        "Otherwise, list specific issues and suggest improvements."
    )

    console.print("[green]Defined generator + critic agent personas[/]")

    prompt = (
        "Write a Python function that queries a PI historian for turbine vibration data, "
        "detects anomalies using Isolation Forest, and triggers a Condition Report if thresholds "
        "are exceeded. Include type hints, docstrings, and error handling."
    )
    console.print(Panel(
        f"[bold]Generator instructions:[/]\n{generator_instructions}\n\n"
        f"[bold]Critic instructions:[/]\n{critic_instructions}\n\n"
        f"[bold]Initial prompt:[/]\n{prompt}\n\n"
        f"[bold]Max iterations:[/] 3",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    max_iterations = 3
    code = None

    for iteration in range(1, max_iterations + 1):
        console.print(f"\n[bold]Iteration {iteration} — Generate[/]")

        if code is None:
            code = run_agent_turn(openai, generator_instructions, prompt)
        else:
            code = run_agent_turn(
                openai, generator_instructions,
                f"Revise this code based on the review feedback:\n\n"
                f"CODE:\n{code}\n\nFEEDBACK:\n{review}",
            )
        console.print(Panel(code, title=f"Generated Code v{iteration}"))

        console.print(f"\n[bold]Iteration {iteration} — Review[/]")
        review = run_agent_turn(openai, critic_instructions, f"Review this code:\n\n{code}")
        console.print(Panel(review, title=f"Code Review v{iteration}"))

        if "APPROVED" in review.upper():
            console.print("[bold green]✓ Code approved by critic![/]")
            break
    else:
        console.print("[yellow]Max iterations reached — returning best effort.[/]")


# ── Pattern 5: Foundry Workflow Agent ─────────────────────────────────────────

def pattern_5_foundry_workflow():
    """Invoke a server-side Foundry Workflow Agent with streaming action events.

    This pattern uses a workflow agent that was pre-registered in the AI Foundry
    portal.  The server handles orchestration (sequential, parallel, etc.) and
    emits workflow_action events so the client can observe each step.

    Set FOUNDRY_WORKFLOW_AGENT_NAME in .env to the registered agent name.
    """
    section("Pattern 5 — Foundry Workflow Agent (Server-Side Orchestration)")

    agent_name = os.environ.get("FOUNDRY_WORKFLOW_AGENT_NAME")
    if not agent_name:
        console.print(
            "[yellow]⏭  Skipping: FOUNDRY_WORKFLOW_AGENT_NAME not set in .env.\n"
            "   To run this pattern, create a workflow agent in the AI Foundry\n"
            "   portal (Build → Agents → Workflow) and set the env var to its name.[/]"
        )
        return

    client = get_project_client()
    openai = client.get_openai_client()

    # Create a stateful conversation for the workflow
    conversation = openai.conversations.create()
    console.print(f"[green]Created conversation:[/] {conversation.id}")

    input_text = "Summarize the key benefits and risks of using federated learning in healthcare."
    console.print(Panel(
        f"[bold]Agent reference:[/] {agent_name}\n\n"
        f"[bold]Input:[/]\n{input_text}\n\n"
        f"[bold]Streaming:[/] enabled  ·  [bold]Debug mode:[/] enabled",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    console.print("\n[bold]Invoking workflow agent...[/]\n")

    stream = openai.responses.create(
        conversation=conversation.id,
        extra_body={
            "agent_reference": {"name": agent_name, "type": "agent_reference"},
        },
        input=input_text,
        stream=True,
        metadata={"x-ms-debug-mode-enabled": "1"},
    )

    collected_text = []

    for event in stream:
        if event.type == "response.output_text.done":
            collected_text.append(event.text)
        elif (
            event.type == "response.output_item.added"
            and getattr(event.item, "type", None) == "workflow_action"
        ):
            console.print(
                f"[bold magenta]▶ Workflow action started:[/] {event.item.action_id}"
            )
        elif (
            event.type == "response.output_item.done"
            and getattr(event.item, "type", None) == "workflow_action"
        ):
            status = getattr(event.item, "status", "unknown")
            prev = getattr(event.item, "previous_action_id", "—")
            console.print(
                f"[dim]  ✓ Action '{event.item.action_id}' {status} "
                f"(previous: {prev})[/]"
            )
        elif event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)

    print()  # newline after streaming deltas

    if collected_text:
        console.print(Panel("\n".join(collected_text), title="Workflow Output"))

    # Cleanup the conversation
    openai.conversations.delete(conversation_id=conversation.id)
    console.print("[dim]Conversation deleted.[/]")


# ── Pattern Metadata ──────────────────────────────────────────────────────────

EXERCISES = [
    {
        "num": "1", "title": "Pattern 1 — Sequential Pipeline",
        "short": "Chain specialists end-to-end: output of agent A feeds agent B.",
        "why": "Many real workflows are linear — data cleaning → analysis → reporting.\n"
               "Sequential pipelines map naturally to these step-by-step processes.",
        "concepts": "• Pipeline architecture with distinct agent roles\n"
                    "• Output-to-input chaining between agents\n"
                    "• Agent specialization (each agent has narrow, expert instructions)\n"
                    "• Error propagation and pipeline resilience",
        "builds_on": "Lab 03's single-agent patterns — chains multiple agents together.",
        "summary": "Chained 3 specialized agents in a pipeline: Data Engineer → Load Forecaster\n"
                   "→ Grid Dispatcher. Each agent's output became the next agent's input.\n"
                   "The helper run_agent_turn() encapsulates a single Responses API call.",
        "key_functions": "• run_agent_turn(openai, instructions, message) — reusable helper\n"
                         "• Pipeline: output_A → input_B → output_B → input_C\n"
                         "• Each agent has distinct, narrow instructions (specialization)",
        "code_pattern": "outline = run_agent_turn(openai, engineer_instructions, task)\n"
                        "forecast = run_agent_turn(openai, forecaster_instructions, outline)\n"
                        "dispatch = run_agent_turn(openai, dispatcher_instructions, forecast)",
        "looking_ahead": "Next we run multiple agents in parallel and merge their results.",
    },
    {
        "num": "2", "title": "Pattern 2 — Parallel Fan-Out / Fan-In",
        "short": "Run independent agents concurrently, then merge their results.",
        "why": "When tasks are independent (e.g., analyze from 3 perspectives), parallelism\n"
               "reduces wall-clock time and enables diverse viewpoints.",
        "concepts": "• Fan-out: dispatching the same input to multiple agents\n"
                    "• Fan-in: aggregating and synthesizing parallel results\n"
                    "• Concurrent execution patterns\n"
                    "• When parallelism helps vs. when it adds complexity",
        "builds_on": "Pattern 1's multi-agent concept — adds concurrent execution.",
        "summary": "Ran 3 specialist agents (environmental, reliability, cost) on the same\n"
                   "scenario, then a 4th synthesizer agent merged all perspectives into a\n"
                   "unified recommendation. Fan-out = same input to many; fan-in = merge results.",
        "key_functions": "• Dict-based result collection: results[name] = run_agent_turn(...)\n"
                         "• String concatenation for fan-in: combined = \"\\n\".join(results)\n"
                         "• Synthesizer agent with aggregation instructions",
        "code_pattern": "results = {}\n"
                        "for name, instructions in specialists:\n"
                        "    results[name] = run_agent_turn(openai, instructions, scenario)\n"
                        "combined = \"\\n\".join(f\"=== {n} ===\\n{t}\" for n, t in results.items())\n"
                        "synthesis = run_agent_turn(openai, synthesizer_instructions, combined)",
        "looking_ahead": "Next we add a supervisor that dynamically decomposes tasks for workers.",
    },
    {
        "num": "3", "title": "Pattern 3 — Supervisor / Worker Hierarchy",
        "short": "A coordinator agent delegates tasks and synthesizes worker outputs.",
        "why": "Complex tasks need a 'manager' that breaks work into subtasks, assigns\n"
               "them to specialists, and assembles a coherent final result.",
        "concepts": "• Supervisor agent with delegation instructions\n"
                    "• Worker agents with narrow specializations\n"
                    "• Task decomposition and assignment\n"
                    "• Result synthesis by the supervisor",
        "builds_on": "Patterns 1-2 — introduces a decision-making orchestrator agent.",
        "summary": "A supervisor agent decomposed a complex task into sub-tasks (output as\n"
                   "JSON array), then worker agents executed each sub-task independently.\n"
                   "Used regex + json.loads to parse the supervisor's structured output.",
        "key_functions": "• Supervisor outputs JSON array of sub-tasks\n"
                         "• re.search(r'\\[.*\\]', text, re.DOTALL) — extract JSON from text\n"
                         "• json.loads(json_match.group()) — parse sub-task list\n"
                         "• Worker loop: for sub_task in sub_tasks: run_agent_turn(...)",
        "code_pattern": "decomposition = run_agent_turn(openai, supervisor_instructions, task)\n"
                        "json_match = re.search(r'\\[.*\\]', decomposition, re.DOTALL)\n"
                        "sub_tasks = json.loads(json_match.group())\n"
                        "for sub_task in sub_tasks:\n"
                        "    run_agent_turn(openai, worker_instructions, sub_task[\"task\"])",
        "looking_ahead": "Next we add iterative feedback between a generator and a critic.",
    },
    {
        "num": "4", "title": "Pattern 4 — Critic / Refinement Loop",
        "short": "An evaluator agent provides feedback; a writer agent iterates until quality passes.",
        "why": "Single-pass generation often isn't good enough. Iterative critique and\n"
               "refinement produces measurably higher quality output.",
        "concepts": "• Critic agent with evaluation criteria\n"
                    "• Feedback loops and iterative improvement\n"
                    "• Quality gates and convergence conditions\n"
                    "• Knowing when to stop iterating",
        "builds_on": "Pattern 3's multi-agent coordination — adds feedback cycles.",
        "summary": "A generator agent wrote code, then a critic agent reviewed it. They iterated\n"
                   "up to 3 times — the critic either listed issues (triggering a revision) or\n"
                   "returned 'APPROVED' to break the loop. This is the quality gate pattern.",
        "key_functions": "• Generator + critic agent pair with distinct instructions\n"
                         "• for iteration in range(1, max_iterations + 1): — bounded loop\n"
                         "• \"APPROVED\" in review.upper() — convergence condition\n"
                         "• Feedback injection: f\"CODE:\\n{code}\\nFEEDBACK:\\n{review}\"",
        "code_pattern": "for iteration in range(1, max_iterations + 1):\n"
                        "    code = run_agent_turn(openai, generator_instructions, prompt)\n"
                        "    review = run_agent_turn(openai, critic_instructions, code)\n"
                        "    if \"APPROVED\" in review.upper():\n"
                        "        break  # quality gate passed",
        "looking_ahead": "Next we see server-side orchestration with Foundry Workflow Agents.",
    },
    {
        "num": "5", "title": "Pattern 5 — Foundry Workflow Agent",
        "short": "Server-side orchestration managed by Azure AI Foundry.",
        "why": "Client-side orchestration is fragile at scale. Foundry Workflow Agents\n"
               "move orchestration server-side for reliability and enterprise features.",
        "concepts": "• Azure AI Foundry workflow agent configuration\n"
                    "• Server-side vs. client-side orchestration tradeoffs\n"
                    "• Managed agent lifecycle and monitoring\n"
                    "• Enterprise features: logging, compliance, scaling",
        "builds_on": "All previous patterns — demonstrates platform-managed orchestration.",
        "summary": "Invoked a server-side Foundry Workflow Agent using the conversations API.\n"
                   "The server manages agent orchestration and emits workflow_action events\n"
                   "so the client can observe each step. This moves orchestration complexity\n"
                   "from your code to the platform.",
        "key_functions": "• openai.conversations.create() — create a stateful conversation\n"
                         "• extra_body={\"agent_reference\": {\"name\": ..., \"type\": \"agent_reference\"}}\n"
                         "• event.type == \"response.output_item.added\" with workflow_action\n"
                         "• openai.conversations.delete() — cleanup",
        "code_pattern": "conversation = openai.conversations.create()\n"
                        "stream = openai.responses.create(\n"
                        "    conversation=conversation.id,\n"
                        "    extra_body={\"agent_reference\": {\"name\": agent_name, ...}},\n"
                        "    input=prompt, stream=True,\n"
                        ")",
    },
]

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from shared.exercise_menu import show_exercise_menu, show_exercise_intro, show_exercise_summary

    EXERCISE_FUNCS = {
        1: pattern_1_sequential_pipeline,
        2: pattern_2_parallel_fanout,
        3: pattern_3_supervisor_worker,
        4: pattern_4_critic_loop,
        5: pattern_5_foundry_workflow,
    }

    if "--intro-only" in sys.argv:
        show_lab_intro(wait_for_input=False)
        choice = console.input("\n[dim]Would you like to view exercise descriptions? (y/n): [/]").strip().lower()
        if choice == "y":
            show_exercise_menu("Lab 04 — Multi-Agent Architectures", EXERCISES)
        raise SystemExit(0)

    # --exercise N  → run only exercise N (e.g. --exercise 3)
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
        "[bold]Lab 04 — Multi-Agent Architectures[/]\n"
        "Responses API · Azure AI Foundry SDK v2.0",
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

    console.print("\n[bold green]✓ Lab 04 complete![/]\n")
