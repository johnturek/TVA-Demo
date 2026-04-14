# Lab 02 — Responses API

## Objective

Explore the **OpenAI Responses API** — a newer, stateless API that supports
built-in tools (web search, file search), structured output, and chained
multi-turn conversations via `previous_response_id`.

## Concepts Covered

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Basic Response | `responses.create()` for simple text generation |
| 2 | Structured Output | JSON Schema enforcement for reliable parsing |
| 3 | Web Search Tool | Built-in `web_search_preview` for grounded answers |
| 4 | Multi-Turn Chaining | `previous_response_id` for stateless conversation |
| 5 | Streaming | Token-by-token streaming with the Responses API |

## Responses API vs. Chat Completions

| Feature | Chat Completions | Responses API |
|---------|-----------------|---------------|
| State management | Client-managed message array | Server-managed via `previous_response_id` |
| Built-in tools | None | `web_search_preview`, `file_search`, `code_interpreter` |
| Structured output | `response_format` | `text.format.json_schema` |
| Streaming | `stream=True` | `stream=True` with typed events |

## Run

```bash
cd foundry-lab
python labs/lab02-responses-api/lab02_responses.py
```

## Challenges

- Extend the TVA generation assets schema to include `fuel_type` and `last_maintenance_date` fields
- Chain 5+ turns on the intra-hour load forecasting topic and observe how context accumulates
- Use the web search tool to find recent NERC reliability standards updates and compare with TVA's current practices
- Compare structured output reliability vs. asking the model to "return JSON" for generation asset data
