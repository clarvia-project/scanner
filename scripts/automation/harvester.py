#!/usr/bin/env python3
"""Clarvia Harvester — Auto-Discovery Crawler for AI Agent Tools.

Crawls multiple sources to discover new tools and queue them for scanning:
1. GitHub — repos with AI/MCP/agent-tool topics
2. npm Registry — packages with MCP/agent keywords
3. PyPI — packages matching agent-tool patterns
4. MCP Registries — extends existing catalog_updater sync

Usage:
    python scripts/automation/harvester.py [--source all|github|npm|pypi|mcp] [--dry-run]
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
HARVEST_DIR = DATA_DIR / "harvester"
DISCOVERIES_PATH = HARVEST_DIR / "discoveries.jsonl"
QUEUE_PATH = DATA_DIR / "new-tools-queue.jsonl"
PREBUILT_PATH = DATA_DIR / "prebuilt-scans.json"

# Rate limit settings
GITHUB_DELAY = 6.5  # seconds between requests (10 req/min unauthenticated)
NPM_DELAY = 1.0
PYPI_DELAY = 1.5

# Minimum thresholds
GITHUB_MIN_STARS = 5
GITHUB_MAX_AGE_DAYS = 180


# ---------------------------------------------------------------------------
# Dedup helpers
# ---------------------------------------------------------------------------

def _load_known_urls() -> set[str]:
    """Load all URLs already in the catalog or queue for deduplication."""
    urls: set[str] = set()

    # From prebuilt scans
    if PREBUILT_PATH.exists():
        try:
            with open(PREBUILT_PATH) as f:
                for entry in json.load(f):
                    url = entry.get("url", "").rstrip("/").lower()
                    if url:
                        urls.add(url)
        except Exception as e:
            logger.warning("Failed to load prebuilt scans for dedup: %s", e)

    # From existing queue
    if QUEUE_PATH.exists():
        try:
            with open(QUEUE_PATH) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        url = entry.get("url", "").rstrip("/").lower()
                        if url:
                            urls.add(url)
        except Exception as e:
            logger.warning("Failed to load queue for dedup: %s", e)

    # From previous discoveries
    if DISCOVERIES_PATH.exists():
        try:
            with open(DISCOVERIES_PATH) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        url = entry.get("url", "").rstrip("/").lower()
                        if url:
                            urls.add(url)
        except Exception as e:
            logger.warning("Failed to load discoveries for dedup: %s", e)

    logger.info("Loaded %d known URLs for deduplication", len(urls))
    return urls


def _append_jsonl(path: Path, entries: list[dict]) -> int:
    """Append entries to a JSONL file. Returns count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(path, "a") as f:
        for entry in entries:
            f.write(json.dumps(entry, default=str) + "\n")
            count += 1
    return count


# ---------------------------------------------------------------------------
# GitHub Harvester
# ---------------------------------------------------------------------------

GITHUB_TOPICS = [
    "mcp-server",
    "ai-agent-tool",
    "langchain-tool",
    "crewai-tool",
    "mcp",
    "model-context-protocol",
    "ai-tool",
    "llm-tool",
    "agent-framework",
]

GITHUB_SEARCH_QUERIES = [
    "mcp server in:name,description",
    "ai agent tool in:name,description",
    "langchain tool in:name,description",
    "model context protocol in:name,description",
]


async def harvest_github(session: aiohttp.ClientSession, known_urls: set[str]) -> list[dict]:
    """Search GitHub for repos matching AI/MCP tool topics."""
    discoveries = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=GITHUB_MAX_AGE_DAYS)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    seen_repos: set[str] = set()

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Clarvia-Harvester/1.0",
    }

    # Search by topics
    for topic in GITHUB_TOPICS:
        query = f"topic:{topic} stars:>={GITHUB_MIN_STARS} pushed:>{cutoff_str}"
        encoded = quote_plus(query)
        url = f"https://api.github.com/search/repositories?q={encoded}&sort=stars&order=desc&per_page=30"

        try:
            await asyncio.sleep(GITHUB_DELAY)
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 403:
                    logger.warning("GitHub rate limited on topic %s, stopping", topic)
                    break
                if resp.status != 200:
                    logger.warning("GitHub search for topic %s returned %d", topic, resp.status)
                    continue

                data = await resp.json()
                items = data.get("items", [])
                logger.info("GitHub topic:%s — %d results", topic, len(items))

                for repo in items:
                    repo_url = repo.get("html_url", "").rstrip("/").lower()
                    full_name = repo.get("full_name", "")
                    if not repo_url or repo_url in known_urls or full_name in seen_repos:
                        continue
                    seen_repos.add(full_name)

                    discoveries.append({
                        "source": "github",
                        "url": repo.get("html_url", ""),
                        "name": repo.get("name", ""),
                        "full_name": full_name,
                        "description": repo.get("description") or "",
                        "stars": repo.get("stargazers_count", 0),
                        "last_updated": repo.get("pushed_at", ""),
                        "topics": repo.get("topics", []),
                        "language": repo.get("language"),
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                        "status": "new",
                    })
        except Exception as e:
            logger.error("GitHub topic search error (%s): %s", topic, e)

    # Search by query strings
    for query_str in GITHUB_SEARCH_QUERIES:
        full_query = f"{query_str} stars:>={GITHUB_MIN_STARS} pushed:>{cutoff_str}"
        encoded = quote_plus(full_query)
        url = f"https://api.github.com/search/repositories?q={encoded}&sort=stars&order=desc&per_page=30"

        try:
            await asyncio.sleep(GITHUB_DELAY)
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 403:
                    logger.warning("GitHub rate limited on query, stopping")
                    break
                if resp.status != 200:
                    continue

                data = await resp.json()
                items = data.get("items", [])
                logger.info("GitHub query '%s' — %d results", query_str[:30], len(items))

                for repo in items:
                    repo_url = repo.get("html_url", "").rstrip("/").lower()
                    full_name = repo.get("full_name", "")
                    if not repo_url or repo_url in known_urls or full_name in seen_repos:
                        continue
                    seen_repos.add(full_name)

                    discoveries.append({
                        "source": "github",
                        "url": repo.get("html_url", ""),
                        "name": repo.get("name", ""),
                        "full_name": full_name,
                        "description": repo.get("description") or "",
                        "stars": repo.get("stargazers_count", 0),
                        "last_updated": repo.get("pushed_at", ""),
                        "topics": repo.get("topics", []),
                        "language": repo.get("language"),
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                        "status": "new",
                    })
        except Exception as e:
            logger.error("GitHub query search error: %s", e)

    logger.info("GitHub: discovered %d new repos", len(discoveries))
    return discoveries


# ---------------------------------------------------------------------------
# npm Registry Harvester
# ---------------------------------------------------------------------------

NPM_SEARCH_KEYWORDS = [
    "mcp server",
    "mcp-server",
    "ai-agent",
    "ai agent tool",
    "langchain tool",
    "tool-use",
    "model-context-protocol",
    "llm-tool",
    "agent-toolkit",
    "crewai-tool",
]


async def harvest_npm(session: aiohttp.ClientSession, known_urls: set[str]) -> list[dict]:
    """Search npm registry for AI/MCP tool packages."""
    discoveries = []
    seen_packages: set[str] = set()

    for keyword in NPM_SEARCH_KEYWORDS:
        encoded = quote_plus(keyword)
        url = f"https://registry.npmjs.org/-/v1/search?text={encoded}&size=50"

        try:
            await asyncio.sleep(NPM_DELAY)
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning("npm search for '%s' returned %d", keyword, resp.status)
                    continue

                data = await resp.json()
                objects = data.get("objects", [])
                logger.info("npm keyword '%s' — %d results", keyword, len(objects))

                for obj in objects:
                    pkg = obj.get("package", {})
                    pkg_name = pkg.get("name", "")
                    if not pkg_name or pkg_name in seen_packages:
                        continue
                    seen_packages.add(pkg_name)

                    npm_url = f"https://www.npmjs.com/package/{pkg_name}"
                    homepage = pkg.get("links", {}).get("homepage", "")
                    repo_url = pkg.get("links", {}).get("repository", "")
                    check_url = (homepage or repo_url or npm_url).rstrip("/").lower()

                    if check_url in known_urls:
                        continue

                    # Get download count from search score
                    search_score = obj.get("score", {})
                    detail = search_score.get("detail", {})
                    popularity = detail.get("popularity", 0)

                    discoveries.append({
                        "source": "npm",
                        "url": homepage or repo_url or npm_url,
                        "npm_url": npm_url,
                        "name": pkg_name,
                        "description": pkg.get("description") or "",
                        "version": pkg.get("version", ""),
                        "homepage": homepage,
                        "repository": repo_url,
                        "keywords": pkg.get("keywords", []),
                        "popularity_score": popularity,
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                        "status": "new",
                    })
        except Exception as e:
            logger.error("npm search error (%s): %s", keyword, e)

    logger.info("npm: discovered %d new packages", len(discoveries))
    return discoveries


# ---------------------------------------------------------------------------
# PyPI Harvester
# ---------------------------------------------------------------------------

PYPI_SEARCH_TERMS = [
    "mcp-server",
    "mcp server",
    "agent-tool",
    "langchain-tool",
    "llm-tool",
    "ai-agent",
    "model-context-protocol",
    "crewai-tool",
]


async def harvest_pypi(session: aiohttp.ClientSession, known_urls: set[str]) -> list[dict]:
    """Search PyPI for AI/MCP tool packages using the JSON API.

    PyPI has no official search API, so we use the Simple Index + direct package
    JSON endpoint approach: search via pypi.org/search HTML (limited) or check
    known package name patterns against the JSON API.
    """
    discoveries = []
    seen_packages: set[str] = set()

    # Use PyPI XML-RPC search (deprecated but still functional for basic queries)
    # Alternatively, try direct package lookups for common patterns
    pypi_package_patterns = [
        "mcp-server-{suffix}",
        "mcp-{suffix}",
        "langchain-{suffix}",
        "crewai-{suffix}",
    ]
    suffixes = [
        "github", "slack", "notion", "postgres", "sqlite", "redis",
        "docker", "kubernetes", "aws", "gcp", "azure", "stripe",
        "openai", "anthropic", "google", "filesystem", "git",
        "brave-search", "fetch", "memory", "everything", "puppeteer",
        "time", "weather", "sequential-thinking", "playwright",
        "discord", "telegram", "email", "calendar", "jira",
    ]

    for pattern in pypi_package_patterns:
        for suffix in suffixes:
            pkg_name = pattern.format(suffix=suffix)
            if pkg_name in seen_packages:
                continue
            seen_packages.add(pkg_name)

            url = f"https://pypi.org/pypi/{pkg_name}/json"
            try:
                await asyncio.sleep(PYPI_DELAY)
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 404:
                        continue
                    if resp.status != 200:
                        continue

                    data = await resp.json()
                    info = data.get("info", {})

                    pypi_url = f"https://pypi.org/project/{pkg_name}/"
                    homepage = info.get("home_page") or info.get("project_url") or ""
                    check_url = (homepage or pypi_url).rstrip("/").lower()
                    if check_url in known_urls:
                        continue

                    discoveries.append({
                        "source": "pypi",
                        "url": homepage or pypi_url,
                        "pypi_url": pypi_url,
                        "name": info.get("name", pkg_name),
                        "description": info.get("summary") or "",
                        "version": info.get("version", ""),
                        "homepage": homepage,
                        "author": info.get("author") or "",
                        "license": info.get("license") or "",
                        "keywords": (info.get("keywords") or "").split(",")[:10],
                        "requires_python": info.get("requires_python") or "",
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                        "status": "new",
                    })
            except Exception as e:
                logger.debug("PyPI lookup error (%s): %s", pkg_name, e)

    # Also try direct search terms via PyPI simple API patterns
    for term in PYPI_SEARCH_TERMS:
        pkg_name = term
        if pkg_name in seen_packages:
            continue
        seen_packages.add(pkg_name)

        url = f"https://pypi.org/pypi/{pkg_name}/json"
        try:
            await asyncio.sleep(PYPI_DELAY)
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
                info = data.get("info", {})
                pypi_url = f"https://pypi.org/project/{pkg_name}/"
                homepage = info.get("home_page") or ""
                check_url = (homepage or pypi_url).rstrip("/").lower()
                if check_url in known_urls:
                    continue
                discoveries.append({
                    "source": "pypi",
                    "url": homepage or pypi_url,
                    "pypi_url": pypi_url,
                    "name": info.get("name", pkg_name),
                    "description": info.get("summary") or "",
                    "version": info.get("version", ""),
                    "homepage": homepage,
                    "author": info.get("author") or "",
                    "keywords": (info.get("keywords") or "").split(",")[:10],
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                    "status": "new",
                })
        except Exception as e:
            logger.debug("PyPI direct lookup error (%s): %s", pkg_name, e)

    logger.info("PyPI: discovered %d new packages", len(discoveries))
    return discoveries


# ---------------------------------------------------------------------------
# MCP Registry Harvester (extends catalog_updater)
# ---------------------------------------------------------------------------

MCP_REGISTRY_API = "https://registry.modelcontextprotocol.io/v0/servers"


async def harvest_mcp_registry(session: aiohttp.ClientSession, known_urls: set[str]) -> list[dict]:
    """Fetch MCP Registry and find new entries not yet in catalog."""
    discoveries = []

    try:
        async with session.get(
            MCP_REGISTRY_API,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                logger.warning("MCP Registry returned %d", resp.status)
                return discoveries

            data = await resp.json()
            servers = data if isinstance(data, list) else data.get("servers", [])
            logger.info("MCP Registry: %d total servers", len(servers))

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

                if url.rstrip("/").lower() in known_urls:
                    continue

                name = srv.get("name") or srv.get("title") or ""
                discoveries.append({
                    "source": "mcp_registry",
                    "url": url,
                    "name": name,
                    "description": srv.get("description") or "",
                    "server_data": srv,
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                    "status": "new",
                })

    except Exception as e:
        logger.error("MCP Registry harvest error: %s", e)

    logger.info("MCP Registry: discovered %d new servers", len(discoveries))
    return discoveries


# ---------------------------------------------------------------------------
# Queue builder
# ---------------------------------------------------------------------------

def queue_discoveries(discoveries: list[dict]) -> int:
    """Add new discoveries to the scan queue and log to discoveries file."""
    if not discoveries:
        return 0

    # Log all discoveries
    _append_jsonl(DISCOVERIES_PATH, discoveries)

    # Build queue entries (only URL + metadata needed for scanning)
    queue_entries = []
    for d in discoveries:
        queue_entries.append({
            "url": d["url"],
            "name": d.get("name", ""),
            "source": d["source"],
            "discovered_at": d["discovered_at"],
            "status": "queued",
        })

    written = _append_jsonl(QUEUE_PATH, queue_entries)
    logger.info("Queued %d new tools for scanning", written)
    return written


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def run_harvest(sources: list[str] | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Run the full harvest pipeline."""
    if sources is None:
        sources = ["github", "npm", "pypi", "mcp"]

    known_urls = _load_known_urls()
    all_discoveries: list[dict] = []
    stats: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
    }

    async with aiohttp.ClientSession() as session:
        if "github" in sources:
            gh = await harvest_github(session, known_urls)
            all_discoveries.extend(gh)
            # Add to known_urls to avoid cross-source duplicates
            for d in gh:
                known_urls.add(d["url"].rstrip("/").lower())
            stats["sources"]["github"] = len(gh)

        if "npm" in sources:
            npm = await harvest_npm(session, known_urls)
            all_discoveries.extend(npm)
            for d in npm:
                known_urls.add(d["url"].rstrip("/").lower())
            stats["sources"]["npm"] = len(npm)

        if "pypi" in sources:
            pypi = await harvest_pypi(session, known_urls)
            all_discoveries.extend(pypi)
            for d in pypi:
                known_urls.add(d["url"].rstrip("/").lower())
            stats["sources"]["pypi"] = len(pypi)

        if "mcp" in sources:
            mcp = await harvest_mcp_registry(session, known_urls)
            all_discoveries.extend(mcp)
            stats["sources"]["mcp_registry"] = len(mcp)

    stats["total_discovered"] = len(all_discoveries)

    if dry_run:
        stats["dry_run"] = True
        stats["queued"] = 0
        logger.info("DRY RUN — would queue %d tools", len(all_discoveries))
        # Print sample
        for d in all_discoveries[:10]:
            logger.info("  [%s] %s — %s", d["source"], d.get("name", "?"), d["url"])
        if len(all_discoveries) > 10:
            logger.info("  ... and %d more", len(all_discoveries) - 10)
    else:
        queued = queue_discoveries(all_discoveries)
        stats["queued"] = queued

    stats["finished_at"] = datetime.now(timezone.utc).isoformat()

    # Save run summary
    summary_path = HARVEST_DIR / "last-run-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(stats, f, indent=2, default=str)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Clarvia Harvester — Auto-Discovery Crawler")
    parser.add_argument(
        "--source",
        choices=["all", "github", "npm", "pypi", "mcp"],
        default="all",
        help="Which sources to crawl (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover but do not queue for scanning",
    )
    args = parser.parse_args()

    sources = None if args.source == "all" else [args.source]
    result = asyncio.run(run_harvest(sources=sources, dry_run=args.dry_run))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
