# PR: jaw9c/awesome-remote-mcp-servers

## Target
https://github.com/jaw9c/awesome-remote-mcp-servers

## Table Row Entry

```markdown
| Clarvia | Developer Tools | `https://clarvia-api.onrender.com/mcp/` | Open | [Source](https://github.com/clarvia-project/scanner/tree/main/mcp-server) |
```

## PR Title
```
Add agent-readiness scoring endpoint to Developer Tools
```

## PR Body
```markdown
Adds a remote MCP endpoint that scores other MCP servers and APIs
for agent-readiness.

**Endpoint:** `https://clarvia-api.onrender.com/mcp/`
**Transport:** Streamable HTTP
**Auth:** Open (no key required)
**Category:** Developer Tools

**What it does:**
Pass any URL to get a 0-100 agent-readiness score with a letter
grade and specific improvement suggestions. Helps when comparing
tools or checking if a service works well with AI agents.

Also available via npm (`npx -y clarvia-mcp-server`) for local use.

- MIT licensed
- Source: https://github.com/clarvia-project/scanner/tree/main/mcp-server

## Checklist
- [x] Table format matches existing entries
- [x] Remote endpoint is live and publicly accessible
- [x] No authentication required
- [x] SSL valid
```

## Notes
- This list specifically collects remote (hosted) MCP servers
- Focus on the endpoint URL and "open auth" -- matches the list's format
- Keep description minimal since the table format is compact
