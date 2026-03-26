# PR Content: appcypher/awesome-mcp-servers

## Where to add

Under the **"Testing & Quality Assurance"** section in README.md. If that section does not exist, add under **"Developer Tools"**.

## Exact markdown entry to add

```markdown
- <img src="https://clarvia.art/favicon.ico" height="14"/> [Clarvia](https://github.com/clarvia-project/scanner) - AEO scoring and tool discovery platform for AI agents — search 15,400+ indexed tools, gate-check services before use, compare alternatives, and submit quality feedback
```

## PR title

```
Add Clarvia - AEO scoring and tool discovery for AI agents
```

## PR body

```markdown
**Clarvia** is an AEO (Agent Engine Optimization) scoring and tool discovery platform. It indexes 15,400+ AI agent tools (MCP servers, APIs, CLIs) and scores them on agent-readiness.

**16 MCP tools** including:
- `search_services` — Search indexed tools by keyword, category, or score
- `scan_service` — Full AEO audit on any URL
- `clarvia_gate_check` — Pass/fail check before calling any external tool
- `clarvia_batch_check` — Check up to 10 URLs at once
- `clarvia_find_alternatives` — Find higher-rated tools in a category
- `clarvia_probe` — Live accessibility probe
- `clarvia_submit_feedback` — Report tool usage outcomes
- `register_my_setup` / `compare_my_setup` / `recommend_upgrades` — Benchmark your toolchain

**Install:**
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

**Links:**
- npm: https://www.npmjs.com/package/clarvia-mcp-server
- Website: https://clarvia.art
- GitHub: https://github.com/clarvia-project/scanner
```
