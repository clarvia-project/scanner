#!/usr/bin/env python3
"""Smithery.ai Crawler — Discover MCP servers from Smithery registry (4,100+ servers).

Smithery exposes a paginated JSON API at https://registry.smithery.ai/servers
with 10 items per page and 410+ pages total.

Usage:
    python scripts/automation/crawlers/smithery_crawler.py [--dry-run] [--max-pages N]
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

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

REGISTRY_API = "https://registry.smithery.ai/servers"
SMITHERY_BASE = "https://smithery.ai"

# Polite rate: 1 req/sec
RATE_LIMITER = RateLimiter(delay=1.0, name="smithery")

# Page size — Smithery default is 10, max is unclear; use 10 for safety
PAGE_SIZE = 10


async def crawl_smithery_servers(
    session: aiohttp.ClientSession,
    *,
    max_pages: int = 0,
) -> list[dict]:
    """Crawl Smithery registry API for all MCP servers."""
    all_servers = []
    page = 1
    total_pages = None

    while True:
        if max_pages and page > max_pages:
            logger.info("Reached max pages limit (%d)", max_pages)
            break

        if total_pages and page > total_pages:
            break

        url = f"{REGISTRY_API}?page={page}&pageSize={PAGE_SIZE}"
        logger.info("Fetching Smithery page %d/%s", page, total_pages or "?")

        data = await fetch_json(session, url, rate_limiter=RATE_LIMITER)
        if not data:
            logger.warning("Failed to fetch page %d, stopping", page)
            break

        servers = data.get("servers", [])
        pagination = data.get("pagination", {})

        if total_pages is None:
            total_pages = pagination.get("totalPages", 1)
            total_count = pagination.get("totalCount", len(servers))
            logger.info("Smithery registry: %d total servers, %d pages", total_count, total_pages)

        if not servers:
            logger.info("Empty page %d, stopping", page)
            break

        for srv in servers:
            name = srv.get("displayName") or srv.get("qualifiedName") or ""
            qualified = srv.get("qualifiedName", "")
            description = srv.get("description") or ""
            homepage = srv.get("homepage") or ""

            # Build the canonical URL — prefer homepage if it's a real URL
            if homepage and homepage.startswith("http"):
                url = homepage
            else:
                url = f"{SMITHERY_BASE}/server/{qualified}" if qualified else ""

            if not url:
                continue

            all_servers.append({
                "name": name,
                "url": url,
                "smithery_url": f"{SMITHERY_BASE}/server/{qualified}" if qualified else "",
                "description": description[:500],
                "qualified_name": qualified,
                "verified": srv.get("verified", False),
                "use_count": srv.get("useCount", 0),
                "icon_url": srv.get("iconUrl", ""),
                "created_at": srv.get("createdAt", ""),
                "is_deployed": srv.get("isDeployed", False),
            })

        page += 1

        # Log progress every 50 pages
        if page % 50 == 0:
            logger.info("Progress: %d servers fetched so far across %d pages", len(all_servers), page - 1)

    # Normalize to common schema
    discoveries = []
    for srv in all_servers:
        discoveries.append(normalize_tool(
            name=srv["name"],
            url=srv["url"],
            description=srv["description"],
            source="smithery",
            category="mcp_server",
            extra={
                "smithery_url": srv.get("smithery_url", ""),
                "qualified_name": srv.get("qualified_name", ""),
                "verified": srv.get("verified", False),
                "use_count": srv.get("use_count", 0),
                "is_deployed": srv.get("is_deployed", False),
            },
        ))

    logger.info("Smithery: total %d servers discovered", len(discoveries))
    return discoveries


async def run(dry_run: bool = False, max_pages: int = 0) -> dict:
    """Run Smithery crawler and return stats."""
    known_urls = load_known_urls()

    async with aiohttp.ClientSession() as session:
        discoveries = await crawl_smithery_servers(session, max_pages=max_pages)

    unique = dedup_discoveries(discoveries, known_urls)

    stats = {
        "source": "smithery",
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
    parser = argparse.ArgumentParser(description="Smithery.ai Crawler")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-pages", type=int, default=0, help="Max pages to crawl (0=all)")
    args = parser.parse_args()

    result = asyncio.run(run(dry_run=args.dry_run, max_pages=args.max_pages))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
