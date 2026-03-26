#!/usr/bin/env python3
"""Clarvia Automation Health Dashboard Generator.

Generates a self-contained static HTML dashboard showing:
  - All automation tasks and their last run status
  - Catalog growth chart (tools indexed over time)
  - Uptime chart (from healthcheck data)
  - Error rate chart (from monitoring data)
  - Self-improvement score trend
  - Harvester stats (tools discovered per source)

Output: data/dashboard/index.html (inline CSS/JS, no external deps)

Usage:
  python scripts/automation/dashboard_generator.py
  python scripts/automation/dashboard_generator.py --output custom/path.html
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DASHBOARD_DIR = DATA_DIR / "dashboard"
SELF_IMPROVEMENT_DIR = DATA_DIR / "self-improvement"
CONFIG_PATH = SCRIPT_DIR / "config.yaml"

DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data collectors
# ---------------------------------------------------------------------------

def collect_task_status() -> list[dict[str, Any]]:
    """Collect automation task status from config and log files."""
    tasks = []

    # Try loading config
    config = _load_config()
    if not config:
        return tasks

    for name, task_cfg in config.get("tasks", {}).items():
        task = {
            "name": name,
            "script": task_cfg.get("script", ""),
            "schedule": task_cfg.get("schedule", ""),
            "enabled": task_cfg.get("enabled", True),
            "last_run": None,
            "last_status": "unknown",
        }

        # Try to find last run info from log
        log_path = DATA_DIR / "automation.log"
        if log_path.exists():
            try:
                lines = log_path.read_text().strip().split("\n")
                for line in reversed(lines[-500:]):
                    if name in line:
                        task["last_run"] = line[:19] if len(line) > 19 else line
                        task["last_status"] = "ok" if "success" in line.lower() or "completed" in line.lower() else "error"
                        break
            except OSError:
                pass

        tasks.append(task)

    return tasks


def collect_catalog_stats() -> dict[str, Any]:
    """Collect catalog growth data from tool files."""
    stats = {
        "total_tools": 0,
        "sources": {},
        "by_date": [],
    }

    # Count tools from various source files
    source_files = {
        "mcp_registry": DATA_DIR / "mcp-scan-results.json",
        "github": DATA_DIR / "github-scan-results.json",
        "glama": DATA_DIR / "glama-scan-results.json",
        "prebuilt": DATA_DIR / "prebuilt-scans.json",
        "all_agent_tools": DATA_DIR / "all-agent-tools.json",
    }

    for source_name, path in source_files.items():
        if path.exists():
            try:
                data = json.loads(path.read_text())
                count = len(data) if isinstance(data, list) else len(data) if isinstance(data, dict) else 0
                stats["sources"][source_name] = count
                stats["total_tools"] += count
            except (json.JSONDecodeError, OSError):
                stats["sources"][source_name] = 0

    # Queue stats
    queue_path = DATA_DIR / "new-tools-queue.jsonl"
    if queue_path.exists():
        try:
            lines = queue_path.read_text().strip().split("\n")
            stats["queue_size"] = len([l for l in lines if l.strip()])
        except OSError:
            stats["queue_size"] = 0

    return stats


def collect_uptime_data() -> list[dict[str, Any]]:
    """Parse healthcheck log for uptime timeline."""
    log_path = DATA_DIR / "healthcheck.log"
    data_points: list[dict[str, Any]] = []

    if not log_path.exists():
        return data_points

    try:
        lines = log_path.read_text().strip().split("\n")
        for line in lines[-100:]:  # last 100 entries
            try:
                entry = json.loads(line)
                data_points.append({
                    "time": entry.get("timestamp", ""),
                    "healthy": entry.get("status") == "healthy" or entry.get("healthy", False),
                })
            except json.JSONDecodeError:
                # Try parsing plain text log format
                if len(line) > 19:
                    ts = line[:19]
                    healthy = "healthy" in line.lower() or "ok" in line.lower()
                    data_points.append({"time": ts, "healthy": healthy})
    except OSError:
        pass

    return data_points


def collect_self_improvement_trend() -> list[dict[str, float]]:
    """Collect self-assessment scores over time."""
    trend: list[dict[str, float]] = []

    if not SELF_IMPROVEMENT_DIR.exists():
        return trend

    for f in sorted(SELF_IMPROVEMENT_DIR.glob("assessment-*.json")):
        try:
            data = json.loads(f.read_text())
            trend.append({
                "date": data.get("date", f.stem.replace("assessment-", "")),
                "score": data.get("overall_score", 0),
            })
        except (json.JSONDecodeError, OSError):
            continue

    return trend


def collect_error_stats() -> dict[str, Any]:
    """Collect error statistics from monitoring data."""
    stats = {"total_errors": 0, "recent": []}

    # Check for error monitoring output
    for pattern in ["error-monitor*.json", "error_report*.json"]:
        for f in sorted(DATA_DIR.glob(pattern)):
            try:
                data = json.loads(f.read_text())
                if isinstance(data, dict):
                    stats["total_errors"] += data.get("error_count", 0)
                    stats["recent"].extend(data.get("errors", [])[:10])
            except (json.JSONDecodeError, OSError):
                pass

    return stats


def _load_config() -> dict[str, Any]:
    """Load automation config.yaml."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        # Minimal YAML parsing without PyYAML dependency
        # Only need top-level keys and task names
        import yaml
        return yaml.safe_load(CONFIG_PATH.read_text()) or {}
    except ImportError:
        # Fallback: basic key-value parsing for display purposes
        logger.warning("PyYAML not installed — using fallback config parser")
        return _parse_yaml_fallback(CONFIG_PATH)
    except Exception as exc:
        logger.warning("Could not load config: %s", exc)
        return {}


def _parse_yaml_fallback(path: Path) -> dict[str, Any]:
    """Minimal YAML-like parser for the config file (no dependency needed)."""
    config: dict[str, Any] = {"tasks": {}}
    current_task = None

    try:
        for line in path.read_text().split("\n"):
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue

            indent = len(line) - len(line.lstrip())

            if indent == 2 and stripped.endswith(":") and not stripped.startswith("-"):
                # Task name
                current_task = stripped.rstrip(":")
                config["tasks"][current_task] = {}
            elif indent == 4 and current_task and ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                elif val.isdigit():
                    val = int(val)
                config["tasks"][current_task][key] = val
    except OSError:
        pass

    return config


# ---------------------------------------------------------------------------
# HTML generator
# ---------------------------------------------------------------------------

def generate_html(
    tasks: list[dict],
    catalog: dict,
    uptime: list[dict],
    trend: list[dict],
    errors: dict,
) -> str:
    """Generate self-contained HTML dashboard."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Prepare chart data as JSON for inline JS
    uptime_json = json.dumps(uptime[-50:])  # last 50 data points
    trend_json = json.dumps(trend)
    sources_json = json.dumps(catalog.get("sources", {}))

    # Task rows HTML
    task_rows = ""
    for t in tasks:
        status_class = {
            "ok": "status-ok",
            "error": "status-error",
            "unknown": "status-unknown",
        }.get(t["last_status"], "status-unknown")
        enabled_badge = '<span class="badge badge-on">ON</span>' if t["enabled"] else '<span class="badge badge-off">OFF</span>'
        task_rows += f"""
        <tr>
            <td><code>{t['name']}</code></td>
            <td><code>{t['script']}</code></td>
            <td><code>{t['schedule']}</code></td>
            <td>{enabled_badge}</td>
            <td><span class="status {status_class}">{t['last_status']}</span></td>
            <td>{t['last_run'] or 'Never'}</td>
        </tr>"""

    # Self-improvement latest
    latest_score = trend[-1]["score"] if trend else "N/A"
    prev_score = trend[-2]["score"] if len(trend) >= 2 else None
    score_delta = ""
    if prev_score is not None:
        d = trend[-1]["score"] - prev_score
        arrow = "+" if d >= 0 else ""
        score_delta = f' <span class="delta {"delta-up" if d >= 0 else "delta-down"}">{arrow}{d:.1f}</span>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Clarvia Automation Dashboard</title>
<style>
  :root {{
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --text-dim: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --red: #f85149;
    --yellow: #d29922;
    --purple: #bc8cff;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text);
    padding: 24px; max-width: 1400px; margin: 0 auto;
  }}
  h1 {{ color: var(--accent); margin-bottom: 4px; font-size: 1.6rem; }}
  .subtitle {{ color: var(--text-dim); margin-bottom: 24px; font-size: 0.9rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; padding: 20px;
  }}
  .card h2 {{ font-size: 1rem; color: var(--accent); margin-bottom: 12px; }}
  .stat-number {{ font-size: 2.4rem; font-weight: 700; }}
  .stat-label {{ color: var(--text-dim); font-size: 0.85rem; }}
  table {{
    width: 100%; border-collapse: collapse;
    font-size: 0.85rem;
  }}
  th, td {{
    text-align: left; padding: 8px 12px;
    border-bottom: 1px solid var(--border);
  }}
  th {{ color: var(--text-dim); font-weight: 600; }}
  code {{
    background: rgba(110,118,129,0.15); padding: 2px 6px;
    border-radius: 4px; font-size: 0.8rem;
  }}
  .status {{ padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
  .status-ok {{ background: rgba(63,185,80,0.15); color: var(--green); }}
  .status-error {{ background: rgba(248,81,73,0.15); color: var(--red); }}
  .status-unknown {{ background: rgba(139,148,158,0.15); color: var(--text-dim); }}
  .badge {{ padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }}
  .badge-on {{ background: rgba(63,185,80,0.15); color: var(--green); }}
  .badge-off {{ background: rgba(139,148,158,0.15); color: var(--text-dim); }}
  .delta {{ font-size: 0.9rem; font-weight: 600; }}
  .delta-up {{ color: var(--green); }}
  .delta-down {{ color: var(--red); }}
  .chart-container {{ position: relative; height: 200px; margin-top: 12px; }}
  .bar-chart {{ display: flex; align-items: flex-end; gap: 4px; height: 160px; padding-top: 10px; }}
  .bar {{
    flex: 1; min-width: 20px; border-radius: 3px 3px 0 0;
    transition: height 0.3s;
    position: relative;
  }}
  .bar:hover::after {{
    content: attr(data-label);
    position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%);
    background: var(--card); border: 1px solid var(--border);
    padding: 4px 8px; border-radius: 4px; font-size: 0.7rem;
    white-space: nowrap; z-index: 10;
  }}
  .bar-healthy {{ background: var(--green); }}
  .bar-unhealthy {{ background: var(--red); }}
  .bar-score {{ background: var(--accent); }}
  .bar-source {{ background: var(--purple); }}
  .source-list {{ list-style: none; }}
  .source-list li {{
    display: flex; justify-content: space-between;
    padding: 6px 0; border-bottom: 1px solid var(--border);
    font-size: 0.85rem;
  }}
  .source-list li:last-child {{ border: none; }}
  .source-count {{ font-weight: 700; color: var(--accent); }}
  footer {{
    margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border);
    color: var(--text-dim); font-size: 0.75rem; text-align: center;
  }}
</style>
</head>
<body>
  <h1>Clarvia Automation Dashboard</h1>
  <p class="subtitle">Generated: {now}</p>

  <!-- Summary cards -->
  <div class="grid">
    <div class="card">
      <h2>Total Tools Indexed</h2>
      <div class="stat-number">{catalog.get('total_tools', 0):,}</div>
      <div class="stat-label">across {len(catalog.get('sources', {}))} sources</div>
    </div>
    <div class="card">
      <h2>Self-Assessment Score</h2>
      <div class="stat-number">{latest_score}{score_delta}</div>
      <div class="stat-label">out of 10.0</div>
    </div>
    <div class="card">
      <h2>Queue Size</h2>
      <div class="stat-number">{catalog.get('queue_size', 0):,}</div>
      <div class="stat-label">tools pending classification</div>
    </div>
    <div class="card">
      <h2>Active Tasks</h2>
      <div class="stat-number">{sum(1 for t in tasks if t.get('enabled'))}</div>
      <div class="stat-label">of {len(tasks)} configured</div>
    </div>
  </div>

  <!-- Automation tasks table -->
  <div class="card" style="margin-bottom: 24px;">
    <h2>Automation Tasks</h2>
    <table>
      <thead>
        <tr><th>Task</th><th>Script</th><th>Schedule</th><th>Enabled</th><th>Status</th><th>Last Run</th></tr>
      </thead>
      <tbody>{task_rows}</tbody>
    </table>
  </div>

  <div class="grid">
    <!-- Uptime chart -->
    <div class="card">
      <h2>Uptime (recent checks)</h2>
      <div class="bar-chart" id="uptime-chart"></div>
    </div>

    <!-- Self-improvement trend -->
    <div class="card">
      <h2>Self-Assessment Trend</h2>
      <div class="bar-chart" id="trend-chart"></div>
    </div>

    <!-- Harvester sources -->
    <div class="card">
      <h2>Tools by Source</h2>
      <ul class="source-list" id="sources-list"></ul>
    </div>

    <!-- Error summary -->
    <div class="card">
      <h2>Error Summary</h2>
      <div class="stat-number" style="color: {('var(--green)' if errors.get('total_errors', 0) == 0 else 'var(--red)')}">{errors.get('total_errors', 0)}</div>
      <div class="stat-label">total errors detected</div>
    </div>
  </div>

  <footer>
    Clarvia Automation System &mdash; Self-improving AI tool quality platform
  </footer>

  <script>
    // Uptime chart
    const uptimeData = {uptime_json};
    const uptimeChart = document.getElementById('uptime-chart');
    uptimeData.forEach((d, i) => {{
      const bar = document.createElement('div');
      bar.className = 'bar ' + (d.healthy ? 'bar-healthy' : 'bar-unhealthy');
      bar.style.height = d.healthy ? '100%' : '30%';
      bar.setAttribute('data-label', (d.time || 'check ' + i) + ': ' + (d.healthy ? 'OK' : 'FAIL'));
      uptimeChart.appendChild(bar);
    }});
    if (uptimeData.length === 0) {{
      uptimeChart.innerHTML = '<span style="color:var(--text-dim);font-size:0.85rem">No healthcheck data available</span>';
    }}

    // Self-improvement trend
    const trendData = {trend_json};
    const trendChart = document.getElementById('trend-chart');
    const maxScore = 10;
    trendData.forEach(d => {{
      const bar = document.createElement('div');
      bar.className = 'bar bar-score';
      bar.style.height = ((d.score / maxScore) * 100) + '%';
      bar.setAttribute('data-label', d.date + ': ' + d.score + '/10');
      trendChart.appendChild(bar);
    }});
    if (trendData.length === 0) {{
      trendChart.innerHTML = '<span style="color:var(--text-dim);font-size:0.85rem">No self-assessment data yet</span>';
    }}

    // Sources list
    const sourcesData = {sources_json};
    const sourcesList = document.getElementById('sources-list');
    const sortedSources = Object.entries(sourcesData).sort((a, b) => b[1] - a[1]);
    sortedSources.forEach(([name, count]) => {{
      const li = document.createElement('li');
      li.innerHTML = '<span>' + name.replace(/_/g, ' ') + '</span><span class="source-count">' + count.toLocaleString() + '</span>';
      sourcesList.appendChild(li);
    }});
    if (sortedSources.length === 0) {{
      sourcesList.innerHTML = '<li style="color:var(--text-dim)">No source data available</li>';
    }}
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_dashboard(output_path: Optional[str] = None) -> str:
    """Generate the dashboard HTML and write to disk."""
    tasks = collect_task_status()
    catalog = collect_catalog_stats()
    uptime = collect_uptime_data()
    trend = collect_self_improvement_trend()
    errors = collect_error_stats()

    html = generate_html(tasks, catalog, uptime, trend, errors)

    out = Path(output_path) if output_path else DASHBOARD_DIR / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)

    logger.info("Dashboard generated: %s (%d bytes)", out, len(html))
    return str(out)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Clarvia automation health dashboard"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output HTML file path (default: data/dashboard/index.html)",
    )
    args = parser.parse_args()

    path = generate_dashboard(output_path=args.output)
    print(f"Dashboard written to {path}")


if __name__ == "__main__":
    main()
