# Clarvia Eternal Operations Runbook

Clarvia is designed to run autonomously forever. This runbook documents every automation component, what alerts mean, and how to intervene if needed (you shouldn't need to).

## Architecture Overview

```
                    ┌──────────────────────────┐
                    │     ORCHESTRATOR          │
                    │  (cron-based scheduler)   │
                    │  scripts/automation/      │
                    │  orchestrator.py           │
                    └──────────┬───────────────┘
                               │ triggers
            ┌──────────────────┼──────────────────────┐
            │                  │                      │
            ▼                  ▼                      ▼
    ┌───────────┐    ┌─────────────┐      ┌────────────────┐
    │ HARVESTER │    │ CLASSIFIER  │      │ HEALTHCHECK    │
    │ 6am daily │    │ 6:30am      │      │ every 5 min    │
    │           │    │ (after      │      │                │
    │ GitHub    │    │  harvester) │      │ API + Frontend │
    │ npm       │    └─────────────┘      └────────────────┘
    │ PyPI      │
    │ MCP Reg.  │
    └─────┬─────┘
          │ feeds
          ▼
    ┌───────────────────────────────────────────────────┐
    │                DATA PIPELINE                       │
    │                                                    │
    │  discoveries.jsonl → new-tools-queue.jsonl         │
    │       → scan → prebuilt-scans.json (catalog)       │
    └───────────┬───────────────────────────────────────┘
                │ monitored by
                ▼
    ┌───────────────────────────────────────────────────┐
    │            ETERNAL OPERATIONS LAYER                │
    │                                                    │
    │  ┌──────────────┐  ┌──────────────┐               │
    │  │ SCHEMA       │  │ DATA         │               │
    │  │ WATCHDOG     │  │ AUDITOR      │               │
    │  │ 5am daily    │  │ 7am daily    │               │
    │  │              │  │              │               │
    │  │ Monitors API │  │ Score dist   │               │
    │  │ schemas for  │  │ Categories   │               │
    │  │ drift        │  │ Duplicates   │               │
    │  └──────────────┘  │ Freshness    │               │
    │                    │ Completeness │               │
    │  ┌──────────────┐  │ Anomalies    │               │
    │  │ SELF-HEALER  │  └──────────────┘               │
    │  │ every 6h     │                                 │
    │  │              │  ┌──────────────┐               │
    │  │ Task failures│  │ CIRCUIT      │               │
    │  │ Disk/logs    │  │ BREAKER      │               │
    │  │ Dependencies │  │ (always-on)  │               │
    │  │ Render health│  │              │               │
    │  │ Auto-archive │  │ Per-source   │               │
    │  └──────────────┘  │ fail/recover │               │
    │                    └──────────────┘               │
    └───────────────────────────────────────────────────┘
                │
                ▼
    ┌───────────────────┐
    │  TELEGRAM ALERTS  │
    │  (all components) │
    └───────────────────┘
```

## Component Details

### 1. Schema Watchdog (`schema_watchdog.py`)

**Schedule:** Daily at 5:00 AM UTC

**What it does:**
- Fetches current API responses from GitHub, npm, PyPI, and MCP Registry
- Extracts type schemas (key names + value types, recursively)
- Compares with saved "golden" schemas in `data/watchdog/schemas/`
- Detects additions (MINOR), removals/type changes (MAJOR), and outages (CRITICAL)

**Auto-actions:**
- MINOR changes: Golden schema auto-updated (additive changes are safe)
- MAJOR changes: Alert sent, recommends checking affected harvester
- CRITICAL: Alert sent, source should be investigated

**Data files:**
- `data/watchdog/schemas/{api_name}.json` — Golden schema snapshots
- `data/watchdog/checks.jsonl` — Full check history

**Alert examples:**
- `Schema Watchdog: GitHub Search API MAJOR DRIFT` — GitHub changed their API response structure
- `Schema Watchdog: PyPI Package JSON API CRITICAL` — PyPI endpoint is down

### 2. Data Auditor (`data_auditor.py`)

**Schedule:** Daily at 7:00 AM UTC (after harvester at 6:00 AM)

**What it does:**
- Score distribution: Checks if newly indexed tools have anomalous scores
- Category distribution: Ensures "other" category doesn't exceed 40%
- Duplicate detection: Finds exact URL dupes and >90% name similarity
- Freshness: Alerts if no new tools added in 7 days
- Completeness: Flags tools missing description, score, or category
- Anomaly detection: Catches if a single run adds >500 tools (likely a bug)

**Auto-fixes:**
- Removes exact URL duplicates (keeps highest-scored version)
- Flags "other" category tools for classifier re-run

**Data files:**
- `data/audits/audit-YYYY-MM-DD.json` — Daily audit reports

**Alert examples:**
- `Data Quality Audit: Issues Detected` — Lists all detected issues
- Score deviation means scoring logic or input data changed
- High "other" percentage means classifier may be degraded

### 3. Self-Healer (`self_healer.py`)

**Schedule:** Every 6 hours

**What it does:**
1. **Task failure tracking** — Reads orchestrator logs, detects 3+ consecutive failures
   - Tries common fixes: clear caches, reset state files
   - Alerts with failure details

2. **Resource monitoring** — Checks directory sizes and log files
   - Backups > 1GB: triggers cleanup of files > 30 days
   - Data > 5GB: alerts for manual review
   - Log files > 100MB: auto-rotates (compress + truncate)

3. **Dependency health** — Verifies `requests`, `yaml`, `aiohttp` are importable
   - Alerts immediately if a dependency is missing/broken

4. **Render service health** — Checks API endpoint and Render status page
   - Distinguishes between our service issues vs Render platform issues

5. **Auto-archival** — Moves old files to `data/archive/`
   - Audit results > 30 days
   - Healthcheck logs > 14 days
   - Harvester rejects > 60 days
   - Watchdog logs > 90 days

**Data files:**
- `data/self-healer/report-YYYY-MM-DD-HHMMSS.json` — Run reports
- `data/archive/` — Compressed archived files

### 4. Circuit Breaker (`circuit_breaker.py`)

**Schedule:** Always-on (imported by other scripts, not scheduled)

**What it does:**
- Provides per-source circuit breakers: github, npm, pypi, mcp_registry, clarvia_api
- States: CLOSED (normal) → OPEN (broken, skip source) → HALF_OPEN (probe)
- 3 failures → OPEN, 30 min cooldown → HALF_OPEN, 1 success → CLOSED
- Caches API responses for fallback when a source is OPEN
- Manages scan retry queue with exponential backoff (3 attempts max)

**Data files:**
- `data/circuit_breaker/state.json` — Current state of all breakers
- `data/circuit_breaker/cache/` — Cached API responses for fallback
- `data/circuit_breaker/retry_queue.json` — Pending scan retries

**CLI usage:**
```bash
# View all circuit breaker states
python scripts/automation/circuit_breaker.py

# Force-reset a tripped breaker
python scripts/automation/circuit_breaker.py --reset github

# Manually trip a breaker (e.g., for maintenance)
python scripts/automation/circuit_breaker.py --trip npm
```

## Complete Task Schedule

| Task               | Schedule            | Timeout | Purpose                      |
|--------------------|---------------------|---------|------------------------------|
| healthcheck        | Every 5 min         | 60s     | API/frontend uptime          |
| error_monitor      | Every 5 min         | 60s     | Error log scanning           |
| onboarding         | Every 30 min        | 180s    | New tool processing          |
| dashboard          | Hourly              | 120s    | Dashboard regeneration       |
| backup             | 3:00 AM daily       | 300s    | Data backup                  |
| dead_link_check    | Sunday 4:00 AM      | 1800s   | Dead link cleanup            |
| schema_watchdog    | 5:00 AM daily       | 300s    | API schema monitoring        |
| harvester          | 6:00 AM daily       | 600s    | Tool discovery crawl         |
| classifier         | 6:30 AM daily       | 300s    | Tool categorization          |
| data_auditor       | 7:00 AM daily       | 300s    | Data quality checks + fixes  |
| integration_verify | 8:00 AM daily       | 300s    | Integration testing          |
| self_healer        | Every 6 hours       | 600s    | Pipeline health + archival   |
| feedback_engine    | 2:00 AM daily       | 300s    | User feedback processing     |
| weekly_report      | Monday 10:00 AM     | 300s    | Weekly metrics report        |
| daily_report       | 10:00 PM daily      | 120s    | Daily summary report         |
| self_improvement   | Sunday 12:00 PM     | 300s    | Self-assessment scoring      |

## Alert Reference

All alerts are sent via Telegram. Format: `{emoji} *{title}*\n\n{body}`

| Level    | Emoji | Meaning                                    |
|----------|-------|--------------------------------------------|
| INFO     | info  | Informational, no action needed            |
| WARNING  | warn  | Something to be aware of                   |
| ERROR    | red   | Automated fix attempted, may need review   |
| CRITICAL | alarm | Immediate attention may be needed          |
| SUCCESS  | check | Recovery or positive event                 |

### When You Get an Alert

**CRITICAL alerts:**
1. Don't panic — the system has likely already started self-healing
2. Check the detailed message for which component is affected
3. If it's a source outage (GitHub/npm/PyPI), the circuit breaker has already isolated it
4. If it's the Clarvia API, healthcheck may have triggered a Render redeploy

**ERROR alerts:**
1. A task has been disabled after 3 failures
2. The self-healer has already tried common fixes (cache clear, state reset)
3. Check the error details — if it's a code bug, you'll need to fix and redeploy

**WARNING alerts:**
1. Data quality issues detected — auto-fixes may have been applied
2. Resource usage approaching limits — archival may be in progress
3. Usually self-resolves, monitor for recurring warnings

## Manual Intervention

### View current system status

```bash
cd /path/to/scanner

# Check all circuit breakers
python scripts/automation/circuit_breaker.py

# Run data audit (read-only)
python scripts/automation/data_auditor.py --dry-run

# Run schema watchdog (read-only)
python scripts/automation/schema_watchdog.py --dry-run

# Run self-healer (read-only)
python scripts/automation/self_healer.py --dry-run
```

### Force-run a specific task

```bash
python scripts/automation/schema_watchdog.py --init  # Regenerate golden schemas
python scripts/automation/data_auditor.py --fix       # Apply auto-fixes
python scripts/automation/self_healer.py --check disk # Run specific check only
```

### Reset after major incident

```bash
# Reset all circuit breakers
for source in github npm pypi mcp_registry clarvia_api; do
    python scripts/automation/circuit_breaker.py --reset $source
done

# Reinitialize golden schemas
python scripts/automation/schema_watchdog.py --init

# Clear state and restart orchestrator
rm data/orchestrator_state.json
python scripts/automation/orchestrator.py
```

## Complete Shutdown

```bash
# Find and kill the orchestrator process
pkill -f "orchestrator.py"

# Or if running via launchd
launchctl unload ~/Library/LaunchAgents/com.clarvia.orchestrator.plist
```

## Restart from Scratch

```bash
# 1. Run setup (creates directories, installs deps, registers launchd)
bash scripts/setup_automation.sh

# 2. Initialize golden schemas
python scripts/automation/schema_watchdog.py --init

# 3. Start orchestrator
python scripts/automation/orchestrator.py &

# Or via launchd for persistence
launchctl load ~/Library/LaunchAgents/com.clarvia.orchestrator.plist
```

## Data Flow Summary

```
External APIs (GitHub, npm, PyPI, MCP)
        │
        ▼ monitored by
  Schema Watchdog ──→ golden schemas (data/watchdog/schemas/)
        │                      │
        │                      ▼ schema drift alerts
        ▼ feeds                │
  Harvester ──→ discoveries.jsonl ──→ new-tools-queue.jsonl
        │                                      │
        │ protected by                         │
  Circuit Breakers ──→ state.json              ▼
        │               cache/          Classifier + Scanner
        │                                      │
        │                                      ▼
        │                              prebuilt-scans.json (CATALOG)
        │                                      │
        │                              monitored by
        ▼                                      │
  Self-Healer ◄────────────────────────────────┤
        │                                      ▼
        │                              Data Auditor
        │                                      │
        ▼                                      ▼
  Archive (data/archive/)              Audit reports (data/audits/)
```
