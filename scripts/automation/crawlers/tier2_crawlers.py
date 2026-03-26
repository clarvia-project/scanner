#!/usr/bin/env python3
"""Tier 2 Crawlers — LangChain Hub, HuggingFace Spaces, Composio.

These are supplementary sources for hot/trending tools:
- LangChain: tools from langchain-ai GitHub repos
- HuggingFace Spaces: trending/popular spaces only (not all 150k+)
- Composio: top action integrations

Usage:
    python scripts/automation/crawlers/tier2_crawlers.py [--dry-run] [--source all|langchain|huggingface|composio]
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


# ---------------------------------------------------------------------------
# LangChain Hub / GitHub tools
# ---------------------------------------------------------------------------

LANGCHAIN_RATE = RateLimiter(delay=1.0 if GITHUB_TOKEN else 6.5, name="langchain_gh")


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": USER_AGENT}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


async def crawl_langchain(session: aiohttp.ClientSession) -> list[dict]:
    """Discover LangChain tools from GitHub repos and community packages."""
    discoveries = []
    headers = _github_headers()

    # 1. Scan langchain-ai org repos for tool-related packages
    langchain_repos = [
        "langchain-ai/langchain",
        "langchain-ai/langchain-tools",
        "langchain-ai/langchain-community",
    ]

    for repo in langchain_repos:
        logger.info("Checking LangChain repo: %s", repo)

        # Get repo contents to find tool directories
        url = f"https://api.github.com/repos/{repo}/contents"
        data = await fetch_json(session, url, headers=headers, rate_limiter=LANGCHAIN_RATE)
        if not data or not isinstance(data, list):
            continue

        # Look for tool-related directories
        for item in data:
            name = item.get("name", "").lower()
            if "tool" in name or name == "libs":
                discoveries.append(normalize_tool(
                    name=f"langchain-{item.get('name', '')}",
                    url=f"https://github.com/{repo}/tree/main/{item.get('name', '')}",
                    description=f"LangChain tool package from {repo}",
                    source="langchain",
                    category="agent_tool",
                ))

    # 2. Search for langchain-tool packages on GitHub
    search_queries = [
        "langchain tool in:name stars:>5",
        "langchain-community in:name stars:>10",
        "langchain integration in:name stars:>10",
    ]

    for query in search_queries:
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page=30"
        data = await fetch_json(session, url, headers=headers, rate_limiter=LANGCHAIN_RATE)
        if data and isinstance(data.get("items"), list):
            for repo in data["items"]:
                discoveries.append(normalize_tool(
                    name=repo.get("name", ""),
                    url=repo.get("html_url", ""),
                    description=repo.get("description") or "",
                    source="langchain",
                    category="agent_tool",
                    extra={
                        "stars": repo.get("stargazers_count", 0),
                        "language": repo.get("language"),
                    },
                ))

    logger.info("LangChain: %d tools discovered", len(discoveries))
    return discoveries


# ---------------------------------------------------------------------------
# HuggingFace Spaces (trending only)
# ---------------------------------------------------------------------------

HF_RATE = RateLimiter(delay=1.0, name="huggingface")
HF_API = "https://huggingface.co/api/spaces"


async def crawl_huggingface(session: aiohttp.ClientSession) -> list[dict]:
    """Discover trending/popular HuggingFace Spaces (tools & agents only)."""
    discoveries = []

    # Only grab trending and recently popular spaces
    # Filter for tool-related spaces
    queries = [
        {"sort": "trending", "limit": 100},
        {"sort": "likes", "limit": 100},
        {"search": "mcp tool", "limit": 50},
        {"search": "agent tool", "limit": 50},
        {"search": "mcp server", "limit": 50},
    ]

    seen = set()
    for params in queries:
        query_parts = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{HF_API}?{query_parts}"
        logger.info("HuggingFace query: %s", query_parts)

        data = await fetch_json(session, url, rate_limiter=HF_RATE)
        if not data or not isinstance(data, list):
            continue

        for space in data:
            space_id = space.get("id", "")
            if not space_id or space_id in seen:
                continue
            seen.add(space_id)

            # Filter: only include spaces that look like tools/agents
            tags = space.get("tags", [])
            card_data = space.get("cardData", {})
            title = card_data.get("title", "") or space_id.split("/")[-1]

            # Check if tool/agent related
            is_tool = any(
                t in (tags + [title.lower()])
                for t in ["tool", "agent", "mcp", "api", "function-calling"]
            )

            # For trending, include all (they're popular for a reason)
            if not is_tool and "trending" not in str(params.get("sort", "")):
                continue

            space_url = f"https://huggingface.co/spaces/{space_id}"
            discoveries.append(normalize_tool(
                name=title or space_id,
                url=space_url,
                description=card_data.get("short_description", "") or space.get("description", ""),
                source="huggingface",
                category="ai_tool",
                extra={
                    "likes": space.get("likes", 0),
                    "tags": tags,
                    "sdk": space.get("sdk", ""),
                },
            ))

    logger.info("HuggingFace: %d spaces discovered", len(discoveries))
    return discoveries


# ---------------------------------------------------------------------------
# Composio (top actions/integrations)
# ---------------------------------------------------------------------------

COMPOSIO_RATE = RateLimiter(delay=1.5, name="composio")
COMPOSIO_BASE = "https://composio.dev"


async def crawl_composio(session: aiohttp.ClientSession) -> list[dict]:
    """Discover Composio integrations/actions."""
    discoveries = []

    # Try API endpoints
    api_paths = [
        "/api/v1/apps",
        "/api/v1/tools",
        "/api/v2/toolkits",
        "/api/apps",
    ]

    for api_path in api_paths:
        url = f"{COMPOSIO_BASE}{api_path}"
        data = await fetch_json(session, url, rate_limiter=COMPOSIO_RATE)
        if data:
            items = data if isinstance(data, list) else data.get("items", data.get("apps", data.get("tools", [])))
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("title") or item.get("appName") or ""
                        slug = item.get("slug") or item.get("key") or ""
                        desc = item.get("description") or ""
                        if name:
                            discoveries.append(normalize_tool(
                                name=name,
                                url=f"{COMPOSIO_BASE}/apps/{slug}" if slug else COMPOSIO_BASE,
                                description=desc,
                                source="composio",
                                category="integration",
                            ))
                logger.info("Composio API %s: %d items", api_path, len(items))
                if discoveries:
                    break  # Found a working API

    # Fallback: scrape the tools page
    if not discoveries:
        logger.info("Composio: trying HTML scrape...")
        html = await fetch_text(session, f"{COMPOSIO_BASE}/tools", rate_limiter=COMPOSIO_RATE)
        if html:
            # Try Next.js data
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    props = data.get("props", {}).get("pageProps", {})
                    for key in ("tools", "apps", "toolkits", "items"):
                        items = props.get(key, [])
                        if isinstance(items, list):
                            for item in items:
                                if isinstance(item, dict):
                                    name = item.get("name") or item.get("appName") or ""
                                    slug = item.get("slug") or item.get("key") or ""
                                    if name:
                                        discoveries.append(normalize_tool(
                                            name=name,
                                            url=f"{COMPOSIO_BASE}/apps/{slug}" if slug else COMPOSIO_BASE,
                                            description=item.get("description", ""),
                                            source="composio",
                                            category="integration",
                                        ))
                except json.JSONDecodeError:
                    pass

            # Also extract from href patterns
            pattern = re.compile(r'href="/apps/([a-zA-Z0-9_-]+)"[^>]*>([^<]*)</a>', re.I)
            for match in pattern.finditer(html):
                slug = match.group(1)
                name = match.group(2).strip() or slug.replace("-", " ").title()
                discoveries.append(normalize_tool(
                    name=name,
                    url=f"{COMPOSIO_BASE}/apps/{slug}",
                    description="",
                    source="composio",
                    category="integration",
                ))

    logger.info("Composio: %d integrations discovered", len(discoveries))
    return discoveries


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def run(sources: list[str] | None = None, dry_run: bool = False) -> dict:
    """Run Tier 2 crawlers."""
    if sources is None:
        sources = ["langchain", "huggingface", "composio"]

    known_urls = load_known_urls()
    all_discoveries = []
    stats = {"sources": {}}

    source_fns = {
        "langchain": crawl_langchain,
        "huggingface": crawl_huggingface,
        "composio": crawl_composio,
    }

    async with aiohttp.ClientSession() as session:
        for source in sources:
            if source not in source_fns:
                continue
            try:
                results = await source_fns[source](session)
                all_discoveries.extend(results)
                stats["sources"][source] = len(results)
            except Exception as e:
                logger.error("Tier 2 %s failed: %s", source, e)
                stats["sources"][source] = f"error: {e}"

    unique = dedup_discoveries(all_discoveries, known_urls)

    stats.update({
        "total_found": len(all_discoveries),
        "new_unique": len(unique),
        "duplicates_skipped": len(all_discoveries) - len(unique),
    })

    if not dry_run:
        saved = save_discoveries(unique)
        stats["queued"] = saved
    else:
        stats["dry_run"] = True
        for d in unique[:5]:
            logger.info("  [NEW] %s [%s] — %s", d["name"], d["source"], d["url"])
        if len(unique) > 5:
            logger.info("  ... and %d more", len(unique) - 5)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Tier 2 Crawlers (LangChain, HuggingFace, Composio)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--source",
        choices=["all", "langchain", "huggingface", "composio"],
        default="all",
    )
    args = parser.parse_args()

    sources = None if args.source == "all" else [args.source]
    result = asyncio.run(run(sources=sources, dry_run=args.dry_run))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
