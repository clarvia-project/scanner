# PR: punkpeye/awesome-mcp-servers

## Target
https://github.com/punkpeye/awesome-mcp-servers

## Section
Check the repo's category structure first. Likely: **Developer Tools** or **Testing & Quality**

## List Entry

```markdown
- [Clarvia](https://github.com/clarvia-project/scanner/tree/main/mcp-server) - Score any MCP server or API for agent-readiness (0-100). Returns a grade, specific issues found, and improvement suggestions. Free, no signup. `npx -y clarvia-mcp-server`
```

## PR Title
```
Add agent-readiness scoring tool
```

## PR Body
```markdown
Adds an MCP server that scores other MCP servers and API endpoints
for agent-readiness.

**Problem it solves:**
There's no standard way to evaluate whether an MCP server works
well with AI agents. This tool gives a 0-100 score based on
response time, error handling, schema completeness, and other
agent-compatibility factors.

**How it works:**
1. Pass a URL to `clarvia_gate_check`
2. Get a score (0-100), grade, and list of specific issues
3. Each issue includes a fix suggestion

**Install:** `npx -y clarvia-mcp-server`
**Remote:** `https://clarvia-api.onrender.com/mcp/`

- MIT licensed, no signup or API key needed
- Source: https://github.com/clarvia-project/scanner/tree/main/mcp-server

## Checklist
- [x] Entry matches existing format
- [x] Alphabetical placement
- [x] Open source (MIT)
- [x] Free to use, no auth required
```

## Notes
- punkpeye's list is one of the most active MCP awesome-lists
- Before submitting, check their CONTRIBUTING.md for format requirements
- This list tends to be more welcoming of new entries than appcypher's
