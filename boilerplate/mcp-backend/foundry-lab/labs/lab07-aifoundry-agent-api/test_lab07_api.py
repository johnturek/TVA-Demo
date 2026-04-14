#!/usr/bin/env python3
"""
Test Lab07 AI Foundry Agent API — Container App health & endpoint verification.

Usage:
    python test_lab07_api.py <BASE_URL>
    python test_lab07_api.py https://foundry-lab07-agent-api.livelyhill-390b5f83.eastus2.azurecontainerapps.io

Tests:
    1. GET  /health      — verify the API is running and returns agent config
    2. GET  /docs        — verify OpenAPI docs are served
    3. POST /chat        — send a test message (may fail if agent not deployed)
    4. POST /chat/stream — verify SSE streaming endpoint responds
"""

import sys
import json
import time
import urllib.request
import urllib.error

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

_test_start = 0.0
_overall_start = 0.0
_step_num = 0


def step(label: str):
    """Print a numbered step header and start its timer."""
    global _step_num, _test_start
    _step_num += 1
    _test_start = time.time()
    print(f"\n  {BOLD}[{_step_num}/4]{RESET} {label}")


def _elapsed() -> str:
    return f"{time.time() - _test_start:.1f}s"


def ok(msg):
    print(f"        {GREEN}✓ PASS{RESET}  {msg}  {DIM}({_elapsed()}){RESET}")


def fail(msg, detail=""):
    print(f"        {RED}✗ FAIL{RESET}  {msg}  {DIM}({_elapsed()}){RESET}")
    if detail:
        for line in detail.strip().split("\n"):
            print(f"                {line}")


def warn(msg):
    print(f"        {YELLOW}⚠ WARN{RESET}  {msg}  {DIM}({_elapsed()}){RESET}")


def test_health(base_url: str) -> bool:
    """GET /health — should return 200 with agent config."""
    url = f"{base_url}/health"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
            status = body.get("status")
            agent = body.get("agent_name", "?")
            version = body.get("agent_version", "?")
            obo = body.get("obo_enabled", False)
            if status == "healthy":
                ok(f"/health → healthy  agent={agent} v{version}  obo={obo}")
                return True
            else:
                fail(f"/health → unexpected status: {status}", json.dumps(body, indent=2))
                return False
    except urllib.error.HTTPError as e:
        fail(f"/health → HTTP {e.code}", e.read().decode()[:200])
        return False
    except Exception as e:
        fail(f"/health → {e}")
        return False


def test_docs(base_url: str) -> bool:
    """GET /docs — FastAPI auto-generated OpenAPI docs."""
    url = f"{base_url}/docs"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                ok("/docs → 200 (OpenAPI docs available)")
                return True
            else:
                fail(f"/docs → HTTP {resp.status}")
                return False
    except urllib.error.HTTPError as e:
        fail(f"/docs → HTTP {e.code}")
        return False
    except Exception as e:
        fail(f"/docs → {e}")
        return False


def test_chat(base_url: str) -> bool:
    """POST /chat — send a test message (may 503 if agent not deployed)."""
    url = f"{base_url}/chat"
    payload = json.dumps({
        "message": "Hello, what is your area of expertise? One sentence please.",
        "conversation_history": []
    }).encode()
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
            response_text = body.get("response", "")[:120]
            history_len = len(body.get("conversation_history", []))
            ok(f"/chat → 200  history={history_len} items")
            print(f"                {CYAN}Agent: {response_text}...{RESET}")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 503:
            warn(f"/chat → 503 (agent not found — deploy it via Lab 03 first)")
            return True  # expected if agent isn't deployed
        fail(f"/chat → HTTP {e.code}", e.read().decode()[:300])
        return False
    except Exception as e:
        fail(f"/chat → {e}")
        return False


def test_chat_stream(base_url: str) -> bool:
    """POST /chat/stream — verify SSE endpoint responds."""
    url = f"{base_url}/chat/stream"
    payload = json.dumps({
        "message": "Say hello in one word.",
        "conversation_history": []
    }).encode()
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "")
            # Read first few SSE events
            chunks = []
            for _ in range(20):
                line = resp.readline().decode().strip()
                if line.startswith("data:"):
                    chunks.append(line)
                    data = json.loads(line[5:].strip())
                    if data.get("type") == "done":
                        break

            if chunks:
                ok(f"/chat/stream → SSE  {len(chunks)} events  content-type={content_type}")
                return True
            else:
                warn("/chat/stream → responded but no SSE data events received")
                return True
    except urllib.error.HTTPError as e:
        if e.code == 503:
            warn(f"/chat/stream → 503 (agent not found — deploy it via Lab 03 first)")
            return True
        fail(f"/chat/stream → HTTP {e.code}", e.read().decode()[:300])
        return False
    except Exception as e:
        fail(f"/chat/stream → {e}")
        return False


def main():
    global _overall_start
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <BASE_URL>")
        print(f"  e.g. python {sys.argv[0]} https://foundry-lab07-agent-api.<hash>.eastus2.azurecontainerapps.io")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    _overall_start = time.time()

    print()
    print(f"{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  Lab07 API Test — {base_url}{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}")

    results = []

    step("GET /health")
    results.append(("health", test_health(base_url)))

    step("GET /docs")
    results.append(("docs", test_docs(base_url)))

    step("POST /chat")
    results.append(("chat", test_chat(base_url)))

    step("POST /chat/stream")
    results.append(("chat/stream", test_chat_stream(base_url)))

    passed = sum(1 for _, r in results if r)
    total = len(results)
    elapsed = time.time() - _overall_start

    print()
    print(f"{BOLD}{'═' * 60}{RESET}")
    color = GREEN if passed == total else YELLOW if passed > 0 else RED
    print(f"  {color}{passed}/{total} tests passed{RESET}  {DIM}({elapsed:.1f}s total){RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}")
    print()

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
