#!/usr/bin/env python3
"""Clarvia Healthcheck & Auto-Recovery System.

Monitors API and frontend endpoints, tracks uptime, and triggers alerts
or Render redeployment on consecutive failures.

Endpoints checked:
  - https://clarvia-api.onrender.com/health (JSON health endpoint)
  - https://clarvia.art (HTTP 200 check)

Usage:
  python scripts/healthcheck.py                # single check
  python scripts/healthcheck.py --loop         # continuous monitoring (every 5 min)
  python scripts/healthcheck.py --dry-run      # test without alerts
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

# Resolve project paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_PATH = DATA_DIR / "healthcheck.log"

sys.path.insert(0, str(SCRIPT_DIR))
from telegram_notifier import send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# --- Configuration ---
ENDPOINTS = [
    {
        "name": "Clarvia API",
        "url": "https://clarvia-api.onrender.com/health",
        "check_type": "json_health",
    },
    {
        "name": "Clarvia Frontend",
        "url": "https://clarvia.art",
        "check_type": "http_200",
    },
]

CHECK_INTERVAL = 300  # 5 minutes
FAILURE_THRESHOLD = 3  # consecutive failures before alerting
RENDER_API_KEY = os.environ.get("RENDER_API_KEY", "")
RENDER_SERVICE_ID = os.environ.get("RENDER_SERVICE_ID", "")

# --- State tracking ---
_failure_counts: dict[str, int] = {}
_total_checks: dict[str, int] = {}
_total_successes: dict[str, int] = {}


def check_endpoint(endpoint: dict) -> tuple[bool, str]:
    """Check a single endpoint's health.

    Returns:
        (is_healthy, detail_message)
    """
    url = endpoint["url"]
    check_type = endpoint["check_type"]

    try:
        resp = requests.get(url, timeout=15, allow_redirects=True)

        if check_type == "json_health":
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    status = data.get("status", "unknown")
                    if status == "healthy":
                        return True, f"status={status}"
                    return False, f"unhealthy status={status}"
                except (json.JSONDecodeError, ValueError):
                    return False, f"invalid JSON response (HTTP {resp.status_code})"
            return False, f"HTTP {resp.status_code}"

        elif check_type == "http_200":
            if resp.status_code == 200:
                return True, "HTTP 200 OK"
            return False, f"HTTP {resp.status_code}"

        return False, f"unknown check_type: {check_type}"

    except requests.ConnectionError:
        return False, "connection refused"
    except requests.Timeout:
        return False, "timeout (15s)"
    except requests.RequestException as exc:
        return False, f"request error: {exc}"


def log_check(name: str, healthy: bool, detail: str) -> None:
    """Append check result to the healthcheck log file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": name,
        "healthy": healthy,
        "detail": detail,
    }

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_uptime_pct(name: str) -> float:
    """Calculate uptime percentage for an endpoint."""
    total = _total_checks.get(name, 0)
    if total == 0:
        return 100.0
    success = _total_successes.get(name, 0)
    return round((success / total) * 100, 2)


def trigger_render_redeploy() -> bool:
    """Trigger a Render service redeployment via their API."""
    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        logger.info("Render API credentials not configured — skipping redeploy")
        return False

    url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/deploys"
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, headers=headers, json={"clearCache": "do_not_clear"}, timeout=15)
        if resp.status_code in (200, 201):
            logger.info("Render redeploy triggered successfully")
            return True
        logger.warning("Render redeploy returned %d: %s", resp.status_code, resp.text[:200])
    except requests.RequestException as exc:
        logger.error("Render redeploy request failed: %s", exc)

    return False


def run_checks(*, dry_run: bool = False) -> dict[str, bool]:
    """Run health checks on all endpoints.

    Returns:
        Dict mapping endpoint name to health status.
    """
    results: dict[str, bool] = {}

    for ep in ENDPOINTS:
        name = ep["name"]
        healthy, detail = check_endpoint(ep)

        # Track totals
        _total_checks[name] = _total_checks.get(name, 0) + 1
        if healthy:
            _total_successes[name] = _total_successes.get(name, 0) + 1
            _failure_counts[name] = 0
        else:
            _failure_counts[name] = _failure_counts.get(name, 0) + 1

        log_check(name, healthy, detail)
        uptime = get_uptime_pct(name)
        failures = _failure_counts.get(name, 0)

        if healthy:
            logger.info("✅ %s — %s (uptime: %.1f%%)", name, detail, uptime)
        else:
            logger.warning(
                "❌ %s — %s (failures: %d/%d, uptime: %.1f%%)",
                name, detail, failures, FAILURE_THRESHOLD, uptime,
            )

        # Alert on consecutive failures
        if failures >= FAILURE_THRESHOLD:
            body = (
                f"Endpoint: `{ep['url']}`\n"
                f"Detail: {detail}\n"
                f"Consecutive failures: {failures}\n"
                f"Uptime: {uptime}%"
            )
            if not dry_run:
                send_alert(f"{name} DOWN", body, level="CRITICAL")

                # Attempt auto-recovery for API
                if ep["check_type"] == "json_health":
                    redeployed = trigger_render_redeploy()
                    if redeployed:
                        send_alert(
                            f"{name} Auto-Recovery",
                            "Render redeploy triggered automatically.",
                            level="INFO",
                        )
            else:
                logger.info("[DRY RUN] Would send alert: %s DOWN", name)

            # Reset counter to avoid spamming every check cycle
            _failure_counts[name] = 0

        results[name] = healthy

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Clarvia healthcheck system")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL, help="Seconds between checks")
    parser.add_argument("--dry-run", action="store_true", help="Disable actual alerts/redeploys")
    args = parser.parse_args()

    if args.loop:
        logger.info("Starting healthcheck loop (interval=%ds)", args.interval)
        while True:
            try:
                run_checks(dry_run=args.dry_run)
            except Exception:
                logger.exception("Healthcheck loop error")
            time.sleep(args.interval)
    else:
        results = run_checks(dry_run=args.dry_run)
        all_ok = all(results.values())
        sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
