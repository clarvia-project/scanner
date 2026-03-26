#!/usr/bin/env python3
"""Clarvia Top 50 Curation System.

Selects the best ~50 tools from the entire catalog (top 3-5 per category)
using a composite curation score that weighs AEO score, popularity,
documentation quality, freshness, and uniqueness.

Outputs:
- data/curated/top50.json  — structured data for the API
- data/curated/top50.md    — human-readable markdown

Usage:
    python scripts/automation/curator.py [--limit 50] [--per-category 5]
"""

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
PREBUILT_PATH = DATA_DIR / "prebuilt-scans.json"
FEEDBACK_DIR = DATA_DIR / "feedback"
CURATED_DIR = DATA_DIR / "curated"

# Add parent to path for classifier import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from classifier import classify_tool


def _load_catalog() -> list[dict[str, Any]]:
    """Load the full tool catalog."""
    if not PREBUILT_PATH.exists():
        logger.error("Catalog not found at %s", PREBUILT_PATH)
        return []
    with open(PREBUILT_PATH) as f:
        return json.load(f)


def _load_feedback_signals() -> dict[str, float]:
    """Load popularity signals from the feedback engine.

    Returns a dict of {tool_url: popularity_score (0-1)}.
    """
    signals: dict[str, float] = {}
    signals_file = FEEDBACK_DIR / "usage_signals.jsonl"
    if not signals_file.exists():
        return signals

    try:
        with open(signals_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                url = entry.get("url", "").rstrip("/").lower()
                pop = entry.get("popularity_boost", entry.get("popularity_signal", 0))
                if url:
                    # Keep the highest signal if there are duplicates
                    signals[url] = max(signals.get(url, 0), pop)
    except Exception as e:
        logger.warning("Failed to load feedback signals: %s", e)

    return signals


def _normalize_name(name: str) -> str:
    """Normalize a tool name for duplicate/fork detection."""
    name = name.lower().strip()
    # Remove common prefixes/suffixes
    for prefix in ("mcp-server-", "mcp-", "@modelcontextprotocol/server-"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    # Remove version suffixes
    name = re.sub(r"[-_]v?\d+(\.\d+)*$", "", name)
    # Normalize separators
    name = re.sub(r"[-_.\s]+", "-", name)
    return name


def compute_curation_score(
    tool: dict[str, Any],
    feedback_signals: dict[str, float],
    seen_names: set[str],
) -> tuple[float, str]:
    """Compute a composite curation score (0-100) for a tool.

    Weights:
    - Clarvia AEO score:       40%
    - Popularity signal:       20%
    - Documentation quality:   20%
    - Freshness:               10%
    - Uniqueness:              10%

    Returns (score, one_line_reason).
    """
    reasons = []

    # --- Clarvia AEO score (0-40) ---
    aeo_score = tool.get("clarvia_score", 0)
    aeo_component = (aeo_score / 100) * 40
    if aeo_score >= 80:
        reasons.append(f"Strong AEO score ({aeo_score})")
    elif aeo_score >= 60:
        reasons.append(f"Good AEO score ({aeo_score})")

    # --- Popularity signal (0-20) ---
    url_lower = tool.get("url", "").rstrip("/").lower()
    pop_signal = feedback_signals.get(url_lower, 0)
    pop_component = pop_signal * 20
    if pop_signal > 0.5:
        reasons.append("High community usage")

    # --- Documentation quality (0-20) ---
    doc_score = 0
    dimensions = tool.get("dimensions", {})

    # Check for structured documentation signals
    doc_dim = dimensions.get("documentation_quality", {})
    if doc_dim:
        doc_raw = doc_dim.get("score", 0)
        doc_max = doc_dim.get("max", 25)
        if doc_max > 0:
            doc_score = (doc_raw / doc_max) * 20
    else:
        # Fallback: heuristic from available fields
        if tool.get("description") and len(tool.get("description", "")) > 20:
            doc_score += 5
        # Check if has API docs or OpenAPI spec
        api_dim = dimensions.get("api_accessibility", {})
        if api_dim and api_dim.get("score", 0) > 15:
            doc_score += 8
        # Check for README-based evidence
        for sub_key, sub_val in (doc_dim.get("sub_factors", {}) if doc_dim else {}).items():
            if sub_val.get("score", 0) > 0:
                doc_score += 2

    doc_component = min(doc_score, 20)
    if doc_component >= 15:
        reasons.append("Excellent documentation")

    # --- Freshness (0-10) ---
    freshness_component = 0
    scanned_at = tool.get("scanned_at", "")
    if scanned_at:
        try:
            if scanned_at.endswith("Z"):
                scanned_at = scanned_at.replace("Z", "+00:00")
            scan_dt = datetime.fromisoformat(scanned_at)
            days_since = (datetime.now(timezone.utc) - scan_dt).days
            if days_since <= 30:
                freshness_component = 10
            elif days_since <= 90:
                freshness_component = 7
            elif days_since <= 180:
                freshness_component = 4
            else:
                freshness_component = 1
        except (ValueError, TypeError):
            freshness_component = 2

    if freshness_component >= 7:
        reasons.append("Recently updated")

    # --- Uniqueness (0-10) ---
    norm_name = _normalize_name(tool.get("service_name", ""))
    if norm_name and norm_name not in seen_names:
        uniqueness_component = 10
    else:
        uniqueness_component = 0
        reasons.append("Similar tool already selected")

    total = aeo_component + pop_component + doc_component + freshness_component + uniqueness_component
    reason = "; ".join(reasons[:3]) if reasons else "Meets baseline quality"
    return round(total, 1), reason


def curate_top50(
    limit: int = 50,
    per_category: int = 5,
) -> dict[str, Any]:
    """Select the top tools from the catalog.

    Algorithm:
    1. Load and classify all tools
    2. Score each tool with composite curation score
    3. Select top per_category per category, up to total limit
    4. Generate structured + markdown outputs
    """
    catalog = _load_catalog()
    if not catalog:
        return {"error": "Empty catalog"}

    feedback_signals = _load_feedback_signals()
    logger.info(
        "Loaded catalog (%d tools), feedback signals (%d entries)",
        len(catalog), len(feedback_signals),
    )

    # Classify and group by category
    by_category: dict[str, list[dict]] = defaultdict(list)
    for tool in catalog:
        cat = tool.get("category", "other")
        if cat in ("other", "", None):
            cat = classify_tool(
                tool.get("service_name", ""),
                tool.get("description", ""),
                tool.get("url", ""),
                tool.get("tags", []),
            )
            tool["category"] = cat
        by_category[cat].append(tool)

    # Score tools per category and pick top N
    selected: list[dict] = []
    category_picks: dict[str, list[dict]] = {}
    global_seen_names: set[str] = set()

    # Sort categories by total tool count (larger categories first for diversity)
    sorted_cats = sorted(by_category.keys(), key=lambda c: len(by_category[c]), reverse=True)

    for cat in sorted_cats:
        if cat == "other":
            continue  # Skip uncategorizable tools

        tools = by_category[cat]
        scored: list[tuple[float, str, dict]] = []

        # Reset per-category name tracking but keep global dedup
        cat_seen = set(global_seen_names)

        for tool in tools:
            score, reason = compute_curation_score(tool, feedback_signals, cat_seen)
            norm = _normalize_name(tool.get("service_name", ""))
            scored.append((score, reason, tool))
            cat_seen.add(norm)

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Pick top N unique tools
        picks = []
        pick_names: set[str] = set()
        for score, reason, tool in scored:
            norm = _normalize_name(tool.get("service_name", ""))
            if norm in global_seen_names:
                continue
            picks.append({
                "name": tool.get("service_name", ""),
                "url": tool.get("url", ""),
                "category": cat,
                "clarvia_score": tool.get("clarvia_score", 0),
                "curation_score": score,
                "reason": reason,
                "rating": tool.get("rating", ""),
                "scan_id": tool.get("scan_id", ""),
                "description": (tool.get("description") or "")[:200],
            })
            global_seen_names.add(norm)
            pick_names.add(norm)
            if len(picks) >= per_category:
                break

        if picks:
            category_picks[cat] = picks
            selected.extend(picks)

        if len(selected) >= limit:
            break

    # Trim to exact limit, keeping category balance
    selected = selected[:limit]

    # Sort final list by curation score
    selected.sort(key=lambda x: x["curation_score"], reverse=True)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(selected),
        "categories": len(category_picks),
        "tools": selected,
        "by_category": {
            cat: [t["name"] for t in picks]
            for cat, picks in category_picks.items()
        },
    }

    # Write outputs
    CURATED_DIR.mkdir(parents=True, exist_ok=True)

    # JSON output
    json_path = CURATED_DIR / "top50.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("Wrote %s (%d tools)", json_path, len(selected))

    # Markdown output
    md_lines = [
        "# Clarvia Top 50 AI Agent Tools",
        "",
        f"*Generated: {result['generated_at']}*",
        f"*{len(selected)} tools across {len(category_picks)} categories*",
        "",
        "---",
        "",
    ]

    for cat in sorted(category_picks.keys()):
        picks = category_picks[cat]
        md_lines.append(f"## {cat.replace('-', ' ').title()}")
        md_lines.append("")
        for i, t in enumerate(picks, 1):
            score_str = f"AEO {t['clarvia_score']}"
            md_lines.append(
                f"{i}. **{t['name']}** ({score_str}) — {t['reason']}"
            )
            if t.get("description"):
                md_lines.append(f"   {t['description'][:120]}")
            md_lines.append(f"   {t['url']}")
            md_lines.append("")
        md_lines.append("")

    md_path = CURATED_DIR / "top50.md"
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))
    logger.info("Wrote %s", md_path)

    return result


def main():
    parser = argparse.ArgumentParser(description="Clarvia Top 50 Curation System")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Total number of tools to select (default: 50)",
    )
    parser.add_argument(
        "--per-category",
        type=int,
        default=5,
        help="Max tools per category (default: 5)",
    )
    args = parser.parse_args()

    result = curate_top50(limit=args.limit, per_category=args.per_category)
    print(json.dumps({
        "total": result.get("total", 0),
        "categories": result.get("categories", 0),
        "by_category": result.get("by_category", {}),
    }, indent=2))


if __name__ == "__main__":
    main()
