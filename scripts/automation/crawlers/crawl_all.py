#!/usr/bin/env python3
"""Clarvia Master Crawler — Orchestrate all source crawlers for comprehensive tool discovery.

Runs each crawler sequentially, deduplicates across sources, and outputs
new discoveries to data/new-tools-queue.jsonl.

Sources (Tier 1 — 100% coverage):
  pulsemcp     — PulseMCP directory (12,500+ servers)
  smithery     — Smithery.ai registry (4,100+ servers)
  anthropic    — Official MCP registry + GitHub org
  mcpservers   — mcpservers.org curated list
  mcpso        — mcp.so marketplace (19,000+ servers)
  awesome      — Awesome MCP GitHub lists
  npm          — Comprehensive npm package search
  pypi         — Comprehensive PyPI package search

Sources (Tier 2 — trending/popular):
  langchain    — LangChain tools from GitHub
  huggingface  — Trending HuggingFace Spaces
  composio     — Composio integrations

Usage:
    python scripts/automation/crawlers/crawl_all.py [--dry-run] [--source SOURCE] [--report]
    python scripts/automation/crawlers/crawl_all.py --dry-run --source smithery
    python scripts/automation/crawlers/crawl_all.py --report  # Show last run stats
"""

import argparse
import asyncio
import importlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from base import (
    load_known_urls,
    dedup_discoveries,
    save_discoveries,
    DATA_DIR,
    QUEUE_PATH,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

REPORT_PATH = DATA_DIR / "crawl-report.json"

# All available crawlers with their module and run function
CRAWLERS = {
    # Tier 1 — Full coverage
    "pulsemcp": {
        "module": "pulsemcp_crawler",
        "tier": 1,
        "description": "PulseMCP directory (12,500+ servers)",
    },
    "smithery": {
        "module": "smithery_crawler",
        "tier": 1,
        "description": "Smithery.ai registry (4,100+ servers)",
    },
    "anthropic": {
        "module": "anthropic_mcp_crawler",
        "tier": 1,
        "description": "Official MCP registry + GitHub org",
    },
    "mcpservers": {
        "module": "mcpservers_crawler",
        "tier": 1,
        "description": "mcpservers.org curated list + awesome lists",
    },
    "mcpso": {
        "module": "mcpso_crawler",
        "tier": 1,
        "description": "mcp.so marketplace (19,000+ servers)",
    },
    "awesome": {
        "module": "awesome_lists_crawler",
        "tier": 1,
        "description": "Awesome MCP GitHub lists",
    },
    "npm": {
        "module": "npm_comprehensive_crawler",
        "tier": 1,
        "description": "Comprehensive npm MCP packages",
    },
    "pypi": {
        "module": "pypi_comprehensive_crawler",
        "tier": 1,
        "description": "Comprehensive PyPI MCP packages",
    },
    # Tier 2 — Trending/popular
    "langchain": {
        "module": "tier2_crawlers",
        "tier": 2,
        "description": "LangChain tools",
        "run_kwargs": {"sources": ["langchain"]},
    },
    "huggingface": {
        "module": "tier2_crawlers",
        "tier": 2,
        "description": "Trending HuggingFace Spaces",
        "run_kwargs": {"sources": ["huggingface"]},
    },
    "composio": {
        "module": "tier2_crawlers",
        "tier": 2,
        "description": "Composio integrations",
        "run_kwargs": {"sources": ["composio"]},
    },
}


def _load_crawler_module(module_name: str):
    """Dynamically import a crawler module."""
    return importlib.import_module(module_name)


async def run_single_crawler(
    name: str,
    config: dict,
    dry_run: bool = False,
) -> dict:
    """Run a single crawler and return stats."""
    logger.info("=" * 60)
    logger.info("Starting crawler: %s — %s", name, config["description"])
    logger.info("=" * 60)

    start_time = time.monotonic()

    try:
        mod = _load_crawler_module(config["module"])
        run_kwargs = config.get("run_kwargs", {})
        run_kwargs["dry_run"] = dry_run
        stats = await mod.run(**run_kwargs)
        elapsed = time.monotonic() - start_time

        stats["elapsed_seconds"] = round(elapsed, 1)
        stats["status"] = "success"

        logger.info(
            "Crawler %s completed in %.1fs — found: %d, new: %d",
            name, elapsed,
            stats.get("total_found", 0),
            stats.get("new_unique", 0),
        )
        return stats

    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.error("Crawler %s failed after %.1fs: %s", name, elapsed, e)
        return {
            "status": "error",
            "error": str(e),
            "elapsed_seconds": round(elapsed, 1),
        }


async def run_all(
    sources: list[str] | None = None,
    dry_run: bool = False,
    tier: int | None = None,
) -> dict:
    """Run all specified crawlers sequentially."""
    start_time = datetime.now(timezone.utc)
    results = {}
    total_found = 0
    total_new = 0

    # Determine which crawlers to run
    if sources:
        crawlers_to_run = {k: v for k, v in CRAWLERS.items() if k in sources}
    elif tier:
        crawlers_to_run = {k: v for k, v in CRAWLERS.items() if v["tier"] == tier}
    else:
        crawlers_to_run = CRAWLERS

    logger.info("Running %d crawlers (dry_run=%s)", len(crawlers_to_run), dry_run)

    for name, config in crawlers_to_run.items():
        stats = await run_single_crawler(name, config, dry_run=dry_run)
        results[name] = stats
        total_found += stats.get("total_found", 0)
        total_new += stats.get("new_unique", 0)

    # Build report
    end_time = datetime.now(timezone.utc)
    report = {
        "started_at": start_time.isoformat(),
        "finished_at": end_time.isoformat(),
        "elapsed_seconds": round((end_time - start_time).total_seconds(), 1),
        "dry_run": dry_run,
        "crawlers_run": len(crawlers_to_run),
        "total_found_across_all": total_found,
        "total_new_unique": total_new,
        "per_source": results,
    }

    # Save report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("CRAWL SUMMARY")
    logger.info("=" * 60)
    logger.info("Total found:  %d", total_found)
    logger.info("New unique:   %d", total_new)
    logger.info("Duration:     %.1fs", report["elapsed_seconds"])
    logger.info("-" * 60)

    for name, stats in results.items():
        status = stats.get("status", "unknown")
        found = stats.get("total_found", 0)
        new = stats.get("new_unique", 0)
        elapsed = stats.get("elapsed_seconds", 0)
        icon = "OK" if status == "success" else "ERR"
        logger.info(
            "  [%s] %-15s  found=%5d  new=%5d  (%.1fs)",
            icon, name, found, new, elapsed,
        )

    logger.info("=" * 60)
    logger.info("Report saved: %s", REPORT_PATH)

    return report


def show_report():
    """Display the last crawl report."""
    if not REPORT_PATH.exists():
        print("No crawl report found. Run a crawl first.")
        return

    with open(REPORT_PATH) as f:
        report = json.load(f)

    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Clarvia Master Crawler — Comprehensive tool discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sources:
  Tier 1: pulsemcp, smithery, anthropic, mcpservers, mcpso, awesome, npm, pypi
  Tier 2: langchain, huggingface, composio

Examples:
  crawl_all.py --dry-run                    # Test all crawlers
  crawl_all.py --source smithery --dry-run  # Test single crawler
  crawl_all.py --tier 1                     # Run all Tier 1 crawlers
  crawl_all.py --report                     # Show last run report
""",
    )
    parser.add_argument("--dry-run", action="store_true", help="Discover but don't queue")
    parser.add_argument(
        "--source",
        choices=list(CRAWLERS.keys()),
        nargs="+",
        help="Run specific crawler(s)",
    )
    parser.add_argument("--tier", type=int, choices=[1, 2], help="Run all crawlers of a tier")
    parser.add_argument("--report", action="store_true", help="Show last crawl report")
    args = parser.parse_args()

    if args.report:
        show_report()
        return

    result = asyncio.run(run_all(
        sources=args.source,
        dry_run=args.dry_run,
        tier=args.tier,
    ))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
