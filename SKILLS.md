# Clarvia Claude Code Skills

Pre-built [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills) that use Clarvia MCP tools to evaluate, compare, and discover AI agent tools directly from your terminal.

## Prerequisites

Add Clarvia as an MCP server in Claude Code:

```bash
claude mcp add clarvia -- npx -y clarvia-mcp-server
```

Or use the remote endpoint (no install):

```bash
claude mcp add clarvia --transport http https://clarvia-api.onrender.com/mcp/
```

## Available Skills

### `/clarvia-scan` — AEO Audit

Scan any tool or MCP server for its AEO (Agent Engine Optimization) score. Returns a full dimension breakdown and actionable recommendations.

**Usage:**
```
/clarvia-scan https://api.stripe.com
/clarvia-scan notion-mcp
```

**What it does:**
1. Runs a full AEO audit via `scan_service` (URL) or `search_services` + `get_service_details` (name)
2. Displays score, agent grade, and per-dimension breakdown
3. If the tool scores below AGENT_FRIENDLY, automatically finds better alternatives

### `/clarvia-compare` — Head-to-Head Comparison

Compare two tools side-by-side across all AEO dimensions.

**Usage:**
```
/clarvia-compare stripe vs square
/clarvia-compare https://api.openai.com, https://api.anthropic.com
```

**What it does:**
1. Fetches AEO scores for both tools
2. Runs `clarvia_batch_check` for direct comparison
3. Presents a dimension-by-dimension table with a winner per category

### `/clarvia-recommend` — Tool Discovery

Get the best tool recommendations for a specific use case, filtered by quality.

**Usage:**
```
/clarvia-recommend payment processing
/clarvia-recommend send emails
/clarvia-recommend database management
```

**What it does:**
1. Searches 15,400+ indexed tools with a minimum score filter
2. Returns top 3 picks with install instructions
3. Includes a quick comparison table

## Installation

### Option A: Copy Skills to Your Project

Copy the `.claude/skills/` directory from this repository into your project:

```bash
# From your project root
mkdir -p .claude/skills
cp path/to/scanner/.claude/skills/clarvia-*.md .claude/skills/
```

### Option B: Symlink (Always Up-to-Date)

```bash
# From your project root
mkdir -p .claude/skills
ln -s /path/to/scanner/.claude/skills/clarvia-scan.md .claude/skills/
ln -s /path/to/scanner/.claude/skills/clarvia-compare.md .claude/skills/
ln -s /path/to/scanner/.claude/skills/clarvia-recommend.md .claude/skills/
```

### Option C: Manual Setup

Create skill files in your project's `.claude/skills/` directory using the templates from `examples/claude-code-skill.md` as a starting point.

## Skill File Format

Each skill is a Markdown file with YAML frontmatter:

```markdown
---
description: Short description shown in skill list
---

Instructions for Claude on how to use the Clarvia MCP tools.
Uses $ARGUMENTS as the user input placeholder.
```

## Related Resources

- [MCP Server README](mcp-server/README.md) — Full list of 16 MCP tools
- [Examples](examples/) — More usage examples and integration patterns
- [API Docs](https://clarvia-api.onrender.com/openapi.json) — REST API reference
