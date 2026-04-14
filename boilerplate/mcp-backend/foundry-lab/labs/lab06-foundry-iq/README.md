# Lab 06 — Foundry IQ (Knowledge Retrieval for Agents)

## Objective

Explore **Foundry IQ** — Microsoft's unified knowledge layer that provides
enterprise-grade, permission-aware, agentic retrieval for AI agents. Built on
Azure AI Search, Foundry IQ goes beyond naive RAG with multi-hop reasoning,
query decomposition, and cross-document synthesis.

## What is Foundry IQ?

Foundry IQ is a knowledge layer announced at Microsoft Ignite 2025. It provides:

- **Reusable knowledge bases** that ground multiple agents and apps
- **Agentic Retrieval Engine** with multi-hop query planning
- **Permission-aware access** integrated with Entra ID
- **Automated indexing** for documents, images, and structured data
- **40% better response relevance** vs. naive RAG (per Microsoft benchmarks)

### Foundry IQ vs. Naive RAG

| Feature | Naive RAG | Foundry IQ |
|---------|-----------|------------|
| Query strategy | Single search pass | Multi-hop decomposition + reasoning |
| Source coverage | Top-K from one query | Multiple search angles, deduplicated |
| Permissions | Manual ACL implementation | Built-in Entra ID integration |
| Reusability | Per-application index | Shared knowledge base across agents |
| Enrichment | Manual chunking/embedding | Automated indexing + enrichment |

## Concepts Covered

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Agent + Search Tool | Agent with Azure AI Search as knowledge source |
| 2 | Agentic Retrieval | Multi-hop reasoning with query decomposition |
| 3 | Naive vs. Agentic | Side-by-side comparison of retrieval quality |

## Run

```bash
cd foundry-lab
# Run Lab 05 first to create the search index
python labs/lab05-rag/lab05_rag.py
# Then run this lab
python labs/lab06-foundry-iq/lab06_foundry_iq.py
```

## Challenges

- Add document-level access control so that dam safety documents are only accessible to users with the `dam-safety` role
- Implement a "confidence score" that measures how well the TVA knowledge base grounded each answer
- Extend the multi-hop Kingston retirement query to also search a second index containing TVA rate case filings
- Add a feedback loop where the agent retries with refined sub-queries if the initial retrieval returns fewer than 2 relevant documents
- Build a knowledge base spanning TVA operational procedures, environmental compliance docs, and engineering standards
