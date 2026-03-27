# Clarvia Automation System — Full Design

**Version**: 2.0 (2026-03-27)
**Status**: Production — Orchestrator running (PID 35633)

---

## Architecture Overview

Every automation task that runs on Clarvia **accumulates data that becomes the moat**.
The compounding effect: more scans → more historical data → no competitor can replicate retroactively.

```
                    ┌─────────────────────────────────┐
                    │     Orchestrator (cron daemon)   │
                    │     PID: 35633, --tick 30        │
                    └──────────────┬──────────────────┘
                                   │
           ┌───────────────────────┼─────────────────────────┐
           │                       │                         │
    ┌──────▼──────┐        ┌───────▼──────┐        ┌────────▼──────┐
    │  HARVESTER  │        │  CALIBRATOR  │        │  REPLICATOR   │
    │  (data in)  │        │  (quality)   │        │  (marketing)  │
    └──────┬──────┘        └───────┬──────┘        └────────┬──────┘
           │                       │                         │
    ┌──────▼──────────────────────▼─────────────────────────▼──────┐
    │                    Supabase (single source of truth)          │
    │                 15,410+ tools  |  historical scan data        │
    └────────────────────────────────────────────────────────────────┘
```

---

## The Moat Compounding Loop

**The key insight**: Every automation run deepens the moat. This is not just ops — this is the product.

```
Daily scans run → historical trend data accumulated (moat layer 1)
    ↓
Agent traffic identified → usage pattern data (moat layer 2)
    ↓
Tool authors improve scores → author relationship data (moat layer 3)
    ↓
More tools scored → broader coverage → more developers trust Clarvia (moat layer 4)
    ↓
Competitors cannot replicate 6+ months of accumulated data retroactively
```

**Rule**: Every automation task must produce data that goes into Supabase.
In-memory only = data lost on restart = moat weakens.

---

## Current Task Inventory (21 total)

### Tier 1: Data Collection (MOAT CORE)

| Task | Schedule | Script | Purpose | Moat Contribution |
|------|----------|--------|---------|-------------------|
| `harvester` | 6:00am daily | `automation/harvester.py` | Discover new tools from GitHub/npm/PyPI/MCP | New tool coverage |
| `classifier` | 6:30am daily | `automation/classifier.py` | Auto-classify discovered tools | Data quality |
| `data_auditor` | 7:00am daily | `automation/data_auditor.py --fix` | Fix data quality issues | Schema consistency |
| `auto_merge` | 8:00am daily | `automation/auto_merge_and_deploy.py` | Merge new tools into catalog | Catalog freshness |
| `dead_link_check` | Sun 4:00am | `automation/dead_link_cleaner.py` | Remove broken tools | Trust signals |

### Tier 2: Quality & Calibration (SCORE CREDIBILITY)

| Task | Schedule | Script | Purpose | Moat Contribution |
|------|----------|--------|---------|-------------------|
| `score_calibration` | Sun 11:00am | `automation/score_calibration.py` | Detect + alert score distribution drift | Scoring credibility |
| `self_healer` | Every 6h | `automation/self_healer.py` | Auto-fix known data issues | Data reliability |
| `schema_watchdog` | 5:00am daily | `automation/schema_watchdog.py` | Validate data schema consistency | Data integrity |
| `curator` | 7:30am daily | `automation/curator.py` | Curate top tools, surface quality | Editorial signal |
| `self_improvement` | Sun noon | `automation/self_improver.py` | Analyze scoring gaps, improve rubric | Algorithm quality |

### Tier 3: Monitoring & Reporting (OPERATIONS)

| Task | Schedule | Script | Purpose | Moat Contribution |
|------|----------|--------|---------|-------------------|
| `healthcheck` | Every 5min | `scripts/healthcheck.py` | Monitor backend/frontend uptime | Reliability data |
| `error_monitor` | Every 5min | `scripts/error_monitor.py` | Detect + alert on errors | SLA tracking |
| `backup` | 3:00am daily | `scripts/backup.py` | Backup all data | Data safety |
| `daily_report` | 10:00pm daily | `automation/daily_report.py` | Telegram daily ops report | Visibility |
| `weekly_report` | Mon 10:00am | `automation/score_reporter.py` | Weekly score changes report | Trend tracking |
| `dashboard` | Hourly | `automation/dashboard_generator.py` | Update metrics dashboard | KPI visibility |

### Tier 4: Marketing (DISTRIBUTION — Agent-only)

| Task | Schedule | Script | Purpose | Moat Contribution |
|------|----------|--------|---------|-------------------|
| `marketing_automation` | 9:00am daily | `automation/marketing_automation.py` | Check MCP registries, npm, PRs, API health | Distribution tracking |
| `sitemap_refresh` | Mon 10:00am | `automation/sitemap_refresh.py` | Rebuild XML sitemaps, ping Google/Bing | SEO coverage |
| `integration_verify` | 8:00am daily | `automation/integration_verifier.py` | Verify external integrations working | Trust maintenance |
| `onboarding` | Every 30min | `automation/onboarding.py` | Process new tool submissions | Catalog growth |
| `feedback_engine` | 2:00am daily | `automation/feedback_engine.py` | Process feedback, update scores | Quality signals |

---

## Moat Data Architecture

### Layer 1: Historical Scan Data (strongest moat)

Every tool scan is stored with a timestamp. After 6 months:
- "Is this tool improving or decaying?" — no competitor can answer without 6 months of data
- Score trend charts per tool (planned: `/tool/{id}/history`)
- Velocity metrics: how fast is the ecosystem improving?

**Storage**: Supabase `scans` table, append-only.
**Accumulation rate**: ~500-1000 scans/day via harvester pipeline.

### Layer 2: Agent Usage Patterns (emerging moat)

Every API request is now tagged with agent type (claude, openai, cursor, langchain, etc.)
via `AnalyticsMiddleware._identify_agent_traffic()`.

This data answers: "Which agent systems are using which tools most frequently?"

**Storage**: JSONL analytics logs (local) + Supabase `api_events` (planned).
**Current status**: Identification working, Supabase persistence pending (requires env var setup).

### Layer 3: Tool Author Relationships (relationship moat)

When tool authors claim their listing and optimize based on Clarvia guidance,
they become Clarvia advocates. They put "AEO Score: X/100" in their READMEs.

**Current status**: Tool claim system not yet built (Month 2 priority).
**Trigger**: Outreach to top 200 MCP authors (상호's action item).

### Layer 4: Coverage Breadth (defensibility)

15,410 tools across 5 types (MCP, API, CLI, Skill, Connector).
Glama: MCP-only. mcp.so: MCP-only. Clarvia: ALL types.

Cross-type coverage becomes the moat when agents need to choose between
an MCP server and a direct API for the same task.

---

## Orchestrator Operations

### Start / Stop

```bash
# Start (already running as of 2026-03-27)
cd /Users/sangho/클로드\ 코드/scanner
python3 scripts/automation/orchestrator.py --tick 30 &

# Check status
ps aux | grep orchestrator

# Stop gracefully
kill -TERM $(pgrep -f "orchestrator.py")
```

### Manual Task Execution

```bash
# Run a specific task immediately
cd /Users/sangho/클로드\ 코드/scanner
python3 scripts/automation/harvester.py --dry-run
python3 scripts/automation/score_calibration.py --dry-run --rescore-top 100
python3 scripts/automation/marketing_automation.py --dry-run
python3 scripts/automation/sitemap_refresh.py --dry-run
```

### Logs

```
data/automation.log         — orchestrator execution log
data/marketing_automation.jsonl — marketing task history
data/reports/              — daily/weekly/calibration reports
data/harvester/            — discovery data from crawlers
```

---

## Critical Known Issues

### Issue 1: Rating System Inconsistency (IMMEDIATE FIX NEEDED)

Two scoring systems with different rating labels:

| Rating | scanner.py threshold | tool_scorer.py threshold |
|--------|---------------------|--------------------------|
| Exceptional | 90+ | N/A |
| Excellent | N/A | 80+ |
| Strong | 75+ | 60+ |
| Moderate | 60+ | 35+ |
| Basic | 40+ | 20+ |
| Low | <40 | <20 |

**Impact**: 0% "Excellent" in catalog (they're labeled "Strong" instead).
This confuses the score_calibration alerts and misleads developers.

**Fix**: Unify both systems to use the same thresholds and label names.
Recommended target: Exceptional(90+) / Excellent(80+) / Strong(65+) / Moderate(45+) / Basic(25+) / Low(<25)

**Owner**: Backend engineer (estimated 2 hours).

### Issue 2: Supabase Not Configured on Render (BLOCKER)

Backend health shows `"database": "not_configured"`.
All agent traffic data, scan history, and analytics are lost on Render restart.

**Fix**: See FOUNDER-ACTION-ITEMS.md — requires Render environment variable setup.

### Issue 3: api.clarvia.art SSL Failure

Custom domain SSL handshake fails. All agent SDK users must use
`clarvia-api.onrender.com` directly.

**Fix**: See FOUNDER-ACTION-ITEMS.md — requires Render SSL configuration.

---

## Automation Quality Standards

Every automation script must:
1. Accept `--dry-run` flag (no writes, no external calls that have side effects)
2. Log start/end with timestamp
3. Write results to `data/` for persistence
4. Send Telegram alert on failure
5. Complete within timeout (configured in config.yaml)
6. Be idempotent (safe to run multiple times)

---

## Adding New Automation Tasks

1. Write the script in `scripts/automation/`
2. Add entry to `scripts/automation/config.yaml`
3. Test with `--dry-run`
4. Reload orchestrator (SIGHUP or restart)

```yaml
# config.yaml entry format
my_new_task:
  script: scripts/automation/my_new_task.py
  schedule: "0 9 * * *"   # 9am daily
  enabled: true
  timeout: 300             # seconds before kill
  description: "What this task does"
```

---

## Metrics to Track

These metrics measure automation health AND moat growth:

| Metric | Target | Current | Source |
|--------|--------|---------|--------|
| Total tools in catalog | >15,000 | 15,410 | `/v1/services` |
| Daily new tools discovered | >50 | ? | harvester log |
| Daily scans run | >100 | ? | `/admin/analytics` |
| Agent traffic identified | >0 | 0 | middleware log |
| Excellent-tier tools | >5% | 0% | leaderboard |
| Backup success rate | 100% | ? | backup log |
| Healthcheck failures | 0/day | ? | error_monitor |

*Track these weekly in the weekly_report task.*

---

*This document is maintained by the Clarvia CEO agent.*
*Last updated: 2026-03-27*
*Review cycle: Weekly (every Monday)*
