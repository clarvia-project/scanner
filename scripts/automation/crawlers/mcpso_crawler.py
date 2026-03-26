#!/usr/bin/env python3
"""mcp.so Crawler — Community MCP marketplace (19,000+ servers).

mcp.so is a Next.js app with 19,000+ servers. It uses server-side rendering
with paginated listings (305+ pages). We try multiple API discovery strategies
and fall back to HTML scraping.

Usage:
    python scripts/automation/crawlers/mcpso_crawler.py [--dry-run] [--max-pages N]
"""

import argparse
import asyncio
import json
import logging
import re
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
    fetch_text,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://mcp.so"
RATE_LIMITER = RateLimiter(delay=2.0, name="mcp_so")


def _parse_next_data(html: str) -> list[dict]:
    """Extract server data from Next.js __NEXT_DATA__ script tag."""
    servers = []

    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return servers

    try:
        data = json.loads(match.group(1))
        page_props = data.get("props", {}).get("pageProps", {})

        # Walk through all page props looking for server arrays
        def _extract_servers(obj, depth=0):
            if depth > 5:
                return
            if isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict) and ("name" in item or "title" in item):
                        name = item.get("name") or item.get("title") or ""
                        url = (
                            item.get("url")
                            or item.get("homepage")
                            or item.get("github_url")
                            or item.get("github")
                            or item.get("repository")
                            or ""
                        )
                        slug = item.get("slug") or item.get("id") or ""
                        desc = item.get("description") or item.get("short_description") or ""

                        if name:
                            servers.append({
                                "name": name,
                                "url": url or (f"{BASE_URL}/server/{slug}" if slug else ""),
                                "mcpso_url": f"{BASE_URL}/server/{slug}" if slug else "",
                                "description": desc[:500],
                                "slug": slug,
                                "category": item.get("category", ""),
                                "stars": item.get("stars", 0),
                                "tags": item.get("tags", []),
                            })
                    elif isinstance(item, dict):
                        _extract_servers(item, depth + 1)
            elif isinstance(obj, dict):
                for v in obj.values():
                    if isinstance(v, (dict, list)):
                        _extract_servers(v, depth + 1)

        _extract_servers(page_props)

    except json.JSONDecodeError:
        logger.warning("Failed to parse __NEXT_DATA__")

    return servers


def _parse_html_links(html: str) -> list[dict]:
    """Extract server links from mcp.so HTML (Next.js App Router SSR output)."""
    servers = []
    seen = set()

    # mcp.so uses URLs like /server/<slug>/<owner> or /en/server/<slug>/<owner>
    # Also simple /server/<slug> format
    patterns = [
        # /en/server/slug/owner or /server/slug/owner
        re.compile(r'href="/(?:en/)?server/([a-zA-Z0-9._-]+(?:/[a-zA-Z0-9._-]+)?)"', re.I),
    ]

    skip_slugs = {"new", "trending", "search", "latest", "featured", "categories", "tags"}

    for pattern in patterns:
        for match in pattern.finditer(html):
            full_path = match.group(1)
            parts = full_path.split("/")
            slug = parts[0]
            owner = parts[1] if len(parts) > 1 else ""

            if slug in seen or slug in skip_slugs:
                continue
            seen.add(slug)

            name = slug.replace("-", " ").replace("_", " ").title()
            server_url = f"{BASE_URL}/server/{full_path}"

            servers.append({
                "name": name,
                "url": server_url,
                "mcpso_url": server_url,
                "slug": slug,
                "owner": owner,
                "description": "",
            })

    # Also extract GitHub links
    gh_pattern = re.compile(
        r'href="(https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+)"', re.I
    )
    for match in gh_pattern.finditer(html):
        url = match.group(1).rstrip("/")
        if url not in seen:
            seen.add(url)
            name = url.split("/")[-1]
            servers.append({"name": name, "url": url, "description": ""})

    return servers


async def crawl_mcpso(
    session: aiohttp.ClientSession,
    *,
    max_pages: int = 0,
) -> list[dict]:
    """Crawl mcp.so for MCP server listings."""
    all_servers = []
    seen_urls = set()

    # Strategy 1: Try API endpoints
    api_paths = [
        "/api/servers",
        "/api/v1/servers",
        "/api/mcp/list",
        "/api/tools",
        "/api/servers/list",
    ]

    for api_path in api_paths:
        for page in range(1, 4):  # Try first 3 pages of each API
            params = f"?page={page}&pageSize=100&limit=100"
            data = await fetch_json(session, f"{BASE_URL}{api_path}{params}", rate_limiter=RATE_LIMITER)
            if data:
                items = data if isinstance(data, list) else data.get("data", data.get("servers", data.get("items", [])))
                if isinstance(items, list) and items:
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("title") or ""
                            url = item.get("url") or item.get("homepage") or item.get("github") or ""
                            if name and url and url not in seen_urls:
                                seen_urls.add(url)
                                all_servers.append({
                                    "name": name,
                                    "url": url,
                                    "description": item.get("description", "")[:300],
                                })
                    logger.info("API %s page %d: %d items", api_path, page, len(items))
                else:
                    break  # No more results from this API
            else:
                break  # This API doesn't exist

    # Strategy 2: Scrape HTML pages (mcp.so uses /servers?page=N)
    pages_to_crawl = max_pages or 100  # Default to 100 pages (~49 per page = ~4900)
    for page in range(1, pages_to_crawl + 1):
        url = f"{BASE_URL}/servers?page={page}" if page > 1 else f"{BASE_URL}/servers"
        logger.info("Fetching mcp.so page %d", page)

        html = await fetch_text(session, url, rate_limiter=RATE_LIMITER)
        if not html:
            break

        # Try Next.js data first
        servers = _parse_next_data(html)
        if not servers:
            servers = _parse_html_links(html)

        if not servers:
            logger.info("No servers found on page %d, stopping", page)
            break

        new_count = 0
        for srv in servers:
            srv_url = srv.get("url", "")
            if srv_url and srv_url not in seen_urls:
                seen_urls.add(srv_url)
                all_servers.append(srv)
                new_count += 1

        logger.info("Page %d: %d new servers (total: %d)", page, new_count, len(all_servers))

        if new_count == 0:
            break

    # Also try category/section pages
    for section in ["servers?sort=featured", "servers?sort=latest", "servers?sort=trending"]:
        url = f"{BASE_URL}/{section}"
        html = await fetch_text(session, url, rate_limiter=RATE_LIMITER)
        if html:
            servers = _parse_next_data(html)
            if not servers:
                servers = _parse_html_links(html)
            for srv in servers:
                srv_url = srv.get("url", "")
                if srv_url and srv_url not in seen_urls:
                    seen_urls.add(srv_url)
                    all_servers.append(srv)

    # Normalize
    discoveries = []
    for srv in all_servers:
        if not srv.get("url"):
            continue
        discoveries.append(normalize_tool(
            name=srv["name"],
            url=srv["url"],
            description=srv.get("description", ""),
            source="mcp_so",
            category="mcp_server",
            extra={
                "mcpso_url": srv.get("mcpso_url", ""),
                "slug": srv.get("slug", ""),
                "tags": srv.get("tags", []),
            },
        ))

    logger.info("mcp.so: total %d servers discovered", len(discoveries))
    return discoveries


async def run(dry_run: bool = False, max_pages: int = 0) -> dict:
    known_urls = load_known_urls()

    async with aiohttp.ClientSession() as session:
        discoveries = await crawl_mcpso(session, max_pages=max_pages)

    unique = dedup_discoveries(discoveries, known_urls)

    stats = {
        "source": "mcp_so",
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
    parser = argparse.ArgumentParser(description="mcp.so Crawler")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-pages", type=int, default=0, help="Max pages (0=default 50)")
    args = parser.parse_args()

    result = asyncio.run(run(dry_run=args.dry_run, max_pages=args.max_pages))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
