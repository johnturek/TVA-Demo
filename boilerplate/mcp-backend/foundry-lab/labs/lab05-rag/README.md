# Lab 05 — Retrieval-Augmented Generation (RAG)

## Objective

Build an end-to-end **RAG pipeline** using Azure AI Search for retrieval and
the Foundry SDK v2.0 for embedding generation and grounded answer synthesis.

## Pipeline

```
Documents → Embed → Upload to Azure AI Search
                              │
User Query → Embed → Hybrid Search (BM25 + Vector + Semantic)
                              │
                      Retrieved Context
                              │
                   Augment Prompt → LLM → Grounded Answer
```

## Concepts Covered

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Index Creation | Define text + vector fields in Azure AI Search |
| 2 | Embedding Generation | Use `text-embedding-3-large` via Foundry |
| 3 | Document Upload | Batch upload documents with vectors |
| 4 | Hybrid Search | Keyword + vector + semantic reranking |
| 5 | RAG Generation | Grounded, source-cited answers |

## Run

```bash
cd foundry-lab
python labs/lab05-rag/lab05_rag.py
```

## Key Concepts

- **BM25**: Term-frequency keyword scoring (great for exact matches)
- **Vector search**: Cosine similarity on embeddings (great for semantic)
- **Hybrid**: Reciprocal Rank Fusion (RRF) merges both signals
- **Semantic ranker**: Cross-encoder reranking for final relevance boost

## Challenges

- Add semantic ranking (`query_type="semantic"`) and compare results for the vegetation clearance query
- Add metadata filtering to restrict answers to `category eq 'safety'` for dam-related queries
- Implement chunking to split long TVA procedures into overlapping 512-token chunks
- Add a second query: *"What emergency notifications are required during a flood event at a TVA dam?"* and compare RAG answer quality with/without retrieved context
- Index additional TVA documents such as the Cold Weather Operations Procedure and query for unit commitment thresholds
