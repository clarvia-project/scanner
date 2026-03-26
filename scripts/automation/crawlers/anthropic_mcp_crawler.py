#!/usr/bin/env python3
"""Anthropic Official MCP Crawler — modelcontextprotocol registry + GitHub repos.

Sources:
1. Official registry API: https://registry.modelcontextprotocol.io/v0/servers
2. Official GitHub org repos: https://github.com/modelcontextprotocol/servers
3. GitHub org: https://github.com/modelcontextprotocol (all repos)

Usage:
    python scripts/automation/crawlers/anthropic_mcp_crawler.py [--dry-run]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import aiohttp

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
    extract_github_urls_from_markdown,
    GITHUB_TOKEN,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REGISTRY_API = "https://registry.modelcontextprotocol.io/v0/servers"
GITHUB_ORG = "modelcontextprotocol"
GITHUB_API = "https://api.github.com"

RATE_LIMITER = RateLimiter(delay=1.0 if GITHUB_TOKEN else 6.5, name="github")
REGISTRY_LIMITER = RateLimiter(delay=0.5, name="mcp_registry")


def _github_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": USER_AGENT,
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


async def crawl_official_registry(session: aiohttp.ClientSession) -> list[dict]:
    """Fetch all servers from the official MCP registry API."""
    logger.info("Fetching official MCP registry...")
    data = await fetch_json(
        session, REGISTRY_API,
        timeout=aiohttp.ClientTimeout(total=60),
        rate_limiter=REGISTRY_LIMITER,
    )

    if not data:
        logger.warning("Failed to fetch MCP registry")
        return []

    servers = data if isinstance(data, list) else data.get("servers", [])
    logger.info("Official MCP registry: %d servers", len(servers))

    discoveries = []
    for srv in servers:
        if not isinstance(srv, dict):
            continue

        # Extract URL from various fields
        url = (
            srv.get("url")
            or srv.get("homepage")
            or (srv.get("repository", {}) or {}).get("url", "")
        )
        if not url:
            continue

        name = srv.get("name") or srv.get("title") or ""
        description = srv.get("description") or ""

        discoveries.append(normalize_tool(
            name=name,
            url=url,
            description=description,
            source="mcp_registry_official",
            category="mcp_server",
            extra={
                "registry_data": {
                    k: v for k, v in srv.items()
                    if k in ("name", "description", "version", "vendor", "categories", "tags")
                },
            },
        ))

    return discoveries


async def crawl_github_org_repos(session: aiohttp.ClientSession) -> list[dict]:
    """Fetch all repos from the modelcontextprotocol GitHub org."""
    logger.info("Fetching modelcontextprotocol GitHub org repos...")
    headers = _github_headers()
    discoveries = []
    page = 1

    while True:
        url = f"{GITHUB_API}/orgs/{GITHUB_ORG}/repos?per_page=100&page={page}"
        data = await fetch_json(session, url, headers=headers, rate_limiter=RATE_LIMITER)

        if not data or not isinstance(data, list) or len(data) == 0:
            break

        for repo in data:
            repo_url = repo.get("html_url", "")
            if not repo_url:
                continue

            discoveries.append(normalize_tool(
                name=repo.get("name", ""),
                url=repo_url,
                description=repo.get("description") or "",
                source="mcp_github_org",
                category="mcp_server",
                extra={
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language"),
                    "topics": repo.get("topics", []),
                    "last_updated": repo.get("pushed_at", ""),
                },
            ))

        if len(data) < 100:
            break
        page += 1

    logger.info("GitHub org repos: %d repos found", len(discoveries))
    return discoveries


async def crawl_servers_repo_readme(session: aiohttp.ClientSession) -> list[dict]:
    """Parse the official servers repo README for linked MCP server repos."""
    logger.info("Parsing modelcontextprotocol/servers README...")
    headers = _github_headers()

    url = f"https://raw.githubusercontent.com/{GITHUB_ORG}/servers/main/README.md"
    text = await fetch_text(session, url, headers=headers, rate_limiter=RATE_LIMITER)

    if not text:
        # Try refs/heads/main
        url = f"{GITHUB_API}/repos/{GITHUB_ORG}/servers/readme"
        data = await fetch_json(session, url, headers=headers, rate_limiter=RATE_LIMITER)
        if data and data.get("content"):
            import base64
            text = base64.b64decode(data["content"]).decode("utf-8", errors="replace")

    if not text:
        logger.warning("Could not fetch servers repo README")
        return []

    entries = extract_github_urls_from_markdown(text)
    discoveries = []
    for entry in entries:
        if "github.com" not in entry["url"]:
            continue
        discoveries.append(normalize_tool(
            name=entry["name"],
            url=entry["url"],
            description=entry.get("description", ""),
            source="mcp_servers_readme",
            category="mcp_server",
        ))

    logger.info("Servers README: %d GitHub links found", len(discoveries))
    return discoveries


async def run(dry_run: bool = False) -> dict:
    """Run all Anthropic MCP crawlers."""
    known_urls = load_known_urls()
    all_discoveries = []

    async with aiohttp.ClientSession() as session:
        # Run all sub-crawlers
        registry = await crawl_official_registry(session)
        org_repos = await crawl_github_org_repos(session)
        readme_links = await crawl_servers_repo_readme(session)

    all_discoveries.extend(registry)
    all_discoveries.extend(org_repos)
    all_discoveries.extend(readme_links)

    unique = dedup_discoveries(all_discoveries, known_urls)

    stats = {
        "source": "anthropic_mcp",
        "sub_sources": {
            "official_registry": len(registry),
            "github_org_repos": len(org_repos),
            "servers_readme": len(readme_links),
        },
        "total_found": len(all_discoveries),
        "new_unique": len(unique),
        "duplicates_skipped": len(all_discoveries) - len(unique),
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
    parser = argparse.ArgumentParser(description="Anthropic Official MCP Crawler")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = asyncio.run(run(dry_run=args.dry_run))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
