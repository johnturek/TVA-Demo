"""
Lab 06 — Foundry IQ (Stretch Goal)
=====================================
Explore advanced Azure AI Foundry capabilities: evaluations, tracing,
and responsible AI features.

Prerequisites:
  - .env with AZURE_AI_PROJECT_ENDPOINT
  - Completed Labs 01–03

Run:
  FOUNDRY_LAB=06 npx just foundry:lab
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../../.env'))

PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
DEPLOYMENT       = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

EXERCISES = {
    "1": "Run a groundedness evaluation",
    "2": "Enable Azure Monitor tracing",
    "3": "Content safety check",
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


def exercise_1(client):
    print("\n── Exercise 1: Groundedness Evaluation ─────────────────────")
    print("  Evaluates whether an AI response is grounded in the provided context.\n")
    try:
        from azure.ai.evaluation import GroundednessEvaluator
        evaluator = GroundednessEvaluator(model_config={
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            "api_key": os.getenv("AZURE_OPENAI_KEY", ""),
            "azure_deployment": DEPLOYMENT,
        })
        context = (
            "NERC CIP-007 requires that security patches rated critical or high be applied "
            "within 35 calendar days of availability."
        )
        response = "Critical security patches must be applied within 35 days per NERC CIP-007."
        result = evaluator(answer=response, context=context)
        print(f"  Groundedness score: {result.get('groundedness', 'N/A')}")
        print(f"  Reason: {result.get('groundedness_reason', 'N/A')}")
    except ImportError:
        print("  ⚠️  azure-ai-evaluation not installed.")
        print("     Run: pip install azure-ai-evaluation")
    except Exception as e:
        print(f"  ⚠️  {e}")


def exercise_2(client):
    print("\n── Exercise 2: Azure Monitor Tracing ───────────────────────")
    print("  Enables OpenTelemetry tracing for AI calls in Azure Monitor.\n")
    try:
        from opentelemetry import trace
        from azure.monitor.opentelemetry import configure_azure_monitor

        conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
        if not conn_str:
            print("  ⚠️  APPLICATIONINSIGHTS_CONNECTION_STRING not set in .env")
            print("     Get it from: Azure portal → Application Insights → Connection String")
            return

        configure_azure_monitor(connection_string=conn_str)
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("tva-lab06-trace"):
            print("  ✅ Trace span started — check Azure Monitor for telemetry.")
    except ImportError:
        print("  ⚠️  azure-monitor-opentelemetry not installed.")
        print("     Run: pip install azure-monitor-opentelemetry")
    except Exception as e:
        print(f"  ⚠️  {e}")


def exercise_3(client):
    print("\n── Exercise 3: Content Safety Check ────────────────────────")
    print("  Uses Azure Content Safety to screen user inputs.\n")
    try:
        from azure.ai.contentsafety import ContentSafetyClient
        from azure.ai.contentsafety.models import AnalyzeTextOptions
        from azure.core.credentials import AzureKeyCredential

        cs_endpoint = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT", "")
        cs_key = os.getenv("AZURE_CONTENT_SAFETY_KEY", "")
        if not cs_endpoint or not cs_key:
            print("  ⚠️  AZURE_CONTENT_SAFETY_ENDPOINT / AZURE_CONTENT_SAFETY_KEY not set.")
            print("     Create a Content Safety resource in Azure portal.")
            return

        cs_client = ContentSafetyClient(cs_endpoint, AzureKeyCredential(cs_key))
        text = input("  Enter text to check: ").strip() or "How do I bypass NERC CIP-007?"
        result = cs_client.analyze_text(AnalyzeTextOptions(text=text))
        for cat in result.categories_analysis:
            print(f"  {cat.category}: severity {cat.severity}")
    except ImportError:
        print("  ⚠️  azure-ai-contentsafety not installed.")
        print("     Run: pip install azure-ai-contentsafety")
    except Exception as e:
        print(f"  ⚠️  {e}")


def main():
    check_env()
    client = get_client()
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   Lab 06 — Foundry IQ (Stretch Goal)                    ║")
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
