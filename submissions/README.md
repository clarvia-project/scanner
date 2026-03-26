# Clarvia MCP Directory Submissions

Templates and configs for submitting the Clarvia MCP server to various directories.

## Directories

| Directory | Status | File |
|-----------|--------|------|
| Cursor Directory | Pending | `cursor-directory.json` |
| LobeHub MCP Marketplace | Pending | `lobehub-manifest.json` |
| Windsurf | Pending | `windsurf-plugin.json` |
| awesome-mcp-servers (wong2) | Pending | `awesome-mcp-wong2.md` |
| awesome-mcp-servers (appcypher) | Pending | `awesome-mcp-appcypher.md` |

## MCP Server Details

- **Name:** Clarvia AEO Scanner
- **Transport:** Streamable HTTP (POST /mcp)
- **Endpoint:** `https://clarvia-api.onrender.com/mcp`
- **OpenAPI Spec:** `https://clarvia-api.onrender.com/openapi.json`
- **Description:** Scan any URL for AI Engine Optimization readiness. Get AEO scores, dimension breakdowns, and actionable recommendations.

## Tools Exposed via MCP

1. `scan_url` - Run a full AEO scan on any URL
2. `get_score` - Quick score lookup (cached/prebuilt first, live fallback)
3. `compare_services` - Compare 2-3 services side by side
4. `get_leaderboard` - Top-scored services by category
5. `search_services` - Full-text search across the service index

## Submission Process

1. Review each template file
2. Fill in any `TODO` placeholders with actual values
3. Submit via the directory's preferred method (PR, form, API)
4. Track status in the table above
