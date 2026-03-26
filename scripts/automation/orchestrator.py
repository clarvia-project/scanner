#!/usr/bin/env python3
"""Clarvia Automation Orchestrator.

Central scheduler that reads task definitions from config.yaml and
executes them according to their cron schedules.

Features:
  - Cron-based scheduling for each task
  - Timeout enforcement per task
  - Logging to data/automation.log
  - Telegram alerts on task failures
  - Graceful shutdown on SIGTERM/SIGINT

Usage:
  python scripts/automation/orchestrator.py              # start scheduler
  python scripts/automation/orchestrator.py --once       # run all due tasks once
  python scripts/automation/orchestrator.py --dry-run    # preview schedule
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
LOG_PATH = DATA_DIR / "automation.log"
STATE_PATH = DATA_DIR / "orchestrator_state.json"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from telegram_notifier import send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Graceful shutdown flag
_shutdown = False


def _handle_signal(signum: int, frame: Any) -> None:
    global _shutdown
    logger.info("Received signal %d — shutting down gracefully", signum)
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def load_config() -> list[dict]:
    """Load task definitions from config.yaml."""
    if not CONFIG_PATH.exists():
        logger.error("Config file not found: %s", CONFIG_PATH)
        return []

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    raw_tasks = data.get("tasks", {})

    # config.yaml stores tasks as a dict {name: {script, schedule, ...}}.
    # Normalize to a list of dicts, each with a "name" key.
    if isinstance(raw_tasks, dict):
        tasks = []
        for name, cfg in raw_tasks.items():
            if isinstance(cfg, dict):
                cfg["name"] = name
                tasks.append(cfg)
        return tasks

    # Already a list (legacy format)
    return raw_tasks


def load_state() -> dict[str, str]:
    """Load last-run timestamps per task.

    Returns:
        Dict mapping task name to ISO timestamp string.
    """
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


def save_state(state: dict[str, str]) -> None:
    """Persist task run timestamps."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def log_task_event(task_name: str, event: str, detail: str = "") -> None:
    """Append a structured event to the automation log."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": task_name,
        "event": event,
        "detail": detail,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def parse_cron(expr: str) -> dict[str, Any]:
    """Parse a simple cron expression into field specs.

    Supports: minute, hour, day, month, weekday.
    Handles: *, */N, comma-separated values, single values.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (need 5 fields): {expr}")

    fields = ["minute", "hour", "day", "month", "weekday"]
    parsed = {}

    for field_name, part in zip(fields, parts):
        if part == "*":
            parsed[field_name] = None  # match any
        elif part.startswith("*/"):
            parsed[field_name] = {"every": int(part[2:])}
        elif "," in part:
            parsed[field_name] = {"values": [int(v) for v in part.split(",")]}
        else:
            parsed[field_name] = {"value": int(part)}

    return parsed


def cron_matches(cron: dict[str, Any], now: datetime) -> bool:
    """Check if the current time matches a parsed cron schedule."""
    checks = {
        "minute": now.minute,
        "hour": now.hour,
        "day": now.day,
        "month": now.month,
        "weekday": now.weekday(),  # 0=Monday
    }

    for field, spec in cron.items():
        current_val = checks[field]

        if spec is None:
            continue  # wildcard — matches anything
        elif isinstance(spec, dict):
            if "every" in spec:
                if current_val % spec["every"] != 0:
                    return False
            elif "values" in spec:
                if current_val not in spec["values"]:
                    return False
            elif "value" in spec:
                if current_val != spec["value"]:
                    return False

    return True


def is_task_due(task: dict, state: dict[str, str]) -> bool:
    """Determine if a task should run now based on its schedule and last run."""
    if not task.get("enabled", True):
        return False

    schedule = task.get("schedule", "")
    if not schedule:
        return False

    now = datetime.now(timezone.utc)

    try:
        cron = parse_cron(schedule)
    except ValueError:
        # Try as interval in seconds
        try:
            interval = int(schedule)
            last_run_str = state.get(task["name"])
            if not last_run_str:
                return True
            last_run = datetime.fromisoformat(last_run_str)
            return (now - last_run).total_seconds() >= interval
        except ValueError:
            logger.warning("Cannot parse schedule for %s: %s", task["name"], schedule)
            return False

    if not cron_matches(cron, now):
        return False

    # Avoid running the same task twice in the same minute
    last_run_str = state.get(task["name"])
    if last_run_str:
        last_run = datetime.fromisoformat(last_run_str)
        if (now - last_run).total_seconds() < 60:
            return False

    return True


def run_task(task: dict) -> tuple[bool, str]:
    """Execute a single task as a subprocess.

    Returns:
        (success, output_or_error)
    """
    script = task["script"]
    args = task.get("args", [])
    timeout = task.get("timeout", 0) or None

    script_path = PROJECT_ROOT / script
    if not script_path.exists():
        return False, f"Script not found: {script_path}"

    cmd = [sys.executable, str(script_path)] + [str(a) for a in args]
    logger.info("Running task '%s': %s", task["name"], " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
            env={**os.environ},
        )

        output = result.stdout[-500:] if result.stdout else ""
        stderr = result.stderr[-500:] if result.stderr else ""

        if result.returncode == 0:
            return True, output
        else:
            return False, f"Exit code {result.returncode}\nstderr: {stderr}"

    except subprocess.TimeoutExpired:
        return False, f"Timed out after {timeout}s"
    except Exception as exc:
        return False, f"Execution error: {exc}"


def process_tasks(tasks: list[dict], state: dict[str, str], *, dry_run: bool = False) -> int:
    """Check and run all due tasks.

    Returns:
        Number of tasks executed.
    """
    executed = 0

    for task in tasks:
        if _shutdown:
            break

        if not is_task_due(task, state):
            continue

        name = task["name"]

        if dry_run:
            logger.info("[DRY RUN] Would run: %s", name)
            executed += 1
            continue

        log_task_event(name, "started")
        success, detail = run_task(task)
        now_iso = datetime.now(timezone.utc).isoformat()

        if success:
            logger.info("Task '%s' completed successfully", name)
            log_task_event(name, "completed", detail[:200])
        else:
            logger.error("Task '%s' failed: %s", name, detail[:200])
            log_task_event(name, "failed", detail[:500])
            send_alert(
                f"Automation Task Failed: {name}",
                f"Task: `{name}`\nScript: `{task['script']}`\n\n```\n{detail[:300]}\n```",
                level="ERROR",
            )

        state[name] = now_iso
        save_state(state)
        executed += 1

    return executed


def main() -> None:
    parser = argparse.ArgumentParser(description="Clarvia automation orchestrator")
    parser.add_argument("--once", action="store_true", help="Run due tasks once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    parser.add_argument("--tick", type=int, default=30, help="Scheduler tick interval (seconds)")
    args = parser.parse_args()

    tasks = load_config()
    if not tasks:
        logger.error("No tasks loaded from config — exiting")
        sys.exit(1)

    enabled = [t for t in tasks if t.get("enabled", True)]
    logger.info(
        "Loaded %d tasks (%d enabled) from %s",
        len(tasks),
        len(enabled),
        CONFIG_PATH.name,
    )

    state = load_state()

    if args.once:
        executed = process_tasks(tasks, state, dry_run=args.dry_run)
        logger.info("Single run complete — %d tasks executed", executed)
        return

    logger.info("Starting orchestrator loop (tick=%ds)", args.tick)
    send_alert(
        "Clarvia Orchestrator Started",
        f"Tasks loaded: {len(enabled)} enabled\nTick interval: {args.tick}s",
        level="INFO",
    )

    while not _shutdown:
        try:
            process_tasks(tasks, state, dry_run=args.dry_run)
        except Exception:
            logger.exception("Orchestrator loop error")

        # Sleep in small increments to respond quickly to shutdown signals
        for _ in range(args.tick):
            if _shutdown:
                break
            time.sleep(1)

    logger.info("Orchestrator stopped")


if __name__ == "__main__":
    main()
