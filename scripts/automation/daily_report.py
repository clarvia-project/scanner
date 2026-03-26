#!/usr/bin/env python3
"""Daily operations report for Clarvia.

Aggregates daily metrics:
  - API requests (total, by endpoint, by user-agent type)
  - Catalog size (total, new today, removed today)
  - Scan count and average score
  - Error count and types
  - Uptime percentage (from healthcheck logs)
  - Automation task results (from orchestrator logs)

Sends a formatted Telegram message and stores in:
    data/reports/daily-YYYY-MM-DD.json

Usage:
    python scripts/automation/daily_report.py [--dry-run] [--api-url URL]
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from telegram_notifier import send_message

logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"
REPORT_DIR = DATA_DIR / "reports"

DEFAULT_API_URL = "https://clarvia-api.onrender.com"


def _fetch_analytics(api_url: str) -> dict[str, Any] | None:
    """Fetch analytics data from the admin endpoint."""
    try:
        resp = requests.get(f"{api_url}/admin/analytics", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.warning("Cannot fetch analytics: %s", exc)
    return None


def _fetch_health(api_url: str) -> dict[str, Any]:
    """Check API health and measure response time."""
    try:
        import time
        start = time.monotonic()
        resp = requests.get(f"{api_url}/health", timeout=10)
        elapsed_ms = (time.monotonic() - start) * 1000
        return {
            "healthy": resp.status_code == 200,
            "status_code": resp.status_code,
            "response_time_ms": round(elapsed_ms, 1),
        }
    except Exception as exc:
        return {"healthy": False, "error": str(exc), "response_time_ms": 0}


def _load_catalog() -> list[dict[str, Any]]:
    """Load current catalog."""
    catalog_path = DATA_DIR / "prebuilt-scans.json"
    if not catalog_path.exists():
        return []
    with open(catalog_path) as f:
        return json.load(f)


def _load_previous_daily() -> dict[str, Any] | None:
    """Load most recent daily report for trend comparison."""
    if not REPORT_DIR.exists():
        return None

    reports = sorted(REPORT_DIR.glob("daily-*.json"), reverse=True)
    for rp in reports:
        try:
            with open(rp) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _count_automation_results() -> dict[str, Any]:
    """Check recent automation run results."""
    results: dict[str, Any] = {}

    # Integration report
    integration_path = REPORT_DIR / "integration_report.json"
    if integration_path.exists():
        try:
            with open(integration_path) as f:
                data = json.load(f)
                summary = data.get("summary", {})
                results["integration"] = {
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                    "last_run": data.get("generated_at", ""),
                }
        except (json.JSONDecodeError, OSError):
            pass

    # Link check
    link_checks = sorted(
        (DATA_DIR / "link_checks").glob("*.json"), reverse=True
    ) if (DATA_DIR / "link_checks").exists() else []

    if link_checks:
        try:
            with open(link_checks[0]) as f:
                data = json.load(f)
                results["link_check"] = {
                    "total": data.get("total", 0),
                    "dead": data.get("dead", 0),
                    "last_run": data.get("checked_at", ""),
                }
        except (json.JSONDecodeError, OSError):
            pass

    # Feedback engine
    signals_path = DATA_DIR / "feedback" / "usage_signals_latest.json"
    if signals_path.exists():
        try:
            with open(signals_path) as f:
                data = json.load(f)
                boosted = sum(1 for s in data if s.get("popularity_boost", 0) > 0)
                results["feedback"] = {
                    "tools_processed": len(data),
                    "tools_boosted": boosted,
                }
        except (json.JSONDecodeError, OSError):
            pass

    return results


def _parse_error_logs() -> dict[str, int]:
    """Count errors from available log files."""
    error_counts: dict[str, int] = {}
    log_path = DATA_DIR / "scan_daemon.log"

    if not log_path.exists():
        return error_counts

    try:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(log_path) as f:
            for line in f:
                if today_str not in line:
                    continue
                line_lower = line.lower()
                if "error" in line_lower:
                    # Categorize error type
                    if "timeout" in line_lower:
                        error_counts["timeout"] = error_counts.get("timeout", 0) + 1
                    elif "connection" in line_lower:
                        error_counts["connection"] = error_counts.get("connection", 0) + 1
                    elif "rate" in line_lower and "limit" in line_lower:
                        error_counts["rate_limit"] = error_counts.get("rate_limit", 0) + 1
                    else:
                        error_counts["other"] = error_counts.get("other", 0) + 1
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Error reading logs: %s", exc)

    return error_counts


def generate_daily_report(api_url: str) -> dict[str, Any]:
    """Build the daily operations report."""
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # Health check
    health = _fetch_health(api_url)

    # Analytics
    analytics = _fetch_analytics(api_url) or {}

    # Catalog stats
    catalog = _load_catalog()
    previous = _load_previous_daily()
    prev_catalog_size = previous.get("catalog", {}).get("total", 0) if previous else 0

    scores = [s.get("clarvia_score", 0) for s in catalog]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    active = sum(1 for s in catalog if not s.get("inactive"))

    # Error analysis
    errors = _parse_error_logs()

    # Automation results
    automation = _count_automation_results()

    # API metrics from analytics
    api_metrics = {
        "total_requests": analytics.get("total_requests", 0),
        "unique_visitors": analytics.get("unique_visitors", 0),
        "agent_requests": analytics.get("agent_requests", 0),
        "human_requests": analytics.get("human_requests", 0),
        "scans_today": analytics.get("scans_total", 0),
    }

    # Build endpoint breakdown from analytics
    endpoints = analytics.get("endpoints", {})
    top_endpoints = sorted(endpoints.items(), key=lambda x: x[1], reverse=True)[:10]

    report = {
        "date": today,
        "generated_at": now.isoformat(),
        "health": health,
        "api": api_metrics,
        "top_endpoints": dict(top_endpoints),
        "catalog": {
            "total": len(catalog),
            "active": active,
            "inactive": len(catalog) - active,
            "change_from_yesterday": len(catalog) - prev_catalog_size,
            "avg_score": avg_score,
        },
        "errors": {
            "total": sum(errors.values()),
            "by_type": errors,
        },
        "automation": automation,
    }

    return report


def format_telegram(report: dict[str, Any]) -> str:
    """Format daily report as a clean Telegram message."""
    h = report["health"]
    api = report["api"]
    cat = report["catalog"]
    err = report["errors"]
    auto = report["automation"]

    health_icon = "✅" if h.get("healthy") else "🔴"
    health_ms = h.get("response_time_ms", 0)

    lines = [
        f"📋 *Clarvia Daily Report* — {report['date']}",
        "",
        f"*Health*: {health_icon} ({health_ms:.0f}ms)",
        "",
        "*API Traffic:*",
        f"  Requests: {api['total_requests']}",
        f"  Visitors: {api['unique_visitors']}",
        f"  Agent: {api['agent_requests']} | Human: {api['human_requests']}",
        f"  Scans: {api['scans_today']}",
        "",
        "*Catalog:*",
        f"  Total: {cat['total']} (active: {cat['active']})",
        f"  Change: {'+' if cat['change_from_yesterday'] >= 0 else ''}{cat['change_from_yesterday']}",
        f"  Avg score: {cat['avg_score']}",
    ]

    # Errors
    if err["total"] > 0:
        lines.append(f"\n*Errors*: {err['total']}")
        for etype, count in err["by_type"].items():
            lines.append(f"  {etype}: {count}")
    else:
        lines.append("\n*Errors*: None ✅")

    # Automation status
    if auto:
        lines.append("\n*Automation:*")
        if "integration" in auto:
            ig = auto["integration"]
            lines.append(
                f"  Integration: {ig['passed']}/{ig['passed'] + ig['failed']} passed"
            )
        if "link_check" in auto:
            lc = auto["link_check"]
            lines.append(f"  Link check: {lc['dead']} dead / {lc['total']} total")
        if "feedback" in auto:
            fb = auto["feedback"]
            lines.append(
                f"  Feedback: {fb['tools_boosted']} boosted / {fb['tools_processed']} processed"
            )

    # Top endpoints
    if report.get("top_endpoints"):
        lines.append("\n*Top Endpoints:*")
        for ep, count in list(report["top_endpoints"].items())[:5]:
            lines.append(f"  {ep}: {count}")

    return "\n".join(lines)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Clarvia daily operations report")
    parser.add_argument("--dry-run", action="store_true", help="Skip Telegram and writes")
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="Base URL of the Clarvia API",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    report = generate_daily_report(args.api_url)

    # Save report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"daily-{report['date']}.json"

    if not args.dry_run:
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info("Daily report saved to %s", report_path)

    # Format and send
    msg = format_telegram(report)

    if args.dry_run:
        logger.info("[DRY RUN]\n%s", msg)
    else:
        send_message(msg)
        logger.info("Daily report sent via Telegram")

    # Also print JSON for debugging
    print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
