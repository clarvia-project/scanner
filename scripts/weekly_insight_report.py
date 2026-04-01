#!/usr/bin/env python3
"""Weekly marketing insight report — auto-generates and can send to Telegram.

Analyzes the past 7 days of analytics data and produces a structured report.

Usage:
    python3 scripts/weekly_insight_report.py [--send-telegram]
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ANALYTICS_DIR = Path(__file__).resolve().parent.parent / "backend" / "data" / "analytics"
EXPERIMENTS_FILE = Path(__file__).resolve().parent.parent / "backend" / "data" / "experiments.json"


def load_week_data(days: int = 7) -> list[dict]:
    """Load analytics entries for the past N days."""
    entries = []
    start = date.today() - timedelta(days=days)
    for i in range(days):
        day = start + timedelta(days=i)
        filepath = ANALYTICS_DIR / f"analytics-{day.isoformat()}.jsonl"
        if not filepath.exists():
            continue
        with open(filepath) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def generate_report(entries: list[dict]) -> str:
    """Generate a structured markdown report from analytics data."""
    if not entries:
        return "# Weekly Insight Report\n\nNo data available for the past 7 days."

    total = len(entries)

    # 1. KPI Summary
    agents = [e for e in entries if e.get("agent")]
    unique_ips = len(set(e.get("ip_hash", "") for e in entries))
    scan_count = sum(1 for e in entries if e.get("tool_activity") == "scan")
    search_count = sum(1 for e in entries if e.get("tool_activity") in ("search", "services"))

    # 2. Channel attribution
    channels = Counter(e.get("referrer_channel", "direct") for e in entries)

    # 3. Agent breakdown
    agent_types = Counter(e.get("agent", "human") for e in entries if e.get("agent"))

    # 4. Top endpoints
    endpoints = Counter(e.get("endpoint", "") for e in entries)

    # 5. Error rate
    errors = sum(1 for e in entries if e.get("status", 200) >= 400)
    error_rate = errors / total * 100 if total else 0

    # 6. Daily trend
    daily = defaultdict(int)
    for e in entries:
        daily[e.get("date", "?")] += 1

    report = f"""# Weekly Insight Report
**Period**: {(date.today() - timedelta(days=7)).isoformat()} ~ {date.today().isoformat()}

## KPI Summary
- **Total API calls**: {total:,}
- **Unique visitors**: {unique_ips:,}
- **Agent requests**: {len(agents):,} ({len(agents)/total*100:.1f}%)
- **Scans**: {scan_count:,}
- **Searches**: {search_count:,}
- **Error rate**: {error_rate:.1f}%

## Channel Attribution
"""
    for ch, count in channels.most_common(10):
        pct = count / total * 100
        report += f"- **{ch}**: {count:,} ({pct:.1f}%)\n"

    report += "\n## Agent Breakdown\n"
    for agent, count in agent_types.most_common(10):
        report += f"- **{agent}**: {count:,}\n"

    report += "\n## Daily Trend\n"
    for day in sorted(daily.keys()):
        bar = "█" * min(50, daily[day] // 10)
        report += f"- {day}: {daily[day]:,} {bar}\n"

    report += "\n## Top Endpoints\n"
    for ep, count in endpoints.most_common(10):
        report += f"- `{ep}`: {count:,}\n"

    # Experiments
    if EXPERIMENTS_FILE.exists():
        try:
            with open(EXPERIMENTS_FILE) as f:
                experiments = json.load(f)
            active = [e for e in experiments if e.get("status") == "active"]
            if active:
                report += "\n## Active Experiments\n"
                for exp in active:
                    report += f"- **{exp.get('id', '?')}**: {exp.get('hypothesis', '')}\n"
                    report += f"  Metric: {exp.get('metric', '?')} | Baseline: {exp.get('baseline', '?')} | Target: {exp.get('target', '?')}\n"
        except Exception:
            pass

    return report


def main():
    send_telegram = "--send-telegram" in sys.argv

    print("Loading analytics data...")
    entries = load_week_data(7)
    print(f"Loaded {len(entries)} entries")

    report = generate_report(entries)
    print(report)

    # Save report
    report_dir = Path(__file__).resolve().parent.parent / "backend" / "data"
    report_file = report_dir / f"weekly-report-{date.today().isoformat()}.md"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"\nReport saved to {report_file}")

    if send_telegram:
        print("Telegram sending not yet implemented — report saved locally")


if __name__ == "__main__":
    main()
