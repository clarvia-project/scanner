#!/usr/bin/env python3
"""Comprehensive npm MCP Package Crawler.

Enhances the base harvester npm search with:
- More search keywords and scoped package queries
- Full pagination (up to 250 results per keyword)
- Scoped packages: @modelcontextprotocol/*, @mcp/*, @anthropic/*
- Better dedup and filtering

Usage:
    python scripts/automation/crawlers/npm_comprehensive_crawler.py [--dry-run]
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from urllib.parse import quote_plus

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from base import (
    RateLimiter,
    normalize_tool,
    load_known_urls,
    dedup_discoveries,
    save_discoveries,
    fetch_json,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RATE_LIMITER = RateLimiter(delay=0.8, name="npm")

# Comprehensive search keywords
SEARCH_KEYWORDS = [
    "mcp-server",
    "mcp server",
    "@modelcontextprotocol",
    "mcp-tool",
    "model-context-protocol",
    "ai-agent-tool",
    "langchain-tool",
    "crewai-tool",
    "ai-tool-server",
    "llm-tool",
    "agent-toolkit",
    "tool-use",
    "mcp-plugin",
    "mcp-connector",
    "mcp-integration",
    "claude-tool",
    "mcp-bridge",
]

# Scoped package prefixes to search
SCOPED_PREFIXES = [
    "@modelcontextprotocol/",
    "@mcp/",
    "@anthropic/",
    "@langchain/",
    "@crewai/",
]

# npm search API — max 250 per request
NPM_SEARCH_API = "https://registry.npmjs.org/-/v1/search"
PAGE_SIZE = 250


async def _search_npm(
    session: aiohttp.ClientSession,
    keyword: str,
    *,
    max_results: int = 500,
) -> list[dict]:
    """Search npm for packages matching a keyword with pagination."""
    results = []
    offset = 0

    while offset < max_results:
        size = min(PAGE_SIZE, max_results - offset)
        url = f"{NPM_SEARCH_API}?text={quote_plus(keyword)}&size={size}&from={offset}"

        data = await fetch_json(session, url, rate_limiter=RATE_LIMITER)
        if not data:
            break

        objects = data.get("objects", [])
        if not objects:
            break

        for obj in objects:
            pkg = obj.get("package", {})
            search_score = obj.get("score", {})
            detail = search_score.get("detail", {})

            results.append({
                "name": pkg.get("name", ""),
                "version": pkg.get("version", ""),
                "description": pkg.get("description") or "",
                "keywords": pkg.get("keywords", []),
                "homepage": pkg.get("links", {}).get("homepage", ""),
                "repository": pkg.get("links", {}).get("repository", ""),
                "npm_url": pkg.get("links", {}).get("npm", ""),
                "publisher": pkg.get("publisher", {}).get("username", ""),
                "popularity": detail.get("popularity", 0),
                "quality": detail.get("quality", 0),
                "maintenance": detail.get("maintenance", 0),
                "deprecated": obj.get("flags", {}).get("deprecated", False),
            })

        total = data.get("total", 0)
        offset += len(objects)

        if len(objects) < size or offset >= total:
            break

    return results


async def crawl_npm_comprehensive(session: aiohttp.ClientSession) -> list[dict]:
    """Comprehensive npm MCP package crawl."""
    all_packages = {}  # name -> package data

    # Search by keywords
    for keyword in SEARCH_KEYWORDS:
        logger.info("npm search: '%s'", keyword)
        results = await _search_npm(session, keyword, max_results=500)
        for pkg in results:
            name = pkg["name"]
            if name not in all_packages:
                all_packages[name] = pkg
        logger.info("  '%s': %d results (unique total: %d)", keyword, len(results), len(all_packages))

    # Search scoped packages
    for prefix in SCOPED_PREFIXES:
        logger.info("npm scope search: '%s'", prefix)
        results = await _search_npm(session, prefix, max_results=250)
        for pkg in results:
            name = pkg["name"]
            if name not in all_packages:
                all_packages[name] = pkg
        logger.info("  '%s': %d results", prefix, len(results))

    # Filter and normalize
    discoveries = []
    for name, pkg in all_packages.items():
        # Skip deprecated packages
        if pkg.get("deprecated"):
            continue

        # Skip packages without description
        if not pkg.get("description"):
            continue

        # Determine best URL
        url = pkg.get("homepage") or pkg.get("repository") or pkg.get("npm_url") or f"https://www.npmjs.com/package/{name}"

        discoveries.append(normalize_tool(
            name=name,
            url=url,
            description=pkg["description"],
            source="npm",
            category="mcp_server",
            extra={
                "npm_url": pkg.get("npm_url") or f"https://www.npmjs.com/package/{name}",
                "version": pkg.get("version", ""),
                "homepage": pkg.get("homepage", ""),
                "repository": pkg.get("repository", ""),
                "keywords": pkg.get("keywords", []),
                "popularity": pkg.get("popularity", 0),
                "quality": pkg.get("quality", 0),
                "publisher": pkg.get("publisher", ""),
            },
        ))

    logger.info("npm comprehensive: %d packages (from %d total searched)", len(discoveries), len(all_packages))
    return discoveries


async def run(dry_run: bool = False) -> dict:
    known_urls = load_known_urls()

    async with aiohttp.ClientSession() as session:
        discoveries = await crawl_npm_comprehensive(session)

    unique = dedup_discoveries(discoveries, known_urls)

    stats = {
        "source": "npm_comprehensive",
        "total_found": len(discoveries),
        "new_unique": len(unique),
        "duplicates_skipped": len(discoveries) - len(unique),
    }

    if not dry_run:
        saved = save_discoveries(unique)
        stats["queued"] = saved
    else:
        stats["dry_run"] = True
        for d in unique[:5]:
            logger.info("  [NEW] %s — %s", d["name"], d["url"])
        if len(unique) > 5:
            logger.info("  ... and %d more", len(unique) - 5)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Comprehensive npm MCP Crawler")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = asyncio.run(run(dry_run=args.dry_run))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
