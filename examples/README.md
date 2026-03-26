# Clarvia MCP Server — Framework Integration Examples

Ready-to-copy configuration files for popular AI coding assistants.

## Quick Start

### Claude Code
```bash
claude mcp add clarvia -- npx -y clarvia-mcp-server
```

### Claude Desktop
Copy `claude-code/settings.json` content to:
`~/Library/Application Support/Claude/claude_desktop_config.json`

### Cursor
Copy `cursor/mcp.json` to your project's `.cursor/mcp.json`

### Windsurf
Copy `windsurf/mcp.json` to your project's `.windsurf/mcp.json`

### Cline
Copy `cline/mcp.json` to your project's `.cline/mcp.json` or VS Code settings

### Continue
Copy `continue/config.json` content to your `~/.continue/config.json`

### Remote Endpoint (any client)
No installation needed — point any MCP-compatible client to:
```
https://clarvia-api.onrender.com/mcp/
```

## What You Get

16 MCP tools for AI agent tool discovery and evaluation:

- **search_services** — Search 15,400+ indexed AI tools
- **scan_service** — Run AEO audits on any URL
- **clarvia_gate_check** — Pass/fail safety check before using a tool
- **clarvia_batch_check** — Check up to 10 URLs at once
- **clarvia_find_alternatives** — Find better-rated alternatives
- **clarvia_probe** — Live accessibility probe

See full tool list at [npmjs.com/package/clarvia-mcp-server](https://www.npmjs.com/package/clarvia-mcp-server)
