# Clarvia MCP Server

MCP (Model Context Protocol) server that exposes Clarvia's AI service evaluation platform as tools for LLM agents.

## Tools

| Tool | Description |
|------|-------------|
| `search_services` | Search indexed services by keyword, category, or minimum score |
| `scan_service` | Scan a URL for Clarvia evaluation |
| `get_service_details` | Get detailed results for a specific scan |
| `list_categories` | List all service categories |
| `get_stats` | Get platform-wide statistics |
| `register_service` | Register a new service for evaluation |

## Installation

```bash
cd mcp-server
npm install
npm run build
```

## Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "node",
      "args": ["/absolute/path/to/scanner/mcp-server/dist/index.js"]
    }
  }
}
```

### Claude Code

Add to `.claude/settings.json` or use `claude mcp add`:

```bash
claude mcp add clarvia node /absolute/path/to/scanner/mcp-server/dist/index.js
```

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "node",
      "args": ["/absolute/path/to/scanner/mcp-server/dist/index.js"]
    }
  }
}
```

## Usage Examples

**Search for AI coding tools:**
```
Use search_services with query "code assistant"
```

**Scan a new service:**
```
Use scan_service with url "https://example.com"
```

**Check platform stats:**
```
Use get_stats to see overall Clarvia statistics
```

**Register a service:**
```
Use register_service with name, url, description, and category
```

## Development

```bash
npm run dev    # Watch mode
npm run build  # Production build
npm start      # Run server
```
