#!/usr/bin/env python3
"""Glama.ai Crawler — Discover MCP servers from Glama registry.

Glama exposes a paginated JSON API at https://glama.ai/api/mcp/v1/servers
with cursor-based pagination (pageInfo.endCursor / hasNextPage).

Usage:
    python scripts/automation/crawlers/glama_crawler.py [--dry-run] [--max-pages N]
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

GLAMA_API = "https://glama.ai/api/mcp/v1/servers"
GLAMA_BASE = "https://glama.ai"

# Polite rate: 1 req/sec
RATE_LIMITER = RateLimiter(delay=1.0, name="glama")

# Page size (API default is 10; we request more for efficiency)
PAGE_SIZE = 100


async def crawl_glama_servers(
    session: aiohttp.ClientSession,
    *,
    max_pages: int = 0,
) -> list[dict]:
    """Crawl Glama MCP server registry API."""
    all_servers: list[dict] = []
    cursor: str | None = None
    page = 0

    while True:
        page += 1
        if max_pages and page > max_pages:
            logger.info("Reached max pages limit (%d)", max_pages)
            break

        # Build URL with cursor-based pagination
        params = f"?limit={PAGE_SIZE}"
        if cursor:
            params += f"&cursor={cursor}"
        url = f"{GLAMA_API}{params}"

        logger.info("Fetching Glama page %d (cursor=%s)", page, (cursor[:20] + "...") if cursor else "start")

        data = await fetch_json(session, url, rate_limiter=RATE_LIMITER)
        if not data:
            logger.warning("Failed to fetch page %d, stopping", page)
            break

        servers = data.get("servers", [])
        page_info = data.get("pageInfo", {})

        if not servers:
            logger.info("Empty page %d, stopping", page)
            break

        for srv in servers:
            server_id = srv.get("id", "")
            name = srv.get("name", "")
            namespace = srv.get("namespace", "")
            slug = srv.get("slug", "")
            description = srv.get("description", "")
            attributes = srv.get("attributes", [])

            # Extract repository URL
            repo = srv.get("repository", {})
            repo_url = ""
            if isinstance(repo, dict):
                repo_url = repo.get("url", "")
            elif isinstance(repo, str):
                repo_url = repo

            # Canonical URL: prefer repo, then glama page
            glama_url = srv.get("url", "")
            if not glama_url and server_id:
                glama_url = f"{GLAMA_BASE}/mcp/servers/{server_id}"
            url_canonical = repo_url or glama_url

            if not url_canonical or not name:
                continue

            # Extract license info
            license_info = srv.get("spdxLicense")
            license_name = ""
            if isinstance(license_info, dict):
                license_name = license_info.get("name", "")

            # Parse attributes for hosting type and author info
            is_official = "author:official" in attributes
            hosting_type = ""
            for attr in attributes:
                if attr.startswith("hosting:"):
                    hosting_type = attr.replace("hosting:", "")
                    break

            # Count tools if available
            tools = srv.get("tools", [])
            tool_count = len(tools) if isinstance(tools, list) else 0

            all_servers.append({
                "name": name,
                "url": url_canonical,
                "glama_url": glama_url,
                "description": description[:500],
                "glama_id": server_id,
                "namespace": namespace,
                "slug": slug,
                "repo_url": repo_url,
                "license": license_name,
                "is_official": is_official,
                "hosting_type": hosting_type,
                "tool_count": tool_count,
                "attributes": attributes,
            })

        logger.info("Page %d: got %d servers (total: %d)", page, len(servers), len(all_servers))

        # Check pagination
        has_next = page_info.get("hasNextPage", False)
        if not has_next:
            logger.info("No more pages (hasNextPage=false)")
            break

        next_cursor = page_info.get("endCursor")
        if not next_cursor:
            logger.info("No endCursor in pageInfo, stopping")
            break

        cursor = next_cursor

        # Progress log every 10 pages
        if page % 10 == 0:
            logger.info("Progress: %d servers fetched across %d pages", len(all_servers), page)

    # Normalize to common schema
    discoveries = []
    for srv in all_servers:
        discoveries.append(normalize_tool(
            name=srv["name"],
            url=srv["url"],
            description=srv["description"],
            source="glama",
            category="mcp_server",
            extra={
                "glama_url": srv.get("glama_url", ""),
                "glama_id": srv.get("glama_id", ""),
                "namespace": srv.get("namespace", ""),
                "repo_url": srv.get("repo_url", ""),
                "license": srv.get("license", ""),
                "is_official": srv.get("is_official", False),
                "hosting_type": srv.get("hosting_type", ""),
                "tool_count": srv.get("tool_count", 0),
            },
        ))

    logger.info("Glama: total %d servers discovered across %d pages", len(discoveries), page)
    return discoveries


async def run(dry_run: bool = False, max_pages: int = 0) -> dict:
    """Run Glama crawler and return stats."""
    known_urls = load_known_urls()

    async with aiohttp.ClientSession() as session:
        discoveries = await crawl_glama_servers(session, max_pages=max_pages)

    unique = dedup_discoveries(discoveries, known_urls)

    stats = {
        "source": "glama",
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
    parser = argparse.ArgumentParser(description="Glama.ai Crawler")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-pages", type=int, default=0, help="Max pages to crawl (0=all)")
    args = parser.parse_args()

    result = asyncio.run(run(dry_run=args.dry_run, max_pages=args.max_pages))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
