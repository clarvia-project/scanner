# PR Content: wong2/awesome-mcp-servers

## Where to add

Under the **"Developer Tools"** section in README.md.

## Exact markdown entry to add

```markdown
- **[Clarvia](https://github.com/clarvia-project/scanner)** - AEO scoring and tool discovery platform for AI agents. Search 15,400+ indexed MCP servers, APIs, and CLIs with agent-readiness scores, gate-check tools before use, compare alternatives, and submit quality feedback. [![npm](https://img.shields.io/npm/v/clarvia-mcp-server)](https://www.npmjs.com/package/clarvia-mcp-server)
```

## PR title

```
Add Clarvia - AEO scoring and tool discovery for AI agents
```

## PR body

```markdown
### What is this MCP server?

[Clarvia](https://clarvia.art) is an AEO (Agent Engine Optimization) scoring and tool discovery platform. It indexes 15,400+ AI agent tools and scores them on agent-readiness (0-100).

### Tools (16 total)

| Tool | Description |
|------|-------------|
| `search_services` | Search indexed tools by keyword, category, or score |
| `scan_service` | Full AEO audit on any URL |
| `get_service_details` | Detailed scoring breakdown for a scanned service |
| `list_categories` | Browse all tool categories with counts |
| `get_stats` | Aggregate directory statistics |
| `register_service` | Submit a new tool for indexing |
| `clarvia_gate_check` | Pass/fail safety check before calling any tool |
| `clarvia_batch_check` | Batch-check up to 10 URLs at once |
| `clarvia_find_alternatives` | Find higher-rated tools in a category |
| `clarvia_probe` | Live accessibility probe (HTTP, OpenAPI, MCP, agents.json) |
| `clarvia_submit_feedback` | Report tool usage outcome (success/failure/partial) |
| `register_my_setup` | Register your agent's current toolchain for benchmarking |
| `compare_my_setup` | Compare your setup against higher-scored alternatives |
| `recommend_upgrades` | Get personalized tool recommendations |
| `clarvia_report_issue` | Report bugs, features, or security issues |
| `clarvia_list_issues` | List and track CS tickets |

### Installation

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

### Links

- npm: https://www.npmjs.com/package/clarvia-mcp-server
- Website: https://clarvia.art
- GitHub: https://github.com/clarvia-project/scanner
```
