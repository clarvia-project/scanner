#!/usr/bin/env python3
"""Awesome MCP Lists Crawler — Parse GitHub awesome-list repos for MCP tools.

Crawls these repos:
- wong2/awesome-mcp-servers
- appcypher/awesome-mcp-servers
- modelcontextprotocol/servers
- punkpeye/awesome-mcp-servers
- Any other community awesome lists

Parses README.md files for GitHub links to MCP server repos.

Usage:
    python scripts/automation/crawlers/awesome_lists_crawler.py [--dry-run]
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
    fetch_text,
    fetch_json,
    extract_github_urls_from_markdown,
    GITHUB_TOKEN,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RATE_LIMITER = RateLimiter(delay=1.0 if GITHUB_TOKEN else 6.5, name="github")

# Known awesome MCP lists on GitHub
AWESOME_REPOS = [
    "wong2/awesome-mcp-servers",
    "appcypher/awesome-mcp-servers",
    "punkpeye/awesome-mcp-servers",
    "modelcontextprotocol/servers",
    "cursor-ai/awesome-mcp",
    "anthropics/awesome-mcp-servers",
]


def _github_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": USER_AGENT,
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


async def _fetch_readme(session: aiohttp.ClientSession, repo: str) -> str | None:
    """Fetch README.md from a GitHub repo (try raw then API)."""
    headers = _github_headers()

    # Try raw URL first (no API rate limit hit)
    for branch in ["main", "master"]:
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
        text = await fetch_text(session, url, headers=headers, rate_limiter=RATE_LIMITER)
        if text:
            return text

    # Fall back to API
    url = f"https://api.github.com/repos/{repo}/readme"
    data = await fetch_json(session, url, headers=headers, rate_limiter=RATE_LIMITER)
    if data and data.get("content"):
        import base64
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")

    return None


async def crawl_awesome_lists(session: aiohttp.ClientSession) -> list[dict]:
    """Crawl all awesome MCP list repos for tool links."""
    all_entries = []
    seen_urls = set()

    # Also search for more awesome lists on GitHub
    extra_repos = []
    headers = _github_headers()
    search_url = "https://api.github.com/search/repositories?q=awesome-mcp+in:name&sort=stars&order=desc&per_page=20"
    data = await fetch_json(session, search_url, headers=headers, rate_limiter=RATE_LIMITER)
    if data and isinstance(data.get("items"), list):
        for repo in data["items"]:
            full_name = repo.get("full_name", "")
            if full_name and full_name not in AWESOME_REPOS:
                extra_repos.append(full_name)
        logger.info("Found %d extra awesome-mcp repos via search", len(extra_repos))

    all_repos = AWESOME_REPOS + extra_repos

    for repo in all_repos:
        logger.info("Fetching README from %s...", repo)
        readme = await _fetch_readme(session, repo)

        if not readme:
            logger.warning("Could not fetch README for %s", repo)
            continue

        entries = extract_github_urls_from_markdown(readme)
        new_count = 0

        for entry in entries:
            url = entry["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Filter out non-MCP entries (awesome lists often have general links)
            name_lower = entry["name"].lower()
            url_lower = url.lower()

            # Skip links that are clearly not MCP servers
            skip_patterns = [
                "awesome-mcp", "/issues", "/pulls", "/discussions",
                "github.com/topics", "github.com/search",
            ]
            if any(p in url_lower for p in skip_patterns):
                continue

            all_entries.append({
                "name": entry["name"],
                "url": url,
                "description": entry.get("description", ""),
                "source_repo": repo,
            })
            new_count += 1

        logger.info("  %s: %d new tool links extracted", repo, new_count)

    # Normalize
    discoveries = []
    for entry in all_entries:
        discoveries.append(normalize_tool(
            name=entry["name"],
            url=entry["url"],
            description=entry.get("description", ""),
            source="awesome_mcp_list",
            category="mcp_server",
            extra={
                "source_repo": entry.get("source_repo", ""),
            },
        ))

    logger.info("Awesome lists: total %d unique tool links across %d repos", len(discoveries), len(all_repos))
    return discoveries


async def run(dry_run: bool = False) -> dict:
    known_urls = load_known_urls()

    async with aiohttp.ClientSession() as session:
        discoveries = await crawl_awesome_lists(session)

    unique = dedup_discoveries(discoveries, known_urls)

    stats = {
        "source": "awesome_mcp_lists",
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
    parser = argparse.ArgumentParser(description="Awesome MCP Lists Crawler")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = asyncio.run(run(dry_run=args.dry_run))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
