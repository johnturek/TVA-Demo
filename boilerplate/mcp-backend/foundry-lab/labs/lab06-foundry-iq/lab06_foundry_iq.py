"""
Lab 06 — Foundry IQ (Knowledge Retrieval for Agents)
=====================================================
Demonstrates Foundry IQ — the unified knowledge layer built on Azure AI Search
that provides enterprise-grade, permission-aware knowledge retrieval for AI agents.

Covers:
  - Agentic Retrieval: multi-hop, reasoning-powered search
  - Knowledge base configuration for agents
  - Agent with Azure AI Search (File Search) tool
  - Combining Foundry IQ retrieval with agent orchestration
  - Comparing naive RAG vs. Foundry IQ agentic retrieval

Prerequisites:
  pip install -r requirements.txt
  cp example.env .env
  Complete Lab 05 first (creates the search index with documents)

Usage:
  python labs/lab06-foundry-iq/lab06_foundry_iq.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from rich.console import Console
from rich.panel import Panel
from shared.config import (
    get_project_client,
    get_model_name,
    get_embedding_model,
    get_openai_embedding_client,
    get_search_config,
)

console = Console()
MODEL = get_model_name()
EMBEDDING_MODEL = get_embedding_model()


def section(title: str):
    console.print(f"\n[bold cyan]{'─' * 60}[/]")
    console.print(f"[bold cyan]  {title}[/]")
    console.print(f"[bold cyan]{'─' * 60}[/]\n")


# ── Lab Introduction ──────────────────────────────────────────────────────────

def show_lab_intro(wait_for_input=True):
    """Display an introduction explaining why this lab matters and what we will learn."""
    console.print(Panel(
        "[bold]Why This Lab?[/]\n\n"
        "Lab 05 showed the classic RAG pattern: search once, stuff results into the "
        "prompt, and generate. That works for simple questions, but complex queries — "
        "the kind real operators ask — often require [cyan]multiple retrieval passes[/], "
        "each informed by the results of the last. [cyan]Foundry IQ[/] is the knowledge "
        "layer that makes this possible by giving agents the ability to decide what to "
        "search, how many times, and from which angles.\n\n"
        "[bold]Concepts Covered[/]\n\n"
        "  • [cyan]Agent-driven retrieval[/] — the agent calls a search tool on its own, "
        "decides what to query, and loops until satisfied\n"
        "  • [cyan]Multi-hop reasoning[/] — decomposing a complex question into "
        "sub-queries, retrieving for each, then synthesizing across all sources\n"
        "  • [cyan]Query decomposition[/] — using the LLM to break a hard question into "
        "simpler, targeted searches\n"
        "  • [cyan]Naive RAG vs. agentic retrieval[/] — a side-by-side comparison showing "
        "how multi-hop retrieval produces more comprehensive, better-grounded answers\n\n"
        "[bold]How This Differs from Lab 05[/]\n\n"
        "Lab 05 used a [bold]single-pass[/] retrieval pipeline where you, the developer, "
        "decided the query and number of results. In this lab the [bold]agent itself[/] "
        "drives the retrieval strategy — it reasons about what information is missing, "
        "issues additional searches, and synthesizes across multiple retrieval hops. "
        "This is the difference between static RAG and intelligent, agentic retrieval.",
        title="🎓 Lab 06 — Foundry IQ (Knowledge Retrieval for Agents)",
        border_style="bright_blue",
    ))
    if wait_for_input:
        console.input("\n[dim]Press Enter to continue...[/]")


# ── Exercise 1: Agent with Azure AI Search Tool ──────────────────────────────

def exercise_1_agent_with_search():
    """Create an agent that uses Azure AI Search as a knowledge source via tool calling."""
    section("Exercise 1 — Agent with Azure AI Search Tool")

    client = get_project_client()
    openai = client.get_openai_client()
    embedding_client = get_openai_embedding_client()
    config = get_search_config()

    from azure.search.documents import SearchClient
    from azure.search.documents.models import VectorizedQuery
    from azure.core.credentials import AzureKeyCredential

    search_client = SearchClient(
        endpoint=config["endpoint"],
        index_name=config["index_name"],
        credential=AzureKeyCredential(config["admin_key"]),
    )

    # Define a search tool the agent can call
    tools = [
        {
            "type": "function",
            "name": "search_knowledge_base",
            "description": (
                "Search the TVA operations knowledge base using a natural-language query. "
                "Returns relevant document excerpts with titles."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant knowledge base documents.",
                    }
                },
                "required": ["query"],
            },
        }
    ]

    INSTRUCTIONS = (
        "You are an expert TVA operations knowledge assistant powered by Foundry IQ. "
        "When answering questions, always search the knowledge base first using the "
        "search_knowledge_base tool. You may call it multiple times with different queries "
        "to gather comprehensive information. "
        "Cite your sources by document title in [brackets]. If the knowledge base doesn't "
        "contain relevant information, state that clearly. "
        "Flag any safety-critical information with a ⚠️ warning emoji."
    )

    def do_search(query: str) -> str:
        """Execute a hybrid search against the Azure AI Search index."""
        query_embedding = embedding_client.embeddings.create(
            model=EMBEDDING_MODEL, input=query
        ).data[0].embedding

        results = search_client.search(
            search_text=query,
            vector_queries=[
                VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=3,
                    fields="content_vector",
                )
            ],
            top=3,
            select=["title", "content"],
        )
        docs = [{"title": r["title"], "content": r["content"]} for r in results]
        if not docs:
            return json.dumps({"results": [], "message": "No results found."})
        return json.dumps({"results": docs})

    tool_names = ", ".join(t["name"] for t in tools)
    console.print(Panel(
        f"[bold]Instructions:[/]\n{INSTRUCTIONS}\n\n"
        f"[bold]Tools:[/] {tool_names}",
        title="📋 Agent Configuration", border_style="dim",
    ))

    console.print("[green]Knowledge agent ready (Responses API + tool calling)[/]\n")

    questions = [
        "What are the inspection requirements for concrete gravity dams during seismic events?",
        "What is the required vegetation clearance for 500kV transmission lines and how often must it be surveyed?",
        "What procedures should operators follow during extreme cold weather to prevent generation shortfalls?",
    ]

    for q in questions:
        console.print(f"[bold]Q:[/] {q}")

        response = openai.responses.create(
            model=MODEL,
            instructions=INSTRUCTIONS,
            input=q,
            tools=tools,
        )

        # Agentic loop: resolve function calls until the model produces a final answer
        while any(item.type == "function_call" for item in response.output):
            tool_outputs = []
            for item in response.output:
                if item.type == "function_call":
                    args = json.loads(item.arguments)
                    console.print(f"  [yellow]🔍 Searching:[/] {args['query']}")
                    result = do_search(args["query"])
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

        console.print(Panel(
            response.output_text,
            title=f"Q: {q[:50]}...",
        ))
        console.print()


# ── Exercise 2: Agentic Retrieval Pattern ─────────────────────────────────────

def exercise_2_agentic_retrieval():
    """Demonstrate multi-hop retrieval where the agent reasons about what to search."""
    section("Exercise 2 — Agentic Retrieval (Multi-Hop Reasoning)")

    client = get_project_client()
    openai = client.get_openai_client()
    embedding_client = get_openai_embedding_client()

    # Simulate Foundry IQ's agentic retrieval: the model decides what to search,
    # retrieves, reasons, and potentially searches again.

    from azure.search.documents import SearchClient
    from azure.search.documents.models import VectorizedQuery
    from azure.core.credentials import AzureKeyCredential

    config = get_search_config()
    search_client = SearchClient(
        endpoint=config["endpoint"],
        index_name=config["index_name"],
        credential=AzureKeyCredential(config["admin_key"]),
    )

    def search_knowledge_base(query: str, top_k: int = 3) -> list[dict]:
        """Search the knowledge base (simulating Foundry IQ's retrieval engine)."""
        query_embedding = embedding_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=query,
        ).data[0].embedding

        results = search_client.search(
            search_text=query,
            vector_queries=[
                VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=top_k,
                    fields="content_vector",
                )
            ],
            top=top_k,
            select=["id", "title", "content"],
        )
        return [{"title": r["title"], "content": r["content"]} for r in results]

    # Complex multi-hop question requiring multiple retrievals
    complex_query = (
        "If TVA retires the last coal unit at Kingston, what environmental regulations change, "
        "how does the retirement affect transmission capacity in East Tennessee, and what replacement "
        "generation options meet both NERC reliability standards and TVA carbon reduction targets?"
    )
    console.print(f"[bold]Complex query:[/] {complex_query}\n")

    # Hop 1: Decompose the question
    console.print("[bold]Hop 1: Query decomposition[/]")
    decomposition_system = (
        "Decompose the user's complex question into 2-3 simpler search queries. "
        "Return a JSON array of strings."
    )
    console.print(Panel(
        f"[bold]System:[/]\n{decomposition_system}\n\n"
        f"[bold]User:[/]\n{complex_query}",
        title="📋 Decomposition Prompt", border_style="dim",
    ))
    decomposition = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": decomposition_system},
            {"role": "user", "content": complex_query},
        ],
        temperature=0.0,
    )

    import re
    decomposed_text = decomposition.choices[0].message.content
    json_match = re.search(r'\[.*\]', decomposed_text, re.DOTALL)
    sub_queries = json.loads(json_match.group()) if json_match else [complex_query]

    console.print(f"  Sub-queries: {sub_queries}\n")

    # Hop 2: Retrieve for each sub-query
    console.print("[bold]Hop 2: Parallel retrieval[/]")
    all_context = []
    seen_titles = set()

    for sq in sub_queries:
        results = search_knowledge_base(sq)
        for doc in results:
            if doc["title"] not in seen_titles:
                seen_titles.add(doc["title"])
                all_context.append(doc)
                console.print(f"  [green]✓[/] Retrieved: {doc['title']}")

    # Hop 3: Synthesize grounded answer
    console.print(f"\n[bold]Hop 3: Grounded synthesis ({len(all_context)} unique sources)[/]")
    context_text = "\n\n".join(
        f"[{doc['title']}]\n{doc['content']}" for doc in all_context
    )

    synthesis_system = (
        "You are a Foundry IQ knowledge agent. Synthesize a comprehensive "
        "answer using the retrieved context. Cite sources in [brackets]. "
        "Connect insights across documents to answer the complex question."
    )
    console.print(Panel(
        f"[bold]System:[/]\n{synthesis_system}\n\n"
        f"[bold]User query:[/]\n{complex_query}\n\n"
        f"[bold]Context documents:[/] {len(all_context)} retrieved",
        title="📋 Synthesis Prompt", border_style="dim",
    ))

    synthesis = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": synthesis_system},
            {
                "role": "user",
                "content": f"Context:\n{context_text}\n\nQuestion: {complex_query}",
            },
        ],
        temperature=0.2,
    )

    console.print(Panel(
        synthesis.choices[0].message.content,
        title="Agentic Retrieval — Synthesized Answer",
        style="bold green",
    ))


# ── Exercise 3: Naive RAG vs. Agentic Retrieval Comparison ────────────────────

def exercise_3_comparison():
    """Compare single-shot naive RAG with multi-hop agentic retrieval."""
    section("Exercise 3 — Naive RAG vs. Agentic Retrieval")

    client = get_project_client()
    openai = client.get_openai_client()
    embedding_client = get_openai_embedding_client()

    from azure.search.documents import SearchClient
    from azure.search.documents.models import VectorizedQuery
    from azure.core.credentials import AzureKeyCredential

    config = get_search_config()
    search_client = SearchClient(
        endpoint=config["endpoint"],
        index_name=config["index_name"],
        credential=AzureKeyCredential(config["admin_key"]),
    )

    query = "How do severe winter weather events cascade from generation shortfalls through transmission constraints to distribution-level rolling blackouts, and what preventive measures exist at each stage?"

    # ── Naive RAG: single search pass ──
    console.print("[bold]Approach A: Naive RAG (single search)[/]\n")

    query_embedding = embedding_client.embeddings.create(
        model=EMBEDDING_MODEL, input=query
    ).data[0].embedding

    results = search_client.search(
        search_text=query,
        vector_queries=[
            VectorizedQuery(vector=query_embedding, k_nearest_neighbors=2, fields="content_vector")
        ],
        top=2,
        select=["title", "content"],
    )
    naive_context = [{"title": r["title"], "content": r["content"]} for r in results]

    for doc in naive_context:
        console.print(f"  [dim]Retrieved: {doc['title']}[/]")

    naive_system = "Answer using only the provided context. Cite sources."
    console.print(Panel(
        f"[bold]System:[/]\n{naive_system}\n\n"
        f"[bold]User query:[/]\n{query}\n\n"
        f"[bold]Context documents:[/] {len(naive_context)} retrieved",
        title="📋 Naive RAG Prompt", border_style="dim",
    ))

    naive_answer = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": naive_system},
            {
                "role": "user",
                "content": (
                    f"Context:\n"
                    + "\n".join(f"[{d['title']}] {d['content']}" for d in naive_context)
                    + f"\n\nQuestion: {query}"
                ),
            },
        ],
        temperature=0.2,
    )
    console.print(Panel(
        naive_answer.choices[0].message.content,
        title="Naive RAG Answer",
    ))

    # ── Agentic Retrieval: multi-hop ──
    console.print("\n[bold]Approach B: Agentic Retrieval (multi-hop)[/]\n")

    # Step 1: Generate multiple search angles
    angles_system = "Generate 3 different search queries to fully answer this question. Return a JSON array."
    console.print(Panel(
        f"[bold]System:[/]\n{angles_system}\n\n"
        f"[bold]User:[/]\n{query}",
        title="📋 Query Decomposition Prompt", border_style="dim",
    ))
    angles = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": angles_system},
            {"role": "user", "content": query},
        ],
        temperature=0.0,
    )

    import re
    angles_text = angles.choices[0].message.content
    json_match = re.search(r'\[.*\]', angles_text, re.DOTALL)
    search_angles = json.loads(json_match.group()) if json_match else [query]

    # Step 2: Retrieve from multiple angles
    agentic_context = []
    seen = set()
    for sq in search_angles:
        sq_embedding = embedding_client.embeddings.create(model=EMBEDDING_MODEL, input=sq).data[0].embedding
        results = search_client.search(
            search_text=sq,
            vector_queries=[
                VectorizedQuery(vector=sq_embedding, k_nearest_neighbors=2, fields="content_vector")
            ],
            top=2,
            select=["title", "content"],
        )
        for r in results:
            if r["title"] not in seen:
                seen.add(r["title"])
                agentic_context.append({"title": r["title"], "content": r["content"]})
                console.print(f"  [green]✓[/] Retrieved: {r['title']} (via: '{sq[:40]}...')")

    # Step 3: Synthesize
    agentic_system = (
        "You are a Foundry IQ agent. Synthesize a comprehensive answer "
        "from the retrieved context. Cite sources. Connect insights across documents."
    )
    console.print(Panel(
        f"[bold]System:[/]\n{agentic_system}\n\n"
        f"[bold]User query:[/]\n{query}\n\n"
        f"[bold]Context documents:[/] {len(agentic_context)} retrieved",
        title="📋 Agentic Synthesis Prompt", border_style="dim",
    ))
    agentic_answer = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": agentic_system},
            {
                "role": "user",
                "content": (
                    f"Context:\n"
                    + "\n".join(f"[{d['title']}] {d['content']}" for d in agentic_context)
                    + f"\n\nQuestion: {query}"
                ),
            },
        ],
        temperature=0.2,
    )
    console.print(Panel(
        agentic_answer.choices[0].message.content,
        title="Agentic Retrieval Answer",
        style="bold green",
    ))

    # Summary
    console.print(Panel(
        f"[bold]Naive RAG:[/] {len(naive_context)} sources, single search pass\n"
        f"[bold]Agentic Retrieval:[/] {len(agentic_context)} sources, {len(search_angles)} search angles\n\n"
        "Foundry IQ's agentic retrieval decomposes complex queries, retrieves from\n"
        "multiple angles, and synthesizes across more sources — producing more\n"
        "comprehensive, grounded answers.",
        title="Comparison Summary",
        style="cyan",
    ))


# ── Exercise Metadata ─────────────────────────────────────────────────────────

EXERCISES = [
    {
        "num": "1", "title": "Exercise 1 — Agent with Azure AI Search Tool",
        "short": "Connect an agent to a search index — the simplest retrieval pattern.",
        "why": "Giving agents direct access to search tools is the fastest way to add\n"
               "knowledge retrieval without building a full RAG pipeline yourself.",
        "concepts": "• Azure AI Search as an agent tool\n"
                    "• Tool-based retrieval vs. manual RAG\n"
                    "• Agent-driven query formulation\n"
                    "• Search tool configuration and permissions",
        "builds_on": "Lab 03's agent tool-calling + Lab 05's search index concepts.",
        "summary": "Created an agent with a custom search_knowledge_base tool backed by Azure\n"
                   "AI Search. The agent autonomously decided what to search, called the tool\n"
                   "one or more times, and synthesized answers with citations — all via the\n"
                   "agentic loop pattern from Lab 03.",
        "key_functions": "• Custom tool: search_knowledge_base(query) → hybrid search results\n"
                         "• Agentic loop: while any function_call in response.output\n"
                         "• do_search() — combines keyword + vector search in one helper\n"
                         "• Agent instructions: \"call the tool multiple times if needed\"",
        "code_pattern": "tools = [{\"type\": \"function\", \"name\": \"search_knowledge_base\", ...}]\n"
                        "response = openai.responses.create(instructions=..., input=q, tools=tools)\n"
                        "while any(item.type == \"function_call\" for item in response.output):\n"
                        "    # execute search, return results, continue loop",
        "looking_ahead": "Next we decompose complex queries into sub-queries for multi-hop retrieval.",
    },
    {
        "num": "2", "title": "Exercise 2 — Agentic Retrieval (Multi-Hop Reasoning)",
        "short": "Multi-step retrieval with reasoning between hops for complex questions.",
        "why": "Simple questions need one search. Complex questions ('Compare X and Y')\n"
               "need multiple retrieval steps with reasoning between them.",
        "concepts": "• Multi-hop reasoning: retrieve → reason → retrieve again\n"
                    "• Query decomposition into sub-questions\n"
                    "• Iterative retrieval with intermediate reasoning\n"
                    "• Knowledge synthesis across multiple sources",
        "builds_on": "Exercise 1's basic retrieval — adds multi-step reasoning loops.",
        "summary": "Implemented 3-hop agentic retrieval: (1) Decomposed a complex question\n"
                   "into sub-queries using the LLM, (2) Retrieved documents for each sub-query\n"
                   "independently, (3) Synthesized a comprehensive answer across all sources.\n"
                   "This produced broader coverage than a single search pass.",
        "key_functions": "• Hop 1: LLM decomposes query → JSON array of sub-queries\n"
                         "• re.search(r'\\[.*\\]', text, re.DOTALL) — extract JSON\n"
                         "• Hop 2: search_knowledge_base(sq) for each sub-query\n"
                         "• seen_titles set — deduplicate across sub-query results\n"
                         "• Hop 3: Synthesis with cross-source context injection",
        "code_pattern": "# Hop 1: Decompose\n"
                        "sub_queries = json.loads(llm_decompose(complex_query))\n"
                        "# Hop 2: Retrieve per sub-query\n"
                        "for sq in sub_queries:\n"
                        "    results = search_knowledge_base(sq)\n"
                        "    all_context.extend(deduplicate(results))\n"
                        "# Hop 3: Synthesize across all sources\n"
                        "answer = llm_synthesize(all_context, complex_query)",
        "looking_ahead": "Next we compare naive RAG vs. agentic retrieval side-by-side.",
    },
    {
        "num": "3", "title": "Exercise 3 — Naive RAG vs. Agentic Retrieval",
        "short": "Head-to-head comparison to understand quality and latency tradeoffs.",
        "why": "Choosing the right retrieval strategy depends on your use case. This\n"
               "comparison gives you data to make informed architecture decisions.",
        "concepts": "• Comparison methodology: same question, different approaches\n"
                    "• Quality vs. latency tradeoffs\n"
                    "• When naive RAG is sufficient vs. when agentic wins\n"
                    "• Cost and complexity considerations",
        "builds_on": "Lab 05's RAG pipeline + Exercise 2's agentic retrieval — compares both.",
        "summary": "Ran the same complex question through two approaches side-by-side:\n"
                   "Naive RAG (single search, 2 sources) vs. Agentic Retrieval (3 decomposed\n"
                   "searches, more sources). Agentic retrieval produced more comprehensive,\n"
                   "better-grounded answers at the cost of additional API calls.",
        "key_functions": "• Approach A (Naive): single search_client.search() → generate\n"
                         "• Approach B (Agentic): decompose → multi-search → synthesize\n"
                         "• Comparison: source count, search angles, answer breadth\n"
                         "• Tradeoff: quality & coverage vs. latency & cost",
        "code_pattern": "# Naive: 1 search pass\n"
                        "naive_docs = search(query, top=2)\n"
                        "naive_answer = generate(naive_docs, query)\n"
                        "# Agentic: decompose → multi-search → synthesize\n"
                        "angles = decompose(query)  # 3 sub-queries\n"
                        "agentic_docs = [search(sq) for sq in angles]  # more sources\n"
                        "agentic_answer = synthesize(agentic_docs, query)",
    },
]

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from shared.exercise_menu import show_exercise_menu, show_exercise_intro, show_exercise_summary

    EXERCISE_FUNCS = {
        1: exercise_1_agent_with_search,
        2: exercise_2_agentic_retrieval,
        3: exercise_3_comparison,
    }

    if "--intro-only" in sys.argv:
        show_lab_intro(wait_for_input=False)
        choice = console.input("\n[dim]Would you like to view exercise descriptions? (y/n): [/]").strip().lower()
        if choice == "y":
            show_exercise_menu("Lab 06 — Foundry IQ", EXERCISES)
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

    console.print(Panel(
        "[bold]Lab 06 — Foundry IQ (Knowledge Retrieval for Agents)[/]\n"
        "Agentic Retrieval · Multi-Hop Reasoning · Foundry SDK v2.0",
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

    console.print("\n[bold green]✓ Lab 06 complete![/]\n")
