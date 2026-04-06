import os
import glob
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchFieldDataType
)

# --- CONFIG ---
# Set these as environment variables or replace directly for workshop use
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")  # e.g. https://xxx.search.windows.net
SEARCH_KEY      = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME      = "tva-knowledge-base"
DOCS_FOLDER     = "./docs"  # Folder containing .txt or .md files to upload


def create_index(index_client):
    """Create the search index if it doesn't already exist."""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="filename", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="category", type=SearchFieldDataType.String, filterable=True),
    ]
    index = SearchIndex(name=INDEX_NAME, fields=fields)
    index_client.create_or_update_index(index)
    print(f"✅ Index '{INDEX_NAME}' ready")


def upload_documents():
    credential = AzureKeyCredential(SEARCH_KEY)
    index_client = SearchIndexClient(SEARCH_ENDPOINT, credential)
    create_index(index_client)

    search_client = SearchClient(SEARCH_ENDPOINT, INDEX_NAME, credential)

    docs = []
    files = glob.glob(f"{DOCS_FOLDER}/*.txt") + glob.glob(f"{DOCS_FOLDER}/*.md")

    if not files:
        print(f"⚠️  No .txt or .md files found in {DOCS_FOLDER}")
        return

    for i, filepath in enumerate(files):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        filename = os.path.basename(filepath)
        docs.append({
            "id": str(i),
            "content": content,
            "filename": filename,
            "category": "tva-regulatory"
        })
        print(f"  📄 Queued: {filename}")

    result = search_client.upload_documents(docs)
    print(f"✅ Uploaded {len(docs)} documents to '{INDEX_NAME}'")


if __name__ == "__main__":
    if not SEARCH_ENDPOINT or not SEARCH_KEY:
        print("❌ Missing environment variables: AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_KEY")
        exit(1)
    upload_documents()
