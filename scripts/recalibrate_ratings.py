#!/usr/bin/env python3
"""One-time rating recalibration script.

Reads prebuilt-scans.json, recalculates ratings using the unified thresholds,
and writes the corrected file back.

Unified thresholds:
  Exceptional: 90+
  Excellent:   80-89
  Strong:      65-79
  Moderate:    45-64
  Basic:       25-44
  Low:         <25

Usage:
    python scripts/recalibrate_ratings.py [--dry-run]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PREBUILT_PATH = DATA_DIR / "prebuilt-scans.json"


def get_rating(score: int) -> str:
    if score >= 90:
        return "Exceptional"
    elif score >= 80:
        return "Excellent"
    elif score >= 65:
        return "Strong"
    elif score >= 45:
        return "Moderate"
    elif score >= 25:
        return "Basic"
    else:
        return "Low"


def recalibrate(dry_run: bool = False) -> dict:
    print(f"Loading {PREBUILT_PATH}...")
    with open(PREBUILT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = list(data.values()) if isinstance(data, dict) else data
    print(f"Total tools: {len(items)}")

    old_dist: Counter = Counter()
    new_dist: Counter = Counter()
    changed = 0

    for item in items:
        score = item.get("clarvia_score", 0) or 0
        old_rating = item.get("rating", "")
        new_rating = get_rating(int(score))

        old_dist[old_rating] += 1
        new_dist[new_rating] += 1

        if old_rating != new_rating:
            item["rating"] = new_rating
            changed += 1

    print(f"\nOld distribution:")
    for rating, count in sorted(old_dist.items(), key=lambda x: -x[1]):
        pct = count / len(items) * 100
        print(f"  {rating}: {count} ({pct:.1f}%)")

    print(f"\nNew distribution:")
    for rating, count in sorted(new_dist.items(), key=lambda x: -x[1]):
        pct = count / len(items) * 100
        print(f"  {rating}: {count} ({pct:.1f}%)")

    print(f"\nChanged: {changed}/{len(items)} tools")

    if not dry_run:
        # Write back in same format
        if isinstance(data, dict):
            # Rebuild dict
            rebuilt = {item.get("scan_id", item.get("id", str(i))): item
                      for i, item in enumerate(items)}
        else:
            rebuilt = items

        backup_path = PREBUILT_PATH.with_suffix(".pre-recalibration.json")
        import shutil
        shutil.copy2(PREBUILT_PATH, backup_path)
        print(f"\nBackup saved to: {backup_path.name}")

        with open(PREBUILT_PATH, "w", encoding="utf-8") as f:
            json.dump(rebuilt, f, ensure_ascii=False, separators=(",", ":"))

        print(f"Saved recalibrated data to: {PREBUILT_PATH.name}")
    else:
        print("\nDRY RUN — no files modified")

    return {
        "total": len(items),
        "changed": changed,
        "old_distribution": dict(old_dist),
        "new_distribution": dict(new_dist),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recalibrate tool ratings")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = recalibrate(dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
