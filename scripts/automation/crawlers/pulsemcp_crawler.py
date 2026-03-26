#!/usr/bin/env python3
"""PulseMCP Crawler — Discover MCP servers from pulsemcp.com directory (12,500+ servers).

PulseMCP is a Rails-based directory. No public JSON API found, so we scrape
the server listing pages which render server cards with names, URLs, and
descriptions in HTML. We paginate through all pages.

Usage:
    python scripts/automation/crawlers/pulsemcp_crawler.py [--dry-run] [--max-pages N]
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

import aiohttp

# Add parent dirs to path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from base import (
    RateLimiter,
    USER_AGENT,
    normalize_tool,
    load_known_urls,
    dedup_discoveries,
    save_discoveries,
    fetch_text,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://www.pulsemcp.com"
SERVERS_URL = f"{BASE_URL}/servers"

# PulseMCP rate: be polite, 1 req/sec
RATE_LIMITER = RateLimiter(delay=1.5, name="pulsemcp")


def _parse_server_cards(html: str) -> list[dict]:
    """Parse server entries from PulseMCP HTML page.

    PulseMCP renders server cards with structured HTML. We extract:
    - Name from heading/title elements
    - URL from links
    - Description from card body text
    """
    servers = []

    # Pattern 1: Look for structured card data with links to server detail pages
    # PulseMCP uses /servers/<slug> pattern
    card_pattern = re.compile(
        r'href="(/servers/[^"]+)"[^>]*>.*?'
        r'(?:<h[23456][^>]*>([^<]+)</h|class="[^"]*name[^"]*"[^>]*>([^<]+)<)',
        re.DOTALL | re.IGNORECASE,
    )

    # Pattern 2: More generic — find all server detail links with surrounding text
    link_pattern = re.compile(
        r'<a[^>]*href="(/servers/([a-zA-Z0-9_-]+))"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    # Pattern 3: Find server cards by common HTML structures
    # Look for title + description combos near /servers/ links
    block_pattern = re.compile(
        r'href="(/servers/([a-zA-Z0-9_-]+))".*?'
        r'(?:>([^<]{2,100})<)',
        re.DOTALL | re.IGNORECASE,
    )

    seen_slugs = set()

    for match in link_pattern.finditer(html):
        path = match.group(1)
        slug = match.group(2)
        link_text = re.sub(r'<[^>]+>', '', match.group(3)).strip()

        if slug in seen_slugs or not slug or slug in ("new", "trending", "search"):
            continue
        seen_slugs.add(slug)

        # Try to find description near this link
        pos = match.end()
        nearby = html[pos:pos + 500]
        desc_match = re.search(r'>([^<]{20,300})<', nearby)
        description = desc_match.group(1).strip() if desc_match else ""

        # Look for external URL (GitHub, npm, etc.) near this card
        ext_url_match = re.search(
            r'href="(https://(?:github\.com|gitlab\.com|npmjs\.com|pypi\.org)[^"]+)"',
            html[max(0, match.start() - 200):match.end() + 500],
        )
        external_url = ext_url_match.group(1) if ext_url_match else ""

        name = link_text or slug.replace("-", " ").title()

        servers.append({
            "name": name,
            "slug": slug,
            "url": external_url or f"{BASE_URL}{path}",
            "pulsemcp_url": f"{BASE_URL}{path}",
            "description": description[:300],
        })

    return servers


async def crawl_pulsemcp(
    session: aiohttp.ClientSession,
    *,
    max_pages: int = 0,
    dry_run: bool = False,
) -> list[dict]:
    """Crawl PulseMCP server directory pages."""
    all_servers = []
    page = 1
    empty_pages = 0

    while True:
        if max_pages and page > max_pages:
            logger.info("Reached max pages limit (%d)", max_pages)
            break

        url = f"{SERVERS_URL}?page={page}" if page > 1 else SERVERS_URL
        logger.info("Fetching PulseMCP page %d: %s", page, url)

        html = await fetch_text(session, url, rate_limiter=RATE_LIMITER)
        if not html:
            logger.warning("Failed to fetch page %d, stopping", page)
            break

        servers = _parse_server_cards(html)
        if not servers:
            empty_pages += 1
            if empty_pages >= 3:
                logger.info("3 consecutive empty pages, stopping at page %d", page)
                break
            page += 1
            continue

        empty_pages = 0
        all_servers.extend(servers)
        logger.info("Page %d: found %d servers (total: %d)", page, len(servers), len(all_servers))

        # Check for next page link
        if f'page={page + 1}' not in html and f"page/{page + 1}" not in html:
            # If we found servers but no next page indicator, try a few more pages
            if page > 5 and not servers:
                logger.info("No next page link found at page %d, stopping", page)
                break

        page += 1

    # Normalize to common schema
    discoveries = []
    for srv in all_servers:
        discoveries.append(normalize_tool(
            name=srv["name"],
            url=srv["url"],
            description=srv.get("description", ""),
            source="pulsemcp",
            category="mcp_server",
            extra={
                "pulsemcp_url": srv.get("pulsemcp_url", ""),
                "slug": srv.get("slug", ""),
            },
        ))

    logger.info("PulseMCP: total %d servers discovered across %d pages", len(discoveries), page - 1)
    return discoveries


async def run(dry_run: bool = False, max_pages: int = 0) -> dict:
    """Run PulseMCP crawler and return stats."""
    known_urls = load_known_urls()

    async with aiohttp.ClientSession() as session:
        discoveries = await crawl_pulsemcp(session, max_pages=max_pages, dry_run=dry_run)

    unique = dedup_discoveries(discoveries, known_urls)

    stats = {
        "source": "pulsemcp",
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
    parser = argparse.ArgumentParser(description="PulseMCP Crawler")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-pages", type=int, default=0, help="Max pages to crawl (0=all)")
    args = parser.parse_args()

    result = asyncio.run(run(dry_run=args.dry_run, max_pages=args.max_pages))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
