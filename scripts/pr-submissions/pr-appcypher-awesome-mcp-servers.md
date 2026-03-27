# PR: Add Clarvia to appcypher/awesome-mcp-servers

## Target repo
https://github.com/appcypher/awesome-mcp-servers

## Target section
**## 🤝 AI Services** (alphabetically: between "Chroma Package Search" and "Chronulus AI" — actually between "Clarvia" and "Comet Opik" under C)

Actually the best fit is **## 💻 Development Tools** (tool validation/discovery for developers building agent systems).
Second option: **## 🔗 Aggregators** (multi-tool meta-server).

## Entry to add (Development Tools section, alphabetically under C)

```markdown
- <img src="https://clarvia.art/favicon.ico" height="14"/> [Clarvia](https://github.com/clarvia-project/scanner/tree/main/mcp-server) - Before calling any external API or MCP, use Clarvia to check if it's agent-ready. Search 15,400+ indexed tools, gate-check agent-compatibility scores (AGENT_NATIVE / AGENT_FRIENDLY / AGENT_POSSIBLE / AGENT_HOSTILE), find alternatives, and audit dependencies.
```

## PR Title
feat: add Clarvia MCP server (agent-ready tool discovery and gate-checking)

## PR Body
```
## Description

This PR adds [Clarvia](https://clarvia.art) to the Development Tools section.

Clarvia is an MCP server for AI agent tool validation and discovery. Before calling any external API or MCP server, agents can use `clarvia_gate_check` to verify agent-readiness, get a standardized grade, and automatically receive alternatives if the service doesn't meet the threshold.

## Details

- **npm**: `npx -y clarvia-mcp-server`
- **Remote MCP (Streamable HTTP)**: `https://clarvia-api.onrender.com/mcp/`
- **Catalog**: 15,400+ indexed tools (MCP servers, APIs, CLIs, Skills)
- **Key tools**: `clarvia_gate_check`, `search_services`, `clarvia_batch_check`, `clarvia_find_alternatives`, `clarvia_probe`
- **License**: MIT
- **Source**: https://github.com/clarvia-project/scanner/tree/main/mcp-server

## Checklist
- [x] Added alphabetically within the section
- [x] Entry follows existing format with favicon img tag
- [x] Link goes to the specific MCP server subdirectory in the repo
- [x] Description is concise and useful
```

## Notes
- Alphabetical position under "C": after "Chroma Package Search", before "CentralMind/Gateway"
- Wait, CentralMind starts with C too. Sort: C-e (Central) < C-h (Chroma) < C-l (Clarvia) < C-o (Comet)
- So insert between "Chroma Package Search" and "Comet Opik"
