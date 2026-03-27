# PR: Add Clarvia to jaw9c/awesome-remote-mcp-servers

## Target repo
https://github.com/jaw9c/awesome-remote-mcp-servers

## Entry to add (table row, alphabetically under C)

Insert after "Cortex" row:

```markdown
| Clarvia | AI Tool Discovery | `https://clarvia-api.onrender.com/mcp/` | Open | [Clarvia](https://clarvia.art) |
```

## PR Title
feat: add Clarvia remote MCP server (AI tool discovery and gate-checking)

## PR Body
```
## Description

This PR adds [Clarvia](https://clarvia.art) to the remote MCP server list.

**Category**: AI Tool Discovery / Agent Infrastructure

**Remote endpoint**: `https://clarvia-api.onrender.com/mcp/`
**Transport**: Streamable HTTP
**Auth**: Open (no API key required for read operations)
**Maintainer**: [Clarvia](https://clarvia.art)

## What it does

Clarvia is the tool-validation and discovery layer for autonomous agents. Before an agent calls any external API or MCP server, it can call `clarvia_gate_check` to:

1. Get an agent-readiness score (0-100) and grade (AGENT_NATIVE / AGENT_FRIENDLY / AGENT_POSSIBLE / AGENT_HOSTILE)
2. Receive a pass/fail decision against a configurable threshold
3. Get automatic alternatives if the service fails

**Key tools**:
- `clarvia_gate_check` — pass/fail before calling any tool
- `search_services` — search 15,400+ indexed tools (MCP, API, CLI, Skill)
- `clarvia_batch_check` — check up to 100 URLs at once
- `clarvia_find_alternatives` — find better-scored tools in the same category
- `clarvia_probe` — real-time HTTP/OpenAPI/MCP health probe

**Usage** (Streamable HTTP):
```json
{
  "mcpServers": {
    "clarvia": {
      "url": "https://clarvia-api.onrender.com/mcp/",
      "transport": "streamable-http"
    }
  }
}
```

Or via npm:
```bash
npx -y clarvia-mcp-server
```

## Quality checklist
- [x] Official endpoint maintained by Clarvia
- [x] Production stable (Render Starter plan, always-on)
- [x] Active maintenance — catalog updated daily
- [x] No authentication required for discovery/gate-check
- [x] SSL valid on production domain
```

## Notes
- Auth level: "Open" (matches AWS Knowledge Base pattern in the list)
- Category: "AI Tool Discovery" — new category, or could be "AI Services"
- Alphabetical position: after "Cortex", before "Dialer"
