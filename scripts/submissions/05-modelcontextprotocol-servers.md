# PR: modelcontextprotocol/servers

## Target
https://github.com/modelcontextprotocol/servers

## Important
This is the **official** MCP repository maintained by Anthropic.
Submission standards are highest here. Check their CONTRIBUTING.md carefully.

## Section
Check for a "Community Servers" or "Third-Party" section.

## Entry (adjust to match their exact format)

```markdown
- **[Clarvia](https://github.com/clarvia-project/scanner/tree/main/mcp-server)** - Agent-readiness scoring for MCP servers and APIs. Returns a 0-100 score with improvement suggestions.
```

## PR Title
```
Add community server: agent-readiness scoring tool
```

## PR Body
```markdown
Adds a community MCP server that evaluates other MCP servers and
API endpoints for agent compatibility.

**What it does:**
Given a URL, it returns:
- A 0-100 agent-readiness score
- A grade (AGENT_NATIVE / AGENT_FRIENDLY / AGENT_POSSIBLE / AGENT_HOSTILE)
- Specific issues found (slow response, missing schemas, etc.)
- Fix suggestions for each issue

**Why it's useful for the MCP ecosystem:**
As the number of MCP servers grows, developers need a way to
evaluate quality before integrating. This tool provides a
standardized scoring methodology that server authors can use
to identify and fix compatibility issues.

**Install:** `npx -y clarvia-mcp-server`
**Remote:** `https://clarvia-api.onrender.com/mcp/`

- MIT licensed
- No API key or signup required
- Source: https://github.com/clarvia-project/scanner/tree/main/mcp-server

## Checklist
- [x] Follows community server format
- [x] Open source (MIT)
- [x] Publicly accessible, no auth required
- [x] Actively maintained
```

## Pre-submission Checklist
- [ ] Read their CONTRIBUTING.md for exact requirements
- [ ] Check if they have a specific PR template
- [ ] Verify the entry format matches existing community entries
- [ ] They may require a more complete MCP server implementation (full spec compliance)
