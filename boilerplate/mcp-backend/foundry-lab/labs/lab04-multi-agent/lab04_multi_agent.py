"""
Lab 04 — Multi-Agent Orchestration (Stretch Goal)
===================================================
Coordinate multiple specialized agents to solve a complex compliance task.

Prerequisites:
  - .env populated with AZURE_AI_PROJECT_ENDPOINT
  - Completed Labs 01–03

Run:
  FOUNDRY_LAB=04 npx just foundry:lab
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../../.env'))

PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
DEPLOYMENT       = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

EXERCISES = {
    "1": "Two-agent handoff — researcher + summarizer",
    "2": "Parallel agent evaluation",
    "Q": "Quit",
}


def check_env():
    if not PROJECT_ENDPOINT:
        print("\n❌  Missing AZURE_AI_PROJECT_ENDPOINT in .env\n")
        sys.exit(1)


def get_client():
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
    return AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())


def run_agent(agents, model, name, instructions, user_message):
    agent = agents.create_agent(model=model, name=name, instructions=instructions)
    thread = agents.create_thread()
    agents.create_message(thread_id=thread.id, role="user", content=user_message)
    run = agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)
    messages = agents.list_messages(thread_id=thread.id)
    result = ""
    for msg in reversed(list(messages)):
        if msg.role == "assistant":
            for block in msg.content:
                if hasattr(block, "text"):
                    result = block.text.value
            break
    agents.delete_agent(agent.id)
    return result


def exercise_1(client):
    print("\n── Exercise 1: Researcher + Summarizer Handoff ─────────────")
    agents = client.agents

    print("  Step 1: Researcher agent gathering CIP-007 details...")
    research = run_agent(
        agents, DEPLOYMENT, "researcher",
        "You are a regulatory researcher. Provide detailed technical answers about NERC CIP standards.",
        "What are all the key requirements of NERC CIP-007?",
    )
    print(f"  Research output ({len(research)} chars)")

    print("  Step 2: Summarizer agent condensing the research...")
    summary = run_agent(
        agents, DEPLOYMENT, "summarizer",
        "You are a technical writer. Summarize the provided text into 3 bullet points.",
        f"Summarize this:\n\n{research}",
    )
    print(f"\n  Final Summary:\n{summary}")


def exercise_2(client):
    print("\n── Exercise 2: Parallel Agent Evaluation ───────────────────")
    print("  Sending the same question to two agents with different personas...\n")
    agents = client.agents
    import threading

    results = {}

    def run_in_thread(role, instructions, key):
        results[key] = run_agent(
            agents, DEPLOYMENT, f"agent-{key}",
            instructions,
            "How should TVA handle a critical security patch under NERC CIP-007?",
        )

    threads = [
        threading.Thread(target=run_in_thread, args=(
            "Strict", "You are a strict compliance officer. Be prescriptive.", "strict")),
        threading.Thread(target=run_in_thread, args=(
            "Pragmatic", "You are a pragmatic engineer. Balance compliance with operations.", "pragmatic")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print("  Strict compliance officer:")
    print(f"  {results.get('strict', 'N/A')}\n")
    print("  Pragmatic engineer:")
    print(f"  {results.get('pragmatic', 'N/A')}")


def main():
    check_env()
    client = get_client()
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   Lab 04 — Multi-Agent Orchestration (Stretch Goal)     ║")
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
        elif choice == "Q":
            print("👋 Done!")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
