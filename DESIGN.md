# Clarvia — DESIGN.md (Agent-First Edition)

> The trust infrastructure where AI agents discover, evaluate, and select tools.

**Last updated:** 2026-03-30
**Status:** Production (Phase 1 live, Phase 2 in progress)
**Owner:** 상호

---

## 1. What Is Clarvia?

Clarvia is the **credit rating agency for AI agent tools**. Agents query Clarvia before choosing a tool. Tool makers check Clarvia to improve their scores.

**One sentence:** AEO score for every AI tool — agents trust it, tool makers optimize for it.

### Who Uses It

| User | What They Do | How They Connect |
|------|-------------|-----------------|
| **AI Agents** (primary) | Find tools, gate-check quality, compare options, report outcomes | MCP server (16 tools), REST API, .well-known/agents.json |
| **Agent Developers** | Configure tool stacks, evaluate alternatives, monitor quality | REST API, OpenAPI spec, npm package |
| **Tool Makers** | Check scores, get improvement roadmaps, track progress | Web dashboard, badge system, scan API |

### Why It Matters

Agents are making tool selection decisions autonomously. Without a trusted scoring layer:
- Agents pick unreliable tools → fail → lose user trust
- Tool makers have no signal on what "agent-ready" means
- No ecosystem standard for agent compatibility

Clarvia solves this by providing transparent, machine-readable quality scores.

---

## 2. Current State (2026-03-30)

### Live & Working

| Component | URL | Status |
|-----------|-----|--------|
| Backend API | clarvia-api.onrender.com | 27K+ tools, 20+ endpoints |
| Frontend | clarvia.art | Next.js on Vercel |
| MCP Server | npm: clarvia-mcp-server | v1.1.2, 16 tools, 595 weekly downloads |
| Agent Discovery | /.well-known/agents.json | JSON Agents standard |
| OpenAPI Spec | /openapi.json | 109KB, complete |
| Health Check | /health | DB + cache + memory |

### Key Numbers

| Metric | Value |
|--------|-------|
| Tools cataloged | 27,844 (15.2K scanned + 12.6K collected) |
| Categories | 27 + 3 type aliases (mcp, cli, skills) |
| Average AEO score | 38.2 / 100 |
| Max AEO score | 71 / 100 |
| npm weekly downloads | 595 |
| MCP registries listed | 4 (Official, Smithery, Glama, mcp.so) |
| Awesome-list PRs | 25+ open |
| Scheduled automation | 18 active tasks |

---

## 3. Agent Use Cases

### 3.1 Tool Discovery

**"What tool should I use for X?"**

```
Agent → GET /v1/recommend?intent=send+email
     ← [{name: "AWS SES MCP", score: 75, relevance: 0.92}, ...]

Agent → GET /v1/services?q=weather&category=mcp
     ← [{name: "Weather MCP", score: 68, install_hint: "npx -y weather-mcp"}, ...]
```

Endpoints:
- `GET /v1/services?q={query}&category={cat}` — Search + filter
- `GET /v1/recommend?intent={description}` — Smart recommendation by intent
- `GET /v1/leaderboard` — Top-ranked tools
- `GET /v1/categories` — Browse by category
- `GET /v1/feed/scores` — Bulk score feed (paginated)

### 3.2 Tool Evaluation

**"Is this tool safe to use?"**

```
Agent → POST /api/scan {url: "https://github.com/org/tool"}
     ← {score: 54, rating: "Moderate", agent_grade: "AGENT_POSSIBLE",
        dimensions: {api_accessibility: 20, agent_compatibility: 6, ...},
        recommendations: ["Add OpenAPI spec (+5pts)", "Add MCP server (+7pts)"]}
```

Endpoints:
- `POST /api/scan` — Full AEO audit of any URL
- MCP: `clarvia_gate_check` — Pass/fail agent-readiness check
- MCP: `clarvia_batch_check` — Evaluate multiple URLs
- MCP: `clarvia_probe` — Real-time availability check

### 3.3 Tool Comparison

**"Should I use A or B?"**

```
Agent → GET /v1/compare?ids=scn_abc,scn_def
     ← [{name: "Tool A", score: 72}, {name: "Tool B", score: 58}]

Agent → MCP: clarvia_find_alternatives {tool_url: "..."}
     ← [{name: "Better Tool", score: 81, reason: "Higher rate limits"}]
```

Endpoints:
- `GET /v1/compare?ids={a},{b}` — Side-by-side comparison
- MCP: `clarvia_find_alternatives` — Better-scored replacements
- MCP: `compare_my_setup` — Evaluate your entire tool stack

### 3.4 Feedback & Monitoring

**"This tool failed. Let others know."**

```
Agent → MCP: clarvia_submit_feedback {tool: "X", outcome: "failure", reason: "429 rate limit"}
     ← {recorded: true, feedback_id: "fb_123"}
```

Endpoints:
- MCP: `clarvia_submit_feedback` — Report tool usage outcomes
- `GET /v1/history/{slug}/delta` — Score change tracking
- `GET /v1/traffic/stats` — Agent traffic analytics
- `GET /v1/traffic/by-tool/{slug}` — Per-tool agent visits

---

## 4. AEO Scoring System

### Formula

```
AEO Score = API Accessibility (25) + Data Structuring (25) +
            Agent Compatibility (25) + Trust Signals (25)
Total: 100 points
```

### Dimensions

| Dimension | Max | What It Measures |
|-----------|-----|-----------------|
| **API Accessibility** | 25 | Endpoint quality (7), response speed (6), rate limit docs (6), auth docs (3), versioning (1), SDK (1), free tier (1) |
| **Data Structuring** | 25 | Response format, schema consistency, error formatting |
| **Agent Compatibility** | 25 | MCP server (7), robot policy (5), discovery (5), idempotency (3), streaming (3), pagination (2) |
| **Trust Signals** | 25 | Documentation, maintenance activity, security practices |

### Gateway Ratings

| Rating | Score | Meaning |
|--------|-------|---------|
| **Excellent** | 60+ | Production-ready for agents |
| **Strong** | 50-59 | Good with minor gaps |
| **Moderate** | 35-49 | Usable but needs improvement |
| **Basic** | 20-34 | Significant gaps |
| **Low** | <20 | Not agent-ready |

### Agent Grades

| Grade | When Assigned | Agent Behavior |
|-------|--------------|----------------|
| AGENT_NATIVE | Score 80+ | Use autonomously |
| AGENT_FRIENDLY | Score 60-79 | Use with configuration |
| AGENT_POSSIBLE | Score 40-59 | Use as fallback only |
| AGENT_HOSTILE | Score <40 | Avoid |

---

## 5. Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌────────────────┐
│   AI Agents      │────▶│   Clarvia API    │────▶│  Data Store    │
│  (Claude, GPT,   │     │   (FastAPI)      │     │  (Supabase +   │
│   Cursor, etc.)  │     │   Render Starter │     │   JSON files)  │
└──────────────────┘     └────────┬─────────┘     └────────────────┘
        │                         │
        │ MCP                     │
        ▼                         ▼
┌──────────────────┐     ┌──────────────────┐
│  MCP Server      │     │  Scanner Engine  │
│  (npm package)   │     │  (Cron tasks)    │
│  16 tools        │     │  11 crawlers     │
└──────────────────┘     └──────────────────┘
        │
        ▼
┌──────────────────┐
│  Agent Discovery │
│  .well-known/*   │
│  robots.txt      │
│  llms.txt        │
│  openapi.json    │
└──────────────────┘
```

### Tech Stack

| Layer | Choice | Status |
|-------|--------|--------|
| Backend | FastAPI on Render (Starter $7/mo) | Live |
| Frontend | Next.js 16 on Vercel | Live |
| Database | Supabase (analytics) + JSON files (catalog) | Live |
| MCP Server | TypeScript, npm published | Live |
| Scanner | Python, 11 crawlers, 18 scheduled tasks | Live |
| Monitoring | Heartbeat (14min) + Health (6hr) + Telegram alerts | Live |

---

## 6. Integration Points

### REST API

Base URL: `https://clarvia-api.onrender.com`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/services?q=&category=&limit=` | Search & filter tools |
| GET | `/v1/services/{scan_id}` | Tool detail |
| GET | `/v1/recommend?intent=` | Smart recommendation |
| GET | `/v1/leaderboard` | Top-ranked tools |
| GET | `/v1/categories` | Category list with counts |
| GET | `/v1/categories/{slug}` | Category detail |
| GET | `/v1/compare?ids=a,b` | Compare tools |
| GET | `/v1/featured/top` | Featured tools (score 60+) |
| GET | `/v1/feed/scores` | Bulk score feed |
| GET | `/v1/feed/stats` | Ecosystem stats |
| GET | `/v1/stats` | Platform numbers |
| GET | `/v1/history/{slug}` | Scan history |
| GET | `/v1/history/{slug}/delta` | Score changes |
| GET | `/v1/traffic/stats` | Agent traffic summary |
| GET | `/v1/traffic/by-tool/{slug}` | Per-tool traffic |
| POST | `/api/scan` | Run AEO audit |
| GET | `/api/badge/{id}.svg` | Score badge image |
| GET | `/health` | Health check |
| GET | `/openapi.json` | Full API spec |

All `/v1/*` endpoints are also accessible via `/api/v1/*` (307 redirect).

### MCP Server (16 Tools)

Install: `npx -y clarvia-mcp-server`

| Tool | Purpose |
|------|---------|
| `search_services` | Find tools by keyword/category/score |
| `get_service_details` | Detailed tool breakdown |
| `scan_service` | Run AEO audit on any URL |
| `clarvia_gate_check` | Pass/fail agent-readiness |
| `clarvia_batch_check` | Evaluate multiple URLs |
| `clarvia_probe` | Real-time availability check |
| `clarvia_find_alternatives` | Better-scored replacements |
| `clarvia_submit_feedback` | Report usage outcomes |
| `list_categories` | Browse categories |
| `get_stats` | Platform statistics |
| `clarvia_top_picks` | Featured tools |
| `register_service` | Submit new tool |
| `register_my_setup` | Register your tool stack |
| `compare_my_setup` | Compare vs alternatives |
| `recommend_upgrades` | Get upgrade suggestions |
| `clarvia_report_issue` | Report bugs/features |

### Discovery Files

| File | Purpose | Format |
|------|---------|--------|
| `/.well-known/agents.json` | Agent capability manifest | JSON |
| `/robots.txt` | AI crawler allowlist (GPTBot, ClaudeBot, etc.) | Text |
| `/llms.txt` | Agent discovery signal | Text |
| `/openapi.json` | Complete API specification | OpenAPI 3.1 |
| `/sitemap.xml` | 15K+ tool page URLs | XML |

---

## 7. Data Pipeline

### Crawlers (11 sources)

| Source | Type | Schedule |
|--------|------|----------|
| Anthropic MCP | Official registry | Every 2hr |
| Smithery | MCP hosting | Every 2hr |
| Glama | MCP directory | Every 2hr |
| mcp.so | MCP marketplace | Every 2hr |
| PulseMCP | MCP directory | Every 2hr |
| mcpservers.org | Curated list | Every 2hr |
| Awesome lists | GitHub repos | Weekly |
| npm | Package registry | Every 2hr |
| PyPI | Package registry | Every 2hr |
| GitHub comprehensive | Code search | Weekly |
| Skills/CLI | SKILL.md files | Weekly |

### Daily Pipeline

```
06:00  Harvester   → Discover new tools from all sources
06:30  Classifier  → Categorize discovered tools
07:00  Curator     → Quality filter and prioritize
03:17  Rescan v2   → Update top tool scores (time-series)
08:00  Auto-merge  → Merge new tools into catalog
09:00  Dashboard   → Generate status dashboard
```

### Scheduled Automation (18 active)

| Task | Frequency | Purpose |
|------|-----------|---------|
| Heartbeat | 14min | Render sleep prevention |
| Health monitor | 6hr | Full platform check |
| Tool discovery | 2hr | New tool scanning |
| Daily rescan | Daily 3:17AM | Score tracking |
| Weekly crawl | Sunday 4:19AM | Bulk discovery |
| Distribution check | Daily 10:11AM | Registry presence |
| Badge adoption | Tue/Fri | Track badge usage |
| Competitor watch | Monday | Competitive intelligence |
| Morning plan | Daily 9:07AM | Marketing strategy |
| Daily marketing | Daily 9:11AM | 10-channel execution |
| Marketing loop | 30min | Execute → analyze → repeat |
| Marketing monitor | Daily 9:27AM | Channel monitoring |
| Evening digest | Daily 10:12PM | KPI summary → Telegram |
| Evening report | Daily 10:06PM | Performance report → Telegram |
| Platform ops | 6hr | Data + security + health |
| Ops check | 6hr | Cross-service health |
| Score calibration | Sunday | Distribution rebalancing |
| Schema watchdog | Daily 5AM | Data integrity |

---

## 8. Competitive Positioning

### vs Glama (primary competitor)

| Dimension | Glama | Clarvia |
|-----------|-------|---------|
| Coverage | 20K+ MCP only | 27K+ (MCP + API + CLI + Skills) |
| Scoring | A-F grades (opaque) | AEO 0-100 (transparent rubric) |
| Actionability | "You got a C" | "Add .well-known/agents.json +5pts" |
| API | None | Machine-readable REST + MCP |
| Tool author tools | None | Improvement roadmap + badge + history |
| Historical data | None | Daily snapshots (data moat) |
| Agent integration | None | 16 MCP tools + gate-check |

### Data Moat Strategy

Historical score data accumulates daily. After 6 months, no competitor can replicate:
1. **Trend data** — "Tool X improved from 42→71 over 3 months"
2. **Benchmark data** — "Average MCP server scores 38.2, top 10% scores 65+"
3. **Correlation data** — "Score 70+ tools get 3x more agent traffic"
4. **Discovery index** — First to catalog new tools across 11 sources
5. **Feedback data** — Agent success/failure reports per tool

---

## 9. Growth Engine

### Channel 1: Agent Registry Presence (Direct Discovery)

Agents find Clarvia when browsing MCP registries:
- Official MCP Registry ✅
- Smithery ✅
- Glama ✅
- mcp.so ✅
- npm (clarvia-mcp-server) ✅

### Channel 2: Ecosystem Badging (Viral Loop)

Tool authors embed Clarvia badges in READMEs:
```markdown
![Clarvia AEO Score](https://clarvia-api.onrender.com/api/badge/{slug}.svg)
```
- Agents see badges → learn about Clarvia → start using API
- Target: 500+ tools with badges by Month 6

### Channel 3: Framework Integration (Lock-in)

Embed AEO scores directly into agent frameworks:
- LangChain tool registry → AEO score in metadata
- CrewAI tool selection → gate-check before activation
- AutoGen tool library → score-based ranking

One framework integration = permanent distribution channel.

### Agent-Only Marketing (No human social media)

All marketing targets where agents discover tools:
1. MCP registries (presence + optimization)
2. npm/PyPI (package SEO)
3. GitHub (awesome-lists, topic tags)
4. .well-known standards
5. OpenAPI spec
6. Framework integrations
7. Developer docs (tool authors)
8. Sitemap (AI crawler indexing)

---

## 10. Success Metrics

### North Star: Daily Active Agents

| Milestone | Target | Timeline |
|-----------|--------|----------|
| Infrastructure | 0 errors for 24hr | Week 1 ✅ |
| MVP | 50 daily agents | Month 1 |
| Traction | 500 daily agents | Month 3 |
| Scale | 5K daily agents | Month 6 |
| Standard | 100K daily agents | Year 1 |
| North Star | 1M daily agents | Year 3 |

### Tracking Dashboard (Telegram Daily)

Every evening at 10PM:
- **Tool count** (with daily delta)
- **API usage** (total calls + by agent type)
- **Website traffic** (visits)
- **Marketing activities** (count + success rate)
- **npm downloads** (daily + weekly)
- **Uptime** (heartbeat failures)
- **Discovery runs** (new tools found)

### Leading Indicators

| Metric | Current | Month 1 Target |
|--------|---------|----------------|
| API calls/day | ~200 | 1,000 |
| Unique agents/day | ~1 | 50 |
| npm downloads/week | 595 | 1,000 |
| Tools with badges | 10 | 100 |
| Awesome-list PRs merged | 0 | 5 |
| Tool authors aware | <100 | 500 |
| Framework integrations | 0 | 1 (started) |

---

## 11. Verification Scenarios

### How to verify "Clarvia is working"

**Agent Discovery Test:**
```bash
# Agent searches for a tool
curl "https://clarvia-api.onrender.com/v1/services?q=weather&limit=3"
# Expected: 3 tools with names, scores, install hints

# Agent gets recommendation
curl "https://clarvia-api.onrender.com/v1/recommend?intent=send+email"
# Expected: ranked tools with relevance scores
```

**Agent Evaluation Test:**
```bash
# Agent scans unknown tool
curl -X POST "https://clarvia-api.onrender.com/api/scan" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://github.com/modelcontextprotocol/servers"}'
# Expected: score, rating, dimensions, recommendations
```

**MCP Test:**
```bash
# Agent uses MCP server
npx -y clarvia-mcp-server
# Then: search_services({query: "database"})
# Expected: ranked list of database tools
```

**Health Test:**
```bash
curl "https://clarvia-api.onrender.com/health"
# Expected: {status: "healthy", checks: {cache: "ok", database: "ok", memory: "ok"}}
```

---

## 12. Not in Scope

Explicitly deferred to prevent scope creep:

- User accounts / authentication (except API keys, Phase 2)
- Payment system (Stripe exists but not active)
- CI/CD integration for tool makers
- Authenticated API scanning
- Real-time WebSocket updates
- Mobile app
- Multi-language support
- Custom scoring weights per customer

---

## 13. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scoring credibility questioned | Agents stop trusting scores | Transparent rubric, public methodology, feedback loop |
| Glama adds API | Direct competition | Data moat (history), cross-type coverage, actionability |
| No agent traffic | Product irrelevant | Framework integration, MCP registry presence, badge viral loop |
| Render cold starts | API too slow | Heartbeat every 14min, background data loading |
| Data staleness | Scores become inaccurate | Daily rescan, 2hr discovery, weekly comprehensive crawl |
