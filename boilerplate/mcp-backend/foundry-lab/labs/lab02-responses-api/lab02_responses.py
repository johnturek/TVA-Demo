"""
Lab 02 — Responses API
=======================
Explore the Azure OpenAI Responses API for stateful, multi-turn conversations.

Prerequisites:
  - .env populated with AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY
  - Deployment named gpt-4o (or set AZURE_OPENAI_DEPLOYMENT_NAME)

Run:
  FOUNDRY_LAB=02 npx just foundry:lab
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../../.env'))

from openai import AzureOpenAI

ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT", "")
API_KEY    = os.getenv("AZURE_OPENAI_KEY", "")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

EXERCISES = {
    "1": "Multi-turn conversation — compliance Q&A",
    "2": "Streaming responses",
    "3": "Function calling (tool use)",
    "Q": "Quit",
}


def check_env():
    if not ENDPOINT or not API_KEY:
        print("\n❌  Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_KEY in .env\n")
        sys.exit(1)


def get_client():
    return AzureOpenAI(
        azure_endpoint=ENDPOINT,
        api_key=API_KEY,
        api_version="2024-02-01",
    )


def exercise_1(client):
    print("\n── Exercise 1: Multi-turn Conversation ─────────────────────")
    print("Type 'done' to end the conversation.\n")
    history = [
        {
            "role": "system",
            "content": "You are a helpful TVA compliance advisor. Keep answers brief.",
        }
    ]
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("done", "exit", "quit"):
            break
        history.append({"role": "user", "content": user_input})
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=history,
            max_tokens=200,
        )
        reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": reply})
        print(f"Assistant: {reply}\n")


def exercise_2(client):
    print("\n── Exercise 2: Streaming Response ──────────────────────────")
    print("Streaming: ", end="", flush=True)
    stream = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": "List 3 key NERC CIP standards TVA must comply with."}],
        max_tokens=150,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()


def exercise_3(client):
    print("\n── Exercise 3: Function Calling (Tool Use) ─────────────────")
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_compliance_deadline",
                "description": "Returns the next compliance deadline for a NERC CIP standard",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "standard": {"type": "string", "description": "NERC CIP standard (e.g. CIP-007)"},
                    },
                    "required": ["standard"],
                },
            },
        }
    ]
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": "When is TVA's next CIP-007 compliance deadline?"}],
        tools=tools,
        tool_choice="auto",
        max_tokens=100,
    )
    msg = response.choices[0].message
    if msg.tool_calls:
        call = msg.tool_calls[0]
        print(f"  Tool called: {call.function.name}")
        print(f"  Arguments:   {call.function.arguments}")
        print("  (In production, you'd execute this function and return the result.)")
    else:
        print(f"  Direct response: {msg.content}")


def main():
    check_env()
    client = get_client()
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   Lab 02 — Responses API                                ║")
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
