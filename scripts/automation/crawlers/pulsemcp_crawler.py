#!/usr/bin/env python3
"""PulseMCP Crawler — Discover MCP servers from pulsemcp.com directory (12,500+ servers).

PulseMCP implements the Generic MCP Registry API at https://api.pulsemcp.com/v0.1.
When PULSEMCP_API_KEY is set, uses the REST API for richer metadata (popularity,
security analysis, official status). Falls back to HTML scraping when no key is
available.

Usage:
    python scripts/automation/crawlers/pulsemcp_crawler.py [--dry-run] [--max-pages N]

Environment:
    PULSEMCP_API_KEY  — API key for api.pulsemcp.com (optional; enables REST API mode)
"""

import argparse
import asyncio
import json
import logging
import os
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
    fetch_json,
    fetch_text,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# REST API (preferred when API key is available)
API_BASE = "https://api.pulsemcp.com"
API_SERVERS = f"{API_BASE}/v0.1/servers"
PULSEMCP_API_KEY = os.environ.get("PULSEMCP_API_KEY", "")

# HTML fallback
HTML_BASE_URL = "https://www.pulsemcp.com"
HTML_SERVERS_URL = f"{HTML_BASE_URL}/servers"

# Polite rate limiting: 1 req/sec
RATE_LIMITER = RateLimiter(delay=1.0, name="pulsemcp")

# API page size (max 100 per PulseMCP docs)
API_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# REST API mode
# ---------------------------------------------------------------------------

async def _fetch_api_page(
    session: aiohttp.ClientSession,
    cursor: str | None = None,
) -> dict | None:
    """Fetch one page from the PulseMCP REST API."""
    params = f"?limit={API_PAGE_SIZE}"
    if cursor:
        params += f"&cursor={cursor}"
    url = f"{API_SERVERS}{params}"

    headers = {
        "X-API-Key": PULSEMCP_API_KEY,
        "Accept": "application/json",
    }

    return await fetch_json(session, url, headers=headers, rate_limiter=RATE_LIMITER)


def _parse_api_server(entry: dict) -> dict | None:
    """Parse a single server entry from the REST API response."""
    server = entry.get("server", entry)  # Handle both wrapped and flat formats
    meta = entry.get("_meta", {})

    name = server.get("name") or server.get("displayName") or ""
    description = server.get("description") or ""
    if not name:
        return None

    # Extract repository URL if available
    repo = server.get("repository", {})
    repo_url = ""
    if isinstance(repo, dict):
        repo_url = repo.get("url", "")
    elif isinstance(repo, str):
        repo_url = repo

    # Build canonical URL: prefer repo, then homepage
    homepage = server.get("homepage", "")
    url = repo_url or homepage or ""

    # PulseMCP enrichments
    pulsemcp_meta = meta.get("com.pulsemcp/server", {})
    version_meta = meta.get("com.pulsemcp/server-version", {})

    return {
        "name": name,
        "url": url,
        "description": description[:500],
        "server_name": server.get("name", ""),
        "version": server.get("version", ""),
        "is_official": pulsemcp_meta.get("isOfficial", False),
        "visitors_weekly": pulsemcp_meta.get("visitorsEstimateMostRecentWeek"),
        "visitors_monthly": pulsemcp_meta.get("visitorsEstimateLastFourWeeks"),
        "visitors_total": pulsemcp_meta.get("visitorsEstimateTotal"),
        "status": version_meta.get("status", ""),
        "published_at": version_meta.get("publishedAt", ""),
        "updated_at": version_meta.get("updatedAt", ""),
        "is_latest": version_meta.get("isLatest", True),
        "source_registry": version_meta.get("source", ""),
        "repo_url": repo_url,
        "homepage": homepage,
    }


async def crawl_pulsemcp_api(
    session: aiohttp.ClientSession,
    *,
    max_pages: int = 0,
) -> list[dict]:
    """Crawl PulseMCP via REST API (requires PULSEMCP_API_KEY)."""
    all_servers: list[dict] = []
    cursor: str | None = None
    page = 0

    while True:
        page += 1
        if max_pages and page > max_pages:
            logger.info("Reached max pages limit (%d)", max_pages)
            break

        logger.info("Fetching PulseMCP API page %d (cursor=%s)", page, cursor[:20] + "..." if cursor else "start")
        data = await _fetch_api_page(session, cursor=cursor)

        if not data:
            logger.warning("Failed to fetch API page %d, stopping", page)
            break

        servers_raw = data.get("servers", [])
        metadata = data.get("metadata", {})

        if not servers_raw:
            logger.info("Empty page %d, stopping", page)
            break

        for entry in servers_raw:
            parsed = _parse_api_server(entry)
            if parsed and parsed["url"]:
                all_servers.append(parsed)

        count = metadata.get("count", len(servers_raw))
        next_cursor = metadata.get("nextCursor")
        logger.info("Page %d: got %d entries (total: %d)", page, count, len(all_servers))

        if not next_cursor:
            logger.info("No more pages (nextCursor is null)")
            break

        cursor = next_cursor

    # Normalize to common schema
    discoveries = []
    for srv in all_servers:
        extra = {
            "pulsemcp_server_name": srv.get("server_name", ""),
            "is_official": srv.get("is_official", False),
            "visitors_weekly": srv.get("visitors_weekly"),
            "visitors_monthly": srv.get("visitors_monthly"),
            "visitors_total": srv.get("visitors_total"),
            "status": srv.get("status", ""),
            "published_at": srv.get("published_at", ""),
            "repo_url": srv.get("repo_url", ""),
        }
        # Remove None values
        extra = {k: v for k, v in extra.items() if v is not None}

        discoveries.append(normalize_tool(
            name=srv["name"],
            url=srv["url"],
            description=srv["description"],
            source="pulsemcp",
            category="mcp_server",
            extra=extra,
        ))

    logger.info("PulseMCP API: total %d servers discovered across %d pages", len(discoveries), page)
    return discoveries


# ---------------------------------------------------------------------------
# HTML scraping fallback (no API key needed)
# ---------------------------------------------------------------------------

def _parse_server_cards(html: str) -> list[dict]:
    """Parse server entries from PulseMCP HTML page."""
    servers = []
    seen_slugs: set[str] = set()

    link_pattern = re.compile(
        r'<a[^>]*href="(/servers/([a-zA-Z0-9_-]+))"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    for match in link_pattern.finditer(html):
        path = match.group(1)
        slug = match.group(2)
        link_text = re.sub(r'<[^>]+>', '', match.group(3)).strip()

        if slug in seen_slugs or not slug or slug in ("new", "trending", "search"):
            continue
        seen_slugs.add(slug)

        # Extract description near link
        pos = match.end()
        nearby = html[pos:pos + 500]
        desc_match = re.search(r'>([^<]{20,300})<', nearby)
        description = desc_match.group(1).strip() if desc_match else ""

        # Look for external URL nearby
        ext_url_match = re.search(
            r'href="(https://(?:github\.com|gitlab\.com|npmjs\.com|pypi\.org)[^"]+)"',
            html[max(0, match.start() - 200):match.end() + 500],
        )
        external_url = ext_url_match.group(1) if ext_url_match else ""

        name = link_text or slug.replace("-", " ").title()

        servers.append({
            "name": name,
            "slug": slug,
            "url": external_url or f"{HTML_BASE_URL}{path}",
            "pulsemcp_url": f"{HTML_BASE_URL}{path}",
            "description": description[:300],
        })

    return servers


async def crawl_pulsemcp_html(
    session: aiohttp.ClientSession,
    *,
    max_pages: int = 0,
) -> list[dict]:
    """Crawl PulseMCP via HTML scraping (fallback when no API key)."""
    all_servers: list[dict] = []
    page = 1
    empty_pages = 0

    while True:
        if max_pages and page > max_pages:
            logger.info("Reached max pages limit (%d)", max_pages)
            break

        url = f"{HTML_SERVERS_URL}?page={page}" if page > 1 else HTML_SERVERS_URL
        logger.info("Fetching PulseMCP HTML page %d: %s", page, url)

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

        if f'page={page + 1}' not in html and f"page/{page + 1}" not in html:
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

    logger.info("PulseMCP HTML: total %d servers discovered across %d pages", len(discoveries), page - 1)
    return discoveries


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def crawl_pulsemcp(
    session: aiohttp.ClientSession,
    *,
    max_pages: int = 0,
    dry_run: bool = False,
) -> list[dict]:
    """Crawl PulseMCP — uses REST API if key is available, else HTML scraping."""
    if PULSEMCP_API_KEY:
        logger.info("PulseMCP: using REST API mode (API key found)")
        return await crawl_pulsemcp_api(session, max_pages=max_pages)
    else:
        logger.info("PulseMCP: using HTML scraping mode (no PULSEMCP_API_KEY set)")
        return await crawl_pulsemcp_html(session, max_pages=max_pages)


async def run(dry_run: bool = False, max_pages: int = 0) -> dict:
    """Run PulseMCP crawler and return stats."""
    known_urls = load_known_urls()

    async with aiohttp.ClientSession() as session:
        discoveries = await crawl_pulsemcp(session, max_pages=max_pages, dry_run=dry_run)

    unique = dedup_discoveries(discoveries, known_urls)

    stats = {
        "source": "pulsemcp",
        "mode": "api" if PULSEMCP_API_KEY else "html",
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
