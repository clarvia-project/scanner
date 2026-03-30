#!/usr/bin/env python3
"""Tool Tier Promotion Engine — Promotes/demotes tools based on score and traffic.

Reads prebuilt-scans.json and agent traffic data to assign tiers:
  - "featured":  score >= 70 + agent traffic > 10/week
  - "trending":  score >= 80 + agent traffic > 50/week
  - "archived":  score < 40 for 30+ days

Outputs tier changes to data/tier-promotions.jsonl and optionally
updates tool metadata in the catalog.

Usage:
  python scripts/tier_promotion.py
  python scripts/tier_promotion.py --dry-run          # preview only
  python scripts/tier_promotion.py --update-catalog    # write back to prebuilt-scans.json
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCAN_DATA_PATHS = [
    PROJECT_ROOT / "frontend" / "public" / "data" / "prebuilt-scans.json",
    PROJECT_ROOT / "data" / "prebuilt-scans.json",
]

AGENT_TRAFFIC_PATH = PROJECT_ROOT / "data" / "agent-traffic.jsonl"
OUTPUT_PATH = PROJECT_ROOT / "data" / "tier-promotions.jsonl"

# Tier thresholds
TRENDING_SCORE = 80
TRENDING_TRAFFIC_WEEKLY = 50

FEATURED_SCORE = 70
FEATURED_TRAFFIC_WEEKLY = 10

ARCHIVE_SCORE = 40
ARCHIVE_DAYS = 30

# Valid tiers (ordered by priority)
TIER_PRIORITY = {"trending": 3, "featured": 2, "standard": 1, "archived": 0}


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse various timestamp formats."""
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass
    return None


def load_scans() -> tuple[list[dict], Path]:
    """Load prebuilt scan data. Returns (scans, path_used)."""
    for path in SCAN_DATA_PATHS:
        if path.exists():
            logger.info("Loading scans from %s", path)
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, list):
                return data, path
            logger.warning("Expected list, got %s", type(data).__name__)
    logger.error("No prebuilt-scans.json found")
    sys.exit(1)


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file, skipping bad lines."""
    entries = []
    if not path.exists():
        return entries
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def compute_weekly_traffic(traffic_entries: list[dict]) -> dict[str, int]:
    """Compute per-tool weekly traffic (last 7 days).

    Traffic entries can reference tools by scan_id, tool_name, or url.
    Returns: {identifier: weekly_visit_count}
    """
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    weekly = defaultdict(int)
    for entry in traffic_entries:
        ts_str = entry.get("ts") or entry.get("date") or entry.get("timestamp", "")
        dt = parse_timestamp(ts_str)
        if dt is None or dt < week_ago:
            continue

        # Try multiple identifier fields
        count = int(entry.get("count", entry.get("visits", entry.get("requests", 1))))

        for id_field in ["scan_id", "tool_name", "tool", "url", "path"]:
            identifier = entry.get(id_field, "")
            if identifier:
                weekly[identifier.lower()] += count
                break

    return dict(weekly)


def get_tool_traffic(scan: dict, weekly_traffic: dict[str, int]) -> int:
    """Look up weekly traffic for a tool using various identifiers."""
    candidates = [
        scan.get("scan_id", "").lower(),
        scan.get("service_name", "").lower(),
        scan.get("url", "").lower(),
    ]

    for candidate in candidates:
        if candidate and candidate in weekly_traffic:
            return weekly_traffic[candidate]

    # Try partial path match (traffic might log /tool/scan_id)
    scan_id = scan.get("scan_id", "")
    if scan_id:
        for key, count in weekly_traffic.items():
            if scan_id.lower() in key:
                return count

    return 0


def determine_tier(score: int, weekly_traffic: int, current_tier: str, scan_date: Optional[str]) -> str:
    """Determine the appropriate tier for a tool."""
    # Check trending first (highest tier)
    if score >= TRENDING_SCORE and weekly_traffic >= TRENDING_TRAFFIC_WEEKLY:
        return "trending"

    # Check featured
    if score >= FEATURED_SCORE and weekly_traffic >= FEATURED_TRAFFIC_WEEKLY:
        return "featured"

    # Check archive condition
    if score < ARCHIVE_SCORE:
        if scan_date:
            scan_dt = parse_timestamp(scan_date)
            if scan_dt:
                days_since = (datetime.now(timezone.utc) - scan_dt).days
                if days_since >= ARCHIVE_DAYS:
                    return "archived"

    # Default: standard tier
    return "standard"


def load_existing_promotions() -> dict[str, dict]:
    """Load existing promotions, keyed by scan_id, for dedup."""
    latest = {}
    for entry in load_jsonl(OUTPUT_PATH):
        scan_id = entry.get("scan_id", "")
        if scan_id:
            latest[scan_id] = entry
    return latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool Tier Promotion Engine")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only")
    parser.add_argument("--update-catalog", action="store_true", help="Write tier back to prebuilt-scans.json")
    args = parser.parse_args()

    logger.info("=== Tool Tier Promotion Engine ===")
    logger.info("Dry run: %s | Update catalog: %s", args.dry_run, args.update_catalog)

    # Load data
    scans, scans_path = load_scans()
    traffic_entries = load_jsonl(AGENT_TRAFFIC_PATH)
    weekly_traffic = compute_weekly_traffic(traffic_entries)
    existing_promotions = load_existing_promotions()

    logger.info("Loaded %d scans, %d traffic entries (%d tools with weekly traffic)",
                len(scans), len(traffic_entries), len(weekly_traffic))

    # Process each tool
    promotions = []
    catalog_updates = 0
    tier_counts = defaultdict(int)

    for scan in scans:
        scan_id = scan.get("scan_id", "")
        score = scan.get("clarvia_score", 0)
        name = scan.get("service_name", "unknown")
        current_tier = scan.get("tier", "standard")
        scan_date = scan.get("scanned_at") or scan.get("last_scanned", "")

        # Get weekly traffic for this tool
        tool_traffic = get_tool_traffic(scan, weekly_traffic)

        # Determine new tier
        new_tier = determine_tier(score, tool_traffic, current_tier, scan_date)
        tier_counts[new_tier] += 1

        # Check if tier changed
        if new_tier != current_tier:
            promotion = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "scan_id": scan_id,
                "service_name": name,
                "score": score,
                "weekly_traffic": tool_traffic,
                "previous_tier": current_tier,
                "new_tier": new_tier,
                "reason": _build_reason(score, tool_traffic, current_tier, new_tier),
            }

            # Check if this is a new change (not already logged)
            existing = existing_promotions.get(scan_id, {})
            if existing.get("new_tier") == new_tier:
                continue  # Already logged this transition

            promotions.append(promotion)

            # Update catalog in-memory
            if args.update_catalog:
                scan["tier"] = new_tier
                catalog_updates += 1

            direction = "promoted" if TIER_PRIORITY.get(new_tier, 0) > TIER_PRIORITY.get(current_tier, 0) else "demoted"
            logger.info(
                "  %s: %s → %s (%s) [score=%d, traffic=%d/wk]",
                name, current_tier, new_tier, direction, score, tool_traffic,
            )

    # Write promotions log
    if promotions and not args.dry_run:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "a") as f:
            for p in promotions:
                f.write(json.dumps(p) + "\n")
        logger.info("Wrote %d tier changes to %s", len(promotions), OUTPUT_PATH)

    # Update catalog file if requested
    if args.update_catalog and catalog_updates > 0 and not args.dry_run:
        with open(scans_path, "w") as f:
            json.dump(scans, f, indent=2)
        logger.info("Updated %d entries in %s", catalog_updates, scans_path)

    # Summary
    logger.info("--- Tier Distribution ---")
    for tier in ["trending", "featured", "standard", "archived"]:
        logger.info("  %s: %d tools", tier, tier_counts.get(tier, 0))
    logger.info("Tier changes this run: %d", len(promotions))


def _build_reason(score: int, traffic: int, old_tier: str, new_tier: str) -> str:
    """Build a human-readable reason for the tier change."""
    reasons = []

    if new_tier == "trending":
        reasons.append(f"score {score} >= {TRENDING_SCORE}")
        reasons.append(f"weekly traffic {traffic} >= {TRENDING_TRAFFIC_WEEKLY}")
    elif new_tier == "featured":
        reasons.append(f"score {score} >= {FEATURED_SCORE}")
        reasons.append(f"weekly traffic {traffic} >= {FEATURED_TRAFFIC_WEEKLY}")
    elif new_tier == "archived":
        reasons.append(f"score {score} < {ARCHIVE_SCORE}")
        reasons.append(f"low score for {ARCHIVE_DAYS}+ days")
    elif new_tier == "standard":
        if old_tier in ("trending", "featured"):
            reasons.append(f"traffic dropped below threshold (weekly: {traffic})")
        elif old_tier == "archived":
            reasons.append(f"score improved to {score}")

    return " + ".join(reasons) if reasons else "tier recalculation"


if __name__ == "__main__":
    main()
