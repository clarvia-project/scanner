# PR: appcypher/awesome-mcp-servers

## Target
https://github.com/appcypher/awesome-mcp-servers

## Section
**Development Tools** (alphabetically under C)

## List Entry

```markdown
- <img src="https://clarvia.art/favicon.ico" height="14"/> [Clarvia](https://github.com/clarvia-project/scanner/tree/main/mcp-server) - Free agent-readiness scoring for MCP servers and APIs. Paste a URL, get a 0-100 score with actionable improvement tips.
```

## PR Title
```
Add free agent-readiness scorer to Development Tools
```

## PR Body
```markdown
Adds a free tool that scores MCP servers and API endpoints for
agent-readiness (0-100 scale with grades like AGENT_NATIVE,
AGENT_FRIENDLY, etc.).

**Why this is useful for the list:**
When evaluating which MCP server to use, this tool answers
"how well does this work with AI agents?" before you commit.
It also suggests concrete fixes (missing error codes, slow
response times, incomplete schemas) so server authors can
improve their scores.

**Install:**
```bash
npx -y clarvia-mcp-server
```

**Or remote (no install):**
```
https://clarvia-api.onrender.com/mcp/
```

- MIT licensed, no signup required
- Source: https://github.com/clarvia-project/scanner/tree/main/mcp-server

## Checklist
- [x] Alphabetical placement in Development Tools
- [x] Matches existing entry format (favicon + link + description)
- [x] Description focuses on what the tool does, not branding
- [x] Open source, free to use
```

## Notes
- Previous submission was rejected for "commercial product promotion"
- This version leads with utility ("free agent-readiness scorer"), not brand
- PR title doesn't mention the product name at all
