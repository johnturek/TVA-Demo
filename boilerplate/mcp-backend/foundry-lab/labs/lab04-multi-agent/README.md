# Lab 04 — Multi-Agent Architectures

## Objective

Explore enterprise multi-agent patterns using the **Azure AI Foundry Agent
Service v2**. Each pattern demonstrates a different orchestration topology
for solving complex, real-world problems.

## Patterns Covered

| # | Pattern | Topology | Use Case |
|---|---------|----------|----------|
| 1 | Sequential Pipeline | A → B → C | TVA dispatch planning: data engineering → load forecasting → generation dispatch |
| 2 | Parallel Fan-Out / Fan-In | A ⟶ [B,C,D] → E | TVA solar/storage proposal evaluated by environmental, reliability, and cost analysts |
| 3 | Supervisor / Worker | S → [W₁, W₂, W₃] | Vegetation risk scoring pipeline decomposed by supervisor across worker agents |
| 4 | Critic / Refinement Loop | G ⇄ C | PI historian anomaly detection code reviewed for operational safety and TVA standards |

## Architecture

```
Pattern 1: Sequential          Pattern 2: Fan-Out / Fan-In

  Data Engineer                 ┌── Environmental ──┐
      │                          │                   │
      ▼               Proposal ──┼── Reliability ────┼── Synthesizer
  Load Forecaster                 │                   │
      │                          └── Cost Analyst ───┘
      ▼
  Grid Dispatcher

Pattern 3: Supervisor           Pattern 4: Critic Loop

  Supervisor                     Generator ──► Critic
    │  │  │                          ▲            │
    ▼  ▼  ▼                          └── if not ──┘
  W₁  W₂  W₃                            APPROVED
```

## Run

```bash
cd foundry-lab
python labs/lab04-multi-agent/lab04_multi_agent.py
```

## Key Design Decisions

- **Agent isolation**: Each agent has a separate thread (no shared context leakage)
- **Cleanup**: Agents are deleted after use to avoid quota exhaustion
- **Orchestration in code**: The Python script controls flow — agents don't call each other directly
- **Deterministic routing**: Supervisor output is parsed as JSON for reliable task dispatch

## Challenges

- Add a 5th pattern: "Debate" — have a Renewable Advocate and a Grid Stability Engineer debate the Kingston retirement, with a TVA executive as judge
- Implement true parallel execution for the fan-out pattern using `asyncio.gather()`
- Extend the vegetation risk supervisor to produce a prioritized weekly work order schedule
- Add token budget tracking across the entire multi-agent dispatch pipeline
