# PR Template: appcypher/awesome-mcp-servers

## Entry to add (under "Testing & Quality Assurance" or "Developer Tools" section)

```markdown
| [Clarvia AEO Scanner](https://clarvia.art) | Scan URLs for AI Engine Optimization readiness — scores, ratings, and recommendations for agent-friendly APIs | [Source](https://github.com/clarvia/clarvia-scanner) |
```

## PR Details

**Title:** Add Clarvia AEO Scanner MCP Server

**Body:**

Clarvia AEO Scanner is a hosted MCP server that scores how well APIs and services work with AI agents.

**Key features:**
- AEO score (0-100) with A+ to F ratings
- Four scoring dimensions: API Accessibility, Data Structuring, Agent Compatibility, Trust Signals
- Batch scanning and CI/CD integration (SARIF output)
- Service comparison and leaderboard
- LangChain middleware for auto-gating tool calls by score

**MCP Details:**
- Transport: Streamable HTTP
- Endpoint: `https://clarvia-api.onrender.com/mcp`
- OpenAPI: `https://clarvia-api.onrender.com/openapi.json`
- Tools: `scan_url`, `get_score`, `compare_services`, `get_leaderboard`, `search_services`

**Rate limits:** Free 10 scans/hr, Pro 100/hr, Enterprise unlimited.

---

_This adds a quality/scoring tool that helps agents evaluate external services before using them._
