const express = require('express');
const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3002;

// ============================================================
// TVA Knowledge Base — pre-loaded public documents
// Add/edit entries here to customize workshop content
// ============================================================
const TVA_DOCS = {
  "nerc-cip-007": {
    id: "nerc-cip-007",
    title: "NERC CIP-007 — Systems Security Management",
    category: "compliance",
    content: "Requires entities to define methods, processes, and procedures for securing BES Cyber Systems. Patch management must occur within 35 calendar days of availability for security patches rated critical or high. Ports and services must be reviewed every 15 months. Security event logging must be retained for at least 90 days."
  },
  "nerc-cip-010": {
    id: "nerc-cip-010",
    title: "NERC CIP-010 — Configuration Change Management and Vulnerability Management",
    category: "compliance",
    content: "Requires baseline configurations for all BES Cyber Systems. Changes must be documented prior to implementation and reviewed for security impact. Vulnerability assessments are required at least once every 15 months for high and medium impact systems. Transient cyber assets must be managed and documented."
  },
  "nerc-cip-011": {
    id: "nerc-cip-011",
    title: "NERC CIP-011 — Information Protection",
    category: "compliance",
    content: "Requires a program to identify, classify, and protect BES Cyber System Information (BCSI). Storage, transit, and use of BCSI must be controlled. Access to BCSI must be authorized and logged. Physical media containing BCSI must be protected and properly sanitized before disposal."
  },
  "tva-grid-reliability": {
    id: "tva-grid-reliability",
    title: "TVA Grid Reliability Annual Report 2025",
    category: "operations",
    content: "TVA's transmission system achieved 99.97% reliability in 2025. SAIDI improved 12% year-over-year to 68 minutes. The Brownsville and Cumberland facilities met all NERC TPL-001 transmission planning standards. Renewable integration increased to 18% of total generation capacity. Grid modernization investments totaled $1.2B."
  },
  "nuclear-safety": {
    id: "nuclear-safety",
    title: "TVA Nuclear Plant Safety Procedures Overview",
    category: "nuclear",
    content: "TVA operates three nuclear facilities: Browns Ferry (AL), Sequoyah (TN), and Watts Bar (TN) — totaling 7 units and approximately 8,000 MW of capacity. Primary coolant temperature normal operating range: 540–560°F. Maximum design temperature: 620°F. Emergency core cooling systems are tested quarterly per NRC 10 CFR 50 requirements. All facilities hold current NRC operating licenses."
  },
  "regulatory-variance": {
    id: "regulatory-variance",
    title: "TVA Regulatory Variance Request Process",
    category: "regulatory",
    content: "Regulatory variance requests must be submitted to the Regulatory Affairs office a minimum of 60 days prior to the required compliance date. Requests must include: technical justification, risk assessment, proposed alternative controls, and timeline for full compliance. Emergency variance requests may be submitted with 5 business days notice with VP-level approval. Contact: regulatory.affairs@tva.gov"
  }
};

// ============================================================
// MCP Tool Definitions
// ============================================================
const TOOLS = [
  {
    name: "search_tva_docs",
    description: "Semantic search across TVA regulatory and compliance documents. Use for open-ended questions.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Natural language search query" },
        top:   { type: "number", description: "Number of results to return (default: 3)" },
        category: { type: "string", description: "Filter by category: compliance, operations, nuclear, regulatory" }
      },
      required: ["query"]
    }
  },
  {
    name: "get_nerc_requirement",
    description: "Look up a specific NERC CIP standard by number (e.g. CIP-007, CIP-010, CIP-011)",
    inputSchema: {
      type: "object",
      properties: {
        standard: { type: "string", description: "NERC CIP standard number, e.g. CIP-007" }
      },
      required: ["standard"]
    }
  },
  {
    name: "check_compliance_status",
    description: "Get TVA's current compliance posture for a given NERC CIP standard",
    inputSchema: {
      type: "object",
      properties: {
        standard: { type: "string", description: "NERC CIP standard, e.g. CIP-007" }
      },
      required: ["standard"]
    }
  },
  {
    name: "list_regulations",
    description: "List all TVA-relevant regulatory frameworks and documents available",
    inputSchema: {
      type: "object",
      properties: {
        category: { type: "string", description: "Optional filter by category" }
      }
    }
  }
];

// ============================================================
// Tool Handlers
// ============================================================
function handleSearchTvaDocs({ query, top = 3, category }) {
  const q = query.toLowerCase();
  let results = Object.values(TVA_DOCS).filter(doc => {
    const matchesQuery = doc.content.toLowerCase().includes(q) || doc.title.toLowerCase().includes(q);
    const matchesCategory = !category || doc.category === category;
    return matchesQuery && matchesCategory;
  });
  return results.slice(0, top);
}

function handleGetNercRequirement({ standard }) {
  const key = `nerc-${standard.toLowerCase().replace(/\s+/g, '-')}`;
  return TVA_DOCS[key] || { error: `No data found for standard: ${standard}` };
}

function handleCheckComplianceStatus({ standard }) {
  // Mock compliance data — replace with real API call in production
  return {
    standard,
    status: "Compliant",
    lastAssessed: "2026-01-15",
    nextAssessmentDue: "2026-07-15",
    openFindings: 0,
    closedFindings: 3,
    note: "All controls verified. Next quarterly review scheduled."
  };
}

function handleListRegulations({ category } = {}) {
  const docs = Object.values(TVA_DOCS);
  const filtered = category ? docs.filter(d => d.category === category) : docs;
  return filtered.map(({ id, title, category }) => ({ id, title, category }));
}

// ============================================================
// MCP Endpoint
// ============================================================
app.post('/mcp', (req, res) => {
  const { method, params } = req.body;

  if (method === 'initialize') {
    return res.json({
      protocolVersion: "2024-11-05",
      capabilities: { tools: {} },
      serverInfo: { name: "tva-mcp-server", version: "1.0.0" }
    });
  }

  if (method === 'tools/list') {
    return res.json({ tools: TOOLS });
  }

  if (method === 'tools/call') {
    const { name, arguments: args } = params;

    try {
      let result;
      switch (name) {
        case 'search_tva_docs':       result = handleSearchTvaDocs(args);       break;
        case 'get_nerc_requirement':  result = handleGetNercRequirement(args);  break;
        case 'check_compliance_status': result = handleCheckComplianceStatus(args); break;
        case 'list_regulations':      result = handleListRegulations(args);     break;
        default:
          return res.status(400).json({ error: `Unknown tool: ${name}` });
      }

      return res.json({
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
      });

    } catch (err) {
      return res.status(500).json({ error: err.message });
    }
  }

  res.status(400).json({ error: `Unknown MCP method: ${method}` });
});

app.get('/health', (_, res) => res.json({ status: 'ok', service: 'TVA MCP Server', tools: TOOLS.length }));

app.listen(PORT, () => {
  console.log(`🏭 TVA MCP Server running on port ${PORT}`);
  console.log(`   Health: http://localhost:${PORT}/health`);
  console.log(`   MCP:    http://localhost:${PORT}/mcp`);
});
