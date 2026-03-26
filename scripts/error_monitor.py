#!/usr/bin/env python3
"""Clarvia Error Monitoring — detects error spikes and sends Telegram alerts.

Monitors the Render service logs (via API) or a local log file for:
  - 500 error spikes (>5 in 5 minutes)
  - Memory warnings
  - Crash loops (repeated restarts)

Includes cooldown logic to avoid spamming the same error type within 30 minutes.

Usage:
  python scripts/error_monitor.py                # single scan
  python scripts/error_monitor.py --loop         # continuous monitoring
  python scripts/error_monitor.py --source file  # monitor local log file
  python scripts/error_monitor.py --dry-run      # test without alerts
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
MONITOR_STATE_PATH = DATA_DIR / "error_monitor_state.json"

sys.path.insert(0, str(SCRIPT_DIR))
from telegram_notifier import send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# --- Configuration ---
RENDER_API_KEY = os.environ.get("RENDER_API_KEY", "")
RENDER_SERVICE_ID = os.environ.get("RENDER_SERVICE_ID", "")
CHECK_INTERVAL = 300  # 5 minutes
ERROR_THRESHOLD = 5  # errors in window to trigger alert
ERROR_WINDOW = 300  # 5-minute window for counting errors
COOLDOWN_SECONDS = 1800  # 30-minute cooldown per error type
LOCAL_LOG_PATH = DATA_DIR / "app.log"  # fallback log file

# --- State ---
_last_alert_time: dict[str, float] = {}
_error_buffer: list[dict] = []


def load_state() -> None:
    """Load persisted cooldown state."""
    global _last_alert_time
    if MONITOR_STATE_PATH.exists():
        try:
            with open(MONITOR_STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
            _last_alert_time = {k: float(v) for k, v in state.get("last_alert_time", {}).items()}
        except (json.JSONDecodeError, ValueError):
            _last_alert_time = {}


def save_state() -> None:
    """Persist cooldown state to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state = {"last_alert_time": _last_alert_time}
    with open(MONITOR_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f)


def is_on_cooldown(error_type: str) -> bool:
    """Check if an error type is within the cooldown window."""
    last = _last_alert_time.get(error_type, 0)
    return (time.time() - last) < COOLDOWN_SECONDS


def mark_alerted(error_type: str) -> None:
    """Record that we sent an alert for this error type."""
    _last_alert_time[error_type] = time.time()
    save_state()


def fetch_render_logs() -> list[dict]:
    """Fetch recent logs from Render API.

    Returns:
        List of log entry dicts with 'timestamp' and 'message' keys.
    """
    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        logger.debug("Render API not configured — skipping remote log fetch")
        return []

    url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/logs"
    headers = {"Authorization": f"Bearer {RENDER_API_KEY}"}
    params = {"limit": 200}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            logs = resp.json()
            if isinstance(logs, list):
                return logs
            return logs.get("logs", logs.get("data", []))
        logger.warning("Render logs API returned %d", resp.status_code)
    except requests.RequestException as exc:
        logger.warning("Failed to fetch Render logs: %s", exc)

    return []


def read_local_logs(path: Path, since_minutes: int = 10) -> list[dict]:
    """Read recent entries from a local JSONL log file.

    Args:
        path: Path to the log file (one JSON object per line).
        since_minutes: Only return entries from the last N minutes.

    Returns:
        List of log entry dicts.
    """
    if not path.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    entries = []

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts_str = entry.get("timestamp", "")
                    if ts_str:
                        ts = datetime.fromisoformat(ts_str)
                        if ts >= cutoff:
                            entries.append(entry)
                    else:
                        entries.append(entry)
                except (json.JSONDecodeError, ValueError):
                    # Try plain text parsing
                    entries.append({"message": line, "timestamp": ""})
    except OSError as exc:
        logger.warning("Failed to read local log %s: %s", path, exc)

    return entries


def classify_errors(logs: list[dict]) -> dict[str, list[dict]]:
    """Classify log entries into error categories.

    Returns:
        Dict mapping error_type to list of matching log entries.
    """
    categories: dict[str, list[dict]] = defaultdict(list)

    for entry in logs:
        msg = entry.get("message", "")
        level = entry.get("level", "").upper()

        # 500 errors
        if re.search(r"\b5\d{2}\b", msg) or "Internal Server Error" in msg:
            categories["500_errors"].append(entry)

        # Memory warnings
        if re.search(r"(?i)(memory|oom|out of memory|mem_usage)", msg):
            categories["memory_warning"].append(entry)

        # Crash loops / restarts
        if re.search(r"(?i)(crash|restart|sigterm|sigkill|killed|exited)", msg):
            categories["crash_loop"].append(entry)

        # Generic errors
        if level in ("ERROR", "CRITICAL", "FATAL"):
            categories["generic_errors"].append(entry)

    return categories


def analyze_and_alert(logs: list[dict], *, dry_run: bool = False) -> int:
    """Analyze logs for error patterns and send alerts.

    Returns:
        Number of alerts sent.
    """
    alerts_sent = 0
    categories = classify_errors(logs)

    for error_type, entries in categories.items():
        count = len(entries)

        # Check threshold
        if error_type == "500_errors" and count < ERROR_THRESHOLD:
            continue
        if error_type == "memory_warning" and count < 2:
            continue
        if error_type == "crash_loop" and count < 3:
            continue
        if error_type == "generic_errors" and count < ERROR_THRESHOLD:
            continue

        # Check cooldown
        if is_on_cooldown(error_type):
            logger.info("Skipping %s alert — on cooldown", error_type)
            continue

        # Build alert message
        sample = entries[0].get("message", "no message")[:300]
        titles = {
            "500_errors": "500 Error Spike",
            "memory_warning": "Memory Warning",
            "crash_loop": "Crash Loop Detected",
            "generic_errors": "Error Spike",
        }
        title = titles.get(error_type, error_type)

        body = (
            f"Type: `{error_type}`\n"
            f"Count: {count} in last {ERROR_WINDOW // 60} min\n"
            f"Sample:\n```\n{sample}\n```"
        )

        if dry_run:
            logger.info("[DRY RUN] Would alert: %s — %d occurrences", error_type, count)
        else:
            send_alert(f"Clarvia {title}", body, level="ERROR")
            mark_alerted(error_type)

        alerts_sent += 1

    return alerts_sent


def run_scan(*, source: str = "auto", dry_run: bool = False) -> int:
    """Run a single monitoring scan.

    Args:
        source: "render" for Render API, "file" for local log, "auto" tries both.
        dry_run: If True, skip actual alerts.

    Returns:
        Number of alerts sent.
    """
    logs: list[dict] = []

    if source in ("render", "auto"):
        render_logs = fetch_render_logs()
        if render_logs:
            logs.extend(render_logs)
            logger.info("Fetched %d log entries from Render API", len(render_logs))

    if source in ("file", "auto"):
        local_logs = read_local_logs(LOCAL_LOG_PATH)
        if local_logs:
            logs.extend(local_logs)
            logger.info("Read %d log entries from local file", len(local_logs))

    if not logs:
        logger.info("No log entries to analyze")
        return 0

    return analyze_and_alert(logs, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clarvia error monitor")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL)
    parser.add_argument("--source", choices=["auto", "render", "file"], default="auto")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_state()

    if args.loop:
        logger.info("Starting error monitor loop (interval=%ds)", args.interval)
        while True:
            try:
                alerts = run_scan(source=args.source, dry_run=args.dry_run)
                if alerts:
                    logger.info("Sent %d alerts", alerts)
            except Exception:
                logger.exception("Error monitor loop error")
            time.sleep(args.interval)
    else:
        alerts = run_scan(source=args.source, dry_run=args.dry_run)
        print(f"Scan complete — {alerts} alert(s) sent")


if __name__ == "__main__":
    main()
