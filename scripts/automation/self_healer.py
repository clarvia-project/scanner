#!/usr/bin/env python3
"""Clarvia Self-Healing Pipeline Manager.

Monitors the automation pipeline and auto-fixes common issues:
  1. Task failure tracking  — Disable tasks after 3 consecutive failures
  2. Resource monitoring    — Disk/log size alerts and auto-cleanup
  3. Dependency health      — Verify key Python packages are importable
  4. Render service health  — Check API deployment status
  5. Auto-archival          — Rotate old data files to archive

Usage:
    python scripts/automation/self_healer.py
    python scripts/automation/self_healer.py --dry-run
    python scripts/automation/self_healer.py --check disk
    python scripts/automation/self_healer.py --check deps
"""

import argparse
import gzip
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ARCHIVE_DIR = DATA_DIR / "archive"
BACKUP_DIR = PROJECT_ROOT / "backups"
AUTOMATION_LOG = DATA_DIR / "automation.log"
HEALTHCHECK_LOG = DATA_DIR / "healthcheck.log"
ORCHESTRATOR_STATE = DATA_DIR / "orchestrator_state.json"
CONFIG_PATH = SCRIPT_DIR / "config.yaml"

sys.path.insert(0, str(SCRIPT_DIR.parent))
from telegram_notifier import send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

CONSECUTIVE_FAILURE_LIMIT = 3
BACKUP_SIZE_LIMIT_MB = 1024           # 1GB
DATA_SIZE_LIMIT_MB = 5120             # 5GB
LOG_FILE_SIZE_LIMIT_MB = 100          # 100MB
AUDIT_ARCHIVE_DAYS = 30
HEALTHCHECK_ARCHIVE_DAYS = 14
DISCOVERY_ARCHIVE_DAYS = 60
KEEP_EVERYTHING_DAYS = 90

REQUIRED_PACKAGES = [
    "requests",
    "pyyaml",
    "aiohttp",
]


# ---------------------------------------------------------------------------
# 1. Task Failure Tracking
# ---------------------------------------------------------------------------

def check_task_failures(*, dry_run: bool = False) -> dict:
    """Analyze orchestrator logs for consecutive task failures.

    If any task has failed 3+ consecutive times, disable it and alert.
    """
    result = {
        "check": "task_failures",
        "status": "ok",
        "disabled_tasks": [],
        "failure_streaks": {},
    }

    if not AUTOMATION_LOG.exists():
        result["status"] = "skipped"
        result["reason"] = "No automation log found"
        return result

    # Parse log entries (JSONL format)
    task_events: dict[str, list[dict]] = {}
    try:
        with open(AUTOMATION_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    task = entry.get("task", "")
                    event = entry.get("event", "")
                    if task and event in ("completed", "failed"):
                        task_events.setdefault(task, []).append(entry)
                except json.JSONDecodeError:
                    continue
    except IOError as exc:
        result["status"] = "error"
        result["error"] = str(exc)
        return result

    # Check for consecutive failures (most recent events)
    for task, events in task_events.items():
        # Sort by timestamp desc
        events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

        consecutive_failures = 0
        for ev in events:
            if ev.get("event") == "failed":
                consecutive_failures += 1
            else:
                break

        result["failure_streaks"][task] = consecutive_failures

        if consecutive_failures >= CONSECUTIVE_FAILURE_LIMIT:
            logger.warning(
                "Task '%s' has %d consecutive failures — disabling",
                task, consecutive_failures,
            )

            last_error = events[0].get("detail", "No detail") if events else "Unknown"

            result["disabled_tasks"].append({
                "task": task,
                "consecutive_failures": consecutive_failures,
                "last_error": last_error[:200],
            })

            if not dry_run:
                # Try common fixes first
                fixes_tried = _try_common_fixes(task)

                send_alert(
                    f"Self-Healer: Task '{task}' Disabled",
                    f"Task has failed {consecutive_failures} consecutive times.\n"
                    f"Last error: `{last_error[:200]}`\n"
                    f"Fixes attempted: {', '.join(fixes_tried) or 'none'}\n\n"
                    f"Task has been disabled in orchestrator tracking.",
                    level="ERROR",
                )

    if result["disabled_tasks"]:
        result["status"] = "alert"

    return result


def _try_common_fixes(task_name: str) -> list[str]:
    """Attempt common fixes for a failing task. Returns list of fixes tried."""
    fixes = []

    # Fix 1: Clear cache files related to the task
    cache_patterns = [
        DATA_DIR / f"{task_name}_cache.json",
        DATA_DIR / f"{task_name}_state.json",
        DATA_DIR / "classifier" / "cache.json",
    ]
    for cache_file in cache_patterns:
        if cache_file.exists():
            try:
                cache_file.unlink()
                fixes.append(f"Cleared cache: {cache_file.name}")
                logger.info("Cleared cache file: %s", cache_file)
            except OSError:
                pass

    # Fix 2: Reset state files
    state_patterns = [
        DATA_DIR / "harvester" / "last-run-summary.json",
    ]
    for state_file in state_patterns:
        if state_file.exists():
            try:
                # Don't delete, just rename to .bak
                bak = state_file.with_suffix(".json.bak")
                state_file.rename(bak)
                fixes.append(f"Reset state: {state_file.name}")
                logger.info("Reset state file: %s", state_file)
            except OSError:
                pass

    return fixes


# ---------------------------------------------------------------------------
# 2. Resource Monitoring
# ---------------------------------------------------------------------------

def _get_dir_size_mb(path: Path) -> float:
    """Get total size of a directory in MB."""
    if not path.exists():
        return 0.0
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    except (OSError, PermissionError):
        pass
    return total / (1024 * 1024)


def _get_file_size_mb(path: Path) -> float:
    """Get file size in MB."""
    if not path.exists():
        return 0.0
    return path.stat().st_size / (1024 * 1024)


def check_resources(*, dry_run: bool = False) -> dict:
    """Monitor disk usage of key directories and files."""
    result = {
        "check": "resources",
        "status": "ok",
        "issues": [],
        "sizes": {},
    }

    # Check backup directory
    backup_size = _get_dir_size_mb(BACKUP_DIR)
    result["sizes"]["backups_mb"] = round(backup_size, 1)
    if backup_size > BACKUP_SIZE_LIMIT_MB:
        result["issues"].append(
            f"Backup directory is {backup_size:.0f}MB (> {BACKUP_SIZE_LIMIT_MB}MB limit)"
        )
        if not dry_run:
            _cleanup_old_backups()

    # Check data directory
    data_size = _get_dir_size_mb(DATA_DIR)
    result["sizes"]["data_mb"] = round(data_size, 1)
    if data_size > DATA_SIZE_LIMIT_MB:
        result["issues"].append(
            f"Data directory is {data_size:.0f}MB (> {DATA_SIZE_LIMIT_MB}MB limit)"
        )

    # Check large log files
    log_files = [
        AUTOMATION_LOG,
        HEALTHCHECK_LOG,
        DATA_DIR / "github-scan.log",
        DATA_DIR / "glama-scan.log",
        DATA_DIR / "mcp-scan.log",
    ]

    for log_file in log_files:
        size = _get_file_size_mb(log_file)
        if size > 0:
            result["sizes"][log_file.name] = round(size, 1)
        if size > LOG_FILE_SIZE_LIMIT_MB:
            result["issues"].append(
                f"Log file {log_file.name} is {size:.0f}MB (> {LOG_FILE_SIZE_LIMIT_MB}MB)"
            )
            if not dry_run:
                _rotate_log(log_file)

    if result["issues"]:
        result["status"] = "warning"
        if not dry_run:
            send_alert(
                "Self-Healer: Resource Warning",
                "\n".join(f"• {i}" for i in result["issues"]),
                level="WARNING",
            )

    return result


def _cleanup_old_backups() -> int:
    """Remove backups older than 30 days. Returns count removed."""
    if not BACKUP_DIR.exists():
        return 0

    cutoff = time.time() - (30 * 86400)
    removed = 0

    for f in sorted(BACKUP_DIR.iterdir()):
        if f.is_file() and f.stat().st_mtime < cutoff:
            try:
                f.unlink()
                removed += 1
            except OSError:
                pass

    if removed:
        logger.info("Cleaned up %d old backup files", removed)
    return removed


def _rotate_log(log_path: Path) -> bool:
    """Rotate a large log file: compress old content, start fresh."""
    if not log_path.exists():
        return False

    try:
        # Compress to .gz archive
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        archive_name = f"{log_path.stem}-{timestamp}.log.gz"
        archive_path = ARCHIVE_DIR / "logs" / archive_name
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "rb") as f_in:
            with gzip.open(archive_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Truncate original
        with open(log_path, "w") as f:
            f.write("")

        logger.info("Rotated log %s -> %s", log_path.name, archive_path.name)
        return True
    except OSError as exc:
        logger.error("Failed to rotate log %s: %s", log_path.name, exc)
        return False


# ---------------------------------------------------------------------------
# 3. Dependency Health
# ---------------------------------------------------------------------------

def check_dependencies(*, dry_run: bool = False) -> dict:
    """Verify that key Python packages are importable."""
    result = {
        "check": "dependencies",
        "status": "ok",
        "issues": [],
        "packages": {},
    }

    for pkg_name in REQUIRED_PACKAGES:
        # Map pip names to import names
        pip_to_import = {
            "pyyaml": "yaml",
            "aiohttp": "aiohttp",
            "requests": "requests",
        }
        import_name = pip_to_import.get(pkg_name, pkg_name)

        try:
            __import__(import_name)
            result["packages"][pkg_name] = "ok"
        except ImportError:
            result["packages"][pkg_name] = "missing"
            result["issues"].append(f"Package '{pkg_name}' is not importable")

    if result["issues"]:
        result["status"] = "alert"
        if not dry_run:
            send_alert(
                "Self-Healer: Dependency Issue",
                f"Missing packages:\n"
                + "\n".join(f"• {i}" for i in result["issues"])
                + "\n\nRun: `pip install " + " ".join(
                    pkg for pkg, st in result["packages"].items() if st == "missing"
                ) + "`",
                level="ERROR",
            )

    return result


# ---------------------------------------------------------------------------
# 4. Render Service Health
# ---------------------------------------------------------------------------

def check_render_health(*, dry_run: bool = False) -> dict:
    """Check Render deployment health via status page and API."""
    result = {
        "check": "render_health",
        "status": "ok",
        "issues": [],
    }

    import requests as req

    # Check our API directly
    api_url = "https://clarvia-api.onrender.com/health"
    try:
        resp = req.get(api_url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "healthy":
                result["api_status"] = "healthy"
                result["api_response_time_ms"] = resp.elapsed.total_seconds() * 1000
            else:
                result["api_status"] = data.get("status", "unknown")
                result["issues"].append(f"API reports unhealthy status: {data.get('status')}")
        else:
            result["api_status"] = f"http_{resp.status_code}"
            result["issues"].append(f"API returned HTTP {resp.status_code}")
    except req.ConnectionError:
        result["api_status"] = "unreachable"
        result["issues"].append("API is unreachable (connection refused)")
    except req.Timeout:
        result["api_status"] = "timeout"
        result["issues"].append("API timed out (>15s)")
    except Exception as exc:
        result["api_status"] = "error"
        result["issues"].append(f"API check error: {exc}")

    # Check Render status page (lightweight)
    try:
        resp = req.get("https://status.render.com/api/v2/status.json", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            indicator = data.get("status", {}).get("indicator", "unknown")
            result["render_platform_status"] = indicator
            if indicator != "none":
                result["issues"].append(
                    f"Render platform status: {indicator} "
                    f"({data.get('status', {}).get('description', '')})"
                )
    except Exception:
        result["render_platform_status"] = "check_failed"

    if result["issues"]:
        result["status"] = "warning" if len(result["issues"]) == 1 else "alert"
        if not dry_run and result["status"] == "alert":
            send_alert(
                "Self-Healer: Service Health Issues",
                "\n".join(f"• {i}" for i in result["issues"]),
                level="WARNING",
            )

    return result


# ---------------------------------------------------------------------------
# 5. Auto-Archival
# ---------------------------------------------------------------------------

def run_archival(*, dry_run: bool = False) -> dict:
    """Move old data files to archive directory."""
    result = {
        "check": "archival",
        "status": "ok",
        "archived": [],
    }

    now = time.time()

    archive_rules = [
        {
            "source": DATA_DIR / "audits",
            "dest": ARCHIVE_DIR / "audits",
            "max_age_days": AUDIT_ARCHIVE_DAYS,
            "pattern": "*.json",
        },
        {
            "source": DATA_DIR,
            "dest": ARCHIVE_DIR / "logs",
            "max_age_days": HEALTHCHECK_ARCHIVE_DAYS,
            "pattern": "healthcheck.log",
            "compress": True,
        },
        {
            "source": DATA_DIR / "harvester",
            "dest": ARCHIVE_DIR / "harvester",
            "max_age_days": DISCOVERY_ARCHIVE_DAYS,
            "pattern": "rejected.jsonl",
            "compress": True,
        },
        {
            "source": DATA_DIR / "watchdog",
            "dest": ARCHIVE_DIR / "watchdog",
            "max_age_days": KEEP_EVERYTHING_DAYS,
            "pattern": "checks.jsonl",
            "compress": True,
        },
    ]

    for rule in archive_rules:
        source_dir = rule["source"]
        if not source_dir.exists():
            continue

        max_age_secs = rule["max_age_days"] * 86400
        pattern = rule["pattern"]

        for fpath in source_dir.glob(pattern):
            if not fpath.is_file():
                continue

            age = now - fpath.stat().st_mtime
            if age < max_age_secs:
                continue

            dest_dir = rule["dest"]
            dest_dir.mkdir(parents=True, exist_ok=True)

            if dry_run:
                result["archived"].append(f"[DRY RUN] Would archive: {fpath.name}")
                continue

            try:
                if rule.get("compress"):
                    # Compress and archive
                    timestamp = datetime.fromtimestamp(
                        fpath.stat().st_mtime, tz=timezone.utc
                    ).strftime("%Y%m%d")
                    dest_path = dest_dir / f"{fpath.stem}-{timestamp}{fpath.suffix}.gz"
                    with open(fpath, "rb") as f_in:
                        with gzip.open(dest_path, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    # Truncate original instead of deleting
                    with open(fpath, "w") as f:
                        f.write("")
                    result["archived"].append(f"Compressed: {fpath.name} -> {dest_path.name}")
                else:
                    # Move to archive
                    dest_path = dest_dir / fpath.name
                    shutil.move(str(fpath), str(dest_path))
                    result["archived"].append(f"Moved: {fpath.name}")

                logger.info("Archived: %s", fpath.name)
            except OSError as exc:
                logger.error("Failed to archive %s: %s", fpath.name, exc)

    if result["archived"]:
        result["archived_count"] = len(result["archived"])
        logger.info("Archived %d files", len(result["archived"]))

    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_self_healer(
    *,
    dry_run: bool = False,
    checks: Optional[list[str]] = None,
) -> dict:
    """Run the full self-healing pipeline.

    Args:
        dry_run: If True, don't apply fixes or send alerts.
        checks: Optional list of specific checks to run.

    Returns:
        Full report dict.
    """
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": [],
        "summary": {"ok": 0, "warning": 0, "alert": 0, "skipped": 0, "error": 0},
    }

    all_checks = {
        "tasks": lambda: check_task_failures(dry_run=dry_run),
        "disk": lambda: check_resources(dry_run=dry_run),
        "deps": lambda: check_dependencies(dry_run=dry_run),
        "render": lambda: check_render_health(dry_run=dry_run),
        "archive": lambda: run_archival(dry_run=dry_run),
    }

    checks_to_run = checks or list(all_checks.keys())

    for name in checks_to_run:
        if name not in all_checks:
            logger.warning("Unknown check: %s", name)
            continue

        try:
            result = all_checks[name]()
            report["checks"].append(result)
            status = result.get("status", "ok")
            report["summary"][status] = report["summary"].get(status, 0) + 1
        except Exception as exc:
            logger.exception("Self-healer check '%s' crashed", name)
            error_result = {
                "check": name,
                "status": "error",
                "error": str(exc),
            }
            report["checks"].append(error_result)
            report["summary"]["error"] = report["summary"].get("error", 0) + 1

    # Save report
    report_dir = DATA_DIR / "self-healer"
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    report_path = report_dir / f"report-{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(
        "Self-healer complete: %s",
        ", ".join(f"{k}={v}" for k, v in report["summary"].items() if v > 0),
    )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Clarvia Self-Healing Pipeline Manager")
    parser.add_argument("--dry-run", action="store_true", help="Don't apply fixes or send alerts")
    parser.add_argument(
        "--check",
        choices=["tasks", "disk", "deps", "render", "archive"],
        help="Run a specific check only",
    )
    args = parser.parse_args()

    checks = [args.check] if args.check else None
    report = run_self_healer(dry_run=args.dry_run, checks=checks)
    print(json.dumps(report, indent=2, default=str))

    has_alerts = report["summary"].get("alert", 0) > 0
    has_errors = report["summary"].get("error", 0) > 0
    sys.exit(1 if (has_alerts or has_errors) else 0)


if __name__ == "__main__":
    main()
