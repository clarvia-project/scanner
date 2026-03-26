#!/usr/bin/env python3
"""Comprehensive PyPI MCP Package Crawler.

Enhances the base harvester PyPI search with:
- More package name patterns and combinations
- PyPI Simple Index scanning for package discovery
- BigQuery public dataset queries (optional)
- Classifier-based search

Usage:
    python scripts/automation/crawlers/pypi_comprehensive_crawler.py [--dry-run]
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import datetime, timezone, timedelta
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

RATE_LIMITER = RateLimiter(delay=1.0, name="pypi")

# Package name patterns to check against PyPI JSON API
PACKAGE_PATTERNS = [
    "mcp-server-{suffix}",
    "mcp-{suffix}",
    "{suffix}-mcp-server",
    "{suffix}-mcp",
    "langchain-{suffix}",
    "crewai-{suffix}",
    "crewai-tools-{suffix}",
]

# Suffixes to combine with patterns
SUFFIXES = [
    # Databases
    "postgres", "postgresql", "mysql", "sqlite", "redis", "mongodb", "dynamodb",
    "supabase", "firebase", "neo4j", "elasticsearch", "clickhouse", "bigquery",
    "snowflake", "cassandra", "airtable", "notion-db", "pinecone", "qdrant",
    "weaviate", "chromadb", "milvus",
    # Cloud & infra
    "aws", "gcp", "azure", "docker", "kubernetes", "k8s", "terraform",
    "cloudflare", "vercel", "netlify", "heroku", "digitalocean", "linode",
    # Dev tools
    "github", "gitlab", "bitbucket", "jira", "linear", "sentry", "datadog",
    "grafana", "prometheus", "jenkins", "circleci", "travisci",
    # Communication
    "slack", "discord", "telegram", "email", "gmail", "outlook", "twilio",
    "teams", "zoom", "whatsapp", "matrix",
    # AI/ML
    "openai", "anthropic", "google", "gemini", "ollama", "huggingface",
    "langchain", "llamaindex", "cohere", "mistral", "groq",
    # File & Storage
    "filesystem", "s3", "gcs", "dropbox", "gdrive", "google-drive", "onedrive",
    "box", "ftp", "sftp",
    # Web & APIs
    "fetch", "brave-search", "serpapi", "web", "http", "rest", "graphql",
    "websocket", "grpc", "puppeteer", "playwright", "selenium",
    # Others
    "git", "memory", "everything", "time", "weather", "calendar",
    "sequential-thinking", "obsidian", "stripe", "shopify", "salesforce",
    "hubspot", "zendesk", "intercom", "twilio", "sendgrid", "mailgun",
]

# Direct package names to check
DIRECT_PACKAGES = [
    "mcp",
    "mcp-server",
    "mcp-tool",
    "mcp-sdk",
    "mcp-python",
    "model-context-protocol",
    "fastmcp",
    "pymcp",
    "mcp-framework",
    "mcp-agent",
    "mcp-client",
    "mcp-proxy",
    "mcp-cli",
    "mcp-hub",
    "anthropic-mcp",
]


async def _check_pypi_package(
    session: aiohttp.ClientSession,
    pkg_name: str,
) -> dict | None:
    """Fetch and validate a single PyPI package."""
    url = f"https://pypi.org/pypi/{pkg_name}/json"
    data = await fetch_json(session, url, rate_limiter=RATE_LIMITER)

    if not data:
        return None

    info = data.get("info", {})
    description = info.get("summary") or ""
    if not description:
        return None

    # Get homepage
    homepage = info.get("home_page") or ""
    project_urls = info.get("project_urls") or {}
    if not homepage:
        homepage = project_urls.get("Homepage") or project_urls.get("homepage") or ""
    repo_url = (
        project_urls.get("Repository")
        or project_urls.get("repository")
        or project_urls.get("Source")
        or project_urls.get("source")
        or project_urls.get("GitHub")
        or ""
    )

    url = repo_url or homepage or f"https://pypi.org/project/{pkg_name}/"

    # Get last release date
    last_updated = ""
    latest_files = data.get("urls", [])
    if latest_files:
        last_updated = latest_files[0].get("upload_time_iso_8601", "")

    return {
        "name": info.get("name", pkg_name),
        "url": url,
        "pypi_url": f"https://pypi.org/project/{pkg_name}/",
        "description": description,
        "version": info.get("version", ""),
        "homepage": homepage,
        "repository": repo_url,
        "author": info.get("author") or "",
        "license": info.get("license") or "",
        "keywords": (info.get("keywords") or "").split(",")[:10],
        "requires_python": info.get("requires_python") or "",
        "last_updated": last_updated,
        "classifiers": info.get("classifiers", []),
    }


async def _search_pypi_html(
    session: aiohttp.ClientSession,
    query: str,
) -> list[str]:
    """Search PyPI via HTML search page (fallback since PyPI has no search API)."""
    url = f"https://pypi.org/search/?q={query}&o=-created"
    html = await fetch_text(session, url, rate_limiter=RATE_LIMITER)
    if not html:
        return []

    # Extract package names from search results
    pattern = re.compile(r'<a class="package-snippet"[^>]*href="/project/([^/]+)/"')
    names = pattern.findall(html)

    # Also check subsequent pages (up to 3)
    for page in range(2, 4):
        page_url = f"{url}&page={page}"
        html = await fetch_text(session, page_url, rate_limiter=RATE_LIMITER)
        if not html:
            break
        more_names = pattern.findall(html)
        if not more_names:
            break
        names.extend(more_names)

    return names


async def crawl_pypi_comprehensive(session: aiohttp.ClientSession) -> list[dict]:
    """Comprehensive PyPI MCP package crawl."""
    all_packages = {}  # name -> package data
    checked = set()

    # Strategy 1: Check known patterns
    logger.info("PyPI: checking known package patterns...")
    for pattern in PACKAGE_PATTERNS:
        for suffix in SUFFIXES:
            pkg_name = pattern.format(suffix=suffix)
            if pkg_name in checked:
                continue
            checked.add(pkg_name)

            result = await _check_pypi_package(session, pkg_name)
            if result:
                all_packages[result["name"]] = result

    logger.info("Pattern check: %d packages found (checked %d)", len(all_packages), len(checked))

    # Strategy 2: Check direct package names
    for pkg_name in DIRECT_PACKAGES:
        if pkg_name in checked:
            continue
        checked.add(pkg_name)

        result = await _check_pypi_package(session, pkg_name)
        if result:
            all_packages[result["name"]] = result

    # Strategy 3: Search PyPI HTML
    search_terms = [
        "mcp server", "mcp-server", "model context protocol",
        "mcp tool", "mcp agent", "fastmcp",
    ]
    for term in search_terms:
        logger.info("PyPI HTML search: '%s'", term)
        names = await _search_pypi_html(session, term)
        for name in names:
            if name in checked:
                continue
            checked.add(name)
            result = await _check_pypi_package(session, name)
            if result:
                all_packages[result["name"]] = result
        logger.info("  '%s': found %d package names", term, len(names))

    # Normalize
    discoveries = []
    for name, pkg in all_packages.items():
        discoveries.append(normalize_tool(
            name=name,
            url=pkg["url"],
            description=pkg["description"],
            source="pypi",
            category="mcp_server",
            extra={
                "pypi_url": pkg.get("pypi_url", ""),
                "version": pkg.get("version", ""),
                "homepage": pkg.get("homepage", ""),
                "repository": pkg.get("repository", ""),
                "author": pkg.get("author", ""),
                "last_updated": pkg.get("last_updated", ""),
            },
        ))

    logger.info("PyPI comprehensive: %d packages found", len(discoveries))
    return discoveries


async def run(dry_run: bool = False) -> dict:
    known_urls = load_known_urls()

    async with aiohttp.ClientSession() as session:
        discoveries = await crawl_pypi_comprehensive(session)

    unique = dedup_discoveries(discoveries, known_urls)

    stats = {
        "source": "pypi_comprehensive",
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
    parser = argparse.ArgumentParser(description="Comprehensive PyPI MCP Crawler")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = asyncio.run(run(dry_run=args.dry_run))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
