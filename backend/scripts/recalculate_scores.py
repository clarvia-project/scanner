#!/usr/bin/env python3
"""Recalculate AEO scores for all indexed tools using the latest scoring algorithm.

Iterates through all collected tool data files, re-applies the scoring algorithm
from tool_scorer.py, and updates the data store. Designed to run as a weekly cron job.

Usage:
    cd scanner/backend
    source .venv/bin/activate
    python scripts/recalculate_scores.py

    # Dry run (no writes):
    python scripts/recalculate_scores.py --dry-run

    # Verbose output:
    python scripts/recalculate_scores.py --verbose

    # Crontab entry (weekly Sunday 3am):
    0 3 * * 0 cd /path/to/scanner/backend && .venv/bin/python scripts/recalculate_scores.py >> /tmp/clarvia-recalc.log 2>&1
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add parent dirs so we can import app modules
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.tool_scorer import normalize_tool, detect_pricing, detect_difficulty, estimate_popularity
# Use the new type-specific scoring engine (replaces old monolithic score_tool)
from app.scoring import score_tool as new_score_tool

# Monkey-patch: replace the old score_tool in tool_scorer with the new one
# so normalize_tool() calls the new scoring engine internally
import app.tool_scorer
app.tool_scorer.score_tool = new_score_tool

logger = logging.getLogger("recalculate_scores")

# ---------------------------------------------------------------------------
# Data file discovery
# ---------------------------------------------------------------------------

# Collected tool files (raw format, scored via tool_scorer)
COLLECTED_FILES = [
    "mcp-registry-all.json",
    "skills-cli-collected.json",
    "all-agent-tools.json",
]

# The merged output file
PREBUILT_SCANS = "prebuilt-scans.json"


def find_data_dir() -> Path:
    """Locate the project data directory."""
    candidates = [
        PROJECT_ROOT / "data",
        BACKEND_DIR / "data",
        Path("/app/data"),
    ]
    for p in candidates:
        if p.is_dir():
            return p
    raise FileNotFoundError("Could not find data directory in any candidate path")


# ---------------------------------------------------------------------------
# Recalculation logic
# ---------------------------------------------------------------------------


def recalculate_collected_tools(
    data_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,
    test_limit: int | None = None,
) -> dict[str, Any]:
    """Re-score all collected tools and update prebuilt-scans.json.

    Returns a summary dict with statistics.
    """
    stats: dict[str, Any] = {
        "files_processed": 0,
        "total_tools": 0,
        "scores_changed": 0,
        "scores_increased": 0,
        "scores_decreased": 0,
        "scores_unchanged": 0,
        "new_tools": 0,
        "errors": 0,
        "score_distribution": Counter(),
        "rating_distribution": Counter(),
        "biggest_changes": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    # Load existing prebuilt scans for comparison
    prebuilt_path = data_dir / PREBUILT_SCANS
    existing_scores: dict[str, int] = {}
    existing_entries: list[dict[str, Any]] = []
    website_scanned: list[dict[str, Any]] = []

    if prebuilt_path.exists():
        with open(prebuilt_path) as f:
            existing_entries = json.load(f)
        # Separate website-scanned entries from collected entries
        for entry in existing_entries:
            sid = entry.get("scan_id", "")
            existing_scores[sid] = entry.get("clarvia_score", 0)
            # Website scans start with "scn_", collected tools start with "tool_"
            if sid.startswith("scn_"):
                website_scanned.append(entry)

    logger.info(
        "Loaded %d existing entries (%d website-scanned, %d collected)",
        len(existing_entries),
        len(website_scanned),
        len(existing_entries) - len(website_scanned),
    )

    # Re-score all collected tools
    seen_ids: set[str] = set()
    seen_names: dict[str, int] = {}
    recalculated: list[dict[str, Any]] = []

    for fname in COLLECTED_FILES:
        fpath = data_dir / fname
        if not fpath.exists():
            logger.warning("File not found: %s", fpath)
            continue

        stats["files_processed"] += 1

        try:
            with open(fpath) as f:
                raw_tools = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read %s: %s", fname, e)
            stats["errors"] += 1
            continue

        file_count = 0
        tools_to_process = raw_tools[:test_limit] if test_limit else raw_tools
        for tool in tools_to_process:
            try:
                normalized = normalize_tool(tool)
                sid = normalized["scan_id"]

                # Dedup by scan_id
                if sid in seen_ids:
                    continue
                seen_ids.add(sid)

                # Dedup by name (keep higher score)
                name_key = normalized["service_name"].lower().strip()
                if name_key in seen_names:
                    existing_idx = seen_names[name_key]
                    if normalized["clarvia_score"] > recalculated[existing_idx]["clarvia_score"]:
                        recalculated[existing_idx] = normalized
                    continue

                seen_names[name_key] = len(recalculated)
                recalculated.append(normalized)
                file_count += 1

                # Track changes
                old_score = existing_scores.get(sid)
                new_score = normalized["clarvia_score"]

                if old_score is not None:
                    delta = new_score - old_score
                    if delta != 0:
                        stats["scores_changed"] += 1
                        if delta > 0:
                            stats["scores_increased"] += 1
                        else:
                            stats["scores_decreased"] += 1

                        if abs(delta) >= 5:
                            stats["biggest_changes"].append({
                                "name": normalized["service_name"],
                                "scan_id": sid,
                                "old_score": old_score,
                                "new_score": new_score,
                                "delta": delta,
                            })
                    else:
                        stats["scores_unchanged"] += 1
                else:
                    stats["new_tools"] += 1

                # Distribution tracking
                stats["score_distribution"][_score_bucket(new_score)] += 1
                stats["rating_distribution"][normalized.get("rating", "Unknown")] += 1

                if verbose:
                    change_str = ""
                    if old_score is not None and old_score != new_score:
                        change_str = f" (was {old_score}, delta {new_score - old_score:+d})"
                    elif old_score is None:
                        change_str = " (NEW)"
                    logger.info(
                        "  %s: score=%d, rating=%s%s",
                        normalized["service_name"],
                        new_score,
                        normalized["rating"],
                        change_str,
                    )

            except Exception as e:
                logger.warning("Error scoring tool in %s: %s", fname, e)
                stats["errors"] += 1

        stats["total_tools"] += file_count
        logger.info("Processed %s: %d tools", fname, file_count)

    # Sort biggest changes by absolute delta
    stats["biggest_changes"].sort(key=lambda x: abs(x["delta"]), reverse=True)
    stats["biggest_changes"] = stats["biggest_changes"][:20]

    # Convert Counters to regular dicts for JSON serialization
    stats["score_distribution"] = dict(sorted(stats["score_distribution"].items()))
    stats["rating_distribution"] = dict(stats["rating_distribution"])

    # Merge: keep website scans + replace collected tools
    merged = website_scanned + recalculated
    logger.info(
        "Merged output: %d website-scanned + %d collected = %d total",
        len(website_scanned),
        len(recalculated),
        len(merged),
    )

    if not dry_run:
        # Backup existing file
        if prebuilt_path.exists():
            backup_dir = data_dir / "backups"
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = backup_dir / f"prebuilt-scans-{timestamp}.json"
            shutil.copy2(prebuilt_path, backup_path)
            logger.info("Backed up to %s", backup_path)

            # Keep only last 5 backups
            backups = sorted(backup_dir.glob("prebuilt-scans-*.json"), reverse=True)
            for old in backups[5:]:
                old.unlink()
                logger.info("Removed old backup: %s", old.name)

        # Write updated file
        with open(prebuilt_path, "w") as f:
            json.dump(merged, f, indent=2, default=str)
        logger.info("Wrote %d entries to %s", len(merged), prebuilt_path)

        # Also update frontend copy if it exists
        frontend_path = PROJECT_ROOT / "frontend" / "public" / "data" / "prebuilt-scans.json"
        if frontend_path.parent.exists():
            shutil.copy2(prebuilt_path, frontend_path)
            logger.info("Synced to frontend: %s", frontend_path)
    else:
        logger.info("[DRY RUN] Would write %d entries to %s", len(merged), prebuilt_path)

    stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    return stats


def _score_bucket(score: int) -> str:
    """Map a score to a distribution bucket."""
    if score >= 80:
        return "80-100"
    elif score >= 60:
        return "60-79"
    elif score >= 40:
        return "40-59"
    elif score >= 20:
        return "20-39"
    else:
        return "0-19"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def print_report(stats: dict[str, Any]) -> None:
    """Print a human-readable summary report."""
    print("\n" + "=" * 60)
    print("  CLARVIA AEO SCORE RECALCULATION REPORT")
    print("=" * 60)
    print(f"  Started:  {stats['started_at']}")
    print(f"  Finished: {stats['finished_at']}")
    print()

    print("--- Summary ---")
    print(f"  Files processed:   {stats['files_processed']}")
    print(f"  Total tools:       {stats['total_tools']}")
    print(f"  Errors:            {stats['errors']}")
    print()

    print("--- Score Changes ---")
    print(f"  Changed:           {stats['scores_changed']}")
    print(f"    Increased:       {stats['scores_increased']}")
    print(f"    Decreased:       {stats['scores_decreased']}")
    print(f"  Unchanged:         {stats['scores_unchanged']}")
    print(f"  New tools:         {stats['new_tools']}")
    print()

    print("--- Score Distribution ---")
    dist = stats["score_distribution"]
    for bucket in ["80-100", "60-79", "40-59", "20-39", "0-19"]:
        count = dist.get(bucket, 0)
        bar = "#" * min(count // 50, 40)
        print(f"  {bucket:>6}: {count:>6}  {bar}")
    print()

    print("--- Rating Distribution ---")
    for rating, count in sorted(stats["rating_distribution"].items()):
        print(f"  {rating:<12}: {count:>6}")
    print()

    if stats["biggest_changes"]:
        print("--- Biggest Score Changes (top 20) ---")
        for c in stats["biggest_changes"]:
            direction = "+" if c["delta"] > 0 else ""
            print(f"  {c['name']:<40} {c['old_score']:>3} -> {c['new_score']:>3} ({direction}{c['delta']})")
        print()

    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recalculate AEO scores for all indexed Clarvia tools."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate scores but do not write changes to disk.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log each tool as it is processed.",
    )
    parser.add_argument(
        "--json-report",
        type=str,
        default=None,
        help="Write the report as JSON to this file path.",
    )
    parser.add_argument(
        "--test",
        type=int,
        default=None,
        metavar="N",
        help="Quick test: score only N tools per file and print results.",
    )
    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        data_dir = find_data_dir()
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # --test implies --dry-run (never write partial results)
    if args.test:
        args.dry_run = True
        logger.info("Test mode: scoring %d tools per file (dry run forced)", args.test)

    logger.info("Data directory: %s", data_dir)
    logger.info("Dry run: %s", args.dry_run)

    start = time.monotonic()
    stats = recalculate_collected_tools(
        data_dir, dry_run=args.dry_run, verbose=args.verbose, test_limit=args.test,
    )
    elapsed = time.monotonic() - start
    stats["elapsed_seconds"] = round(elapsed, 2)

    print_report(stats)

    if args.json_report:
        report_path = Path(args.json_report)
        with open(report_path, "w") as f:
            json.dump(stats, f, indent=2)
        logger.info("JSON report written to %s", report_path)

    if stats["errors"] > 0:
        logger.warning("Completed with %d errors", stats["errors"])
        sys.exit(2)


if __name__ == "__main__":
    main()
