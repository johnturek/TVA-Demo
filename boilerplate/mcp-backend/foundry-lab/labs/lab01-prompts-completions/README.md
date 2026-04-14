# Lab 01 — Prompts & Completions

## Objective

Learn the fundamentals of interacting with Azure AI Foundry models through the
**Foundry SDK v2.0** (`azure-ai-projects`). You will authenticate via
`DefaultAzureCredential`, obtain an OpenAI-compatible client from your Foundry
project, and explore prompt engineering techniques.

## Concepts Covered

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Basic Chat Completion | Send a prompt → receive a response |
| 2 | System Prompt Engineering | Steer model behavior with system messages |
| 3 | Temperature & Sampling | Control creativity vs. determinism |
| 4 | Streaming Completion | Token-by-token output for real-time UX |
| 5 | Multi-Turn Conversation | Maintain context across turns |

## Prerequisites

1. Run `deploy.ps1` to provision the Azure infrastructure
2. Copy the output values into `foundry-lab/.env`
3. Install dependencies: `pip install -r requirements.txt`
4. Authenticate: `az login`

## Run

```bash
cd foundry-lab
python labs/lab01-prompts-completions/lab01_completions.py
```

## Key SDK Patterns

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient(
    endpoint="https://<account>.services.ai.azure.com/api/projects/<project>",
    credential=DefaultAzureCredential(),
)

# Get an OpenAI-compatible client scoped to this project
openai = client.get_openai_client()

response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello, Foundry!"}],
)
```

## Challenges

- Add a **Hydro Operator** persona and ask it to explain how TVA dispatches hydro units during peak demand
- Lower `temperature` to 0.0 for the load spike diagnosis prompt — observe how determinism affects root cause analysis
- Extend the multi-turn conversation to ask: *"Generate a Python function that reads hourly load data from a CSV and flags peaks above the 95th percentile"*
- Experiment with `top_p` vs `temperature` using the demand response question
