#!/usr/bin/env python3
"""mcpservers.org Crawler — Curated MCP server directory.

mcpservers.org hosts a curated awesome-list-style directory.
The site renders HTML with embedded server data. We scrape the listings
and also try common API patterns.

Usage:
    python scripts/automation/crawlers/mcpservers_crawler.py [--dry-run]
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
    extract_github_urls_from_markdown,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://mcpservers.org"
RATE_LIMITER = RateLimiter(delay=1.5, name="mcpservers")

# Known categories from the site
CATEGORIES = [
    "web-scraping", "communication", "productivity", "development",
    "database", "cloud-service", "file-system", "cloud-storage",
    "version-control", "ai", "search", "security", "data-analysis",
    "media", "monitoring", "automation", "education", "finance",
    "gaming", "iot", "other",
]


def _parse_server_entries(html: str) -> list[dict]:
    """Extract server entries from mcpservers.org HTML."""
    servers = []
    seen = set()

    # Pattern: look for server detail links and surrounding data
    # mcpservers.org typically uses /server/<slug> or card-based layouts

    # Try to find Next.js __NEXT_DATA__ JSON blob
    next_data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if next_data_match:
        try:
            next_data = json.loads(next_data_match.group(1))
            # Navigate the Next.js data structure for server listings
            page_props = next_data.get("props", {}).get("pageProps", {})

            # Try various key names
            for key in ("servers", "mcps", "items", "data", "tools", "featured", "latest"):
                items = page_props.get(key, [])
                if isinstance(items, list):
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        name = item.get("name") or item.get("title") or ""
                        url = item.get("url") or item.get("homepage") or item.get("github") or ""
                        slug = item.get("slug") or item.get("id") or ""
                        desc = item.get("description") or ""

                        if not name and not url:
                            continue
                        if slug in seen:
                            continue
                        seen.add(slug or url)

                        servers.append({
                            "name": name,
                            "url": url or f"{BASE_URL}/server/{slug}" if slug else "",
                            "description": desc[:300],
                            "slug": slug,
                            "category": item.get("category", ""),
                            "tags": item.get("tags", []),
                        })

            # Also check nested structures
            for key in page_props:
                if isinstance(page_props[key], dict) and "items" in page_props[key]:
                    for item in page_props[key]["items"]:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("title") or ""
                            url = item.get("url") or item.get("homepage") or ""
                            if name and url and url not in seen:
                                seen.add(url)
                                servers.append({
                                    "name": name,
                                    "url": url,
                                    "description": item.get("description", "")[:300],
                                })

        except json.JSONDecodeError:
            logger.warning("Failed to parse __NEXT_DATA__ JSON")

    # Fallback: parse HTML links
    if not servers:
        # Look for GitHub URLs in the page
        github_pattern = re.compile(
            r'href="(https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+)"[^>]*>'
            r'([^<]*)</a>',
            re.IGNORECASE,
        )
        for match in github_pattern.finditer(html):
            url = match.group(1).rstrip("/")
            name = match.group(2).strip() or url.split("/")[-1]
            if url not in seen:
                seen.add(url)
                servers.append({"name": name, "url": url, "description": ""})

        # Look for server detail page links
        detail_pattern = re.compile(
            r'href="/(server|mcp)/([a-zA-Z0-9_-]+)"[^>]*>([^<]*)</a>',
            re.IGNORECASE,
        )
        for match in detail_pattern.finditer(html):
            slug = match.group(2)
            name = match.group(3).strip() or slug.replace("-", " ").title()
            if slug not in seen:
                seen.add(slug)
                servers.append({
                    "name": name,
                    "url": f"{BASE_URL}/{match.group(1)}/{slug}",
                    "description": "",
                    "slug": slug,
                })

    return servers


async def crawl_mcpservers(session: aiohttp.ClientSession) -> list[dict]:
    """Crawl mcpservers.org for all server listings."""
    all_servers = []

    # Try main page first
    logger.info("Fetching mcpservers.org main page...")
    html = await fetch_text(session, BASE_URL, rate_limiter=RATE_LIMITER)
    if html:
        servers = _parse_server_entries(html)
        all_servers.extend(servers)
        logger.info("Main page: %d servers found", len(servers))

    # Try category pages
    for cat in CATEGORIES:
        url = f"{BASE_URL}/category/{cat}"
        html = await fetch_text(session, url, rate_limiter=RATE_LIMITER)
        if html:
            servers = _parse_server_entries(html)
            # Filter out already-seen
            new = [s for s in servers if s.get("url") not in {x.get("url") for x in all_servers}]
            all_servers.extend(new)
            if new:
                logger.info("Category %s: %d new servers", cat, len(new))

    # Try API endpoints
    for api_path in ["/api/servers", "/api/v1/servers", "/api/mcps"]:
        data = await fetch_json(session, f"{BASE_URL}{api_path}", rate_limiter=RATE_LIMITER)
        if data:
            items = data if isinstance(data, list) else data.get("servers", data.get("items", []))
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("title") or ""
                        url = item.get("url") or item.get("homepage") or ""
                        if name and url:
                            all_servers.append({
                                "name": name,
                                "url": url,
                                "description": item.get("description", "")[:300],
                            })
                logger.info("API %s: %d items", api_path, len(items))

    # Also fetch the associated awesome-mcp-servers README
    # (mcpservers.org is linked to wong2/awesome-mcp-servers)
    readme_url = "https://raw.githubusercontent.com/wong2/awesome-mcp-servers/main/README.md"
    logger.info("Fetching wong2/awesome-mcp-servers README...")
    readme = await fetch_text(session, readme_url, rate_limiter=RATE_LIMITER)
    if readme:
        entries = extract_github_urls_from_markdown(readme)
        existing_urls = {s.get("url") for s in all_servers}
        for entry in entries:
            if entry["url"] not in existing_urls:
                all_servers.append({
                    "name": entry["name"],
                    "url": entry["url"],
                    "description": entry.get("description", ""),
                })
        logger.info("Awesome list README: %d GitHub links", len(entries))

    # Normalize
    discoveries = []
    for srv in all_servers:
        if not srv.get("url"):
            continue
        discoveries.append(normalize_tool(
            name=srv["name"],
            url=srv["url"],
            description=srv.get("description", ""),
            source="mcpservers_org",
            category="mcp_server",
            extra={
                "slug": srv.get("slug", ""),
                "tags": srv.get("tags", []),
            },
        ))

    logger.info("mcpservers.org: total %d servers discovered", len(discoveries))
    return discoveries


async def run(dry_run: bool = False) -> dict:
    known_urls = load_known_urls()

    async with aiohttp.ClientSession() as session:
        discoveries = await crawl_mcpservers(session)

    unique = dedup_discoveries(discoveries, known_urls)

    stats = {
        "source": "mcpservers_org",
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
    parser = argparse.ArgumentParser(description="mcpservers.org Crawler")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = asyncio.run(run(dry_run=args.dry_run))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
