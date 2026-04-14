# mcp_server.py
"""Minimal MCP server: PRM authentication + OBO token exchange + external API tools.

Goals:
- PRM-protected MCP server with Streamable HTTP transport.
- OBO flow to call Microsoft Graph on behalf of the authenticated user.
- External API integration (Federal Policy Analyst).
- Read config from environment variables (optionally loaded from .env).

Tools exposed:
- help
- get_my_profile (OBO → Graph /me)
- analyze_policy (Federal Policy Analyst)
"""

from __future__ import annotations

import json
import os
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional, cast

import requests
import uvicorn
from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None  # type: ignore[assignment]

import msal


_DOTENV_PATH = Path(__file__).resolve().parent / ".env"
if _DOTENV_PATH.exists():
    load_dotenv(dotenv_path=_DOTENV_PATH, override=True)


def _require_env_value(name: str) -> str:
    """Return a required setting from environment variables.

    Local development may provide these via application/external_apps/mcp/.env.
    Azure deployments should provide these as App Settings / env vars.
    """
    value = os.getenv(name, "").strip()
    if not value:
        source_hint = f" (loadable from {_DOTENV_PATH} when present)" if _DOTENV_PATH.exists() else ""
        raise ValueError(f"Missing required environment variable {name}{source_hint}")
    return value


def _require_env_int(name: str) -> int:
    raw = _require_env_value(name)
    try:
        return int(raw)
    except Exception as exc:
        raise ValueError(f"Invalid integer for {name}: {raw!r} ({exc})")


def _require_env_bool(name: str) -> bool:
    raw = _require_env_value(name).strip().lower()
    if raw in ["1", "true", "yes", "y", "on"]:
        return True
    if raw in ["0", "false", "no", "n", "off"]:
        return False
    raise ValueError(f"Invalid boolean for {name}: {raw!r} (use true/false)")


DEFAULT_REQUIRE_MCP_AUTH = _require_env_bool("MCP_REQUIRE_AUTH")
DEFAULT_PRM_METADATA_PATH = _require_env_value("MCP_PRM_METADATA_PATH").strip()

MCP_BIND_HOST = _require_env_value("FASTMCP_HOST")
MCP_BIND_PORT = _require_env_int("FASTMCP_PORT")

# ── OBO (On-Behalf-Of) configuration ────────────────────────────────────────
# Optional: set OBO_CLIENT_ID + OBO_CLIENT_SECRET + OBO_TENANT_ID + OBO_SCOPE
# to enable the get_my_profile tool that exchanges the PRM bearer token for a
# downstream token (e.g. Microsoft Graph).
_OBO_CLIENT_ID = os.getenv("OBO_CLIENT_ID", "").strip()
_OBO_CLIENT_SECRET = os.getenv("OBO_CLIENT_SECRET", "").strip()
_OBO_TENANT_ID = os.getenv("OBO_TENANT_ID", "").strip()
_OBO_SCOPE = os.getenv("OBO_SCOPE", "https://graph.microsoft.com/.default").strip()
_OBO_ENABLED = bool(_OBO_CLIENT_ID and _OBO_CLIENT_SECRET and _OBO_TENANT_ID)

_OBO_APP: Optional[msal.ConfidentialClientApplication] = None
if _OBO_ENABLED:
    _OBO_APP = msal.ConfidentialClientApplication(
        client_id=_OBO_CLIENT_ID,
        client_credential=_OBO_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{_OBO_TENANT_ID}",
    )
    print(f"[MCP] OBO enabled: client_id={_OBO_CLIENT_ID} scope={_OBO_SCOPE}")
else:
    print("[MCP] OBO not configured (set OBO_CLIENT_ID, OBO_CLIENT_SECRET, OBO_TENANT_ID to enable)")


# Pass host=MCP_BIND_HOST so FastMCP does not auto-enable DNS rebinding
# protection with localhost-only allowed_hosts.  When host is "0.0.0.0"
# (local and Azure), FastMCP skips the restriction — otherwise the Azure
# Container Apps FQDN in the Host header triggers a 421 Misdirected Request.
_mcp = FastMCP("mcp-server", host=MCP_BIND_HOST, port=MCP_BIND_PORT)

# Session cache: bearer_token -> requests.Session
_SESSION_CACHE: Dict[str, requests.Session] = {}
_SESSION_LOCK = threading.Lock()

# Cache the /external/login payload (contains user + claims) per bearer token.
_LOGIN_PAYLOAD_CACHE: Dict[str, Dict[str, Any]] = {}

# Cache bearer token per MCP streamable-http session id. This lets the server reuse
# the PRM-provided bearer token across tool calls even if the client doesn't resend it.
_MCP_SESSION_TOKEN_CACHE: Dict[str, Dict[str, Any]] = {}
_MCP_SESSION_TOKEN_TTL_SECONDS = _require_env_int("MCP_SESSION_TOKEN_TTL_SECONDS")

_STATE_LOCK = threading.Lock()
_STATE: Dict[str, Any] = {
    "event": None,
    "pending": False,
    "error": None,
    "auth_flow": None,
    "user_code": None,
    "verification_uri": None,
    "verification_uri_complete": None,
    "expires_in": None,
    "interval": None,
    "access_token": None,
    "backend_session": None,
    "user_profile": None,
    "token_claims": None,
}


def _env(name: str) -> str:
    """Back-compat helper: required value from environment variables (no defaults)."""
    return _require_env_value(name)


def _extract_bearer_token(auth_header: str) -> Optional[str]:
    """Extract bearer token from Authorization header."""
    if not auth_header:
        return None
    token = auth_header.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token or None


def _get_bearer_token_from_context(ctx: Optional[Context[Any, Any, Any]]) -> Optional[str]:
    """Extract bearer token from the current request Context.

    This is the canonical way tools should access PRM-provided auth.
    """
    if ctx is None:
        return None

    request_context = getattr(ctx, "request_context", None)
    request = getattr(request_context, "request", None) if request_context else None
    headers = getattr(request, "headers", None) if request else None
    if not headers:
        return None

    auth_header = headers.get("authorization")
    return _extract_bearer_token(auth_header or "")


def _get_or_create_backend_session(bearer_token: str) -> requests.Session:
    """Get cached session or create new one via backend /external/login."""
    with _SESSION_LOCK:
        if bearer_token in _SESSION_CACHE:
            print("[MCP] Using cached backend session for token")
            return _SESSION_CACHE[bearer_token]
    
    BACKEND_BASE_URL = _env("BACKEND_BASE_URL")
    BACKEND_VERIFY_SSL = _require_env_bool("BACKEND_VERIFY_SSL")
    
    print("[MCP] Creating new backend session via /external/login")
    
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {bearer_token}"})
    
    # Call backend /external/login to establish session
    login_url = f"{BACKEND_BASE_URL}/external/login"
    try:
        response = session.post(login_url, json={}, verify=BACKEND_VERIFY_SSL, timeout=30)
        
        if response.status_code != 200:
            try:
                error_details = response.json()
            except Exception:
                error_details = {"raw": response.text}
            raise RuntimeError(f"Backend login failed ({response.status_code}): {error_details}")
        
        print("[MCP] backend session created successfully")

        try:
            login_payload: Dict[str, Any] = response.json()
        except Exception:
            login_payload = {}
        
        # Cache the session
        with _SESSION_LOCK:
            _SESSION_CACHE[bearer_token] = session
            if login_payload:
                _LOGIN_PAYLOAD_CACHE[bearer_token] = login_payload
        
        return session
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to connect to Backend: {e}")


def _get_cached_login_payload(bearer_token: str) -> Optional[Dict[str, Any]]:
    with _SESSION_LOCK:
        payload = _LOGIN_PAYLOAD_CACHE.get(bearer_token)
    return payload if isinstance(payload, dict) else None


def _request_device_code(device_code_url: str, client_id: str, scope: str) -> Dict[str, Any]:
    print(f"[MCP] Requesting device code from {device_code_url}")
    response = requests.post(
        device_code_url,
        data={"client_id": client_id, "scope": scope},
        timeout=30,
    )
    if response.status_code != 200:
        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text}
        raise RuntimeError(f"Device code request failed ({response.status_code}): {payload}")
    return response.json()


def _infer_device_code_url(token_url: str) -> str:
    token_url = (token_url or "").strip()
    if token_url.endswith("/oauth2/v2.0/token"):
        return token_url.replace("/oauth2/v2.0/token", "/oauth2/v2.0/devicecode")
    if token_url.endswith("/oauth2/token"):
        return token_url.replace("/oauth2/token", "/oauth2/devicecode")
    raise ValueError(
        "Cannot infer device-code URL from OAUTH_TOKEN_URL; set OAUTH_DEVICE_CODE_URL."
    )


def _poll_device_code_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    device_code: str,
    timeout_seconds: int,
    poll_interval: int,
) -> Dict[str, Any]:
    start = time.time()
    interval = max(1, poll_interval)

    secret_present = bool(client_secret)
    print(
        "[MCP] Starting token polling (PUBLIC CLIENT mode - no secret sent). "
        f"token_url={token_url} client_secret_in_env={secret_present} (not used for device code flow)"
    )

    attempt = 0
    while time.time() - start < timeout_seconds:
        attempt += 1
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": client_id,
            "device_code": device_code,
        }
        # NOTE: Device code flow for PUBLIC CLIENTS (like this app) does NOT include client_secret.
        # Only confidential clients use client_secret with device code flow.
        # The AADSTS7000218 error means the app registration is NOT configured as confidential,
        # so we must omit client_secret entirely.

        # Debug: show what we're sending
        has_secret_key = "client_secret" in data
        print(f"[MCP] Token poll attempt #{attempt}: POST data keys={list(data.keys())} has_client_secret_key={has_secret_key} (public client mode)")

        response = requests.post(token_url, data=data, timeout=30)
        print(f"[MCP] Token poll attempt #{attempt}: response status={response.status_code}")

        if response.status_code == 200:
            try:
                return response.json()
            except Exception as exc:
                raise RuntimeError(f"Token response was not JSON: {exc}")

        payload: Dict[str, Any]
        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text}

        error = str(payload.get("error", "")).lower()
        if error == "authorization_pending":
            time.sleep(interval)
            continue
        if error == "slow_down":
            interval += 5
            time.sleep(interval)
            continue
        if error == "expired_token":
            raise TimeoutError("Device code expired before login completed.")

        raise RuntimeError(f"Device-code token exchange failed ({response.status_code}): {payload}")

    raise TimeoutError("Device code login did not complete within timeout.")


def _start_background_poll() -> None:
    token_url = _env("OAUTH_TOKEN_URL")
    client_id = _env("OAUTH_CLIENT_ID")
    client_secret = _env("OAUTH_CLIENT_SECRET")
    timeout_seconds = _require_env_int("OAUTH_TIMEOUT_SECONDS")

    with _STATE_LOCK:
        device_code = _STATE.get("device_code")
        interval = int(_STATE.get("interval") or 5)
        event = _STATE.get("event")

    if not device_code or not isinstance(event, threading.Event):
        return

    def _worker() -> None:
        try:
            token_payload = _poll_device_code_token(
                token_url=token_url,
                client_id=client_id,
                client_secret=client_secret,
                device_code=device_code,
                timeout_seconds=timeout_seconds,
                poll_interval=interval,
            )
            access_token = token_payload.get("access_token")
            if not access_token:
                raise RuntimeError(f"Token payload missing access_token: {token_payload}")

            BACKEND_BASE_URL = _env("BACKEND_BASE_URL")
            BACKEND_VERIFY_SSL = _require_env_bool("BACKEND_VERIFY_SSL")
            
            session = requests.Session()
            session.headers.update({"Authorization": f"Bearer {access_token}"})
            
            print(f"[MCP] Creating backend session at {BACKEND_BASE_URL}/external/login")
            print(f"[MCP] Token length: {len(access_token)} chars")
            external_login_response = session.post(
                f"{BACKEND_BASE_URL}/external/login",
                verify=BACKEND_VERIFY_SSL,
                timeout=30
            )
            
            if external_login_response.status_code != 200:
                print(f"[MCP] backend /external/login failed: {external_login_response.status_code}")
                print(f"[MCP] Response body: {external_login_response.text}")
                external_login_response.raise_for_status()
            
            external_login_payload = external_login_response.json()
            print(f"[MCP] backend session created: {external_login_payload.get('session_created')}")

            user_info = external_login_payload.get("user", {})
            all_claims = external_login_payload.get("claims", {})

            with _STATE_LOCK:
                _STATE["access_token"] = access_token
                _STATE["backend_session"] = session
                _STATE["user_profile"] = user_info
                _STATE["token_claims"] = all_claims
                _STATE["pending"] = False
                _STATE["error"] = None
            print("[MCP] Device-code token exchange succeeded.")
        except Exception as exc:
            error_msg = str(exc)
            with _STATE_LOCK:
                _STATE["pending"] = False
                _STATE["error"] = error_msg
                # Clear stale auth fields so status returns "none" instead of leaving device_code around
                _STATE["auth_flow"] = None
                _STATE["user_code"] = None
                _STATE["verification_uri"] = None
                _STATE["device_code"] = None
            print(f"[MCP] Device-code login failed: {error_msg}")
        finally:
            event.set()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


# ── OBO (On-Behalf-Of) token exchange + Graph tool ──────────────────────────

def _acquire_obo_token(bearer_token: str) -> str:
    """Exchange a PRM bearer token for a downstream token via OBO flow.

    Uses MSAL ConfidentialClientApplication.acquire_token_on_behalf_of().
    Raises RuntimeError on failure.
    """
    if not _OBO_ENABLED or _OBO_APP is None:
        raise RuntimeError("OBO is not configured. Set OBO_CLIENT_ID, OBO_CLIENT_SECRET, and OBO_TENANT_ID.")

    result = _OBO_APP.acquire_token_on_behalf_of(
        user_assertion=bearer_token,
        scopes=[_OBO_SCOPE],
    )

    if "access_token" in result:
        print(f"[MCP] OBO token acquired (scope={_OBO_SCOPE})")
        return result["access_token"]

    error = result.get("error", "unknown_error")
    error_desc = result.get("error_description", "No description")
    raise RuntimeError(f"OBO token exchange failed: {error} — {error_desc}")


@_mcp.tool(name="get_my_profile")
def get_my_profile(ctx: Context[Any, Any, Any]) -> Dict[str, Any]:
    """Call Microsoft Graph /me using OBO to return the authenticated user's profile.

    Demonstrates the On-Behalf-Of flow:
    1. PRM bearer token arrives from the MCP client (validated by APIM).
    2. The MCP server exchanges it for a Graph token via OBO.
    3. The server calls GET https://graph.microsoft.com/v1.0/me.

    Requires OBO_CLIENT_ID, OBO_CLIENT_SECRET, and OBO_TENANT_ID env vars.
    """
    if not _OBO_ENABLED:
        return {
            "success": False,
            "error": "obo_not_configured",
            "message": "OBO is not configured. Set OBO_CLIENT_ID, OBO_CLIENT_SECRET, and OBO_TENANT_ID.",
        }

    bearer_token = _get_bearer_token_from_context(ctx)
    if not bearer_token:
        with _STATE_LOCK:
            access_token = _STATE.get("access_token")
        if isinstance(access_token, str) and access_token.strip():
            bearer_token = access_token.strip()
        else:
            return {
                "success": False,
                "error": "not_authenticated",
                "message": "Not authenticated. Provide a PRM bearer token or complete device-code login.",
            }

    try:
        downstream_token = _acquire_obo_token(bearer_token)
    except RuntimeError as e:
        return {
            "success": False,
            "error": "obo_failed",
            "message": str(e),
        }

    # Call Microsoft Graph /me
    graph_url = "https://graph.microsoft.com/v1.0/me"
    print(f"[MCP] Calling Graph GET {graph_url}")
    try:
        response = requests.get(
            graph_url,
            headers={"Authorization": f"Bearer {downstream_token}"},
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": "graph_request_failed",
            "message": f"Failed to call Microsoft Graph: {e}",
        }

    if response.status_code != 200:
        try:
            details = response.json()
        except Exception:
            details = {"raw": response.text}
        return {
            "success": False,
            "error": "graph_error",
            "status_code": response.status_code,
            "details": details,
        }

    profile = response.json()
    return {
        "success": True,
        "auth_flow": "obo",
        "displayName": profile.get("displayName"),
        "mail": profile.get("mail"),
        "userPrincipalName": profile.get("userPrincipalName"),
        "jobTitle": profile.get("jobTitle"),
        "officeLocation": profile.get("officeLocation"),
        "id": profile.get("id"),
    }


# ── Federal Policy Analyst tool ─────────────────────────────────────────────

_POLICY_ANALYST_URL = "https://analyst.turek.in/api/v1/analyze/sync"


@_mcp.tool(name="analyze_policy")
def analyze_policy(query: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Analyze a federal policy question using the Federal Policy Analyst service.

    Submit a question about federal regulations, compliance, cybersecurity,
    privacy, or procurement for expert analysis.

    Args:
        query: The policy question to analyze (required).
        context: Additional context about the situation (optional).
    """
    if not query or not query.strip():
        return {
            "success": False,
            "error": "missing_parameter",
            "message": "query is required.",
        }

    payload: Dict[str, Any] = {"query": query.strip()}
    if context and context.strip():
        payload["context"] = context.strip()

    print(f"[MCP] Calling Federal Policy Analyst: POST {_POLICY_ANALYST_URL}")
    try:
        response = requests.post(
            _POLICY_ANALYST_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": "request_failed",
            "message": f"Failed to reach Federal Policy Analyst: {e}",
        }

    if response.status_code != 200:
        try:
            details = response.json()
        except Exception:
            details = {"raw": response.text}
        return {
            "success": False,
            "error": "analyst_error",
            "status_code": response.status_code,
            "details": details,
        }

    result = response.json()
    return {
        "success": True,
        "requestId": result.get("requestId"),
        "status": result.get("status"),
        "result": result.get("result"),
    }


# ── Help tool ──────────────────────────────────────────────────────────────────

_TOOL_HELP: Dict[str, Dict[str, Any]] = {
    "help": {
        "category": "Help",
        "description": "Show help for all available tools or get detailed usage for a specific tool.",
        "auth_required": True,
        "backend_api": None,
        "parameters": {
            "tool_name": "(optional) Name of a specific tool to get detailed help for. Omit to list all tools.",
        },
        "examples": [
            'help',
            'help tool_name="get_my_profile"',
        ],
    },
    "get_my_profile": {
        "category": "OBO (On-Behalf-Of)",
        "description": (
            "Call Microsoft Graph /me using the OBO flow. Exchanges the PRM bearer token "
            "for a downstream Graph token and returns the user's profile."
        ),
        "auth_required": True,
        "backend_api": "GET https://graph.microsoft.com/v1.0/me (via OBO)",
        "parameters": {},
        "examples": ["get_my_profile"],
        "notes": "Requires OBO_CLIENT_ID, OBO_CLIENT_SECRET, and OBO_TENANT_ID env vars.",
    },
    "analyze_policy": {
        "category": "Federal Policy",
        "description": (
            "Analyze a federal policy question using the Federal Policy Analyst service. "
            "Covers regulations, compliance, cybersecurity, privacy, and procurement."
        ),
        "auth_required": True,
        "backend_api": "POST https://analyst.turek.in/api/v1/analyze/sync",
        "parameters": {
            "query": "(required) The policy question to analyze.",
            "context": "(optional) Additional context about the situation.",
        },
        "examples": [
            'analyze_policy query="What are FedRAMP requirements for cloud services?"',
            'analyze_policy query="CMMC Level 2 controls" context="DoD contractor handling CUI"',
        ],
    },
}


def _get_registered_tool_names() -> list[str]:
    """Return the names of tools currently registered with FastMCP."""
    try:
        # FastMCP stores tools in _tool_manager.tools (dict of name -> Tool)
        tool_manager = getattr(_mcp, "_tool_manager", None)
        if tool_manager is not None:
            tools_dict = getattr(tool_manager, "tools", None)
            if isinstance(tools_dict, dict):
                return list(tools_dict.keys())
        return list(_TOOL_HELP.keys())
    except Exception:
        return list(_TOOL_HELP.keys())


@_mcp.tool(name="help")
def help_tool(tool_name: Optional[str] = None) -> Dict[str, Any]:
    """Show help for all available MCP tools or get detailed usage for a specific tool.

    Args:
        tool_name: Name of a specific tool to get help for. Omit to list all available tools.

    Returns a help summary or detailed usage information.
    """
    registered_names = _get_registered_tool_names()

    if tool_name and tool_name.strip():
        name = tool_name.strip()
        info = _TOOL_HELP.get(name)
        if not info:
            return {
                "error": "unknown_tool",
                "message": f"No tool named '{name}'. Use help (with no arguments) to list all available tools.",
                "available_tools": sorted(_TOOL_HELP.keys()),
            }
        result: Dict[str, Any] = {
            "tool_name": name,
            "category": info.get("category", ""),
            "description": info.get("description", ""),
            "auth_required": info.get("auth_required", True),
            "backend_api": info.get("backend_api"),
            "parameters": info.get("parameters", {}),
            "examples": info.get("examples", []),
            "available": name in registered_names,
        }
        if info.get("notes"):
            result["notes"] = info["notes"]
        return result

    # No tool_name provided — list all tools grouped by category.
    categories: Dict[str, list[Dict[str, Any]]] = {}
    for name, info in _TOOL_HELP.items():
        cat = info.get("category", "Other")
        categories.setdefault(cat, [])
        categories[cat].append({
            "tool_name": name,
            "description": info.get("description", ""),
            "auth_required": info.get("auth_required", True),
        })

    return {
        "total_tools": sum(len(tools) for tools in categories.values()),
        "categories": categories,
        "hint": 'Call help with tool_name="<name>" for detailed usage, parameters, and examples.',
    }


class _PrmAndAuthShim:
    """ASGI middleware that serves PRM metadata and enforces authentication."""
    
    def __init__(self, app: Any, streamable_path: str, require_auth: bool, prm_metadata_path: str) -> None:
        self._app = app
        self._streamable_path = streamable_path
        self._require_auth = require_auth
        self._prm_metadata_path = prm_metadata_path

        # Validate PRM metadata at startup (no fallbacks/defaults).
        _ = self._load_prm_metadata()
    
    def _load_prm_metadata(self) -> Dict[str, Any]:
        candidate_path = Path(self._prm_metadata_path)
        if not candidate_path.is_absolute():
            candidate_path = Path(__file__).resolve().parent / candidate_path
        
        if not candidate_path.exists():
            raise ValueError(f"PRM metadata file not found at {candidate_path}")
        
        with candidate_path.open("r", encoding="utf-8") as handle:
            data: Any = json.load(handle)

        if not isinstance(data, dict):
            raise ValueError(f"PRM metadata at {candidate_path} must be a JSON object")

        # Dynamically set authorization_servers and scopes_supported from
        # environment variables (.env locally, Azure App Settings in the cloud).
        # These are required — missing values cause an immediate startup error.
        token_url = _require_env_value("OAUTH_TOKEN_URL")
        client_id = _require_env_value("OAUTH_CLIENT_ID")

        # Extract tenant-specific authority from token URL
        # e.g. https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
        #   -> https://login.microsoftonline.com/{tenant}/v2.0
        authority = token_url.replace("/oauth2/v2.0/token", "/v2.0").replace("/oauth2/token", "/v2.0")
        data["authorization_servers"] = [authority]
        data["scopes_supported"] = [f"api://{client_id}/mcp.invoke"]

        # resource is set dynamically at serve time from the request origin
        # (see __call__ method), so we don't set it here.

        return cast(Dict[str, Any], data)
    
    @staticmethod
    def _get_request_origin(scope: Dict[str, Any]) -> str:
        headers_list = list(scope.get("headers", []))

        # Behind a reverse proxy (e.g. Azure Container Apps), TLS is terminated
        # at the ingress and the ASGI scope["scheme"] is always "http".
        # Check X-Forwarded-Proto first, then FASTMCP_SCHEME, then scope.
        forwarded_proto_values = [
            value for (key, value) in headers_list
            if (key or b"").lower() == b"x-forwarded-proto"
        ]
        forwarded_proto = (
            b"".join(forwarded_proto_values).decode("utf-8", errors="ignore").strip()
            if forwarded_proto_values else ""
        )

        if forwarded_proto:
            scheme = forwarded_proto
        else:
            scheme = str(scope.get("scheme") or "").strip()
            if not scheme:
                scheme = _require_env_value("FASTMCP_SCHEME")

        host_values = [value for (key, value) in headers_list if (key or b"").lower() == b"host"]
        host = b"".join(host_values).decode("utf-8", errors="ignore").strip()
        if not host:
            host = f"{MCP_BIND_HOST}:{MCP_BIND_PORT}"
        return f"{scheme}://{host}"
    
    async def _send_json(self, send: Any, status: int, payload: Dict[str, Any], headers: Optional[list[tuple[bytes, bytes]]] = None) -> None:
        body = json.dumps(payload).encode("utf-8")
        response_headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
            (b"cache-control", b"no-store"),
        ]
        if headers:
            response_headers.extend(headers)
        
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": response_headers,
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
    
    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return
        
        path = scope.get("path") or ""
        method = scope.get("method") or ""
        
        origin = self._get_request_origin(scope)
        prm_url = f"{origin}/.well-known/oauth-protected-resource"
        streamable_path = (self._streamable_path or "").rstrip("/")
        normalized_path = path.rstrip("/")
        
        # Serve PRM metadata
        if method == "GET" and path == "/.well-known/oauth-protected-resource":
            prm = self._load_prm_metadata()
            prm["resource"] = f"{origin}{streamable_path}"
            await self._send_json(send, 200, prm)
            return

        # Enforce authentication for MCP endpoints (this is what triggers PRM handshake).
        is_mcp_path = normalized_path == streamable_path or path.startswith(streamable_path + "/")
        if self._require_auth and is_mcp_path:
            headers_list = list(scope.get("headers", []))

            # 1) Try Authorization header
            auth_values = [value for (key, value) in headers_list if (key or b"").lower() == b"authorization"]
            auth_header_bytes = b"".join(auth_values).strip()
            auth_header = auth_header_bytes.decode("utf-8", errors="ignore") if auth_header_bytes else ""
            bearer_token = _extract_bearer_token(auth_header)

            # 2) If missing, try cached token via MCP session id header
            session_id_values = [value for (key, value) in headers_list if (key or b"").lower() == b"mcp-session-id"]
            mcp_session_id = b"".join(session_id_values).decode("utf-8", errors="ignore").strip() if session_id_values else ""

            if not bearer_token and mcp_session_id:
                with _SESSION_LOCK:
                    cached = _MCP_SESSION_TOKEN_CACHE.get(mcp_session_id)
                if isinstance(cached, dict):
                    cached_token = cached.get("bearer_token")
                    expires_at = cached.get("expires_at")
                    if isinstance(expires_at, (int, float)) and expires_at < time.time():
                        with _SESSION_LOCK:
                            _MCP_SESSION_TOKEN_CACHE.pop(mcp_session_id, None)
                    elif isinstance(cached_token, str) and cached_token.strip():
                        bearer_token = cached_token.strip()
                        # Inject Authorization header into scope so tools can read it via Context
                        scope_headers = list(scope.get("headers", []))
                        scope_headers.append((b"authorization", f"Bearer {bearer_token}".encode("utf-8")))
                        scope["headers"] = scope_headers

            has_token = bool(bearer_token)
            print(
                f"[MCP PRM] {method} {path} - has_bearer_token={has_token} has_mcp_session_id={bool(mcp_session_id)}"
            )

            if not has_token:
                link_target = f'<{prm_url}>; rel="oauth-protected-resource"'.encode("utf-8")
                # Keep this header minimal and PRM-focused so clients can discover metadata and reuse auth silently.
                scope_hint = ""
                try:
                    prm = self._load_prm_metadata()
                    scopes = prm.get("scopes_supported")
                    if isinstance(scopes, list) and scopes and isinstance(scopes[0], str) and scopes[0].strip():
                        scope_hint = scopes[0].strip()
                except Exception:
                    scope_hint = ""

                if scope_hint:
                    www_auth = f'Bearer resource_metadata="{prm_url}", scope="{scope_hint}"'.encode("utf-8")
                else:
                    www_auth = f'Bearer resource_metadata="{prm_url}"'.encode("utf-8")
                await self._send_json(
                    send,
                    401,
                    {
                        "error": "unauthorized",
                        "message": "Authorization required to use this MCP server.",
                        "hint": "Complete PRM auth in the client; the server will cache the token after the first authenticated request.",
                    },
                    headers=[
                        (b"www-authenticate", www_auth),
                        (b"link", link_target),
                    ],
                )
                return

            # If we have a bearer token, capture the MCP session id from either the request
            # (mcp-session-id header) or the response (base transport may assign it).
            if bearer_token:
                if mcp_session_id:
                    with _SESSION_LOCK:
                        _MCP_SESSION_TOKEN_CACHE[mcp_session_id] = {
                            "bearer_token": bearer_token,
                            "expires_at": time.time() + _MCP_SESSION_TOKEN_TTL_SECONDS,
                        }

                async def send_capture_session_id(message: Dict[str, Any]) -> None:
                    if message.get("type") == "http.response.start":
                        resp_headers = list(message.get("headers", []))
                        resp_session_values = [
                            value
                            for (key, value) in resp_headers
                            if (key or b"").lower() == b"mcp-session-id"
                        ]
                        resp_session_id = (
                            b"".join(resp_session_values).decode("utf-8", errors="ignore").strip()
                            if resp_session_values
                            else ""
                        )
                        if resp_session_id:
                            with _SESSION_LOCK:
                                _MCP_SESSION_TOKEN_CACHE[resp_session_id] = {
                                    "bearer_token": bearer_token,
                                    "expires_at": time.time() + _MCP_SESSION_TOKEN_TTL_SECONDS,
                                }
                    await send(message)

                await self._app(scope, receive, send_capture_session_id)
                return
        
        await self._app(scope, receive, send)


if __name__ == "__main__":
    print(f"[MCP] Starting server with MCP_REQUIRE_AUTH={DEFAULT_REQUIRE_MCP_AUTH}")
    print(f"[MCP] PRM metadata path: {DEFAULT_PRM_METADATA_PATH}")

    base_app = _mcp.streamable_http_app()

    # Streamable HTTP transport is required for MCP Inspector.
    if DEFAULT_REQUIRE_MCP_AUTH:
        app_to_run: Any = _PrmAndAuthShim(
            app=base_app,
            streamable_path="/mcp",
            require_auth=DEFAULT_REQUIRE_MCP_AUTH,
            prm_metadata_path=DEFAULT_PRM_METADATA_PATH,
        )
        print(f"[MCP] Server starting on {MCP_BIND_HOST}:{MCP_BIND_PORT}/mcp (with PRM authentication)")
    else:
        app_to_run = base_app
        print(f"[MCP] Server starting on {MCP_BIND_HOST}:{MCP_BIND_PORT}/mcp (no authentication)")

    uvicorn.run(app_to_run, host=MCP_BIND_HOST, port=MCP_BIND_PORT, log_level="info")
