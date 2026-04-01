#!/usr/bin/env python3
"""Rotate old JSONL log files — compress and archive files older than 30 days.

Usage:
    python3 scripts/log_rotation.py [--dry-run]
"""

import gzip
import os
import sys
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "backend" / "data"
ARCHIVE_DIR = DATA_DIR / "archive"
MAX_AGE_DAYS = 30


def main():
    dry_run = "--dry-run" in sys.argv
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    cutoff = date.today() - timedelta(days=MAX_AGE_DAYS)
    rotated = 0

    # Find JSONL files
    for filepath in DATA_DIR.glob("*.jsonl"):
        # Check file modification time
        mtime = date.fromtimestamp(os.path.getmtime(filepath))
        if mtime >= cutoff:
            continue

        gz_path = ARCHIVE_DIR / f"{filepath.name}.gz"

        if dry_run:
            print(f"[DRY RUN] Would compress: {filepath.name} ({filepath.stat().st_size / 1024:.1f} KB)")
            rotated += 1
            continue

        # Compress
        try:
            with open(filepath, "rb") as f_in:
                with gzip.open(gz_path, "wb") as f_out:
                    f_out.write(f_in.read())
            filepath.unlink()
            rotated += 1
            print(f"Rotated: {filepath.name} -> archive/{gz_path.name}")
        except Exception as e:
            print(f"ERROR rotating {filepath.name}: {e}")

    # Also rotate analytics directory
    analytics_dir = DATA_DIR / "analytics"
    if analytics_dir.exists():
        for filepath in analytics_dir.glob("analytics-*.jsonl"):
            try:
                file_date = filepath.stem.replace("analytics-", "")
                if file_date < cutoff.isoformat():
                    if dry_run:
                        print(f"[DRY RUN] Would compress: analytics/{filepath.name}")
                        rotated += 1
                    else:
                        gz_path = ARCHIVE_DIR / f"{filepath.name}.gz"
                        with open(filepath, "rb") as f_in:
                            with gzip.open(gz_path, "wb") as f_out:
                                f_out.write(f_in.read())
                        filepath.unlink()
                        rotated += 1
                        print(f"Rotated: analytics/{filepath.name}")
            except (ValueError, OSError):
                continue

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Rotated {rotated} files")


if __name__ == "__main__":
    main()
