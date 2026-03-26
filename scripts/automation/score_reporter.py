#!/usr/bin/env python3
"""Weekly score report generator for Clarvia.

Generates a weekly digest containing:
  - New tools indexed this week (count + top 5 by score)
  - Score changes > 1.0 point (improvements and drops)
  - Top 10 tools by score (current leaderboard)
  - Category distribution stats
  - Total catalog size trend

Output formats:
  1. Markdown (for Telegram / GitHub)
  2. JSON (for API: GET /v1/feed/weekly-report)
  3. Plain text summary

Reports stored in: data/reports/weekly-YYYY-WW.json

Usage:
    python scripts/automation/score_reporter.py [--dry-run] [--format json|markdown|text]
"""

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from telegram_notifier import send_message

logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"
REPORT_DIR = DATA_DIR / "reports"


def _load_catalog() -> list[dict[str, Any]]:
    """Load current catalog from prebuilt-scans.json."""
    catalog_path = DATA_DIR / "prebuilt-scans.json"
    if not catalog_path.exists():
        logger.warning("Catalog file not found: %s", catalog_path)
        return []
    with open(catalog_path) as f:
        return json.load(f)


def _load_previous_report() -> dict[str, Any] | None:
    """Load the most recent previous weekly report for comparison."""
    if not REPORT_DIR.exists():
        return None

    reports = sorted(REPORT_DIR.glob("weekly-*.json"), reverse=True)
    for rp in reports:
        try:
            with open(rp) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _iso_week_id() -> str:
    """Return current ISO week as 'YYYY-WW'."""
    now = datetime.now(timezone.utc)
    return f"{now.isocalendar()[0]}-{now.isocalendar()[1]:02d}"


def generate_report() -> dict[str, Any]:
    """Build the weekly report data."""
    catalog = _load_catalog()
    previous = _load_previous_report()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Build lookup from previous report
    prev_scores: dict[str, float] = {}
    prev_names: set[str] = set()
    if previous and "catalog_snapshot" in previous:
        for item in previous["catalog_snapshot"]:
            name = item.get("name", "")
            prev_scores[name] = item.get("score", 0)
            prev_names.add(name)

    # Current scores
    current_items = []
    for s in catalog:
        name = s.get("service_name", "")
        score = s.get("clarvia_score", 0)
        current_items.append({
            "name": name,
            "url": s.get("url", ""),
            "score": score,
            "rating": s.get("rating", ""),
            "category": s.get("category", "other"),
            "scanned_at": s.get("scanned_at", ""),
        })

    current_names = {item["name"] for item in current_items}

    # New tools (in current but not in previous)
    new_tools = [item for item in current_items if item["name"] not in prev_names]
    new_tools_sorted = sorted(new_tools, key=lambda x: x["score"], reverse=True)

    # Score changes > 1.0
    score_changes = []
    for item in current_items:
        name = item["name"]
        if name in prev_scores:
            delta = item["score"] - prev_scores[name]
            if abs(delta) >= 1.0:
                score_changes.append({
                    "name": name,
                    "previous_score": prev_scores[name],
                    "current_score": item["score"],
                    "delta": round(delta, 1),
                })

    improvements = sorted(
        [c for c in score_changes if c["delta"] > 0],
        key=lambda x: x["delta"],
        reverse=True,
    )
    drops = sorted(
        [c for c in score_changes if c["delta"] < 0],
        key=lambda x: x["delta"],
    )

    # Top 10 by score
    top10 = sorted(current_items, key=lambda x: x["score"], reverse=True)[:10]

    # Category distribution
    cat_counts = Counter(item["category"] for item in current_items)

    # Catalog size trend
    prev_size = len(prev_names) if previous else 0
    current_size = len(current_items)

    report = {
        "week_id": _iso_week_id(),
        "generated_at": now.isoformat(),
        "summary": {
            "total_tools": current_size,
            "previous_total": prev_size,
            "net_change": current_size - prev_size,
            "new_tools_count": len(new_tools),
            "score_improvements": len(improvements),
            "score_drops": len(drops),
        },
        "new_tools": {
            "count": len(new_tools),
            "top5": [
                {"name": t["name"], "score": t["score"], "category": t["category"]}
                for t in new_tools_sorted[:5]
            ],
        },
        "score_changes": {
            "improvements": improvements[:10],
            "drops": drops[:10],
        },
        "leaderboard": [
            {"rank": i + 1, "name": t["name"], "score": t["score"], "rating": t["rating"]}
            for i, t in enumerate(top10)
        ],
        "category_distribution": dict(
            sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
        ),
        # Snapshot for next week's comparison
        "catalog_snapshot": [
            {"name": item["name"], "score": item["score"]}
            for item in current_items
        ],
    }

    return report


def format_markdown(report: dict[str, Any]) -> str:
    """Format report as Markdown (Telegram-compatible)."""
    s = report["summary"]
    lines = [
        "📊 *Clarvia Weekly Report*",
        f"Week: {report['week_id']}",
        "",
        f"*Catalog*: {s['total_tools']} tools ({'+' if s['net_change'] >= 0 else ''}{s['net_change']} from last week)",
        f"*New tools*: {s['new_tools_count']}",
        f"*Score improvements*: {s['score_improvements']}",
        f"*Score drops*: {s['score_drops']}",
    ]

    # New tools top 5
    if report["new_tools"]["top5"]:
        lines.append("\n*New Tools (top 5):*")
        for t in report["new_tools"]["top5"]:
            lines.append(f"  • {t['name']} — {t['score']}pts [{t['category']}]")

    # Top 10 leaderboard
    if report["leaderboard"]:
        lines.append("\n*Leaderboard:*")
        for t in report["leaderboard"]:
            lines.append(f"  {t['rank']}. {t['name']} — {t['score']}pts ({t['rating']})")

    # Notable changes
    improvements = report["score_changes"]["improvements"][:5]
    drops = report["score_changes"]["drops"][:5]

    if improvements:
        lines.append("\n*Biggest Improvements:*")
        for c in improvements:
            lines.append(f"  ↑ {c['name']}: {c['previous_score']} → {c['current_score']} (+{c['delta']})")

    if drops:
        lines.append("\n*Biggest Drops:*")
        for c in drops:
            lines.append(f"  ↓ {c['name']}: {c['previous_score']} → {c['current_score']} ({c['delta']})")

    # Categories
    cat = report["category_distribution"]
    if cat:
        lines.append("\n*Categories:*")
        for name, count in list(cat.items())[:8]:
            lines.append(f"  {name}: {count}")

    return "\n".join(lines)


def format_text(report: dict[str, Any]) -> str:
    """Format report as plain text."""
    s = report["summary"]
    lines = [
        f"Clarvia Weekly Report — Week {report['week_id']}",
        f"Total: {s['total_tools']} tools | New: {s['new_tools_count']} | "
        f"Improvements: {s['score_improvements']} | Drops: {s['score_drops']}",
    ]
    if report["leaderboard"]:
        lines.append("Top 10: " + ", ".join(
            f"{t['name']}({t['score']})" for t in report["leaderboard"]
        ))
    return "\n".join(lines)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Clarvia weekly score reporter")
    parser.add_argument("--dry-run", action="store_true", help="Skip Telegram send")
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "text", "all"],
        default="all",
        help="Output format",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    report = generate_report()

    # Save JSON report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    week_id = report["week_id"]
    report_path = REPORT_DIR / f"weekly-{week_id}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Report saved to %s", report_path)

    # Output
    if args.format in ("json", "all"):
        print(json.dumps(report, indent=2))
    if args.format in ("markdown", "all"):
        md = format_markdown(report)
        print(md)
    if args.format in ("text", "all"):
        print(format_text(report))

    # Send Telegram
    if not args.dry_run:
        md = format_markdown(report)
        send_message(md)
        logger.info("Weekly report sent via Telegram")
    else:
        logger.info("[DRY RUN] Skipping Telegram send")

    return 0


if __name__ == "__main__":
    sys.exit(main())
