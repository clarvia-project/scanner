# Clarvia Automation System

Autonomous platform operations for the Clarvia AI tool quality platform. This system keeps the catalog fresh, monitors health, scores tools, and continuously self-improves.

## Architecture Overview

Three conceptual engines drive the automation flywheel:

```
                     +-----------------+
                     |  THE HARVESTER  |
                     |  (Discovery)    |
                     +-------+---------+
                             |
                    new tools discovered
                             |
                             v
                     +-----------------+
                     | THE CALIBRATOR  |
                     | (Scoring)       |
                     +-------+---------+
                             |
                   tools scored & ranked
                             |
                             v
                     +-----------------+
                     | THE REPLICATOR  |
                     | (Growth)        |
                     +-------+---------+
                             |
                  reports, feedback, badges
                             |
                             +-----> loop back to Harvester
```

### The Harvester (Discovery Layer)
Continuously discovers new AI tools from multiple sources:
- **MCP Registry** — Official Model Context Protocol registry
- **Glama.ai** — MCP server directory
- **GitHub** — Repositories tagged with mcp/agent topics
- **npm/PyPI** — Package registries for AI tool packages
- **Community submissions** — User-submitted tools via API

Scripts: `harvester.py`, `sync_mcp_registry.py`, `collect_all_agent_tools.py`

### The Calibrator (Scoring Layer)
Evaluates every discovered tool against Clarvia's AEO criteria:
- **API Accessibility** (25 pts) — Endpoint existence, speed, auth, rate limits
- **Agent Compatibility** (25 pts) — MCP support, structured output, tool calling
- **Data Structuring** (25 pts) — Schema quality, JSON-LD, OpenAPI spec
- **Trust Signals** (25 pts) — HTTPS, CORS, uptime, community signals
- **On-chain Bonus** (25 pts) — Blockchain-native features (optional)

Scripts: `classifier.py`, `self_improver.py`, `integration_verifier.py`

### The Replicator (Growth Layer)
Turns scores into actionable outputs that drive platform growth:
- Daily/weekly reports via Telegram
- Badge generation for high-scoring tools
- Feedback engine for tool maintainers
- Dashboard for operational visibility

Scripts: `daily_report.py`, `score_reporter.py`, `feedback_engine.py`, `dashboard_generator.py`

## Flywheel Diagram

```
  +----> Discover tools -----> Score tools -----> Publish results ---+
  |                                                                   |
  |   Harvester crawls       Calibrator runs     Reports & badges     |
  |   MCP, GitHub, npm       AEO scan pipeline   attract maintainers  |
  |                                                                   |
  +--- Maintainers improve <-- Feedback sent <-- Gaps identified <---+
              |
              v
       Self-Improver runs Clarvia's own AEO criteria against itself
       => Platform quality goes up => More tools trust Clarvia => Loop
```

## Task Reference

| Task | Schedule | Description |
|------|----------|-------------|
| `healthcheck` | Every 5 min | Monitor API and frontend uptime |
| `error_monitor` | Every 5 min | Detect and alert on error spikes |
| `backup` | 3am daily | Backup critical data files |
| `harvester` | 6am daily | Discover new tools from all sources |
| `classifier` | 6:30am daily | Score newly discovered tools |
| `dead_link_check` | Sunday 4am | Remove dead links from catalog |
| `daily_report` | 10pm daily | Send daily stats to Telegram |
| `weekly_report` | Monday 10am | Comprehensive weekly analysis |
| `self_improvement` | Sunday noon | Self-assess Clarvia against own criteria |
| `integration_verify` | 8am daily | Verify MCP/API integrations work |
| `onboarding` | Every 30 min | Process new tool submissions |
| `feedback_engine` | 2am daily | Generate improvement feedback for tools |
| `dashboard` | Hourly | Regenerate automation health dashboard |

## Setup

### Prerequisites
- Python 3.11+
- `requests` library (included in backend requirements)
- Optional: `pyyaml` for config parsing

### Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
cp scripts/automation/.env.example scripts/automation/.env
```

Required:
- `TELEGRAM_BOT_TOKEN` — Bot token from @BotFather
- `TELEGRAM_CHAT_ID` — Target chat for notifications

Optional:
- `GITHUB_TOKEN` — Increases GitHub API rate limit (5000/hr vs 60/hr)
- `RENDER_API_KEY` — Enables auto-redeploy on health failures
- `RENDER_SERVICE_ID` — Render service to redeploy

### Running Tasks

Run any task manually:
```bash
python scripts/automation/self_improver.py
python scripts/automation/dashboard_generator.py
python scripts/healthcheck.py --loop
```

Dry-run mode (no side effects):
```bash
python scripts/automation/self_improver.py --dry-run
```

### Adding New Automation Tasks

1. Create a Python script in `scripts/automation/`
2. Follow the pattern: argparse CLI, logging, telegram alerts, data output
3. Add entry to `config.yaml` with schedule and timeout
4. Import `telegram_notifier` for alert integration:
   ```python
   sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
   from telegram_notifier import send_alert
   ```
5. Regenerate dashboard to include the new task

### Directory Structure

```
scripts/
  automation/
    config.yaml          # Master task configuration
    .env.example         # Environment variable template
    self_improver.py     # Self-assessment engine
    dashboard_generator.py # Health dashboard generator
    harvester.py         # Tool discovery (Phase 3)
    classifier.py        # Tool scoring (Phase 3)
    ...
  healthcheck.py         # Uptime monitoring
  telegram_notifier.py   # Shared notification module
  catalog_updater.py     # Catalog sync
data/
  self-improvement/      # Assessment history (JSON)
  dashboard/             # Generated HTML dashboard
  new-tools-queue.jsonl  # Pending tool queue
  automation.log         # Orchestrator log
```

## Monitoring & Troubleshooting

### Dashboard
View the automation dashboard at `data/dashboard/index.html` or serve it:
```bash
python -m http.server 8080 --directory data/dashboard
```

### Common Issues

**Task not running?**
- Check `enabled: true` in config.yaml
- Verify the script path exists
- Check automation.log for errors

**Telegram alerts not sending?**
- Verify TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set
- Test with: `python scripts/telegram_notifier.py --dry-run`

**Self-improvement score dropping?**
- Check if API or frontend is down (availability dimension)
- Review data/self-improvement/ for detailed breakdowns
- Run manually: `python scripts/automation/self_improver.py`

**Dashboard shows stale data?**
- Dashboard regenerates hourly by default
- Force refresh: `python scripts/automation/dashboard_generator.py`
