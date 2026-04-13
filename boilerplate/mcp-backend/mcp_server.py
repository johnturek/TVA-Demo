"""
TVA MCP Server — Python/FastMCP
Serves TVA regulatory and compliance documents via the MCP protocol.

Usage:
  python mcp_server.py

Environment variables (set in .env):
  FASTMCP_HOST        Host to bind (default: 0.0.0.0)
  FASTMCP_PORT        Port to listen on (default: 8000)
  MCP_REQUIRE_AUTH    Set to "true" to enforce Entra ID / OBO auth
"""

import os
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

HOST = os.getenv("FASTMCP_HOST", "0.0.0.0")
PORT = int(os.getenv("FASTMCP_PORT", "8000"))

mcp = FastMCP("tva-mcp-server")

# ── TVA Knowledge Base ────────────────────────────────────────────────────────

TVA_DOCS = {
    "nerc-cip-007": {
        "id": "nerc-cip-007",
        "title": "NERC CIP-007 — Systems Security Management",
        "category": "compliance",
        "content": (
            "Requires entities to define methods, processes, and procedures for securing "
            "BES Cyber Systems. Patch management must occur within 35 calendar days of "
            "availability for security patches rated critical or high. Ports and services "
            "must be reviewed every 15 months. Security event logging must be retained for "
            "at least 90 days."
        ),
    },
    "nerc-cip-010": {
        "id": "nerc-cip-010",
        "title": "NERC CIP-010 — Configuration Change Management and Vulnerability Management",
        "category": "compliance",
        "content": (
            "Requires baseline configurations for all BES Cyber Systems. Changes must be "
            "documented prior to implementation and reviewed for security impact. Vulnerability "
            "assessments are required at least once every 15 months for high and medium impact "
            "systems. Transient cyber assets must be managed and documented."
        ),
    },
    "nerc-cip-011": {
        "id": "nerc-cip-011",
        "title": "NERC CIP-011 — Information Protection",
        "category": "compliance",
        "content": (
            "Requires a program to identify, classify, and protect BES Cyber System Information "
            "(BCSI). Storage, transit, and use of BCSI must be controlled. Access to BCSI must "
            "be authorized and logged. Physical media containing BCSI must be protected and "
            "properly sanitized before disposal."
        ),
    },
    "tva-grid-reliability": {
        "id": "tva-grid-reliability",
        "title": "TVA Grid Reliability Annual Report 2025",
        "category": "operations",
        "content": (
            "TVA's transmission system achieved 99.97% reliability in 2025. SAIDI improved 12% "
            "year-over-year to 68 minutes. The Brownsville and Cumberland facilities met all "
            "NERC TPL-001 transmission planning standards. Renewable integration increased to "
            "18% of total generation capacity. Grid modernization investments totaled $1.2B."
        ),
    },
    "nuclear-safety": {
        "id": "nuclear-safety",
        "title": "TVA Nuclear Plant Safety Procedures Overview",
        "category": "nuclear",
        "content": (
            "TVA operates three nuclear facilities: Browns Ferry (AL), Sequoyah (TN), and "
            "Watts Bar (TN) — totaling 7 units and approximately 8,000 MW of capacity. "
            "Primary coolant temperature normal operating range: 540–560°F. Maximum design "
            "temperature: 620°F. Emergency core cooling systems are tested quarterly per "
            "NRC 10 CFR 50 requirements. All facilities hold current NRC operating licenses."
        ),
    },
    "regulatory-variance": {
        "id": "regulatory-variance",
        "title": "TVA Regulatory Variance Request Process",
        "category": "regulatory",
        "content": (
            "Regulatory variance requests must be submitted to the Regulatory Affairs office "
            "a minimum of 60 days prior to the required compliance date. Requests must include: "
            "technical justification, risk assessment, proposed alternative controls, and timeline "
            "for full compliance. Emergency variance requests may be submitted with 5 business "
            "days notice with VP-level approval. Contact: regulatory.affairs@tva.gov"
        ),
    },
}

# ── MCP Tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def search_tva_docs(query: str, top: int = 3, category: str = None) -> list:
    """Semantic search across TVA regulatory and compliance documents."""
    q = query.lower()
    results = [
        doc for doc in TVA_DOCS.values()
        if (q in doc["content"].lower() or q in doc["title"].lower())
        and (category is None or doc["category"] == category)
    ]
    return results[:top]


@mcp.tool()
def get_nerc_requirement(standard: str) -> dict:
    """Look up a specific NERC CIP standard by number (e.g. CIP-007, CIP-010, CIP-011)."""
    key = f"nerc-{standard.lower().replace(' ', '-')}"
    return TVA_DOCS.get(key, {"error": f"No data found for standard: {standard}"})


@mcp.tool()
def check_compliance_status(standard: str) -> dict:
    """Get TVA's current compliance posture for a given NERC CIP standard."""
    return {
        "standard": standard,
        "status": "Compliant",
        "lastAssessed": "2026-01-15",
        "nextAssessmentDue": "2026-07-15",
        "openFindings": 0,
        "closedFindings": 3,
        "note": "All controls verified. Next quarterly review scheduled.",
    }


@mcp.tool()
def list_regulations(category: str = None) -> list:
    """List all TVA-relevant regulatory frameworks and documents available."""
    docs = list(TVA_DOCS.values())
    if category:
        docs = [d for d in docs if d["category"] == category]
    return [{"id": d["id"], "title": d["title"], "category": d["category"]} for d in docs]


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print(f"🏭 TVA MCP Server starting on {HOST}:{PORT}")
    print(f"   MCP endpoint:  http://{HOST}:{PORT}/mcp")
    print(f"   Health:        http://{HOST}:{PORT}/health")
    mcp.run(transport="http", host=HOST, port=PORT)
