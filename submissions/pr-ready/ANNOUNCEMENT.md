# Clarvia Launch Announcements

## Twitter/X (280 chars max)

```
Clarvia: the quality index for AI agent tools.

Search 12,800+ MCP servers, APIs & CLIs scored on agent-readiness (0-100). Gate-check tools before calling, find alternatives, benchmark your setup.

Free MCP server: npx clarvia-mcp-server

https://clarvia.art
```

**Character count: 274**

---

## Reddit r/AI_Agents

**Title:**
```
Clarvia - Open tool discovery and quality scoring for AI agents (12,800+ indexed MCP servers, APIs, CLIs)
```

**Body:**
```
Hey r/AI_Agents,

We built Clarvia to solve a problem we kept hitting: how do you know which MCP server or API is actually good before your agent calls it?

**What it does:**
Clarvia indexes 12,800+ AI agent tools and scores each one on agent-readiness (0-100) across five dimensions: description quality, documentation, ecosystem presence, agent compatibility, and trust signals.

**How agents use it:**
- `search_services` — find the best tool for a task
- `clarvia_gate_check` — pass/fail check before calling any tool
- `clarvia_find_alternatives` — if a tool scores low, find a better one
- `clarvia_probe` — real-time health check (is it online? does it have OpenAPI?)
- `register_my_setup` + `compare_my_setup` — benchmark your whole toolchain

**How to try it:**
Add to your MCP config:
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

16 tools total, all free. The index is community-driven — submit your own tools and get scored.

Website: https://clarvia.art
npm: https://npmjs.com/package/clarvia-mcp-server
GitHub: https://github.com/clarvia-project/scanner

Happy to answer questions or take feedback.
```

---

## Hacker News - Show HN

**Title:**
```
Show HN: Clarvia - Quality index for AI agent tools (12,800+ MCP servers scored)
```

**Body:**
```
Clarvia is an open tool discovery and quality scoring platform for AI agents. We index 12,800+ MCP servers, APIs, and CLIs, and score each on agent-readiness across five dimensions.

The core use case: before your agent calls an external tool, run `clarvia_gate_check` to verify it meets a minimum quality threshold. If it fails, `clarvia_find_alternatives` returns better-scored options in the same category.

We ship as an MCP server (npx clarvia-mcp-server) with 16 tools, so any MCP-compatible agent (Claude, Cursor, Windsurf, etc.) can use it natively.

Scoring dimensions:
- Description quality (does the tool explain what it does?)
- Documentation (homepage, repo, versioning, API docs)
- Ecosystem presence (registry listings, downloads, install commands)
- Agent compatibility (MCP support, tool definitions, API specs)
- Trust signals (known org, HTTPS, semver, official registries)

Everything is free. The index is community-driven — anyone can submit tools.

Website: https://clarvia.art
npm: https://npmjs.com/package/clarvia-mcp-server
GitHub: https://github.com/clarvia-project/scanner
```
