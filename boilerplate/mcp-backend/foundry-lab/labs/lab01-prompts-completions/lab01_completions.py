"""
Lab 01 — Prompts & Completions
================================
Learn the basics of the Azure OpenAI completions API using Azure AI Foundry.

Prerequisites:
  - .env populated with AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY
  - Deployment named gpt-4o (or set AZURE_OPENAI_DEPLOYMENT_NAME)

Run:
  FOUNDRY_LAB=01 npx just foundry:lab
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
    "1": "Basic completion — TVA system status",
    "2": "System prompt — compliance analyst persona",
    "3": "Temperature & top_p exploration",
    "4": "Token counting with tiktoken",
    "Q": "Quit",
}


def check_env():
    if not ENDPOINT or not API_KEY:
        print("\n❌  Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_KEY in .env")
        print("   Open .env and add the values from your Foundry portal.\n")
        sys.exit(1)


def get_client():
    return AzureOpenAI(
        azure_endpoint=ENDPOINT,
        api_key=API_KEY,
        api_version="2024-02-01",
    )


def exercise_1(client):
    print("\n── Exercise 1: Basic Completion ────────────────────────────")
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": "Summarize TVA's mission in one sentence."}],
        max_tokens=100,
    )
    print("Response:", response.choices[0].message.content)
    print(f"Tokens used: {response.usage.total_tokens}")


def exercise_2(client):
    print("\n── Exercise 2: System Prompt (Compliance Analyst Persona) ──")
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a TVA compliance analyst specializing in NERC CIP standards. "
                    "Answer concisely and cite specific CIP requirements when relevant."
                ),
            },
            {"role": "user", "content": "What is the patch management window under NERC CIP-007?"},
        ],
        max_tokens=200,
    )
    print("Response:", response.choices[0].message.content)


def exercise_3(client):
    print("\n── Exercise 3: Temperature & top_p Exploration ─────────────")
    for temp in [0.0, 0.7, 1.2]:
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[{"role": "user", "content": "Describe TVA's grid reliability in one sentence."}],
            max_tokens=60,
            temperature=temp,
        )
        print(f"  temperature={temp}: {response.choices[0].message.content.strip()}")


def exercise_4(client):
    print("\n── Exercise 4: Token Counting ───────────────────────────────")
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4o")
        text = "What NERC CIP standards apply to TVA's bulk electric system?"
        tokens = enc.encode(text)
        print(f"  Prompt: \"{text}\"")
        print(f"  Token count: {len(tokens)}")
    except ImportError:
        print("  ⚠️  tiktoken not installed. Run: pip install tiktoken")


def main():
    check_env()
    client = get_client()
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   Lab 01 — Prompts & Completions                        ║")
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
        elif choice == "4":
            exercise_4(client)
        elif choice == "Q":
            print("👋 Done!")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
