#!/usr/bin/env python3
"""Score Calibration — Analyze and correct score distribution drift.

Clarvia's scoring credibility is its core moat. If scores drift
(e.g., 0% Excellent when 5-10% should qualify), the trust layer breaks.

This script:
1. Pulls current score distribution from the API
2. Compares against target distribution
3. Flags calibration drift with severity
4. Rescores top 500 tools to detect systematic errors
5. Generates a calibration report

Target distribution (based on industry-standard quality curves):
  Excellent (80+): 5-10%
  Strong (60-79):  20-30%
  Moderate (35-59): 35-45%
  Basic (20-34):   15-25%
  Low (<20):        5-15%

Usage:
    python scripts/automation/score_calibration.py [--dry-run] [--rescore-top N]
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = DATA_DIR / "reports"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from telegram_notifier import send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

API_BASE = "https://clarvia-api.onrender.com"

# Target distribution ranges (min%, max%)
# Unified rating system (scanner.py + tool_scorer.py now use same thresholds):
#   Exceptional: 90+  |  Excellent: 80+  |  Strong: 65+
#   Moderate: 45+     |  Basic: 25+      |  Low: <25
TARGET_DISTRIBUTION = {
    "Exceptional": (1.0, 5.0),    # 90+ — top tier, rare by design
    "Excellent": (4.0, 12.0),     # 80-89 — high quality tools
    "Strong": (15.0, 30.0),       # 65-79 — above average
    "Moderate": (30.0, 50.0),     # 45-64 — typical quality
    "Basic": (15.0, 30.0),        # 25-44 — below average
    "Low": (5.0, 20.0),           # <25 — low quality / incomplete data
}


def fetch_score_distribution() -> dict[str, Any]:
    """Fetch current score distribution from the leaderboard/stats endpoint."""
    try:
        resp = requests.get(f"{API_BASE}/v1/leaderboard?limit=100", timeout=15)
        if resp.status_code != 200:
            return {"error": f"API {resp.status_code}"}

        data = resp.json()
        items = data.get("leaderboard", data.get("items", []))

        # Count by rating — unified system
        distribution: dict[str, int] = {
            "Exceptional": 0, "Excellent": 0, "Strong": 0,
            "Moderate": 0, "Basic": 0, "Low": 0,
            "other": 0,  # catch any legacy labels
        }
        scores = []
        for item in items:
            rating = item.get("rating", "")
            score = item.get("clarvia_score", 0)
            if rating in distribution:
                distribution[rating] += 1
            elif rating:
                distribution["other"] += 1  # Legacy label — flag for investigation
            scores.append(score)

        total = len(items)
        return {
            "total_sampled": total,
            "distribution_count": distribution,
            "distribution_pct": {
                k: round(v / total * 100, 1) if total else 0
                for k, v in distribution.items()
            },
            "score_stats": {
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
                "avg": round(sum(scores) / len(scores), 1) if scores else 0,
            },
        }
    except Exception as exc:
        return {"error": str(exc)}


def analyze_drift(distribution_pct: dict[str, float]) -> list[dict[str, Any]]:
    """Compare actual distribution against target. Return drift alerts."""
    alerts = []
    for tier, (min_pct, max_pct) in TARGET_DISTRIBUTION.items():
        actual = distribution_pct.get(tier, 0)
        if actual < min_pct:
            severity = "CRITICAL" if actual < min_pct * 0.5 else "WARNING"
            alerts.append({
                "tier": tier,
                "actual_pct": actual,
                "target_min": min_pct,
                "target_max": max_pct,
                "severity": severity,
                "message": f"{tier} tier at {actual:.1f}% (expected {min_pct}-{max_pct}%) — underscoring likely",
            })
        elif actual > max_pct:
            severity = "WARNING"
            alerts.append({
                "tier": tier,
                "actual_pct": actual,
                "target_min": min_pct,
                "target_max": max_pct,
                "severity": severity,
                "message": f"{tier} tier at {actual:.1f}% (expected {min_pct}-{max_pct}%) — overscoring possible",
            })

    return alerts


def fetch_top_tools(n: int = 100) -> list[dict[str, Any]]:
    """Fetch top N tools by score for detailed inspection."""
    try:
        resp = requests.get(
            f"{API_BASE}/v1/services?limit={n}&sort=score_desc",
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("services", data.get("items", []))
        return []
    except Exception:
        return []


def run(dry_run: bool = False, rescore_top: int = 0) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    logger.info("=== Score Calibration: %s ===", now.isoformat())

    report: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "dry_run": dry_run,
    }

    # 1. Fetch distribution
    dist = fetch_score_distribution()
    report["distribution"] = dist

    if "error" in dist:
        logger.error("Cannot fetch distribution: %s", dist["error"])
        return report

    logger.info("Distribution: %s", dist.get("distribution_pct", {}))
    logger.info("Score stats: %s", dist.get("score_stats", {}))

    # 2. Analyze drift
    drift_alerts = analyze_drift(dist.get("distribution_pct", {}))
    report["drift_alerts"] = drift_alerts

    if drift_alerts:
        for alert in drift_alerts:
            logger.warning("[%s] %s", alert["severity"], alert["message"])
    else:
        logger.info("Score distribution is within target ranges — no calibration needed")

    # 3. Check for 0% Excellent (critical signal of dead code / systematic bug)
    excellent_pct = dist.get("distribution_pct", {}).get("Excellent", 0)
    if excellent_pct == 0:
        report["critical_flag"] = "ZERO_EXCELLENT"
        logger.error(
            "CRITICAL: 0%% Excellent tier. This indicates a systematic scoring bug "
            "(dead code, wrong thresholds, or data pipeline issue). "
            "Run: python backend/app/tool_scorer.py --test to diagnose."
        )

    # 4. Fetch top tools for quality spot check
    if rescore_top > 0:
        top_tools = fetch_top_tools(rescore_top)
        report["top_tools_sample"] = [
            {
                "name": t.get("name"),
                "score": t.get("clarvia_score"),
                "rating": t.get("rating"),
                "type": t.get("service_type"),
            }
            for t in top_tools[:20]
        ]
        logger.info("Fetched %d top tools for spot check", len(top_tools))

    # 5. Save report
    if not dry_run:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / f"calibration-{now.strftime('%Y-%m-%d')}.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        logger.info("Calibration report saved: %s", report_path)

    # 6. Send Telegram alert
    critical = [a for a in drift_alerts if a["severity"] == "CRITICAL"]
    warnings = [a for a in drift_alerts if a["severity"] == "WARNING"]

    lines = [
        f"[Score Calibration] {now.strftime('%Y-%m-%d')}",
        f"",
        f"Distribution (top 100 sample):",
    ]
    for tier, pct in dist.get("distribution_pct", {}).items():
        min_t, max_t = TARGET_DISTRIBUTION.get(tier, (0, 100))
        status = "OK" if min_t <= pct <= max_t else ("CRITICAL" if pct < min_t * 0.5 else "WARN")
        lines.append(f"  {tier}: {pct:.1f}% [{min_t}-{max_t}%] {status}")

    if critical:
        lines.append(f"")
        lines.append(f"CRITICAL ALERTS: {len(critical)}")
        for alert in critical:
            lines.append(f"  - {alert['message']}")

    if warnings:
        lines.append(f"WARNINGS: {len(warnings)}")
        for alert in warnings:
            lines.append(f"  - {alert['message']}")

    if not critical and not warnings:
        lines.append(f"")
        lines.append(f"All tiers within target range. No action needed.")

    try:
        send_message("\n".join(lines))
    except Exception:
        pass

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clarvia Score Calibration")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rescore-top", type=int, default=100, help="Fetch top N tools for spot check")
    args = parser.parse_args()
    result = run(dry_run=args.dry_run, rescore_top=args.rescore_top)
    print(json.dumps(result, indent=2, ensure_ascii=False))
