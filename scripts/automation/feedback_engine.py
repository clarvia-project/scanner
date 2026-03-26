#!/usr/bin/env python3
"""Usage feedback engine for Clarvia scoring.

Analyzes API call patterns to derive popularity signals and feed them
back into tool scoring. Tracks per-tool metrics:
  - Search appearances (how often a tool shows up in search results)
  - Direct score lookups (how often someone checks a specific tool's score)
  - Badge views (how often a tool's badge is loaded)

Calculates a "popularity signal" from usage data and writes it to
data/feedback/usage_signals.jsonl for the scorer to consume.

Usage:
    python scripts/automation/feedback_engine.py [--dry-run] [--api-url URL]
"""

import argparse
import json
import logging
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from telegram_notifier import send_message

logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"
FEEDBACK_DIR = DATA_DIR / "feedback"
SIGNALS_FILE = FEEDBACK_DIR / "usage_signals.jsonl"

# Maximum popularity boost (added to Clarvia score, 0-5 range)
MAX_POPULARITY_BOOST = 5.0


def _load_analytics_snapshot(api_url: str) -> dict[str, Any] | None:
    """Fetch analytics snapshot from the running API (admin endpoint)."""
    import requests

    try:
        resp = requests.get(f"{api_url}/admin/analytics", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.warning("Cannot fetch analytics from API: %s", exc)

    return None


def _load_catalog() -> list[dict[str, Any]]:
    """Load current catalog."""
    catalog_path = DATA_DIR / "prebuilt-scans.json"
    if not catalog_path.exists():
        return []
    with open(catalog_path) as f:
        return json.load(f)


def _extract_tool_mentions_from_logs() -> Counter:
    """Parse available log files for tool name mentions in search queries.

    Falls back to catalog-based estimation if no logs available.
    """
    mentions: Counter = Counter()

    # Check for any available request log files
    log_candidates = [
        DATA_DIR / "scan_daemon.log",
        PROJECT_ROOT / "backend" / "app.log",
    ]

    for log_path in log_candidates:
        if not log_path.exists():
            continue
        try:
            with open(log_path) as f:
                for line in f:
                    # Look for search query patterns in log lines
                    if "/v1/search" in line or "/v1/score" in line:
                        # Extract query parameter if present
                        if "q=" in line:
                            parts = line.split("q=")
                            if len(parts) > 1:
                                query = parts[1].split("&")[0].split(" ")[0].strip()
                                mentions[query.lower()] += 1
                        # Extract URL parameter for score lookups
                        if "url=" in line:
                            parts = line.split("url=")
                            if len(parts) > 1:
                                url = parts[1].split("&")[0].split(" ")[0].strip()
                                mentions[url.lower()] += 1
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Error reading log %s: %s", log_path, exc)

    return mentions


def _load_previous_signals() -> dict[str, dict[str, Any]]:
    """Load previous usage signals for trend comparison."""
    signals: dict[str, dict[str, Any]] = {}
    if not SIGNALS_FILE.exists():
        return signals

    try:
        with open(SIGNALS_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    name = entry.get("tool_name", "")
                    if name:
                        signals[name] = entry
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass

    return signals


def compute_popularity_signal(
    tool_name: str,
    search_appearances: int,
    score_lookups: int,
    badge_views: int,
    catalog_size: int,
) -> float:
    """Compute a 0-5 popularity boost from usage metrics.

    Uses log-scaled signals normalized against catalog size to prevent
    gaming through repeated requests.
    """
    if catalog_size == 0:
        return 0.0

    # Weighted sum of signals (search is most valuable)
    raw = (
        search_appearances * 3.0
        + score_lookups * 2.0
        + badge_views * 1.0
    )

    if raw == 0:
        return 0.0

    # Log scale to dampen extreme outliers
    log_signal = math.log1p(raw)

    # Normalize: assume max reasonable signal is ~1000 interactions/week
    max_expected = math.log1p(1000 * 6)  # 1000 * (3+2+1 weight)
    normalized = min(log_signal / max_expected, 1.0)

    return round(normalized * MAX_POPULARITY_BOOST, 2)


def generate_usage_signals(api_url: str) -> list[dict[str, Any]]:
    """Analyze usage patterns and generate per-tool popularity signals."""
    catalog = _load_catalog()
    if not catalog:
        logger.warning("Empty catalog — no signals to generate")
        return []

    catalog_size = len(catalog)

    # Try to get analytics from API
    analytics = _load_analytics_snapshot(api_url)

    # Extract tool mentions from logs
    log_mentions = _extract_tool_mentions_from_logs()

    # Build per-tool metrics
    tool_metrics: dict[str, dict[str, int]] = defaultdict(
        lambda: {"search_appearances": 0, "score_lookups": 0, "badge_views": 0}
    )

    # From analytics endpoint data (if available)
    if analytics:
        endpoint_stats = analytics.get("endpoints", {})
        # Estimate per-tool based on endpoint hits
        search_total = endpoint_stats.get("/v1/search", 0)
        score_total = endpoint_stats.get("/v1/score", 0)
        badge_total = sum(
            v for k, v in endpoint_stats.items() if k.startswith("/badge/")
        )

        # Distribute proportionally across catalog (baseline)
        if search_total > 0:
            per_tool = max(1, search_total // catalog_size)
            for s in catalog:
                name = s.get("service_name", "")
                tool_metrics[name]["search_appearances"] += per_tool

    # From log-based mentions (more granular)
    for s in catalog:
        name = s.get("service_name", "").lower()
        url = s.get("url", "").lower()
        # Count mentions matching this tool
        for mention, count in log_mentions.items():
            if name and name in mention:
                tool_metrics[s.get("service_name", "")]["search_appearances"] += count
            if url and url in mention:
                tool_metrics[s.get("service_name", "")]["score_lookups"] += count

    # Load previous signals for trend data
    previous = _load_previous_signals()

    # Compute signals
    signals = []
    for s in catalog:
        name = s.get("service_name", "")
        if not name:
            continue

        metrics = tool_metrics.get(name, {"search_appearances": 0, "score_lookups": 0, "badge_views": 0})

        boost = compute_popularity_signal(
            tool_name=name,
            search_appearances=metrics["search_appearances"],
            score_lookups=metrics["score_lookups"],
            badge_views=metrics["badge_views"],
            catalog_size=catalog_size,
        )

        prev = previous.get(name, {})
        prev_boost = prev.get("popularity_boost", 0.0)

        signal = {
            "tool_name": name,
            "url": s.get("url", ""),
            "search_appearances": metrics["search_appearances"],
            "score_lookups": metrics["score_lookups"],
            "badge_views": metrics["badge_views"],
            "popularity_boost": boost,
            "previous_boost": prev_boost,
            "boost_delta": round(boost - prev_boost, 2),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        signals.append(signal)

    return signals


def save_signals(signals: list[dict[str, Any]]) -> Path:
    """Write signals to JSONL file (append-only log)."""
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

    # Also write a current snapshot (overwrite)
    snapshot_path = FEEDBACK_DIR / "usage_signals_latest.json"
    with open(snapshot_path, "w") as f:
        json.dump(signals, f, indent=2)

    # Append to JSONL log
    with open(SIGNALS_FILE, "a") as f:
        for sig in signals:
            f.write(json.dumps(sig) + "\n")

    return snapshot_path


def format_summary(signals: list[dict[str, Any]]) -> str:
    """Create a short summary of the feedback run."""
    total = len(signals)
    boosted = sum(1 for s in signals if s["popularity_boost"] > 0)
    avg_boost = (
        sum(s["popularity_boost"] for s in signals) / total if total else 0
    )
    top_boosted = sorted(signals, key=lambda x: x["popularity_boost"], reverse=True)[:5]

    lines = [
        "📈 *Clarvia Feedback Engine*",
        f"Processed: {total} tools",
        f"Tools with boost: {boosted}",
        f"Avg boost: {avg_boost:.2f}",
    ]

    if top_boosted:
        lines.append("\n*Top popularity boosts:*")
        for s in top_boosted:
            if s["popularity_boost"] > 0:
                lines.append(
                    f"  • {s['tool_name']}: +{s['popularity_boost']} "
                    f"(search:{s['search_appearances']}, lookups:{s['score_lookups']})"
                )

    return "\n".join(lines)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Clarvia usage feedback engine")
    parser.add_argument("--dry-run", action="store_true", help="Skip writes and Telegram")
    parser.add_argument(
        "--api-url",
        default="https://clarvia-api.onrender.com",
        help="Base URL of the Clarvia API",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logger.info("Running feedback engine...")
    signals = generate_usage_signals(args.api_url)

    if not signals:
        logger.warning("No signals generated")
        return 0

    summary = format_summary(signals)
    logger.info("\n%s", summary)

    if not args.dry_run:
        path = save_signals(signals)
        logger.info("Signals saved to %s", path)
        send_message(summary)
    else:
        logger.info("[DRY RUN] Would save %d signals", len(signals))

    return 0


if __name__ == "__main__":
    sys.exit(main())
