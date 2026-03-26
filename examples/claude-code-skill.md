# Clarvia as a Claude Code Skill

## Quick Setup

Add Clarvia as an MCP server in Claude Code:

```bash
claude mcp add clarvia -- npx -y clarvia-mcp-server
```

## Custom Slash Command (Skill)

Create a file at `.claude/commands/gate-check.md` in your project:

```markdown
---
description: Gate-check a tool URL before using it
---

Use the clarvia_gate_check tool to verify the service at $ARGUMENTS meets the AGENT_FRIENDLY threshold.

If it passes, report the score and grade.
If it fails, use clarvia_find_alternatives to suggest better options in the same category.
```

### Usage

```
/gate-check https://api.example.com
```

## More Skill Examples

### Scan a service

Create `.claude/commands/scan.md`:

```markdown
---
description: Run a full AEO audit on a URL
---

Use the scan_service tool to audit $ARGUMENTS for agent-readiness.
Summarize the score breakdown and highlight areas for improvement.
```

### Find best tools in a category

Create `.claude/commands/find-tools.md`:

```markdown
---
description: Find the best AI agent tools in a category
---

Use search_services to find tools in the "$ARGUMENTS" category with min_score 70.
Present results as a ranked table with name, score, and description.
```

### Audit your toolchain

Create `.claude/commands/audit-setup.md`:

```markdown
---
description: Audit your current MCP server setup
---

1. Use register_my_setup with the MCP servers currently configured in this project
2. Use compare_my_setup with the returned setup_id
3. Use recommend_upgrades to suggest improvements
4. Present a summary table showing current tools, their scores, and recommended upgrades
```

## Remote Endpoint (No Install)

If you prefer not to install anything locally, use the remote MCP endpoint:

```bash
claude mcp add clarvia --transport http https://clarvia-api.onrender.com/mcp/
```
