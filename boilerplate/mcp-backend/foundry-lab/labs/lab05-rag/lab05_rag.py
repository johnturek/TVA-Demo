"""
Lab 05 — Retrieval-Augmented Generation (RAG)
===============================================
Demonstrates end-to-end RAG using Azure AI Search and the Foundry SDK v2.0.

Covers:
  - Creating an Azure AI Search index with vector fields
  - Generating embeddings via the Foundry project
  - Uploading documents with vector embeddings
  - Hybrid search (keyword + semantic + vector)
  - RAG: search → augment prompt → generate grounded answer

Prerequisites:
  pip install -r requirements.txt
  cp example.env .env

Usage:
  python labs/lab05-rag/lab05_rag.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from rich.console import Console
from rich.panel import Panel
from shared.config import (
    get_project_client,
    get_model_name,
    get_embedding_model,
    get_search_config,
    get_openai_embedding_client,
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
        "Language models are trained on a snapshot of public data — they know nothing "
        "about your organization's private documents, policies, or real-time operational "
        "data. [cyan]Retrieval-Augmented Generation (RAG)[/] bridges this gap by "
        "retrieving relevant documents at query time and injecting them into the prompt "
        "so the model can generate grounded, accurate answers.\n\n"
        "[bold]Concepts Covered[/]\n\n"
        "  • [cyan]Azure AI Search index[/] — creating an index with both text and "
        "vector fields for hybrid retrieval\n"
        "  • [cyan]Embedding generation[/] — converting documents into high-dimensional "
        "vectors via the Foundry embedding model\n"
        "  • [cyan]Document upload[/] — populating the index with vectors and metadata\n"
        "  • [cyan]Hybrid search[/] — combining keyword matching with vector similarity "
        "for best-of-both-worlds retrieval\n"
        "  • [cyan]Grounded generation[/] — augmenting the LLM prompt with retrieved "
        "context and generating answers with source citations\n\n"
        "[bold]How This Differs from Labs 01–04[/]\n\n"
        "All previous labs relied entirely on the model's built-in knowledge. This lab "
        "introduces an [bold]external knowledge source[/] — an Azure AI Search index "
        "loaded with domain-specific documents. The model now answers from your data, "
        "not just its training data.",
        title="🎓 Lab 05 — Retrieval-Augmented Generation (RAG)",
        border_style="bright_blue",
    ))
    if wait_for_input:
        console.input("\n[dim]Press Enter to continue...[/]")


# ── Sample Documents ──────────────────────────────────────────────────────────

SAMPLE_DOCS = [
    {
        "id": "doc-001",
        "title": "NERC Transmission Planning Standard TPL-001-5",
        "content": (
            "NERC Standard TPL-001-5 establishes requirements for transmission planning in the bulk "
            "electric system (BES). Planning coordinators and transmission planners must ensure the "
            "BES can serve load under steady-state and contingency conditions. The standard requires "
            "annual steady-state and stability assessments for P0 through P7 contingency categories, "
            "ranging from no contingency to extreme events. TVA, as a planning coordinator, must "
            "demonstrate N-1 and N-1-1 reliability and document corrective action plans for any "
            "violations of thermal, voltage, or stability limits."
        ),
        "category": "reliability",
    },
    {
        "id": "doc-002",
        "title": "TVA Vegetation Management Standard Practice",
        "content": (
            "TVA's Vegetation Management Standard Practice defines minimum clearance distances for "
            "transmission line rights-of-way. For 500kV transmission lines, a minimum radial "
            "clearance of 15 feet must be maintained to prevent flashover under maximum sag "
            "conditions. Annual aerial surveys using LiDAR are required for all 500kV and 161kV "
            "corridors. High-growth zones must be patrolled quarterly. Encroachment risk scores "
            "are calculated using a combination of species growth rate, proximity to conductor, "
            "and historical outage data. Work orders must be issued within 5 business days for "
            "any span rated Critical or High risk."
        ),
        "category": "operations",
    },
    {
        "id": "doc-003",
        "title": "Extreme Cold Weather Operations Procedure",
        "content": (
            "During extreme cold weather events (forecast temperatures below 10 degrees F), TVA activates "
            "the Cold Weather Operations Procedure. Unit commitment must be maximized 48 hours in "
            "advance: all available hydro units are brought to full capacity, combined-cycle gas "
            "units are pre-warmed, and combustion turbine peakers are placed on hot standby. "
            "Fuel oil reserves must be verified at or above 72-hour burn capacity for all oil-fired "
            "units. Load shedding thresholds are set at 3% below forecast peak. Demand response "
            "programs are activated when reserve margin falls below 12%. System operators must "
            "coordinate with neighboring utilities via the SERC Reliability Corporation emergency "
            "assistance protocols."
        ),
        "category": "operations",
    },
    {
        "id": "doc-004",
        "title": "Dam Safety Monitoring Protocol",
        "content": (
            "TVA's Dam Safety Monitoring Protocol governs instrumentation, inspection, and emergency "
            "response for all 49 TVA dams. Each dam must have continuous piezometer and seepage "
            "monitoring with automated alerts when readings exceed threshold values. Formal "
            "inspections are conducted annually by TVA staff and every five years by an independent "
            "board of consultants. Seismic sensors are required at all concrete gravity and arch "
            "dams; triggered recordings above 0.05g must be reviewed within 24 hours. Flood "
            "inundation maps and Emergency Action Plans (EAPs) must be updated every three years "
            "and shared with local emergency management agencies. During a flood event exceeding "
            "the 100-year return period, the Dam Safety Manager must be notified immediately and "
            "downstream communities alerted per the EAP."
        ),
        "category": "safety",
    },
    {
        "id": "doc-005",
        "title": "Renewable Integration and Battery Storage Guidelines",
        "content": (
            "TVA's Renewable Integration and Battery Storage Guidelines provide technical "
            "requirements for connecting utility-scale solar and battery energy storage systems "
            "(BESS) to the TVA transmission system. Solar farms above 20 MW must provide reactive "
            "power support and low-voltage ride-through capability per IEEE 1547-2018. BESS systems "
            "must be capable of providing frequency regulation services within 200 milliseconds of "
            "a frequency deviation exceeding 0.036 Hz. Co-located solar-plus-storage projects must "
            "submit an integrated interconnection study. All inverter-based resources must include "
            "cybersecurity controls compliant with NERC CIP standards. Forecasting accuracy of "
            "plus or minus 5% for day-ahead solar generation is required for resources above 50 MW."
        ),
        "category": "planning",
    },
]


# ── Exercise 1: Create Search Index ───────────────────────────────────────────

def exercise_1_create_index():
    """Create an Azure AI Search index with text and vector fields."""
    section("Exercise 1 — Create Search Index")

    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SimpleField,
        SearchableField,
        SearchField,
        SearchFieldDataType,
        VectorSearch,
        HnswAlgorithmConfiguration,
        VectorSearchProfile,
    )
    from azure.core.credentials import AzureKeyCredential

    config = get_search_config()
    index_client = SearchIndexClient(
        endpoint=config["endpoint"],
        credential=AzureKeyCredential(config["admin_key"]),
    )

    index_name = config["index_name"]

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="vector-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
        profiles=[VectorSearchProfile(name="vector-profile", algorithm_configuration_name="hnsw-config")],
    )

    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)

    result = index_client.create_or_update_index(index)
    console.print(f"[green]Created/updated index:[/] {result.name}")
    console.print(f"[dim]Fields: {', '.join(f.name for f in result.fields)}[/]")

    return index_name


# ── Exercise 2: Generate Embeddings ───────────────────────────────────────────

def exercise_2_generate_embeddings():
    """Generate vector embeddings for sample documents."""
    section("Exercise 2 — Generate Embeddings")

    openai = get_openai_embedding_client()

    for doc in SAMPLE_DOCS:
        response = openai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=doc["content"],
        )
        doc["content_vector"] = response.data[0].embedding
        console.print(f"  [green]✓[/] {doc['id']}: {doc['title']} "
                      f"[dim]({len(doc['content_vector'])} dims)[/]")

    console.print(f"\n[green]Generated embeddings for {len(SAMPLE_DOCS)} documents.[/]")
    return SAMPLE_DOCS


# ── Exercise 3: Upload Documents ──────────────────────────────────────────────

def exercise_3_upload_documents(index_name: str, docs: list):
    """Upload documents with embeddings to Azure AI Search."""
    section("Exercise 3 — Upload Documents")

    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential

    config = get_search_config()
    search_client = SearchClient(
        endpoint=config["endpoint"],
        index_name=index_name,
        credential=AzureKeyCredential(config["admin_key"]),
    )

    result = search_client.upload_documents(documents=docs)
    succeeded = sum(1 for r in result if r.succeeded)
    console.print(f"[green]Uploaded {succeeded}/{len(docs)} documents.[/]")


# ── Exercise 4: Hybrid Search ─────────────────────────────────────────────────

def exercise_4_hybrid_search(index_name: str):
    """Perform hybrid search (keyword + vector) with semantic ranking."""
    section("Exercise 4 — Hybrid Search")

    from azure.search.documents import SearchClient
    from azure.search.documents.models import VectorizedQuery
    from azure.core.credentials import AzureKeyCredential

    config = get_search_config()
    search_client = SearchClient(
        endpoint=config["endpoint"],
        index_name=index_name,
        credential=AzureKeyCredential(config["admin_key"]),
    )

    # Generate query embedding
    openai = get_openai_embedding_client()

    query_text = "What is the required vegetation clearance distance for 500kV transmission lines?"
    console.print(f"[bold]Query:[/] {query_text}\n")

    query_embedding = openai.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query_text,
    ).data[0].embedding

    # Hybrid search: keyword + vector
    results = search_client.search(
        search_text=query_text,
        vector_queries=[
            VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=3,
                fields="content_vector",
            )
        ],
        top=3,
        select=["id", "title", "content", "category"],
    )

    retrieved_docs = []
    for i, result in enumerate(results):
        retrieved_docs.append(result)
        console.print(Panel(
            f"[bold]{result['title']}[/] (category: {result['category']})\n\n{result['content']}",
            title=f"Result {i + 1} — Score: {result['@search.score']:.4f}",
        ))

    return query_text, retrieved_docs


# ── Exercise 5: RAG — Grounded Generation ─────────────────────────────────────

def exercise_5_rag_generation(query: str, context_docs: list):
    """Augment a prompt with retrieved context and generate a grounded answer."""
    section("Exercise 5 — RAG: Grounded Generation")

    client = get_project_client()
    openai = client.get_openai_client()

    # Build context from retrieved documents
    context = "\n\n".join(
        f"[{doc['title']}]\n{doc['content']}" for doc in context_docs
    )

    system_msg = (
        "You are a TVA operations knowledge assistant. Answer the user's question "
        "using ONLY the provided TVA procedures and standards. Cite document titles in "
        "square brackets. If the context doesn't contain enough information, "
        "say so explicitly. Flag any safety-critical information with a warning emoji."
    )
    console.print(Panel(
        f"[bold]System:[/]\n{system_msg}\n\n"
        f"[bold]User query:[/]\n{query}\n\n"
        f"[bold]Context documents:[/] {len(context_docs)} retrieved\n"
        + "\n".join(f"  • {doc['title']}" for doc in context_docs),
        title="📋 Prompt Breakdown", border_style="dim",
    ))

    messages = [
        {
            "role": "system",
            "content": system_msg,
        },
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}",
        },
    ]

    response = openai.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=500,
    )

    answer = response.choices[0].message.content
    console.print(Panel(answer, title="RAG-Grounded Answer", style="bold green"))
    console.print(f"[dim]Sources used: {len(context_docs)} documents[/]")
    console.print(f"[dim]Tokens: {response.usage.total_tokens}[/]")


# ── Exercise Metadata ─────────────────────────────────────────────────────────

EXERCISES = [
    {
        "num": "1", "title": "Exercise 1 — Create Search Index",
        "short": "Design and deploy an Azure AI Search index with vector fields.",
        "why": "A well-designed index is the foundation of any retrieval system. Schema\n"
               "choices (fields, analyzers, vector config) directly affect search quality.",
        "concepts": "• Azure AI Search index schema definition\n"
                    "• Field types: searchable text, filterable, vector\n"
                    "• Vector search configuration (algorithm, dimensions)\n"
                    "• Semantic ranking configuration",
        "builds_on": "New topic — sets up the infrastructure that all RAG exercises depend on.",
        "summary": "Created an Azure AI Search index with text fields (title, content) and a\n"
                   "vector field (content_vector) for hybrid search. Configured HNSW algorithm\n"
                   "for approximate nearest neighbor search with 3072 dimensions.",
        "key_functions": "• SearchIndexClient — manages index definitions\n"
                         "• SimpleField / SearchableField / SearchField — field types\n"
                         "• VectorSearch + HnswAlgorithmConfiguration — vector config\n"
                         "• VectorSearchProfile — links algorithm to field\n"
                         "• index_client.create_or_update_index() — deploy the index",
        "code_pattern": "fields = [\n"
                        "    SimpleField(name=\"id\", type=String, key=True),\n"
                        "    SearchableField(name=\"content\", type=String),\n"
                        "    SearchField(name=\"content_vector\", type=Collection(Single),\n"
                        "        vector_search_dimensions=3072, ...),\n"
                        "]\n"
                        "index_client.create_or_update_index(SearchIndex(name, fields, vector_search))",
        "looking_ahead": "Next we generate vector embeddings for our documents.",
    },
    {
        "num": "2", "title": "Exercise 2 — Generate Embeddings",
        "short": "Turn text into vector representations for semantic similarity search.",
        "why": "Embeddings capture meaning, not just keywords. They enable finding\n"
               "semantically similar content even when exact words don't match.",
        "concepts": "• Embedding models (text-embedding-3-large)\n"
                    "• Vector representations and dimensionality\n"
                    "• Semantic similarity vs. keyword matching\n"
                    "• Batch embedding generation",
        "builds_on": "Exercise 1's index schema — which includes vector fields for embeddings.",
        "summary": "Used the embedding model to convert each document's text content into a\n"
                   "3072-dimensional vector. These vectors capture semantic meaning — similar\n"
                   "concepts produce similar vectors, enabling meaning-based search.",
        "key_functions": "• openai.embeddings.create(model, input) — generate embedding\n"
                         "• response.data[0].embedding — the vector (list of floats)\n"
                         "• get_openai_embedding_client() — dedicated embedding client\n"
                         "• EMBEDDING_MODEL (text-embedding-3-large) — 3072 dimensions",
        "code_pattern": "response = openai.embeddings.create(\n"
                        "    model=EMBEDDING_MODEL,\n"
                        "    input=doc[\"content\"],\n"
                        ")\n"
                        "doc[\"content_vector\"] = response.data[0].embedding",
        "looking_ahead": "Next we upload these documents + vectors to the search index.",
    },
    {
        "num": "3", "title": "Exercise 3 — Upload Documents",
        "short": "Populate the search index with documents and their embeddings.",
        "why": "The retrieval pipeline needs data. Document ingestion connects your\n"
               "content to the search infrastructure for querying.",
        "concepts": "• Document preparation (text + metadata + vectors)\n"
                    "• Batch upload to Azure AI Search\n"
                    "• Index population and refresh timing\n"
                    "• Document structure best practices",
        "builds_on": "Exercise 1's index + Exercise 2's embeddings — combines both.",
        "summary": "Uploaded documents (with text, metadata, and vector embeddings) to the\n"
                   "Azure AI Search index using batch upload. Each document includes id,\n"
                   "title, content, category, and the content_vector generated in Exercise 2.",
        "key_functions": "• SearchClient(endpoint, index_name, credential) — data plane client\n"
                         "• search_client.upload_documents(documents) — batch upload\n"
                         "• result.succeeded — check upload status per document",
        "code_pattern": "search_client = SearchClient(endpoint, index_name, credential)\n"
                        "result = search_client.upload_documents(documents=docs)\n"
                        "succeeded = sum(1 for r in result if r.succeeded)",
        "looking_ahead": "Next we query the index using hybrid search (keyword + vector).",
    },
    {
        "num": "4", "title": "Exercise 4 — Hybrid Search",
        "short": "Combine keyword + vector search for better results than either alone.",
        "why": "Hybrid search consistently outperforms pure keyword or pure vector search.\n"
               "It catches both exact term matches and semantic similarities.",
        "concepts": "• Hybrid search: BM25 keyword + vector similarity\n"
                    "• Relevance scoring and result ranking\n"
                    "• Semantic reranking for improved precision\n"
                    "• Query construction and search parameters",
        "builds_on": "Exercises 1-3's populated index — queries it with hybrid search.",
        "summary": "Performed hybrid search combining keyword matching (BM25) with vector\n"
                   "similarity. The query text finds exact term matches while the query\n"
                   "embedding finds semantically similar content — best of both worlds.",
        "key_functions": "• VectorizedQuery(vector, k_nearest_neighbors, fields) — vector query\n"
                         "• search_client.search(search_text, vector_queries, top, select)\n"
                         "• result['@search.score'] — combined relevance score\n"
                         "• Embedding the query: openai.embeddings.create(model, input=query)",
        "code_pattern": "query_embedding = openai.embeddings.create(model, input=query).data[0].embedding\n"
                        "results = search_client.search(\n"
                        "    search_text=query,\n"
                        "    vector_queries=[VectorizedQuery(\n"
                        "        vector=query_embedding, k_nearest_neighbors=3,\n"
                        "        fields=\"content_vector\")],\n"
                        "    top=3,\n"
                        ")",
        "looking_ahead": "Next we complete the RAG pipeline: retrieve → augment prompt → generate.",
    },
    {
        "num": "5", "title": "Exercise 5 — RAG: Grounded Generation",
        "short": "Generate answers grounded in retrieved documents with citations.",
        "why": "RAG is how you make LLMs answer from YOUR data, not just training data.\n"
               "Grounding dramatically reduces hallucination and enables citation.",
        "concepts": "• The RAG pattern: retrieve → augment prompt → generate\n"
                    "• Context injection into the system/user message\n"
                    "• Citation generation and source attribution\n"
                    "• Grounded vs. ungrounded response comparison",
        "builds_on": "The complete RAG pipeline — all previous exercises culminate here.",
        "summary": "Completed the RAG pipeline: retrieved documents from Exercise 4, injected\n"
                   "them as context into the prompt, and generated a grounded answer with\n"
                   "source citations. The model answered from YOUR documents, not training data.",
        "key_functions": "• Context injection: f\"Context:\\n{context}\\n\\nQuestion: {query}\"\n"
                         "• System prompt: \"Answer using ONLY the provided context\"\n"
                         "• temperature=0.3 — low temperature for factual accuracy\n"
                         "• Citation instruction: \"Cite document titles in [brackets]\"",
        "code_pattern": "context = \"\\n\".join(f\"[{doc['title']}]\\n{doc['content']}\" for doc in docs)\n"
                        "messages = [\n"
                        "    {\"role\": \"system\", \"content\": \"Answer using ONLY the context...\"},\n"
                        "    {\"role\": \"user\", \"content\": f\"Context:\\n{context}\\n\\nQuestion: {q}\"},\n"
                        "]\n"
                        "response = openai.chat.completions.create(model, messages, temperature=0.3)",
    },
]

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from shared.exercise_menu import show_exercise_menu, show_exercise_intro, show_exercise_summary

    if "--intro-only" in sys.argv:
        show_lab_intro(wait_for_input=False)
        choice = console.input("\n[dim]Would you like to view exercise descriptions? (y/n): [/]").strip().lower()
        if choice == "y":
            show_exercise_menu("Lab 05 — RAG", EXERCISES)
        raise SystemExit(0)

    # --exercise N  → run only exercise N (e.g. --exercise 4)
    # NOTE: Exercises 3-5 depend on earlier exercises for data (index, docs).
    # When jumping ahead, prerequisites run automatically.
    selected = None
    if "--exercise" in sys.argv:
        idx = sys.argv.index("--exercise")
        if idx + 1 < len(sys.argv):
            try:
                selected = int(sys.argv[idx + 1])
            except ValueError:
                pass
        valid = {1, 2, 3, 4, 5}
        if selected not in valid:
            console.print(f"[bold red]Invalid exercise number. Choose from: {sorted(valid)}[/]")
            raise SystemExit(1)

    console.print(Panel(
        "[bold]Lab 05 — Retrieval-Augmented Generation (RAG)[/]\n"
        "Azure AI Search + Foundry SDK v2.0",
        style="bold green",
    ))

    def run_pipeline(up_to: int):
        """Run exercises 1..up_to, passing data between them."""
        index_name = None
        docs = None
        query = None
        context_docs = None

        exercise_funcs = {
            1: exercise_1_create_index,
            2: exercise_2_generate_embeddings,
            3: exercise_3_upload_documents,
            4: exercise_4_hybrid_search,
            5: exercise_5_rag_generation,
        }

        for n in range(1, up_to + 1):
            show_exercise_intro(EXERCISES[n - 1], func=exercise_funcs[n])
            if n == 1:
                index_name = exercise_1_create_index()
            elif n == 2:
                docs = exercise_2_generate_embeddings()
            elif n == 3:
                exercise_3_upload_documents(index_name, docs)
                import time
                console.print("\n[dim]Waiting 3s for indexing...[/]")
                time.sleep(3)
            elif n == 4:
                query, context_docs = exercise_4_hybrid_search(index_name)
            elif n == 5:
                exercise_5_rag_generation(query, context_docs)
            show_exercise_summary(EXERCISES[n - 1])
            if n < up_to:
                if not selected:
                    console.input("\n[dim]Press Enter to continue...[/]")

    if selected:
        if selected > 1:
            console.print(f"[dim]Running prerequisites (exercises 1–{selected - 1}) first...[/]\n")
        run_pipeline(up_to=selected)
    else:
        show_lab_intro()
        run_pipeline(up_to=5)

    console.print("\n[bold green]✓ Lab 05 complete![/]\n")

    console.print("\n[bold green]✓ Lab 05 complete![/]\n")
