"""
Lab 05 — RAG with Azure AI Search (Stretch Goal)
==================================================
Build a retrieval-augmented generation pipeline using Azure AI Search
as the knowledge base for TVA compliance documents.

Prerequisites:
  - .env with AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY
  - .env with AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_ADMIN_KEY, AZURE_SEARCH_INDEX_NAME
  - Run `npx just upload-docs` first to populate the search index

Run:
  FOUNDRY_LAB=05 npx just foundry:lab
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../../.env'))

OPENAI_ENDPOINT  = os.getenv("AZURE_OPENAI_ENDPOINT", "")
OPENAI_KEY       = os.getenv("AZURE_OPENAI_KEY", "")
DEPLOYMENT       = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
SEARCH_ENDPOINT  = os.getenv("AZURE_SEARCH_ENDPOINT", "")
SEARCH_KEY       = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
INDEX_NAME       = os.getenv("AZURE_SEARCH_INDEX_NAME", "tva-knowledge-base")

EXERCISES = {
    "1": "Keyword search the TVA knowledge base",
    "2": "RAG — search + generate answer",
    "3": "Hybrid search (keyword + vector)",
    "Q": "Quit",
}


def check_env():
    missing = []
    if not OPENAI_ENDPOINT or not OPENAI_KEY:
        missing.append("AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_KEY")
    if not SEARCH_ENDPOINT or not SEARCH_KEY:
        missing.append("AZURE_SEARCH_ENDPOINT / AZURE_SEARCH_ADMIN_KEY")
    if missing:
        print(f"\n❌  Missing in .env: {', '.join(missing)}\n")
        sys.exit(1)


def get_search_client():
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
    return SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY),
    )


def get_openai_client():
    from openai import AzureOpenAI
    return AzureOpenAI(azure_endpoint=OPENAI_ENDPOINT, api_key=OPENAI_KEY, api_version="2024-02-01")


def exercise_1(search_client):
    print("\n── Exercise 1: Keyword Search ───────────────────────────────")
    query = input("  Search query: ").strip() or "patch management"
    results = search_client.search(search_text=query, top=3)
    for r in results:
        title = r.get("title", r.get("id", "unknown"))
        content = r.get("content", "")[:200]
        print(f"\n  📄 {title}")
        print(f"     {content}...")


def exercise_2(search_client, openai_client):
    print("\n── Exercise 2: RAG — Search + Generate ─────────────────────")
    question = input("  Question: ").strip() or "What is TVA's patch management policy?"

    results = search_client.search(search_text=question, top=3)
    context = "\n\n".join(
        f"[{r.get('title', r.get('id', 'doc'))}]\n{r.get('content', '')}"
        for r in results
    )

    if not context.strip():
        print("  ⚠️  No documents found. Run `npx just upload-docs` to populate the index.")
        return

    response = openai_client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a TVA compliance advisor. Answer using only the provided documents. "
                    "Cite specific documents when relevant."
                ),
            },
            {
                "role": "user",
                "content": f"Documents:\n{context}\n\nQuestion: {question}",
            },
        ],
        max_tokens=300,
    )
    print(f"\n  Answer: {response.choices[0].message.content}")


def exercise_3(search_client):
    print("\n── Exercise 3: Hybrid Search ────────────────────────────────")
    print("  ℹ️  Hybrid search requires a vector index with embeddings.")
    print("     This exercise shows the API structure; run after setting up")
    print("     an embedding model in your Foundry project.")
    query = input("  Search query: ").strip() or "CIP-007 compliance"
    try:
        from azure.search.documents.models import VectorizableTextQuery
        results = search_client.search(
            search_text=query,
            vector_queries=[VectorizableTextQuery(text=query, k_nearest_neighbors=3, fields="content_vector")],
            top=3,
        )
        for r in results:
            title = r.get("title", r.get("id", "unknown"))
            score = r.get("@search.score", 0)
            print(f"  📄 {title} (score: {score:.3f})")
    except Exception as e:
        print(f"  ⚠️  {e}")
        print("     Ensure your index has a content_vector field with embeddings.")


def main():
    check_env()
    search_client = get_search_client()
    openai_client = get_openai_client()
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   Lab 05 — RAG with Azure AI Search (Stretch Goal)      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    while True:
        print("\nExercises:")
        for k, v in EXERCISES.items():
            print(f"  [{k}] {v}")
        choice = input("Select: ").strip().upper()
        if choice == "1":
            exercise_1(search_client)
        elif choice == "2":
            exercise_2(search_client, openai_client)
        elif choice == "3":
            exercise_3(search_client)
        elif choice == "Q":
            print("👋 Done!")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
