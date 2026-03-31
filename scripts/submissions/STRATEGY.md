# Awesome-List Submission Strategy v2

## What went wrong (v1)

The awesome-claude-code-toolkit rejection cited "commercial product promotion."
Root causes:
1. PR title/body led with brand name ("Add Clarvia...")
2. Description read like a product pitch ("Clarvia is the agent-tool validation layer")
3. Feature dump (5 tools listed) felt like an ad
4. "15,400+ indexed tools" reads as marketing copy

## v2 Principles

1. **Lead with what the user gets**, not with the product name
2. **One-sentence description** -- what problem does it solve for the reader?
3. **Brand name appears only as the link text** (unavoidable), nowhere else
4. **No feature dump** -- mention 1-2 key capabilities, link to docs for the rest
5. **PR title = what changes in the list**, not a product tagline
6. **PR body = why this belongs here**, referencing how it fits the list's criteria
7. **Tone = fellow contributor**, not vendor

## Description Templates

### Short (list entry):
"Free AEO scoring for MCP servers -- paste any URL, get an agent-readiness grade and improvement tips."

### Medium (PR body):
"Scores any MCP server or API endpoint for agent-readiness (0-100).
Useful when you're picking between tools and want to know which ones
work well with AI agents out of the box. No signup required."

### What NOT to say:
- "Clarvia is..." / "Clarvia provides..."
- "The standard validation layer"
- Listing every tool/endpoint
- "15,400+ indexed tools"
- Any superlative ("best", "only", "first")

## Target Lists (5)

1. appcypher/awesome-mcp-servers -- largest MCP list
2. jaw9c/awesome-remote-mcp-servers -- remote-only focus
3. punkpeye/awesome-mcp-servers -- another major MCP list
4. wong2/awesome-mcp-servers (via mcpservers.org) -- web submission
5. modelcontextprotocol/servers -- official MCP registry
