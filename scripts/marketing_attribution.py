#!/usr/bin/env python3
"""Marketing Attribution Tracker — Correlates marketing activities with agent traffic.

Reads marketing-log.jsonl and agent-traffic.jsonl, measures traffic lift
around each marketing activity, and outputs attribution data.

Usage:
  python scripts/marketing_attribution.py
  python scripts/marketing_attribution.py --window 3     # 3-day window instead of 7
  python scripts/marketing_attribution.py --min-lift 10   # only report 10%+ lift

Output: data/marketing-attribution.jsonl
  Each entry: {activity_type, activity_date, channel, detail,
               traffic_before, traffic_after, lift_percent, attribution_confidence}
"""

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

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
MARKETING_LOG_PATH = PROJECT_ROOT / "data" / "marketing-log.jsonl"
AGENT_TRAFFIC_PATH = PROJECT_ROOT / "data" / "agent-traffic.jsonl"
OUTPUT_PATH = PROJECT_ROOT / "data" / "marketing-attribution.jsonl"

DEFAULT_WINDOW_DAYS = 7

CLARVIA_API_BASE = "https://clarvia-api.onrender.com"


def sync_agent_traffic_from_api(days: int = 30) -> int:
    """Fetch agent traffic from the production Clarvia API and write to local JSONL.

    The AgentTrafficMiddleware on Render records to /app/data/agent-traffic.jsonl,
    but the stats endpoint aggregates it. We reconstruct per-day entries from the
    /v1/traffic/stats endpoint so marketing_attribution can correlate locally.

    Returns the number of daily entries written.
    """
    url = f"{CLARVIA_API_BASE}/v1/traffic/stats?days={days}"
    logger.info("Syncing agent traffic from %s", url)

    try:
        req = Request(url, headers={"User-Agent": "clarvia-attribution-sync/1.0"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except (URLError, json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to fetch agent traffic from API: %s", e)
        return 0

    daily = data.get("daily", [])
    if not daily:
        logger.info("No daily traffic data from API")
        return 0

    # Load existing entries to avoid duplicates
    existing_dates: set[str] = set()
    if AGENT_TRAFFIC_PATH.exists():
        with open(AGENT_TRAFFIC_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = entry.get("timestamp", "")
                    if len(ts) >= 10:
                        existing_dates.add(ts[:10])
                except json.JSONDecodeError:
                    continue

    written = 0
    with open(AGENT_TRAFFIC_PATH, "a") as f:
        for day_data in daily:
            date_str = day_data.get("date", "")
            if not date_str or date_str in existing_dates:
                continue

            by_agent = day_data.get("by_agent", {})
            total = day_data.get("total", 0)

            # Write one entry per agent type per day
            if by_agent:
                for agent_type, count in by_agent.items():
                    entry = {
                        "timestamp": f"{date_str}T12:00:00+00:00",
                        "timestamp_unix": datetime.strptime(date_str, "%Y-%m-%d")
                            .replace(hour=12, tzinfo=timezone.utc)
                            .timestamp(),
                        "agent_type": agent_type,
                        "requests": count,
                        "path": "/api/aggregate",
                        "method": "GET",
                        "status_code": 200,
                        "source": "api_sync",
                    }
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    written += 1
            else:
                # Fallback: single entry with total count
                entry = {
                    "timestamp": f"{date_str}T12:00:00+00:00",
                    "timestamp_unix": datetime.strptime(date_str, "%Y-%m-%d")
                        .replace(hour=12, tzinfo=timezone.utc)
                        .timestamp(),
                    "agent_type": "unknown",
                    "requests": total,
                    "path": "/api/aggregate",
                    "method": "GET",
                    "status_code": 200,
                    "source": "api_sync",
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                written += 1

    logger.info("Synced %d agent traffic entries from API", written)
    return written


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse various timestamp formats into a timezone-aware datetime."""
    if not ts_str:
        return None

    formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f+00:00",
        "%Y-%m-%dT%H:%M:%S+00:00",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(ts_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    # Try fromisoformat as fallback
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass

    return None


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file, skipping malformed lines."""
    entries = []
    if not path.exists():
        logger.warning("File not found: %s", path)
        return entries

    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                logger.debug("Skipping malformed line %d in %s", i, path.name)
    return entries


def build_daily_traffic(traffic_entries: list[dict]) -> dict[str, int]:
    """Build a date -> visit_count mapping from agent traffic entries.

    Handles various traffic entry formats:
      - {"ts": "...", "count": N}
      - {"date": "...", "visits": N}
      - {"ts": "...", "agent": "..."}  (each entry = 1 visit)
    """
    daily = defaultdict(int)

    for entry in traffic_entries:
        # Try to get timestamp
        ts_str = entry.get("ts") or entry.get("date") or entry.get("timestamp", "")
        dt = parse_timestamp(ts_str)
        if dt is None:
            continue

        date_key = dt.strftime("%Y-%m-%d")

        # Get count (various field names)
        count = (
            entry.get("count")
            or entry.get("visits")
            or entry.get("requests")
            or 1  # each entry counts as 1 if no explicit count
        )
        daily[date_key] += int(count)

    return dict(daily)


def get_traffic_in_window(
    daily_traffic: dict[str, int],
    center_date: datetime,
    window_days: int,
    direction: str = "before",
) -> int:
    """Sum traffic in a window before or after a given date."""
    total = 0
    for offset in range(1, window_days + 1):
        if direction == "before":
            d = center_date - timedelta(days=offset)
        else:
            d = center_date + timedelta(days=offset)
        date_key = d.strftime("%Y-%m-%d")
        total += daily_traffic.get(date_key, 0)
    return total


def compute_lift(before: int, after: int) -> float:
    """Compute percentage lift. Returns 0 if before is 0."""
    if before == 0:
        return 100.0 if after > 0 else 0.0
    return round(((after - before) / before) * 100, 2)


def assess_confidence(
    lift_percent: float,
    traffic_before: int,
    traffic_after: int,
    activity_success: bool,
) -> str:
    """Assess attribution confidence level.

    Returns: "high", "medium", "low", or "none"
    """
    if not activity_success:
        return "none"

    # Need minimum baseline traffic for meaningful attribution
    if traffic_before < 5 and traffic_after < 5:
        return "low"

    if lift_percent > 50 and traffic_before >= 10:
        return "high"
    elif lift_percent > 20 and traffic_before >= 5:
        return "medium"
    elif lift_percent > 0:
        return "low"
    else:
        return "none"


def main() -> None:
    parser = argparse.ArgumentParser(description="Marketing Attribution Tracker")
    parser.add_argument(
        "--window", type=int, default=DEFAULT_WINDOW_DAYS,
        help=f"Days to compare before/after (default: {DEFAULT_WINDOW_DAYS})"
    )
    parser.add_argument(
        "--min-lift", type=float, default=0,
        help="Minimum lift %% to include in output (default: 0 = all)"
    )
    args = parser.parse_args()

    logger.info("=== Marketing Attribution Tracker ===")
    logger.info("Window: %d days | Min lift: %.1f%%", args.window, args.min_lift)

    # Sync agent traffic from production API if local data is sparse
    if not AGENT_TRAFFIC_PATH.exists() or AGENT_TRAFFIC_PATH.stat().st_size < 100:
        logger.info("Local agent-traffic.jsonl is empty/missing — syncing from production API...")
        sync_agent_traffic_from_api(days=30)
    else:
        # Always try to sync recent data (new days only, deduped)
        sync_agent_traffic_from_api(days=7)

    # Load data
    marketing_entries = load_jsonl(MARKETING_LOG_PATH)
    traffic_entries = load_jsonl(AGENT_TRAFFIC_PATH)

    logger.info("Loaded %d marketing activities, %d traffic entries",
                len(marketing_entries), len(traffic_entries))

    if not marketing_entries:
        logger.warning("No marketing activities found. Nothing to attribute.")
        return

    # Build daily traffic index
    daily_traffic = build_daily_traffic(traffic_entries)
    logger.info("Traffic data spans %d unique days", len(daily_traffic))

    # Load existing attributions to avoid duplicates
    existing_keys = set()
    existing_entries = load_jsonl(OUTPUT_PATH)
    for e in existing_entries:
        key = f"{e.get('activity_type', '')}|{e.get('activity_date', '')}|{e.get('channel', '')}"
        existing_keys.add(key)

    # Process each marketing activity
    new_attributions = []
    for activity in marketing_entries:
        ts_str = activity.get("ts", "")
        activity_dt = parse_timestamp(ts_str)
        if activity_dt is None:
            logger.debug("Skipping activity with unparseable timestamp: %s", ts_str)
            continue

        activity_type = activity.get("activity", "unknown")
        channel = activity.get("channel", "unknown")
        detail = activity.get("detail", "")
        success = activity.get("success", True)
        activity_date = activity_dt.strftime("%Y-%m-%d")

        # Dedup check
        dedup_key = f"{activity_type}|{activity_date}|{channel}"
        if dedup_key in existing_keys:
            continue

        # Compute traffic windows
        traffic_before = get_traffic_in_window(
            daily_traffic, activity_dt, args.window, direction="before"
        )
        traffic_after = get_traffic_in_window(
            daily_traffic, activity_dt, args.window, direction="after"
        )

        lift = compute_lift(traffic_before, traffic_after)
        confidence = assess_confidence(lift, traffic_before, traffic_after, success)

        attribution = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "activity_type": activity_type,
            "activity_date": activity_date,
            "channel": channel,
            "detail": detail[:200],  # truncate long details
            "activity_success": success,
            "traffic_before_window": traffic_before,
            "traffic_after_window": traffic_after,
            "window_days": args.window,
            "lift_percent": lift,
            "attribution_confidence": confidence,
        }

        if lift >= args.min_lift:
            new_attributions.append(attribution)
            existing_keys.add(dedup_key)

    # Write output
    if new_attributions:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "a") as f:
            for attr in new_attributions:
                f.write(json.dumps(attr) + "\n")
        logger.info("Wrote %d new attribution entries to %s", len(new_attributions), OUTPUT_PATH)
    else:
        logger.info("No new attributions to write.")

    # Summary
    if new_attributions:
        high_impact = [a for a in new_attributions if a["attribution_confidence"] in ("high", "medium")]
        logger.info("--- Attribution Summary ---")
        logger.info("Total activities analyzed: %d", len(new_attributions))
        logger.info("High/medium confidence attributions: %d", len(high_impact))

        for attr in sorted(new_attributions, key=lambda x: x["lift_percent"], reverse=True)[:5]:
            logger.info(
                "  %s [%s] — %+.1f%% lift (%d → %d) [%s confidence]",
                attr["activity_type"],
                attr["channel"],
                attr["lift_percent"],
                attr["traffic_before_window"],
                attr["traffic_after_window"],
                attr["attribution_confidence"],
            )


if __name__ == "__main__":
    main()
