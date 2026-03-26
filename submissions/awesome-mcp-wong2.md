# PR Template: wong2/awesome-mcp-servers

## Entry to add (under "Developer Tools" section)

```markdown
- [Clarvia AEO Scanner](https://clarvia.art) - Scan any URL for AI Engine Optimization (AEO) readiness. Returns scores (0-100), ratings (A+ to F), dimension breakdowns, and actionable recommendations. Supports batch scanning, CI/CD integration (SARIF), and service comparison.
```

## PR Details

**Title:** Add Clarvia AEO Scanner - AI Engine Optimization scoring for APIs and services

**Body:**

### What is this MCP server?

Clarvia AEO Scanner is an MCP server that evaluates how well APIs and web services work with AI agents. It scores services on four dimensions:

1. **API Accessibility** - OpenAPI spec, response formats, error handling
2. **Data Structuring** - Schema quality, JSON-LD, structured data
3. **Agent Compatibility** - Rate limits, auth methods, tool-friendliness
4. **Trust Signals** - HTTPS, documentation, uptime

### Transport

Streamable HTTP at `https://clarvia-api.onrender.com/mcp`

### Tools

| Tool | Description |
|------|-------------|
| `scan_url` | Full AEO scan with dimension breakdowns |
| `get_score` | Quick score lookup (cached) |
| `compare_services` | Side-by-side comparison |
| `get_leaderboard` | Top services by category |
| `search_services` | Search the service index |

### Links

- Website: https://clarvia.art
- OpenAPI Spec: https://clarvia-api.onrender.com/openapi.json
- LangChain Package: `pip install clarvia-langchain`
