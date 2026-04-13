"""
Lab 03 — Agents
================
Build an autonomous AI agent using Azure AI Foundry Agent Service.

Prerequisites:
  - .env populated with AZURE_AI_PROJECT_ENDPOINT
  - azure-ai-projects SDK installed (included in foundry-lab/requirements.txt)

Run:
  FOUNDRY_LAB=03 npx just foundry:lab
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../../.env'))

PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
DEPLOYMENT       = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
AGENT_NAME       = os.getenv("AZURE_AGENT_NAME", "tva-compliance-agent")

EXERCISES = {
    "1": "Create a compliance agent and run a single query",
    "2": "Multi-turn agent conversation",
    "3": "Agent with file search (upload TVA docs)",
    "Q": "Quit",
}


def check_env():
    if not PROJECT_ENDPOINT:
        print("\n❌  Missing AZURE_AI_PROJECT_ENDPOINT in .env")
        print("   Find it in Azure AI Foundry portal → your project → Overview.\n")
        sys.exit(1)


def get_client():
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
    return AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())


def exercise_1(client):
    print("\n── Exercise 1: Create Agent + Single Query ─────────────────")
    agents = client.agents
    agent = agents.create_agent(
        model=DEPLOYMENT,
        name=AGENT_NAME,
        instructions=(
            "You are a TVA compliance advisor. Answer questions about NERC CIP standards "
            "and TVA grid operations. Be concise and cite specific requirements."
        ),
    )
    print(f"  ✅ Agent created: {agent.id}")

    thread = agents.create_thread()
    agents.create_message(thread_id=thread.id, role="user",
                          content="What is the patch window under NERC CIP-007?")
    run = agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)
    print(f"  Run status: {run.status}")

    messages = agents.list_messages(thread_id=thread.id)
    for msg in reversed(list(messages)):
        if msg.role == "assistant":
            for block in msg.content:
                if hasattr(block, "text"):
                    print(f"\n  Agent: {block.text.value}")
            break

    agents.delete_agent(agent.id)
    print("  ✅ Agent cleaned up")


def exercise_2(client):
    print("\n── Exercise 2: Multi-turn Agent Conversation ───────────────")
    print("Type 'done' to end.\n")
    agents = client.agents
    agent = agents.create_agent(
        model=DEPLOYMENT,
        name=AGENT_NAME,
        instructions="You are a TVA compliance advisor. Be concise.",
    )
    thread = agents.create_thread()

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("done", "exit", "quit"):
            break
        agents.create_message(thread_id=thread.id, role="user", content=user_input)
        run = agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)
        messages = agents.list_messages(thread_id=thread.id)
        for msg in reversed(list(messages)):
            if msg.role == "assistant":
                for block in msg.content:
                    if hasattr(block, "text"):
                        print(f"Agent: {block.text.value}\n")
                break

    agents.delete_agent(agent.id)
    print("  ✅ Agent cleaned up")


def exercise_3(client):
    print("\n── Exercise 3: Agent with File Search ──────────────────────")
    print("  This exercise uploads a sample TVA document and uses it for RAG.")
    agents = client.agents

    sample_doc = (
        "NERC CIP-007 requires patch management within 35 days for critical patches. "
        "TVA's Brownsville facility last completed its patch cycle on 2026-02-15. "
        "Next review due: 2026-05-15."
    )

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(sample_doc)
        tmp_path = f.name

    with open(tmp_path, "rb") as f:
        uploaded = agents.upload_file_and_poll(file=f, purpose="assistants")
    print(f"  ✅ File uploaded: {uploaded.id}")

    vs = agents.create_vector_store_and_poll(file_ids=[uploaded.id], name="tva-docs")
    print(f"  ✅ Vector store: {vs.id}")

    agent = agents.create_agent(
        model=DEPLOYMENT,
        name=AGENT_NAME,
        instructions="Use the provided documents to answer TVA compliance questions.",
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vs.id]}},
    )
    thread = agents.create_thread()
    agents.create_message(thread_id=thread.id, role="user",
                          content="When is Brownsville's next NERC CIP-007 patch review?")
    run = agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)
    messages = agents.list_messages(thread_id=thread.id)
    for msg in reversed(list(messages)):
        if msg.role == "assistant":
            for block in msg.content:
                if hasattr(block, "text"):
                    print(f"\n  Agent: {block.text.value}")
            break

    agents.delete_agent(agent.id)
    agents.delete_vector_store(vs.id)
    os.unlink(tmp_path)
    print("  ✅ Resources cleaned up")


def main():
    check_env()
    client = get_client()
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   Lab 03 — Agents                                       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    while True:
        print("\nExercises:")
        for k, v in EXERCISES.items():
            print(f"  [{k}] {v}")
        choice = input("Select: ").strip().upper()
        if choice == "1":
            exercise_1(client)
        elif choice == "2":
            exercise_2(client)
        elif choice == "3":
            exercise_3(client)
        elif choice == "Q":
            print("👋 Done!")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
