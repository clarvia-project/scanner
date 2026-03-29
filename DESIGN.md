# Clarvia — DESIGN.md

> The standard infrastructure where AI agents discover, evaluate, and pay for tools.

**Last updated:** 2026-03-29
**Status:** Pre-production redesign
**Owner:** 상호

---

## 1. What Is Clarvia?

Clarvia scores and catalogs AI agent tools (MCP servers, skills, CLIs) so that **agents can programmatically find the best tools** and **tool makers can optimize their products**.

Think of it as **"the credit rating agency for AI tools"** — agents check Clarvia before choosing a tool, tool makers check Clarvia to improve.

### Core Value
- **For agents:** Machine-readable API to discover and evaluate tools by quality score (AEO score)
- **For tool makers:** Dashboard showing how their tools rank, what to improve, competitive intel
- **For humans:** Curated catalog to browse and compare AI tools

---

## 2. What Exists Today

### Working
- FastAPI backend with scanner, scoring engine, routes
- Next.js frontend (partially built)
- MCP server (published to Smithery)
- ~59 scanned tool results in JSON
- Scoring algorithm (AEO score)
- Data collection scripts (scan_batch, scan_daemon, rescan_all)

### Not Working
- Backend not deployed (no live API)
- Frontend not connected to live backend
- No health check endpoint responding
- No automated scanning running
- No real agent traffic

---

## 3. MVP Scope (Minimum to call it "live")

### Must Have (Phase 1)
1. **Maximum tool coverage** — Every MCP server from every registry (Smithery, PulseMCP, Glama, npm, PyPI, GitHub). Target: 1,000+ tools. More is better.
2. **Accurate AEO scores** — Scoring algorithm validated against manual review. Score accuracy > coverage count.
3. **API that responds** — `/health`, `/api/v1/tools`, `/api/v1/tools/{id}`, `/api/v1/search`
4. **MCP server live on Smithery** — So agents can actually use Clarvia
5. **Frontend showing the catalog** — Browse, search, filter, tool detail page
6. **Daily auto-rescan** — Scores stay fresh without manual work

### Priority Order
Data coverage & accuracy first → API & MCP reliability → Frontend polish.
An ugly site with 2,000 accurate tool scores beats a beautiful site with 100.

### Not in Phase 1
- User accounts / auth
- Tool maker dashboard
- Payment / subscription
- Comparison tool
- Historical trend data
- Agent traffic analytics

---

## 4. Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│   Frontend   │────▶│   Backend    │────▶│   Data Store   │
│  (Next.js)   │     │  (FastAPI)   │     │  (PostgreSQL)  │
│  Vercel      │     │  Render      │     │  Render PG     │
└─────────────┘     └──────┬───────┘     └────────────────┘
                           │
                    ┌──────┴───────┐
                    │  MCP Server  │
                    │  (Smithery)  │
                    └──────────────┘
                           │
                    ┌──────┴───────┐
                    │  Scanner     │
                    │  (Cron job)  │
                    └──────────────┘
```

### Tech Stack
| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | Next.js on Vercel | Already built, free hosting, fast |
| Backend | FastAPI on Render | Already built, Starter plan paid |
| Database | PostgreSQL on Render | Structured data, free tier available |
| MCP Server | Node.js on Smithery | Already published |
| Scanner | Render Cron Job | Automated daily scanning |

### Key Decision: JSON files → PostgreSQL
Current data is in JSON files. Moving to PostgreSQL because:
- Query performance at 500+ tools
- Concurrent access (API + scanner)
- Structured relationships (tools, scores, scan history)
- Render offers free PostgreSQL

---

## 5. Data Model

### `tools` table
```sql
CREATE TABLE tools (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT NOT NULL,
  slug          TEXT UNIQUE NOT NULL,
  category      TEXT NOT NULL,        -- mcp_server, skill, cli
  source_url    TEXT,
  description   TEXT,
  author        TEXT,
  registry      TEXT,                 -- smithery, pulsemcp, npm, etc.
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### `scores` table
```sql
CREATE TABLE scores (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_id       UUID REFERENCES tools(id),
  aeo_score     NUMERIC(4,1),        -- 0.0 to 100.0
  scan_data     JSONB,               -- Full scan result
  scanned_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_scores_tool_id ON scores(tool_id);
CREATE INDEX idx_scores_scanned_at ON scores(scanned_at);
```

### `daily_snapshots` table (for trends)
```sql
CREATE TABLE daily_snapshots (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_id       UUID REFERENCES tools(id),
  aeo_score     NUMERIC(4,1),
  snapshot_date DATE NOT NULL,
  UNIQUE(tool_id, snapshot_date)
);
```

---

## 6. API Endpoints

### Public API (v1)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/tools` | List tools (paginated, filterable) |
| GET | `/api/v1/tools/{slug}` | Tool detail + latest score |
| GET | `/api/v1/search?q=` | Full-text search |
| GET | `/api/v1/categories` | List categories with counts |
| GET | `/api/v1/stats` | Total tools, avg score, last scan |

### MCP Server Interface
The MCP server wraps these same endpoints for agent consumption.
Tools exposed: `search_tools`, `get_tool_detail`, `get_recommendations`, `compare_tools`

---

## 7. Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Home | `/` | Hero + search + top tools + stats |
| Catalog | `/tools` | Browse all tools, filter, sort |
| Detail | `/tools/[slug]` | Tool info, AEO score breakdown, badge |
| Compare | `/compare` | Side-by-side (Phase 2) |
| About | `/about` | What is AEO, methodology |

### Design Principles
- Clean, minimal (variant.com style)
- Dark mode default
- Mobile responsive
- Score badge prominently displayed on every tool card

---

## 8. Deployment Plan

### Step 1: Database
- Create Render PostgreSQL instance
- Run schema migration
- Import existing JSON data into PostgreSQL

### Step 2: Backend
- Update FastAPI to read from PostgreSQL (not JSON files)
- Add `/health` endpoint that checks DB connection
- Deploy to Render, verify health check responds

### Step 3: Scanner
- Create Render Cron Job for daily scanning
- Scanner writes results to PostgreSQL
- Verify first automated scan completes

### Step 4: Frontend
- Connect to live backend API
- Deploy to Vercel
- Verify pages load with real data

### Step 5: MCP Server
- Update to point to live API
- Republish on Smithery
- Verify agent can query through MCP

### Step 6: Verification
- All endpoints responding
- 500+ tools in database
- Daily scan running
- Frontend showing real data
- MCP server queryable by agents
- Health monitoring active

---

## 9. Success Criteria

Clarvia is "live" when ALL of these are true:
- [ ] `/health` returns 200 with DB status
- [ ] `/api/v1/tools` returns 1,000+ tools
- [ ] AEO score accuracy validated (sample 50 tools, manual review matches ±10%)
- [ ] Every tool has an AEO score
- [ ] Frontend loads at clarvia.com with real data
- [ ] MCP server responds on Smithery
- [ ] Daily auto-scan runs without manual intervention
- [ ] Health check alerts if anything goes down

---

## 10. What This Does NOT Include

To prevent scope creep, these are explicitly deferred:
- User auth / accounts
- Tool maker dashboard
- Payment system
- Email notifications
- Social features
- Mobile app
- Multi-language support
