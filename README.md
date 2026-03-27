<div align="center">

<img src="docs/images/hero-banner.png" alt="Clarvia — AEO Scanner for AI Agent Tools" width="720" />

# Clarvia

**The AEO (Agent Engine Optimization) Standard for AI Agent Tools**

Score, discover, and validate **15,400+ AI agent tools** for quality, accessibility, and agent-readiness.

[![npm version](https://img.shields.io/npm/v/clarvia-mcp-server?color=cb3837&label=npm)](https://www.npmjs.com/package/clarvia-mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/clarvia-mcp-server?color=blue)](https://www.npmjs.com/package/clarvia-mcp-server)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![MCP Tools](https://img.shields.io/badge/MCP_tools-16-6366f1)](https://clarvia.art)
[![Python Tools](https://img.shields.io/badge/Python_tools-24-3776AB)](#python-mcp-server)
[![Services Indexed](https://img.shields.io/badge/services_indexed-15%2C400%2B-22c55e)](#)
[![API Endpoints](https://img.shields.io/badge/API_endpoints-110%2B-orange)](#rest-api)
[![Website](https://img.shields.io/badge/web-clarvia.art-000?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgZmlsbD0id2hpdGUiIHZpZXdCb3g9IjAgMCAxNiAxNiI+PGNpcmNsZSBjeD0iOCIgY3k9IjgiIHI9IjgiLz48L3N2Zz4=)](https://clarvia.art)

[Website](https://clarvia.art) · [npm](https://www.npmjs.com/package/clarvia-mcp-server) · [API Docs](https://clarvia-api.onrender.com/openapi.json) · [Leaderboard](https://clarvia.art/leaderboard)

</div>

---

## Install (one command)

```bash
npx -y clarvia-mcp-server
```

Or add to any MCP client config:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["-y", "clarvia-mcp-server"]
    }
  }
}
```

**No install needed?** Use the remote endpoint directly:
```
https://clarvia-api.onrender.com/mcp/
```

---

## What is Clarvia?

Clarvia assigns an **AEO Score (0-100)** to any AI tool, API, or MCP server — measuring how easily AI agents can discover, integrate, and trust it. Think of it as **"Lighthouse for AI agent tools."**

**4 scoring dimensions** (25 points each):

| Dimension | What it measures |
|---|---|
| **API Accessibility** | Endpoint existence, response speed, auth documentation |
| **Data Structuring** | Schema definition, pricing clarity, error structure |
| **Agent Compatibility** | MCP server presence, robots.txt, sitemap/discovery |
| **Trust Signals** | Uptime, documentation quality, update frequency |

Plus an optional **Onchain Bonus (+25)** for web3 services.

---

## For Agents

> *Before calling any external tool, check if it's agent-ready.*

Clarvia gives your agent a **quality gate** for tool selection:

```
Agent workflow:
  Need a payment API?
  -> search_services("payment API")
  -> clarvia_gate_check(top_result)
  -> PASS? Use it. FAIL? clarvia_find_alternatives("payment")
  -> After use: clarvia_submit_feedback(result)
```

**Agent Grades:**
- `AGENT_NATIVE` (80+) — Built for agents, full MCP/OpenAPI support
- `AGENT_FRIENDLY` (60-79) — Good API, minor gaps
- `AGENT_POSSIBLE` (40-59) — Usable with effort
- `AGENT_HOSTILE` (0-39) — Avoid for autonomous use

---

## For Tool Makers

> *See your tool the way AI agents see it.*

- **Your AEO score** — how agent-ready your tool is today
- **Specific gaps** — missing OpenAPI spec? No MCP server? Poor error messages?
- **Category ranking** — how you compare to alternatives
- **Actionable fixes** — each dimension tells you exactly what to improve

---

## Quick Start by Framework

<details>
<summary><strong>Claude Desktop</strong></summary>

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["-y", "clarvia-mcp-server"]
    }
  }
}
```
</details>

<details>
<summary><strong>Claude Code</strong></summary>

```bash
claude mcp add clarvia -- npx -y clarvia-mcp-server
```
</details>

<details>
<summary><strong>Cursor</strong></summary>

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["-y", "clarvia-mcp-server"]
    }
  }
}
```
</details>

<details>
<summary><strong>Windsurf</strong></summary>

Add to `.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["-y", "clarvia-mcp-server"]
    }
  }
}
```
</details>

<details>
<summary><strong>Cline</strong></summary>

Add to `.cline/mcp.json` or VS Code settings:

```json
{
  "mcpServers": {
    "clarvia": {
      "command": "npx",
      "args": ["-y", "clarvia-mcp-server"]
    }
  }
}
```
</details>

<details>
<summary><strong>Continue.dev</strong></summary>

Add to `~/.continue/config.json`:

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "stdio",
          "command": "npx",
          "args": ["-y", "clarvia-mcp-server"]
        }
      }
    ]
  }
}
```
</details>

<details>
<summary><strong>Remote Endpoint (any MCP client)</strong></summary>

```
https://clarvia-api.onrender.com/mcp/
```

No local installation required. Works with any MCP client supporting Streamable HTTP transport.
</details>

See [examples/](examples/) for ready-to-copy config files.

---

## MCP Tools — Node.js Server (16 tools)

### Discovery & Search

| Tool | Description |
|------|-------------|
| `search_services` | Search 15,400+ indexed AI tools by keyword, category, or minimum AEO score |
| `list_categories` | List all tool categories with service counts |
| `get_stats` | Platform-wide statistics — total services, score distributions |

### Scanning & Evaluation

| Tool | Description |
|------|-------------|
| `scan_service` | Full AEO audit on any URL — agent discoverability, API quality, docs, MCP readiness |
| `get_service_details` | Detailed scoring breakdown for a scanned service |
| `register_service` | Submit a new service for indexing and scoring |

### Agent Safety & Gating

| Tool | Description |
|------|-------------|
| `clarvia_gate_check` | Pass/fail safety check — agent grade with boolean result |
| `clarvia_batch_check` | Batch-check up to 10 URLs in one call |
| `clarvia_find_alternatives` | Find higher-rated alternatives in a category |
| `clarvia_probe` | Live probe — HTTP reachability, latency, OpenAPI, MCP, agents.json |

### Setup Management

| Tool | Description |
|------|-------------|
| `register_my_setup` | Register your tool setup for AEO scoring per tool |
| `compare_my_setup` | Compare your setup against higher-scored alternatives |
| `recommend_upgrades` | Personalized upgrade recommendations |

### Feedback & Support

| Tool | Description |
|------|-------------|
| `clarvia_submit_feedback` | Report tool usage outcomes for reliability data |
| `clarvia_report_issue` | Report bugs, request features, flag issues |
| `clarvia_list_issues` | List existing tickets and known issues |

---

## Python MCP Server (24 tools)

The backend also runs a Python-based MCP server with extended capabilities:

| Tool | Description |
|------|-------------|
| `search_services` | Search indexed tools with advanced filters |
| `scan_service` | Full AEO audit |
| `get_service_details` | Detailed scoring breakdown |
| `list_categories` | Browse categories |
| `get_stats` | Platform statistics |
| `register_service` | Submit new service |
| `clarvia_gate_check` | Pass/fail safety gate |
| `clarvia_batch_check` | Batch URL checking |
| `clarvia_find_alternatives` | Category alternatives |
| `clarvia_probe` | Live accessibility probe |
| `clarvia_submit_feedback` | Report usage outcomes |
| `clarvia_rescan` | Trigger rescan of a profiled service |
| `clarvia_get_rank` | Get category ranking for a service |
| `clarvia_get_feedback` | Get community feedback for a service |
| `clarvia_trending` | Trending tools by score changes |
| `clarvia_similar` | Find similar tools to a given service |
| `clarvia_audit` | Audit npm/pip package dependencies |
| `clarvia_featured` | Get featured/curated tools |
| `clarvia_demand` | See most-requested tool categories |

Access via remote endpoint: `https://clarvia-api.onrender.com/mcp/`

---

## Claude Code Skills

Pre-built skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that use Clarvia MCP tools:

| Skill | Command | Description |
|-------|---------|-------------|
| **Scan** | `/clarvia-scan <url-or-name>` | Run a full AEO audit on any tool |
| **Compare** | `/clarvia-compare <tool-A> vs <tool-B>` | Head-to-head dimension comparison |
| **Recommend** | `/clarvia-recommend <use-case>` | Get top tool picks for a use case |

**Quick setup:**
```bash
claude mcp add clarvia -- npx -y clarvia-mcp-server
cp .claude/skills/clarvia-*.md /your/project/.claude/skills/
```

See [SKILLS.md](SKILLS.md) for full installation and usage details.

---

## REST API (110+ endpoints)

Full OpenAPI spec: [`/openapi.json`](https://clarvia-api.onrender.com/openapi.json)

Key endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/services` | Search and filter services |
| `GET` | `/v1/search` | Full-text search |
| `GET` | `/v1/score` | Quick score lookup |
| `GET` | `/v1/leaderboard` | Top-scored services |
| `GET` | `/v1/categories` | Browse categories |
| `POST` | `/v1/audit` | Run AEO audit |
| `GET` | `/v1/recommend` | Intent-based recommendations |
| `GET` | `/v1/similar/{id}` | Find similar tools |
| `GET` | `/v1/trending` | Trending services |
| `GET` | `/v1/featured` | Curated picks |
| `GET` | `/v1/stats` | Platform statistics |
| `GET` | `/v1/compare` | Compare up to 4 tools |
| `POST` | `/v1/profiles` | Create service profile |
| `GET` | `/v1/demand` | Most-demanded categories |
| `GET` | `/v1/feed/registry` | Machine-readable feed for registries |

Rate limits: **10 scans/hour** (free) · **100/hour** (with `X-API-Key`)

---

## Agent Discovery Endpoints

Clarvia is designed to be discovered by AI agents:

| Endpoint | URL |
|----------|-----|
| OpenAPI Spec | `https://clarvia-api.onrender.com/openapi.json` |
| agents.json | `https://clarvia.art/.well-known/agents.json` |
| llms.txt | `https://clarvia.art/llms.txt` |
| llms-full.txt | `https://clarvia.art/llms-full.txt` |
| robots.txt | `https://clarvia.art/robots.txt` |
| Sitemap | `https://clarvia.art/sitemap.xml` |
| MCP Endpoint | `https://clarvia-api.onrender.com/mcp/` |

---

## Architecture

```
scanner/
  backend/           # FastAPI (Python 3.12+) — 110+ API endpoints + MCP server
    app/
      checks/        # 13 scoring sub-factors
      routes/        # REST API endpoints
      services/      # Supabase, PDF generation, enrichment
      mcp_server.py  # Python MCP server (24 tools)
  frontend/          # Next.js + Tailwind — clarvia.art
  mcp-server/        # Node.js MCP server (TypeScript, 16 tools)
  cli/               # CLI scanner tool
  examples/          # Framework integration configs
  github-action/     # GitHub Actions for CI/CD AEO checks
```

## Development

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# MCP Server
cd mcp-server && npm install && npm run dev

# Docker (full stack)
docker compose up --build
```

---

## Integrations

| Platform | Type | Link |
|----------|------|------|
| npm | MCP Server | [clarvia-mcp-server](https://www.npmjs.com/package/clarvia-mcp-server) |
| PyPI | LangChain integration | [clarvia-langchain](https://pypi.org/project/clarvia-langchain/) |
| GitHub Actions | CI/CD AEO check | [github-action/](github-action/) |
| Smithery | MCP Registry | [smithery.yaml](mcp-server/smithery.yaml) |
| MCP Registry | Official registry | `io.github.digitamaz/clarvia` |
| Glama.ai | MCP Directory | [glama.ai/mcp/servers](https://glama.ai/mcp/servers) |
| mcp.so | MCP Directory | [mcp.so](https://mcp.so) |

---

## Links

- **Website**: [clarvia.art](https://clarvia.art)
- **npm**: [clarvia-mcp-server](https://www.npmjs.com/package/clarvia-mcp-server)
- **PyPI**: [clarvia-langchain](https://pypi.org/project/clarvia-langchain/)
- **API**: [clarvia-api.onrender.com](https://clarvia-api.onrender.com/openapi.json)
- **MCP Registry**: `io.github.digitamaz/clarvia`
- **Remote MCP**: `https://clarvia-api.onrender.com/mcp/`

## License

[MIT](LICENSE)
