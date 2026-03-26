<div align="center">

# clarvia-mcp-server

**MCP server for Clarvia AEO Scanner -- search, evaluate, and gate-check 12,800+ AI agent tools**

[![npm version](https://img.shields.io/npm/v/clarvia-mcp-server?color=cb3837)](https://www.npmjs.com/package/clarvia-mcp-server)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![MCP Tools](https://img.shields.io/badge/MCP_tools-11-6366f1)](#tools)

</div>

---

## Install

```bash
npx clarvia-mcp-server
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
      "args": ["clarvia-mcp-server"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add clarvia -- npx clarvia-mcp-server
```

### Cursor / Windsurf

Add to `.cursor/mcp.json` or `.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["clarvia-mcp-server"]
    }
  }
}
```

---

## Tools

| Tool | Description |
|------|-------------|
| `search_services` | Search 12,800+ indexed AI tools by keyword, category, or minimum score |
| `scan_service` | Run a full AEO audit on any URL |
| `get_service_details` | Get detailed scoring breakdown for a scanned service |
| `list_categories` | List all tool categories with service counts |
| `get_stats` | Get platform-wide statistics (averages, distributions) |
| `register_service` | Submit a new service for indexing and scoring |
| `clarvia_gate_check` | Quick pass/fail safety check before using a tool |
| `clarvia_batch_check` | Batch-check up to 10 URLs in one call |
| `clarvia_find_alternatives` | Find higher-rated alternatives in a category |
| `clarvia_probe` | Live accessibility probe (HTTP, latency, OpenAPI, MCP) |
| `clarvia_submit_feedback` | Report tool usage outcomes to improve reliability data |

---

## Usage Examples

**Search for AI tools:**
```
Use search_services with query "code assistant" to find coding tools
```

**Gate-check before calling a tool:**
```
Use clarvia_gate_check with url "https://api.example.com" and min_score 60
```

**Scan a new service:**
```
Use scan_service with url "https://example.com" to get a full AEO audit
```

**Find alternatives when a tool fails:**
```
Use clarvia_find_alternatives with category "payment" and min_score 70
```

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
- **MCP Registry**: `io.github.digitamaz/clarvia`

## License

[MIT](LICENSE)
