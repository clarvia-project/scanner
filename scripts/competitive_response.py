#!/usr/bin/env python3
"""Competitive Response Generator — Analyzes competitor moves and suggests actions.

Reads competitor-weekly.jsonl, analyzes each new competitor move for impact
on Clarvia, generates suggested response actions, and optionally sends
significant findings to Telegram.

Usage:
  python scripts/competitive_response.py
  python scripts/competitive_response.py --notify          # send to Telegram
  python scripts/competitive_response.py --since 2026-03-25  # only recent entries
  python scripts/competitive_response.py --dry-run          # preview only

Output: data/competitive-responses.jsonl
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
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
COMPETITOR_PATH = PROJECT_ROOT / "data" / "competitor-weekly.jsonl"
OUTPUT_PATH = PROJECT_ROOT / "data" / "competitive-responses.jsonl"

# Competitor intelligence: what each competitor does and where they overlap with Clarvia
COMPETITOR_PROFILES = {
    "pulsemcp": {
        "name": "PulseMCP",
        "overlap": "MCP discovery and scoring",
        "our_edge": "free + agent-first + AEO scoring standard",
        "threat_areas": ["paid features", "community building", "partnerships"],
    },
    "smithery": {
        "name": "Smithery",
        "overlap": "MCP server registry and routing",
        "our_edge": "broader tool coverage (MCP + CLI + Skills) + quality scoring",
        "threat_areas": ["dynamic routing", "skills registry", "developer tooling"],
    },
    "glama": {
        "name": "Glama",
        "overlap": "MCP server directory",
        "our_edge": "deeper analysis per tool, not just listing",
        "threat_areas": ["scale (20K+ servers)", "usage metrics", "sorting algorithms"],
    },
    "opentools": {
        "name": "OpenTools",
        "overlap": "AI tool directory",
        "our_edge": "agent-specific focus vs generic AI tools",
        "threat_areas": ["breadth of listings", "SEO presence"],
    },
    "mcp_so": {
        "name": "MCP.so",
        "overlap": "MCP ecosystem hub",
        "our_edge": "scoring/rating system + badge ecosystem",
        "threat_areas": ["enterprise features", "RBAC", "team management"],
    },
}

# Response templates based on threat level and type
RESPONSE_TEMPLATES = {
    "pricing_threat": [
        "Emphasize our free tier — their paid features are our free defaults",
        "Create comparison page: Clarvia Free vs {competitor} Paid",
        "Blog post: Why AEO scoring should be free and open",
    ],
    "feature_overlap": [
        "Accelerate our version of {feature} — ship within 1 week",
        "Differentiate: add agent-specific angle that {competitor} lacks",
        "Document our approach publicly to establish thought leadership",
    ],
    "community_threat": [
        "Increase presence in shared community channels",
        "Launch Clarvia badge program to build tool-maker loyalty",
        "Create content showcasing tools that use Clarvia badges",
    ],
    "scale_threat": [
        "Focus on quality over quantity — curated > comprehensive",
        "Highlight our deeper analysis per tool (not just listing count)",
        "Partner with tool creators directly for exclusive insights",
    ],
    "partnership_threat": [
        "Identify and reach out to same potential partners first",
        "Offer free integration/badge to partners they're courting",
        "Build technical integrations that create switching costs",
    ],
    "pivot_threat": [
        "Monitor closely — their pivot validates or invalidates our direction",
        "If validates: accelerate our roadmap in that area",
        "If invalidates: document why our approach differs",
    ],
}


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse timestamp string."""
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file."""
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


def load_processed_keys() -> set[str]:
    """Load already-processed competitor entries to avoid duplicates."""
    processed = set()
    for entry in load_jsonl(OUTPUT_PATH):
        key = entry.get("source_key", "")
        if key:
            processed.add(key)
    return processed


def classify_threat(competitor: str, description: str) -> tuple[str, str]:
    """Classify the type and severity of a competitor move.

    Returns: (threat_type, severity)
    """
    desc_lower = description.lower()

    # Classify threat type
    if any(w in desc_lower for w in ["paid", "pricing", "subscription", "$", "premium", "monetiz"]):
        threat_type = "pricing_threat"
    elif any(w in desc_lower for w in ["partner", "committee", "alliance", "collab"]):
        threat_type = "partnership_threat"
    elif any(w in desc_lower for w in ["pivot", "rebrand", "direction", "focus shift"]):
        threat_type = "pivot_threat"
    elif any(w in desc_lower for w in ["community", "academy", "event", "meetup", "discord"]):
        threat_type = "community_threat"
    elif any(w in desc_lower for w in ["20k", "10k", "scale", "growth", "servers added"]):
        threat_type = "scale_threat"
    else:
        threat_type = "feature_overlap"

    # Classify severity from the finding text
    if "HIGH" in description:
        severity = "high"
    elif "MEDIUM" in description:
        severity = "medium"
    else:
        severity = "low"

    return threat_type, severity


def generate_responses(
    competitor: str,
    description: str,
    threat_type: str,
    severity: str,
) -> list[str]:
    """Generate suggested response actions based on threat classification."""
    profile = COMPETITOR_PROFILES.get(competitor, {})
    competitor_name = profile.get("name", competitor)
    our_edge = profile.get("our_edge", "unique value proposition")

    templates = RESPONSE_TEMPLATES.get(threat_type, RESPONSE_TEMPLATES["feature_overlap"])

    responses = []
    for template in templates:
        response = template.format(
            competitor=competitor_name,
            feature=description[:50],
            edge=our_edge,
        )
        responses.append(response)

    # Add urgency-based action for high severity
    if severity == "high":
        responses.insert(0, f"URGENT: Review {competitor_name} move immediately and prioritize response")

    # Cap at 3 responses
    return responses[:3]


def format_telegram_message(responses: list[dict]) -> str:
    """Format competitive responses for Telegram notification."""
    lines = ["*Competitive Intelligence Alert*\n"]

    for resp in responses:
        severity_icon = {"high": "!!!", "medium": "!!", "low": "!"}.get(resp["severity"], "!")
        lines.append(
            f"{severity_icon} *{resp['competitor_name']}* ({resp['severity'].upper()})"
        )
        lines.append(f"Move: {resp['description'][:100]}")
        lines.append("Suggested actions:")
        for i, action in enumerate(resp["suggested_actions"], 1):
            lines.append(f"  {i}. {action}")
        lines.append("")

    return "\n".join(lines)


def send_telegram(message: str) -> bool:
    """Send notification via telegram_notifier module."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from telegram_notifier import send_message
        return send_message(message, parse_mode="Markdown")
    except ImportError:
        logger.warning("telegram_notifier module not available")
        return False
    except Exception as e:
        logger.error("Failed to send Telegram notification: %s", e)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Competitive Response Generator")
    parser.add_argument("--notify", action="store_true", help="Send significant findings to Telegram")
    parser.add_argument("--since", type=str, default=None, help="Only process entries after this date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    logger.info("=== Competitive Response Generator ===")
    logger.info("Notify: %s | Since: %s | Dry run: %s", args.notify, args.since, args.dry_run)

    # Parse since date
    since_dt = None
    if args.since:
        since_dt = parse_timestamp(args.since)
        if since_dt is None:
            since_dt = parse_timestamp(args.since + "T00:00:00+00:00")

    # Load data
    competitor_entries = load_jsonl(COMPETITOR_PATH)
    processed_keys = load_processed_keys()

    logger.info("Loaded %d competitor entries, %d already processed",
                len(competitor_entries), len(processed_keys))

    # Process each entry
    all_responses = []

    for entry in competitor_entries:
        ts_str = entry.get("ts", "")
        entry_dt = parse_timestamp(ts_str)

        # Skip if before --since date
        if since_dt and entry_dt and entry_dt < since_dt:
            continue

        # Build a unique key for dedup
        source_key = f"{ts_str}|{entry.get('action', '')}"
        if source_key in processed_keys:
            continue

        # Extract findings (handle both flat and nested formats)
        findings = entry.get("findings", {})
        if isinstance(findings, str):
            # Flat format: whole entry is one finding
            findings = {"unknown": findings}

        for competitor, description in findings.items():
            if not description:
                continue

            # Classify and generate response
            threat_type, severity = classify_threat(competitor, description)
            suggested_actions = generate_responses(competitor, description, threat_type, severity)

            profile = COMPETITOR_PROFILES.get(competitor, {})

            response_entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "source_key": source_key,
                "source_ts": ts_str,
                "competitor": competitor,
                "competitor_name": profile.get("name", competitor),
                "description": description,
                "threat_type": threat_type,
                "severity": severity,
                "our_edge": profile.get("our_edge", ""),
                "suggested_actions": suggested_actions,
            }

            all_responses.append(response_entry)

            logger.info(
                "  %s [%s/%s]: %s",
                profile.get("name", competitor),
                severity,
                threat_type,
                description[:80],
            )
            for action in suggested_actions:
                logger.info("    -> %s", action)

    # Write output
    if all_responses and not args.dry_run:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "a") as f:
            for resp in all_responses:
                f.write(json.dumps(resp) + "\n")
        logger.info("Wrote %d response entries to %s", len(all_responses), OUTPUT_PATH)

    # Send Telegram notification for significant findings
    if args.notify and not args.dry_run:
        significant = [r for r in all_responses if r["severity"] in ("high", "medium")]
        if significant:
            message = format_telegram_message(significant)
            if send_telegram(message):
                logger.info("Telegram notification sent (%d significant items)", len(significant))
            else:
                logger.warning("Failed to send Telegram notification")
        else:
            logger.info("No significant findings to notify about")

    # Summary
    logger.info("--- Summary ---")
    logger.info("New responses generated: %d", len(all_responses))
    by_severity = {}
    for r in all_responses:
        sev = r["severity"]
        by_severity[sev] = by_severity.get(sev, 0) + 1
    for sev in ["high", "medium", "low"]:
        if sev in by_severity:
            logger.info("  %s: %d", sev, by_severity[sev])


if __name__ == "__main__":
    main()
