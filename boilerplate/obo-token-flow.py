import os
import requests

# --- CONFIG ---
TENANT_ID     = os.getenv("AZURE_TENANT_ID")
CLIENT_ID     = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
BACKEND_URL   = os.getenv("TVA_BACKEND_URL", "https://tva-workshop-apim.azure-api.net/tva/api/query")
SCOPE         = f"api://{CLIENT_ID}/.default"


def exchange_token_obo(user_access_token: str) -> str:
    """
    Exchange a user's access token (from Copilot Studio / Entra ID) for a
    downstream token scoped to the TVA backend API using the OBO flow.

    Call this in your APIM inbound policy or backend middleware — NOT in
    client-side code (client secret must stay server-side).
    """
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

    data = {
        "grant_type":           "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "client_id":            CLIENT_ID,
        "client_secret":        CLIENT_SECRET,
        "assertion":            user_access_token,
        "scope":                SCOPE,
        "requested_token_use":  "on_behalf_of"
    }

    response = requests.post(url, data=data)

    if response.status_code != 200:
        print(f"❌ OBO exchange failed: {response.status_code} {response.text}")
        response.raise_for_status()

    token_data = response.json()
    print("✅ OBO token acquired")
    return token_data["access_token"]


def call_tva_backend(user_token: str, query: str) -> dict:
    """
    Full example: exchange user token via OBO, then call the TVA backend API.
    """
    obo_token = exchange_token_obo(user_token)

    headers = {
        "Authorization": f"Bearer {obo_token}",
        "Content-Type":  "application/json"
    }

    response = requests.post(
        BACKEND_URL,
        headers=headers,
        json={"query": query, "top": 3}
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # For local testing: paste a real user access token here
    # In production this token comes from Copilot Studio's auth flow
    test_token = os.getenv("TEST_USER_TOKEN")

    if not test_token:
        print("Set TEST_USER_TOKEN env var to a valid Entra ID access token to test OBO flow.")
        print("You can get one from: https://jwt.ms after signing in via your app registration.")
        exit(0)

    result = call_tva_backend(test_token, "NERC CIP-007 patch management requirements")
    print("Backend response:", result)
