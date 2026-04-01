<div align="center">

# clarvia-mcp-server

**MCP server for Clarvia — search, evaluate, and gate-check 27,831+ AI agent tools**

[![npm version](https://img.shields.io/npm/v/clarvia-mcp-server?color=cb3837)](https://www.npmjs.com/package/clarvia-mcp-server)
[![Smithery](https://smithery.ai/badge/@clarvia/aeo-scanner)](https://smithery.ai/server/@clarvia/aeo-scanner)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![MCP Tools](https://img.shields.io/badge/MCP_tools-24-6366f1)](#tools)

</div>

---

## Quick Start

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["-y", "clarvia-mcp-server"]
    }
  }
}
```

Or use the remote endpoint (no install needed):

```
https://clarvia-api.onrender.com/mcp/
```

## Configure

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["-y", "clarvia-mcp-server"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add clarvia -- npx -y clarvia-mcp-server
```

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["-y", "clarvia-mcp-server"]
    }
  }
}
```

### Windsurf

Add to `.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["-y", "clarvia-mcp-server"]
    }
  }
}
```

### Cline

Add to VS Code settings or `.cline/mcp.json`:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["-y", "clarvia-mcp-server"]
    }
  }
}
```

---

## Tools

### Discovery & Search

| Tool | Description |
|------|-------------|
| `search_services` | Search 27,906+ indexed AI tools (MCP servers, APIs, CLIs) by keyword, category, or minimum AEO score |
| `list_categories` | List all tool categories in the directory with service counts |
| `get_stats` | Get platform-wide statistics — total services, average scores, distributions |

### Scanning & Evaluation

| Tool | Description |
|------|-------------|
| `scan_service` | Run a full AEO audit on any URL — evaluates agent discoverability, API quality, docs, MCP readiness |
| `get_service_details` | Get detailed scoring breakdown for a previously scanned service |
| `register_service` | Submit a new service for indexing and AEO scoring |

### Agent Safety & Gating

| Tool | Description |
|------|-------------|
| `clarvia_gate_check` | Quick pass/fail safety check — returns agent grade (NATIVE/FRIENDLY/POSSIBLE/HOSTILE) with boolean result |
| `clarvia_batch_check` | Batch-check up to 10 URLs in one call — compare tool candidates side-by-side |
| `clarvia_find_alternatives` | Find higher-rated alternative tools in a category, ranked by agent-readiness |
| `clarvia_probe` | Live accessibility probe — HTTP reachability, latency, OpenAPI, MCP server-card, agents.json |

### Setup Management

| Tool | Description |
|------|-------------|
| `register_my_setup` | Register your tool setup to get AEO scores and category rankings for each tool |
| `compare_my_setup` | Compare your setup against higher-scored alternatives in each category |
| `recommend_upgrades` | Get personalized upgrade recommendations based on your registered setup |

### Feedback & Support

| Tool | Description |
|------|-------------|
| `clarvia_submit_feedback` | Report tool usage outcomes (success/failure/partial) to improve reliability data |
| `clarvia_report_issue` | Report bugs, request features, or flag security issues |
| `clarvia_list_issues` | List existing tickets — check status or find known issues |

---

## Usage Examples

**Search for AI tools:**
```
Use search_services with query "code assistant" to find coding tools
```

**Gate-check before calling a tool:**
```
Use clarvia_gate_check with url "https://api.example.com" and min_rating "AGENT_FRIENDLY"
```

**Scan a new service:**
```
Use scan_service with url "https://example.com" to get a full AEO audit
```

**Find alternatives when a tool fails:**
```
Use clarvia_find_alternatives with category "payment" and min_score 70
```

**Benchmark your agent's toolchain:**
```
Use register_my_setup with tools ["dune-mcp", "notion-mcp", "telegram-bot"]
Then use compare_my_setup with the returned setup_id
```

**Report usage outcome:**
```
Use clarvia_submit_feedback with profile_id, outcome "success", and latency_ms
```

---

## Add Your AEO Score Badge

If you're an MCP server developer, add your Clarvia AEO score to your README:

```markdown
[![AEO Score](https://clarvia.art/api/badge/YOUR-TOOL-NAME)](https://clarvia.art/profile/YOUR-TOOL-NAME)
```

Example output: `Clarvia: AEO 87/100` — shows your agent-readiness score, auto-updates when scores change.

[Check your tool's score →](https://clarvia.art)

---

## Development

```bash
npm install
npm run dev    # Watch mode
npm run build  # Production build
npm start      # Run server
```

## Links

- **Website**: [clarvia.art](https://clarvia.art)
- **GitHub**: [clarvia-project/scanner](https://github.com/clarvia-project/scanner)
- **npm**: [clarvia-mcp-server](https://www.npmjs.com/package/clarvia-mcp-server)
- **GitHub Action**: [clarvia-project/clarvia-aeo-check](https://github.com/clarvia-project/clarvia-aeo-check) — AEO check in CI/CD pipelines
- **MCP Registry**: `io.github.digitamaz/clarvia`
- **Remote Endpoint**: `https://clarvia-api.onrender.com/mcp/`

## License

[MIT](LICENSE)
