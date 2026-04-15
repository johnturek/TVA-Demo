"""
Lab 01 — Prompts & Completions
===============================
Demonstrates basic prompt engineering and chat completions using the
Azure AI Foundry SDK v2.0. Covers:

  - Authenticating with DefaultAzureCredential via AIProjectClient
  - Obtaining an OpenAI-compatible client from the Foundry project
  - System / user / assistant message roles
  - Temperature, top_p, and max_tokens parameters
  - Streaming vs. non-streaming completions

Prerequisites:
  pip install -r requirements.txt
  cp example.env .env   # fill in your values

Usage:
  python labs/lab01-prompts-completions/lab01_completions.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from rich.console import Console
from rich.panel import Panel
from shared.config import get_project_client, get_model_name

console = Console()
MODEL = get_model_name()


# ── Helper ────────────────────────────────────────────────────────────────────

def section(title: str):
    console.print(f"\n[bold cyan]{'─' * 60}[/]")
    console.print(f"[bold cyan]  {title}[/]")
    console.print(f"[bold cyan]{'─' * 60}[/]\n")


# ── Lab Introduction ──────────────────────────────────────────────────────────

def show_lab_intro(wait_for_input=True):
    """Display an introduction explaining why this lab matters and what we will learn."""
    console.print(Panel(
        "[bold]Why This Lab?[/]\n\n"
        "Every AI-powered application starts with a conversation between a user and a "
        "language model. Before we can build agents, orchestrate multi-agent workflows, "
        "or wire up retrieval pipelines, we need to master the fundamentals: how prompts "
        "are structured, how the model responds, and what knobs we can turn to shape its "
        "behavior.\n\n"
        "[bold]Concepts Covered[/]\n\n"
        "  • [cyan]Message roles[/] — system, user, and assistant messages and how each "
        "steers the conversation\n"
        "  • [cyan]System prompt engineering[/] — crafting personas that change the model's "
        "tone, focus, and expertise\n"
        "  • [cyan]Temperature & sampling[/] — controlling determinism vs. creativity\n"
        "  • [cyan]Streaming[/] — receiving tokens as they are generated for responsive UIs\n"
        "  • [cyan]Multi-turn conversations[/] — accumulating message history so the model "
        "retains context across turns\n\n"
        "[bold]Starting Point[/]\n\n"
        "This is our foundation lab. Everything in Labs 02–06 builds on the Chat "
        "Completions API patterns you will see here. Master these building blocks and "
        "the rest of the workshop will click into place.",
        title="🎓 Lab 01 — Prompts & Completions",
        border_style="bright_blue",
    ))
    if wait_for_input:
        console.input("\n[dim]Press Enter to continue...[/]")


# ── Exercise 1: Basic Chat Completion ─────────────────────────────────────────

def exercise_1_basic_completion():
    """Send a simple user prompt and receive a completion."""
    section("Exercise 1 — Basic Chat Completion")

    client = get_project_client()
    openai = client.get_openai_client()

    user_msg = "Explain how LSTM networks are used for short-term energy load forecasting in three sentences."
    console.print(Panel(
        f"[bold]User:[/]\n{user_msg}",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": user_msg}
        ],
    )

    console.print(Panel(response.choices[0].message.content, title="Model Response"))
    console.print(f"[dim]Tokens: prompt={response.usage.prompt_tokens}  "
                  f"completion={response.usage.completion_tokens}  "
                  f"total={response.usage.total_tokens}[/]")


# ── Exercise 2: System Prompt Engineering ─────────────────────────────────────

def exercise_2_system_prompt():
    """Demonstrate how system prompts steer model behavior."""
    section("Exercise 2 — System Prompt Engineering")

    client = get_project_client()
    openai = client.get_openai_client()

    personas = [
        ("Grid Operator", "You are a TVA grid operator. Explain concepts in terms of generation dispatch and load balancing."),
        ("Environmental Analyst", "You are a TVA environmental compliance analyst. Reference NERC and EPA regulations."),
        ("Executive Briefer", "You are briefing TVA's VP of Power Operations. Be concise, data-driven, cite KPIs."),
    ]

    question = "What causes peak electricity demand in the Tennessee Valley?"

    for name, system_msg in personas:
        console.print(Panel(
            f"[bold]System:[/]\n{system_msg}\n\n"
            f"[bold]User:[/]\n{question}",
            title=f"📋 [{name}] Prompt", border_style="dim",
        ))
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": question},
            ],
            max_tokens=200,
        )
        console.print(Panel(response.choices[0].message.content, title=f"[{name}]"))


# ── Exercise 3: Temperature & Sampling ────────────────────────────────────────

def exercise_3_temperature():
    """Show how temperature affects creativity vs. determinism."""
    section("Exercise 3 — Temperature & Sampling")

    client = get_project_client()
    openai = client.get_openai_client()

    prompt = "Generate three possible root causes for an unexpected 200 MW load spike in the Eastern Tennessee service territory during off-peak hours."
    console.print(Panel(
        f"[bold]User:[/]\n{prompt}\n\n"
        f"[bold]Temperatures:[/] 0.0, 0.7, 1.5",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    for temp in [0.0, 0.7, 1.5]:
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
        )
        console.print(Panel(
            response.choices[0].message.content.strip(),
            title=f"temp={temp:.1f}",
            border_style="dim",
        ))
        console.print()


# ── Exercise 4: Streaming Completion ──────────────────────────────────────────

def exercise_4_streaming():
    """Demonstrate streaming token-by-token output."""
    section("Exercise 4 — Streaming Completion")

    client = get_project_client()
    openai = client.get_openai_client()

    system_msg = "You are a concise technical writer."
    user_msg = "List 5 best practices for prompt engineering."
    console.print(Panel(
        f"[bold]System:[/]\n{system_msg}\n\n"
        f"[bold]User:[/]\n{user_msg}\n\n"
        f"[bold]Streaming:[/] enabled  ·  [bold]Max tokens:[/] 300",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    console.print("[dim]Streaming response:[/] ", end="")

    stream = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        stream=True,
        max_tokens=300,
    )

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            print(delta.content, end="", flush=True)

    print()


# ── Exercise 5: Multi-Turn Conversation ───────────────────────────────────────

def exercise_5_multi_turn():
    """Build a multi-turn conversation by accumulating message history."""
    section("Exercise 5 — Multi-Turn Conversation")

    client = get_project_client()
    openai = client.get_openai_client()

    system_msg = "You are a helpful TVA power systems data science tutor."
    initial_question = "What is peak demand shaving?"
    followups = [
        "How does TVA use demand response programs to achieve it?",
        "What machine learning models can predict the best times to trigger demand response?",
        "Show me a Python example using pandas to detect demand peaks from hourly load data.",
    ]
    # Build the turn plan: list of (turn_label, user_prompt) pairs
    turns = [("Initial Question", initial_question)] + [
        (f"Follow-up {i+1}", q) for i, q in enumerate(followups)
    ]

    # Show the prompt breakdown with turn ↔ question mapping
    mapping_lines = "\n".join(
        f"  [bold]{label}:[/] {prompt}" for label, prompt in turns
    )
    console.print(Panel(
        f"[bold]System:[/]\n{system_msg}\n\n"
        f"[bold]Turn → Question Mapping:[/]\n{mapping_lines}",
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": initial_question},
    ]

    def truncate(text: str, length: int = 60) -> str:
        return text[:length] + "…" if len(text) > length else text

    ROLE_STYLE = {"system": "bold red", "user": "bold green", "assistant": "bold yellow"}

    for i, (label, prompt) in enumerate(turns):
        if i > 0:
            messages.append({"role": "user", "content": prompt})

        # Build a readable summary of every message the model will see
        history_lines = []
        for idx, msg in enumerate(messages):
            role = msg["role"]
            style = ROLE_STYLE.get(role, "dim")
            prefix = f"  {idx+1}."
            history_lines.append(
                f"{prefix} [{style}]{role:>9}[/]  {truncate(msg['content'])}"
            )
        history_block = "\n".join(history_lines)

        console.print(Panel(
            f"[bold]Messages sent to the model this turn ({len(messages)}):[/]\n"
            f"{history_block}",
            title=f"📨 {label} — API Request",
            border_style="dim",
        ))

        response = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=250,
        )

        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})

        console.print(Panel(
            f"[bold dim]🗣 {prompt}[/]\n\n{reply}",
            title=f"💬 {label} — Model Response",
            subtitle=f"[dim]{response.usage.total_tokens} tokens[/]",
        ))


# ── Exercise Metadata ─────────────────────────────────────────────────────────

EXERCISES = [
    {
        "num": "1", "title": "Exercise 1 — Basic Chat Completion",
        "short": "Send a message, get a response — the foundation of all LLM interaction.",
        "why": "Every AI application starts here. Understanding the chat completions API\n"
               "is the prerequisite for everything else — prompt design, agents, RAG, and more.",
        "concepts": "• Chat Completions API endpoint and request structure\n"
                    "• Message roles (user) and model selection\n"
                    "• API authentication via Azure AI Foundry SDK\n"
                    "• Interpreting response objects (choices, content, usage)",
        "builds_on": "Starting point — no prerequisites. This is ground zero.",
        "summary": "Sent a single user message to the Chat Completions API and received a\n"
                   "model-generated response. Inspected the response object for content and\n"
                   "token usage statistics.",
        "key_functions": "• openai.chat.completions.create() — the core API call\n"
                         "• response.choices[0].message.content — extracting the reply\n"
                         "• response.usage.prompt_tokens / completion_tokens / total_tokens\n"
                         "• get_project_client() → client.get_openai_client() — SDK auth chain",
        "code_pattern": "response = openai.chat.completions.create(\n"
                        "    model=MODEL,\n"
                        "    messages=[{\"role\": \"user\", \"content\": prompt}]\n"
                        ")",
        "looking_ahead": "Next we add system messages to steer the model's persona and behavior.",
    },
    {
        "num": "2", "title": "Exercise 2 — System Prompt Engineering",
        "short": "Shape model behavior with system messages — the primary customization lever.",
        "why": "System prompts define the model's persona, constraints, and output format.\n"
               "They are your most powerful tool for controlling quality in production.",
        "concepts": "• System role messages and their influence on behavior\n"
                    "• Prompt engineering techniques (persona, constraints, examples)\n"
                    "• Instruction following and compliance testing\n"
                    "• Message ordering: system → user → assistant",
        "builds_on": "Exercise 1's basic completion — adds the system role to the message array.",
        "summary": "Used three different system prompts (Grid Operator, Environmental Analyst,\n"
                   "Executive Briefer) to answer the same question — demonstrating how system\n"
                   "messages dramatically change tone, focus, and expertise of the response.",
        "key_functions": "• {\"role\": \"system\", \"content\": ...} — the system message role\n"
                         "• max_tokens parameter — controlling response length\n"
                         "• Message ordering: system → user in the messages array",
        "code_pattern": "messages=[\n"
                        "    {\"role\": \"system\", \"content\": persona_instructions},\n"
                        "    {\"role\": \"user\",   \"content\": question},\n"
                        "]",
        "looking_ahead": "Next we explore temperature to control randomness vs. determinism.",
    },
    {
        "num": "3", "title": "Exercise 3 — Temperature & Sampling",
        "short": "Control randomness and creativity with generation parameters.",
        "why": "Production apps need deterministic output for consistency, while creative\n"
               "tasks benefit from higher randomness. Temperature tuning is essential.",
        "concepts": "• Temperature parameter (0 = deterministic, 1+ = creative)\n"
                    "• Top-p (nucleus) sampling and how it differs from temperature\n"
                    "• max_tokens and response length control\n"
                    "• Choosing the right settings for your use case",
        "builds_on": "Exercises 1-2's message structure — adds generation parameters.",
        "summary": "Ran the same prompt at temperatures 0.0, 0.7, and 1.5 to observe how\n"
                   "temperature controls output randomness. Low temperature produced consistent,\n"
                   "focused answers; high temperature produced more creative, varied responses.",
        "key_functions": "• temperature parameter (0.0 = deterministic, 1.0+ = creative)\n"
                         "• top_p (nucleus sampling) — alternative randomness control\n"
                         "• Interaction between temperature and top_p",
        "code_pattern": "openai.chat.completions.create(\n"
                        "    model=MODEL,\n"
                        "    messages=[...],\n"
                        "    temperature=0.7,   # 0.0=focused, 1.5=creative\n"
                        ")",
        "looking_ahead": "Next we enable streaming to receive tokens as they're generated.",
    },
    {
        "num": "4", "title": "Exercise 4 — Streaming Completion",
        "short": "Token-by-token output for responsive UIs and reduced perceived latency.",
        "why": "Users perceive streaming responses as faster even when total latency is the\n"
               "same. Streaming is critical for chat UIs and any interactive application.",
        "concepts": "• Server-sent events and chunked transfer encoding\n"
                    "• Streaming iterator pattern (for chunk in stream)\n"
                    "• Delta content vs. full content\n"
                    "• When to use streaming vs. non-streaming",
        "builds_on": "Exercise 1's basic completion — switches to stream=True mode.",
        "summary": "Enabled stream=True and iterated over chunks to print tokens as they\n"
                   "arrived. Each chunk contains a delta (partial content) instead of the full\n"
                   "response — ideal for responsive chat interfaces.",
        "key_functions": "• stream=True parameter — enables chunked streaming\n"
                         "• chunk.choices[0].delta.content — the incremental text\n"
                         "• print(..., end=\"\", flush=True) — real-time terminal output",
        "code_pattern": "stream = openai.chat.completions.create(..., stream=True)\n"
                        "for chunk in stream:\n"
                        "    delta = chunk.choices[0].delta\n"
                        "    if delta.content:\n"
                        "        print(delta.content, end=\"\", flush=True)",
        "looking_ahead": "Next we combine everything into a multi-turn conversation with history.",
    },
    {
        "num": "5", "title": "Exercise 5 — Multi-Turn Conversation",
        "short": "Maintain context across multiple exchanges for natural dialogue.",
        "why": "Real applications are rarely single-turn. Multi-turn conversation\n"
               "management is how you build chatbots, copilots, and assistants.",
        "concepts": "• Conversation history as a growing message array\n"
                    "• Context window limits and token management\n"
                    "• Appending assistant responses to maintain state\n"
                    "• Turn-taking patterns for interactive dialogue",
        "builds_on": "All previous exercises — combines roles, parameters, and streaming\n"
                     "into a coherent multi-turn conversation.",
        "summary": "Built a 4-turn conversation by appending each assistant reply back into\n"
                   "the messages array before the next call. The model has no built-in memory —\n"
                   "context is preserved by resending the full conversation history every turn.",
        "key_functions": "• messages.append({\"role\": \"assistant\", \"content\": reply}) — history tracking\n"
                         "• Growing messages list = growing token usage per turn\n"
                         "• Context window management (watch total_tokens)",
        "code_pattern": "messages = [{\"role\": \"system\", ...}, {\"role\": \"user\", ...}]\n"
                        "response = openai.chat.completions.create(model=MODEL, messages=messages)\n"
                        "messages.append({\"role\": \"assistant\", \"content\": reply})\n"
                        "# repeat: append user msg → call API → append assistant reply",
    },
]

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from shared.exercise_menu import show_exercise_menu, show_exercise_intro, show_exercise_summary

    EXERCISE_FUNCS = {
        1: exercise_1_basic_completion,
        2: exercise_2_system_prompt,
        3: exercise_3_temperature,
        4: exercise_4_streaming,
        5: exercise_5_multi_turn,
    }

    if "--intro-only" in sys.argv:
        show_lab_intro(wait_for_input=False)
        choice = console.input("\n[dim]Would you like to view exercise descriptions? (y/n): [/]").strip().lower()
        if choice == "y":
            show_exercise_menu("Lab 01 — Prompts & Completions", EXERCISES)
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

    console.print(Panel("[bold]Lab 01 — Prompts & Completions[/]\n"
                        "Azure AI Foundry SDK v2.0 · Chat Completions API",
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

    console.print("\n[bold green]✓ Lab 01 complete![/]\n")
