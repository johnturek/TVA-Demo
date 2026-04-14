"""
Shared configuration for all Foundry labs.
Loads environment variables and provides a configured AIProjectClient.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


def get_project_endpoint() -> str:
    """Return the Foundry project endpoint or exit with guidance."""
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        print(
            "ERROR: AZURE_AI_PROJECT_ENDPOINT is not set.\n"
            "Run the infrastructure deployment first, then copy the endpoint to .env.\n"
            "  Format: https://<account>.services.ai.azure.com/api/projects/<project>"
        )
        sys.exit(1)
    return endpoint


def get_project_client():
    """Return an authenticated AIProjectClient using DefaultAzureCredential."""
    from azure.identity import DefaultAzureCredential
    from azure.ai.projects import AIProjectClient

    return AIProjectClient(
        endpoint=get_project_endpoint(),
        credential=DefaultAzureCredential(),
    )


def get_agents_client():
    """Return an authenticated AgentsClient (azure-ai-agents v2) using DefaultAzureCredential."""
    from azure.identity import DefaultAzureCredential
    from azure.ai.agents import AgentsClient

    return AgentsClient(
        endpoint=get_project_endpoint(),
        credential=DefaultAzureCredential(),
    )


def get_search_config() -> dict:
    """Return Azure AI Search configuration from environment."""
    return {
        "endpoint": os.environ.get("AZURE_SEARCH_ENDPOINT", ""),
        "admin_key": os.environ.get("AZURE_SEARCH_ADMIN_KEY", ""),
        "index_name": os.environ.get("AZURE_SEARCH_INDEX_NAME", "foundry-lab-index"),
    }


def get_model_name() -> str:
    """Return the default model deployment name."""
    return os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")


def get_embedding_model() -> str:
    """Return the embedding model deployment name."""
    return os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")


def get_openai_embedding_client():
    """Return an AzureOpenAI client routed to the account-level endpoint.

    The project-level endpoint returned by AIProjectClient.get_openai_client()
    does not support the /embeddings route.  This helper extracts the account
    base URL from the project endpoint and returns a properly configured client.
    """
    from azure.identity import DefaultAzureCredential
    import openai as _openai

    project_endpoint = get_project_endpoint()
    # e.g. https://<account>.services.ai.azure.com/api/projects/<project>
    account_endpoint = project_endpoint.split("/api/projects")[0]

    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")

    return _openai.AzureOpenAI(
        azure_endpoint=account_endpoint,
        api_key=token.token,
        api_version="2024-10-21",
    )
