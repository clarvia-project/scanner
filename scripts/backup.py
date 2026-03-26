#!/usr/bin/env python3
"""Clarvia Daily Backup System.

Creates compressed backups of critical data and configuration files.
Manages retention (keeps last 7 days) and sends Telegram notifications.

Backed up:
  - data/ (catalog, tickets, scan results, API keys)
  - backend/app/ configs

Usage:
  python scripts/backup.py               # run backup now
  python scripts/backup.py --dry-run     # preview without creating archive
  python scripts/backup.py --retain 14   # keep last 14 days
"""

import argparse
import glob
import logging
import os
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
BACKUP_DIR = PROJECT_ROOT / "backups"

sys.path.insert(0, str(SCRIPT_DIR))
from telegram_notifier import send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Directories/files to back up (relative to PROJECT_ROOT)
BACKUP_TARGETS = [
    "data",
    "backend/app/config.py",
    "backend/app/main.py",
    "render.yaml",
    ".env",
]

DEFAULT_RETAIN_DAYS = 7
BACKUP_PREFIX = "clarvia-backup-"


def collect_files(targets: list[str]) -> list[Path]:
    """Resolve backup targets to actual file paths.

    Returns:
        List of existing file paths to include in the archive.
    """
    files: list[Path] = []

    for target in targets:
        full_path = PROJECT_ROOT / target
        if full_path.is_dir():
            for child in full_path.rglob("*"):
                if child.is_file() and "__pycache__" not in str(child):
                    files.append(child)
        elif full_path.is_file():
            files.append(full_path)
        else:
            logger.debug("Backup target not found, skipping: %s", target)

    return files


def create_backup(*, dry_run: bool = False) -> Path | None:
    """Create a timestamped tar.gz backup archive.

    Returns:
        Path to the created archive, or None on failure/dry-run.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_name = f"{BACKUP_PREFIX}{timestamp}.tar.gz"
    archive_path = BACKUP_DIR / archive_name

    files = collect_files(BACKUP_TARGETS)
    if not files:
        logger.warning("No files found to back up")
        return None

    total_size = sum(f.stat().st_size for f in files)
    logger.info(
        "Backing up %d files (%.1f MB) -> %s",
        len(files),
        total_size / (1024 * 1024),
        archive_name,
    )

    if dry_run:
        logger.info("[DRY RUN] Would create %s with %d files", archive_name, len(files))
        for f in files[:10]:
            logger.info("  - %s", f.relative_to(PROJECT_ROOT))
        if len(files) > 10:
            logger.info("  ... and %d more", len(files) - 10)
        return None

    start_time = time.time()
    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            for file_path in files:
                arcname = file_path.relative_to(PROJECT_ROOT)
                tar.add(file_path, arcname=str(arcname))

        elapsed = time.time() - start_time
        archive_size = archive_path.stat().st_size
        logger.info(
            "Backup complete: %s (%.1f MB, %.1fs)",
            archive_name,
            archive_size / (1024 * 1024),
            elapsed,
        )
        return archive_path

    except Exception as exc:
        logger.error("Backup creation failed: %s", exc)
        return None


def cleanup_old_backups(retain_days: int = DEFAULT_RETAIN_DAYS) -> int:
    """Delete backups older than retain_days.

    Returns:
        Number of deleted archives.
    """
    if not BACKUP_DIR.exists():
        return 0

    pattern = str(BACKUP_DIR / f"{BACKUP_PREFIX}*.tar.gz")
    archives = sorted(glob.glob(pattern))
    deleted = 0

    # Keep the most recent `retain_days` archives
    if len(archives) > retain_days:
        to_delete = archives[: len(archives) - retain_days]
        for path in to_delete:
            try:
                os.remove(path)
                logger.info("Deleted old backup: %s", Path(path).name)
                deleted += 1
            except OSError as exc:
                logger.warning("Failed to delete %s: %s", path, exc)

    return deleted


def run_backup(*, retain_days: int = DEFAULT_RETAIN_DAYS, dry_run: bool = False) -> bool:
    """Run the full backup pipeline: create + cleanup + notify.

    Returns:
        True if backup succeeded.
    """
    logger.info("Starting Clarvia backup...")

    archive_path = create_backup(dry_run=dry_run)

    if dry_run:
        logger.info("[DRY RUN] Backup preview complete")
        return True

    if archive_path is None:
        send_alert(
            "Clarvia Backup FAILED",
            "Failed to create daily backup archive.\nCheck automation logs for details.",
            level="ERROR",
        )
        return False

    deleted = cleanup_old_backups(retain_days=retain_days)
    archive_size_mb = archive_path.stat().st_size / (1024 * 1024)

    # Count remaining backups
    remaining = len(glob.glob(str(BACKUP_DIR / f"{BACKUP_PREFIX}*.tar.gz")))

    send_alert(
        "Clarvia Backup Complete",
        (
            f"Archive: `{archive_path.name}`\n"
            f"Size: {archive_size_mb:.1f} MB\n"
            f"Old backups removed: {deleted}\n"
            f"Total backups on disk: {remaining}"
        ),
        level="SUCCESS",
    )

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Clarvia daily backup")
    parser.add_argument("--retain", type=int, default=DEFAULT_RETAIN_DAYS, help="Days to retain")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating archive")
    args = parser.parse_args()

    success = run_backup(retain_days=args.retain, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
