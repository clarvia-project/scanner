#!/usr/bin/env python3
"""Badge Outreach Preparation Script.

Queries the prebuilt scans catalog, identifies tools eligible for
badge embedding (score >= threshold), and generates ready-to-use
badge markdown for each.

Output:
  - Console report of eligible tools
  - JSON file at data/badge-outreach.json with all markdown snippets

Usage:
  python scripts/badge_outreach.py [--threshold 70] [--limit 50] [--output data/badge-outreach.json]
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BADGE_BASE = "https://clarvia.art/api/badge"
SITE_BASE = "https://clarvia.art"

# Candidate scan data paths (checked in order)
SCAN_DATA_PATHS = [
    Path(__file__).resolve().parent.parent / "frontend" / "public" / "data" / "prebuilt-scans.json",
    Path(__file__).resolve().parent.parent / "data" / "prebuilt-scans.json",
]


def load_scans() -> list[dict]:
    """Load prebuilt scan data from the first available path."""
    for path in SCAN_DATA_PATHS:
        if path.exists():
            logger.info("Loading scans from %s", path)
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            logger.warning("Expected list, got %s", type(data).__name__)
    logger.error("No prebuilt-scans.json found in candidate paths")
    sys.exit(1)


def generate_badge_markdown(scan: dict) -> dict:
    """Generate badge embed snippets for a single tool.

    Returns a dict with:
      - markdown: basic image syntax
      - markdown_linked: badge that links to report page
      - html: img tag with link
      - readme_section: full README section suggestion
    """
    name = scan.get("service_name", "unknown")
    score = scan.get("clarvia_score", 0)
    scan_id = scan.get("scan_id", "")

    # Use scan_id for the badge URL (most reliable identifier)
    identifier = quote(scan_id, safe="") if scan_id else quote(name, safe="")

    badge_url = f"{BADGE_BASE}/{identifier}.svg"
    report_url = f"{SITE_BASE}/tool/{identifier}"

    markdown = f"![Clarvia AEO Score]({badge_url})"
    markdown_linked = f"[![Clarvia AEO Score]({badge_url})]({report_url})"
    html = (
        f'<a href="{report_url}">'
        f'<img src="{badge_url}" alt="Clarvia AEO Score: {score}/100" />'
        f"</a>"
    )

    # Full README section suggestion
    readme_section = (
        f"## AEO Score\n\n"
        f"{markdown_linked}\n\n"
        f"This project has a Clarvia AEO Score of **{score}/100**. "
        f"[View full report]({report_url}).\n"
    )

    return {
        "markdown": markdown,
        "markdown_linked": markdown_linked,
        "html": html,
        "readme_section": readme_section,
        "badge_url": badge_url,
        "report_url": report_url,
    }


def filter_eligible(
    scans: list[dict],
    threshold: int,
    limit: int,
) -> list[dict]:
    """Filter and sort scans by score, returning top eligible tools."""
    eligible = [
        s for s in scans
        if s.get("clarvia_score", 0) >= threshold
        and s.get("service_name")
        and s.get("scan_id")
    ]
    eligible.sort(key=lambda s: s["clarvia_score"], reverse=True)
    return eligible[:limit]


def main():
    parser = argparse.ArgumentParser(
        description="Generate badge outreach list for high-scoring tools",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=60,
        help="Minimum Clarvia score for badge eligibility (default: 60)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max tools to include (default: 100)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON path (default: data/badge-outreach.json)",
    )
    args = parser.parse_args()

    # Resolve output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(__file__).resolve().parent.parent / "data" / "badge-outreach.json"

    # Load and filter
    scans = load_scans()
    logger.info("Loaded %d total scans", len(scans))

    eligible = filter_eligible(scans, args.threshold, args.limit)
    logger.info(
        "Found %d tools with score >= %d (limit %d)",
        len(eligible), args.threshold, args.limit,
    )

    if not eligible:
        logger.warning("No tools meet the threshold. Try lowering --threshold.")
        return

    # Generate outreach data
    outreach_entries = []
    for scan in eligible:
        snippets = generate_badge_markdown(scan)
        entry = {
            "service_name": scan["service_name"],
            "scan_id": scan["scan_id"],
            "score": scan["clarvia_score"],
            "rating": scan.get("rating", "Unknown"),
            "category": scan.get("category", "unknown"),
            "url": scan.get("url", ""),
            "badge_snippets": snippets,
            "outreach_status": "pending",  # pending | contacted | badge_added | declined
        }
        outreach_entries.append(entry)

    # Write output
    output_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": args.threshold,
        "total_eligible": len(outreach_entries),
        "tools": outreach_entries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    logger.info("Wrote outreach data to %s", output_path)

    # Console report
    print("\n" + "=" * 72)
    print(f" Badge Outreach: {len(outreach_entries)} tools (threshold >= {args.threshold})")
    print("=" * 72)

    for i, entry in enumerate(outreach_entries, 1):
        print(
            f"\n{i:3d}. {entry['service_name']}"
            f"  (score: {entry['score']}, category: {entry['category']})"
        )
        print(f"     URL: {entry['url']}")
        print(f"     Badge: {entry['badge_snippets']['markdown_linked']}")

    print("\n" + "-" * 72)
    print(f" Output: {output_path}")
    print(f" Next step: Review list, then create PRs adding badges to READMEs")
    print("-" * 72 + "\n")


if __name__ == "__main__":
    main()
