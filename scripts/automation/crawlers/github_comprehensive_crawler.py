#!/usr/bin/env python3
"""GitHub Comprehensive MCP/Skills Discovery Crawler — MEGA crawler.

Combines multiple GitHub discovery strategies to maximize coverage:

1. Topic-based discovery: repos tagged with MCP/agent/tool topics
2. Dependency graph: repos that import key MCP SDKs (npm + PyPI)
3. File-based discovery: repos containing MCP config files
4. Awesome list parsing: extract tool links from curated lists
5. Stats enrichment: stars, forks, last commit, language, license

This is the primary scaling crawler for pushing Clarvia's catalog from 15K to 50K+ tools.

GitHub Search API limits:
- Max 1000 results per search query
- Max 30 requests/min unauthenticated, 30/min search API (authenticated)
- Rate limit header: X-RateLimit-Remaining

Usage:
    python scripts/automation/crawlers/github_comprehensive_crawler.py [--dry-run]
    python scripts/automation/crawlers/github_comprehensive_crawler.py --dry-run --strategy topics
"""

import argparse
import asyncio
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

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

# 1.5s between GitHub API calls (conservative to stay within rate limits)
RATE_LIMITER = RateLimiter(delay=1.5 if GITHUB_TOKEN else 8.0, name="github")

# --- Strategy 1: Topic-based discovery ---
TOPIC_QUERIES = [
    # MCP-specific topics
    "topic:mcp-server",
    "topic:mcp",
    "topic:model-context-protocol",
    "topic:mcp-tools",
    "topic:mcp-plugin",
    "topic:mcp-integration",
    # Skills topics
    "topic:agent-skills",
    "topic:claude-skills",
    "topic:codex-skills",
    # Broader AI agent/tool topics (with qualifier to avoid noise)
    "topic:ai-agent mcp",
    "topic:ai-tools mcp",
    "topic:llm-tools mcp",
    "topic:ai-agent-tool",
]

# --- Strategy 2: Dependency graph (code search) ---
DEPENDENCY_QUERIES = [
    # npm: repos using MCP SDK
    '"@modelcontextprotocol/sdk" filename:package.json',
    '"@modelcontextprotocol/server" filename:package.json',
    '"@anthropic-ai/sdk" "mcp" filename:package.json',
    # PyPI: repos using MCP package
    '"mcp" filename:requirements.txt',
    '"mcp-server" filename:requirements.txt',
    '"modelcontextprotocol" filename:setup.py',
    '"modelcontextprotocol" filename:pyproject.toml',
    # Go: repos using MCP SDK
    '"github.com/mark3labs/mcp-go" filename:go.mod',
    # Rust: repos using MCP crate
    '"mcp-server" filename:Cargo.toml',
]

# --- Strategy 3: File-based discovery ---
FILE_QUERIES = [
    # MCP config files
    "filename:mcp.json",
    'filename:server.json path:".mcp"',
    # README mentions
    '"modelcontextprotocol" filename:README.md',
    '"MCP server" filename:README.md stars:>2',
    # SKILL.md files (Claude/Codex skills)
    "filename:SKILL.md",
]

# --- Strategy 4: Awesome lists ---
AWESOME_REPOS = [
    "wong2/awesome-mcp-servers",
    "punkpeye/awesome-mcp-servers",
    "appcypher/awesome-mcp-servers",
]

# Max pages per search query (GitHub caps at 1000 results = 10 pages of 100)
MAX_PAGES_PER_QUERY = 10
RESULTS_PER_PAGE = 100


def _github_headers() -> dict:
    """Build GitHub API request headers."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": USER_AGENT,
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


async def _check_rate_limit(session: aiohttp.ClientSession) -> dict | None:
    """Check GitHub API rate limit status."""
    headers = _github_headers()
    data = await fetch_json(
        session,
        "https://api.github.com/rate_limit",
        headers=headers,
        rate_limiter=RATE_LIMITER,
    )
    if data:
        search_limit = data.get("resources", {}).get("search", {})
        core_limit = data.get("resources", {}).get("core", {})
        logger.info(
            "GitHub rate limit — search: %d/%d remaining, core: %d/%d remaining",
            search_limit.get("remaining", 0),
            search_limit.get("limit", 0),
            core_limit.get("remaining", 0),
            core_limit.get("limit", 0),
        )
        return data
    return None


async def _handle_rate_limit(response_headers: dict) -> None:
    """Sleep until rate limit resets if we're close to the limit."""
    remaining = int(response_headers.get("X-RateLimit-Remaining", "999"))
    if remaining <= 2:
        reset_at = int(response_headers.get("X-RateLimit-Reset", "0"))
        now = int(time.time())
        sleep_for = max(reset_at - now + 2, 10)
        logger.warning(
            "Rate limit nearly exhausted (%d remaining). Sleeping %ds until reset.",
            remaining, sleep_for,
        )
        await asyncio.sleep(sleep_for)


async def _github_search_repos(
    session: aiohttp.ClientSession,
    query: str,
    *,
    sort: str = "stars",
    order: str = "desc",
    max_pages: int = MAX_PAGES_PER_QUERY,
) -> list[dict]:
    """Search GitHub repos with full pagination. Returns raw repo dicts."""
    headers = _github_headers()
    all_repos = []

    for page in range(1, max_pages + 1):
        url = (
            f"https://api.github.com/search/repositories"
            f"?q={quote_plus(query)}"
            f"&sort={sort}&order={order}"
            f"&per_page={RESULTS_PER_PAGE}&page={page}"
        )

        await RATE_LIMITER.wait()

        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 403:
                    # Rate limited — wait and retry once
                    await _handle_rate_limit(dict(resp.headers))
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as retry_resp:
                        if retry_resp.status != 200:
                            logger.warning("Search retry failed: %d for query '%s'", retry_resp.status, query)
                            break
                        data = await retry_resp.json(content_type=None)
                elif resp.status == 422:
                    # Validation error (e.g., bad query syntax)
                    logger.warning("Search query invalid (422): '%s'", query)
                    break
                elif resp.status != 200:
                    logger.warning("Search returned %d for query '%s' page %d", resp.status, query, page)
                    break
                else:
                    data = await resp.json(content_type=None)

                    # Check rate limit headers proactively
                    remaining = int(resp.headers.get("X-RateLimit-Remaining", "999"))
                    if remaining <= 5:
                        await _handle_rate_limit(dict(resp.headers))

        except Exception as e:
            logger.error("Search request failed for '%s' page %d: %s", query, page, e)
            break

        items = data.get("items", [])
        if not items:
            break

        all_repos.extend(items)
        total_count = data.get("total_count", 0)

        # Stop if we've got all results or hit the 1000 cap
        if len(all_repos) >= total_count or len(all_repos) >= 1000:
            break

        if len(items) < RESULTS_PER_PAGE:
            break

    return all_repos


async def _github_search_code(
    session: aiohttp.ClientSession,
    query: str,
    *,
    max_pages: int = 5,
) -> list[str]:
    """Search GitHub code and return unique repo full_names."""
    headers = _github_headers()
    repo_names = set()

    for page in range(1, max_pages + 1):
        url = (
            f"https://api.github.com/search/code"
            f"?q={quote_plus(query)}"
            f"&per_page={RESULTS_PER_PAGE}&page={page}"
        )

        await RATE_LIMITER.wait()

        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 403:
                    await _handle_rate_limit(dict(resp.headers))
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as retry_resp:
                        if retry_resp.status != 200:
                            logger.warning("Code search retry failed: %d", retry_resp.status)
                            break
                        data = await retry_resp.json(content_type=None)
                elif resp.status != 200:
                    logger.warning("Code search returned %d for '%s' page %d", resp.status, query, page)
                    break
                else:
                    data = await resp.json(content_type=None)

                    remaining = int(resp.headers.get("X-RateLimit-Remaining", "999"))
                    if remaining <= 5:
                        await _handle_rate_limit(dict(resp.headers))

        except Exception as e:
            logger.error("Code search failed for '%s' page %d: %s", query, page, e)
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            repo = item.get("repository", {})
            full_name = repo.get("full_name", "")
            if full_name:
                repo_names.add(full_name)

        total_count = data.get("total_count", 0)
        fetched_so_far = page * RESULTS_PER_PAGE
        if fetched_so_far >= total_count or fetched_so_far >= 1000:
            break
        if len(items) < RESULTS_PER_PAGE:
            break

    return list(repo_names)


async def _fetch_repo_details(
    session: aiohttp.ClientSession,
    full_name: str,
) -> dict | None:
    """Fetch enriched details for a single repo."""
    headers = _github_headers()
    url = f"https://api.github.com/repos/{full_name}"
    return await fetch_json(session, url, headers=headers, rate_limiter=RATE_LIMITER)


def _repo_to_entry(repo: dict) -> dict:
    """Convert a GitHub API repo object to a normalized entry dict."""
    full_name = repo.get("full_name", "")
    return {
        "name": repo.get("name", full_name.split("/")[-1] if "/" in full_name else full_name),
        "url": repo.get("html_url", f"https://github.com/{full_name}"),
        "description": repo.get("description") or "",
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "last_commit_date": repo.get("pushed_at", ""),
        "topics": repo.get("topics", []),
        "license": (repo.get("license") or {}).get("spdx_id", ""),
        "primary_language": repo.get("language") or "",
        "full_name": full_name,
        "archived": repo.get("archived", False),
        "fork": repo.get("fork", False),
        "created_at": repo.get("created_at", ""),
        "open_issues": repo.get("open_issues_count", 0),
    }


# =============================================================================
# Strategy implementations
# =============================================================================


async def strategy_topics(session: aiohttp.ClientSession) -> list[dict]:
    """Strategy 1: Discover repos by GitHub topics."""
    logger.info("=" * 50)
    logger.info("STRATEGY 1: Topic-based discovery (%d queries)", len(TOPIC_QUERIES))
    logger.info("=" * 50)

    all_repos = {}  # full_name -> repo entry

    for query in TOPIC_QUERIES:
        logger.info("  Topic search: '%s'", query)
        repos = await _github_search_repos(session, query)
        new_count = 0
        for repo in repos:
            fn = repo.get("full_name", "")
            if fn and fn not in all_repos:
                entry = _repo_to_entry(repo)
                # Skip archived and fork repos
                if entry["archived"] or entry["fork"]:
                    continue
                all_repos[fn] = entry
                new_count += 1
        logger.info("    -> %d results, %d new unique (total: %d)", len(repos), new_count, len(all_repos))

    logger.info("Strategy 1 total: %d unique repos from topics", len(all_repos))
    return list(all_repos.values())


async def strategy_dependencies(session: aiohttp.ClientSession) -> list[dict]:
    """Strategy 2: Discover repos via dependency/code search."""
    logger.info("=" * 50)
    logger.info("STRATEGY 2: Dependency graph (%d queries)", len(DEPENDENCY_QUERIES))
    logger.info("=" * 50)

    all_repo_names = set()

    for query in DEPENDENCY_QUERIES:
        logger.info("  Dependency search: '%s'", query)
        repo_names = await _github_search_code(session, query)
        before = len(all_repo_names)
        all_repo_names.update(repo_names)
        logger.info(
            "    -> %d repos found, %d new (total: %d)",
            len(repo_names), len(all_repo_names) - before, len(all_repo_names),
        )

    logger.info("Fetching details for %d repos from dependency graph...", len(all_repo_names))

    # Fetch full details for repos we don't have yet
    results = []
    batch_count = 0
    for full_name in all_repo_names:
        repo_data = await _fetch_repo_details(session, full_name)
        if repo_data:
            entry = _repo_to_entry(repo_data)
            if not entry["archived"] and not entry["fork"]:
                results.append(entry)
        batch_count += 1
        if batch_count % 50 == 0:
            logger.info("  Enriched %d/%d repos...", batch_count, len(all_repo_names))

    logger.info("Strategy 2 total: %d repos from dependency graph", len(results))
    return results


async def strategy_files(session: aiohttp.ClientSession) -> list[dict]:
    """Strategy 3: Discover repos via file-based code search."""
    logger.info("=" * 50)
    logger.info("STRATEGY 3: File-based discovery (%d queries)", len(FILE_QUERIES))
    logger.info("=" * 50)

    all_repo_names = set()

    for query in FILE_QUERIES:
        logger.info("  File search: '%s'", query)
        repo_names = await _github_search_code(session, query)
        before = len(all_repo_names)
        all_repo_names.update(repo_names)
        logger.info(
            "    -> %d repos, %d new (total: %d)",
            len(repo_names), len(all_repo_names) - before, len(all_repo_names),
        )

    logger.info("Fetching details for %d repos from file search...", len(all_repo_names))

    results = []
    batch_count = 0
    for full_name in all_repo_names:
        repo_data = await _fetch_repo_details(session, full_name)
        if repo_data:
            entry = _repo_to_entry(repo_data)
            if not entry["archived"] and not entry["fork"]:
                results.append(entry)
        batch_count += 1
        if batch_count % 50 == 0:
            logger.info("  Enriched %d/%d repos...", batch_count, len(all_repo_names))

    logger.info("Strategy 3 total: %d repos from file search", len(results))
    return results


async def strategy_awesome_lists(session: aiohttp.ClientSession) -> list[dict]:
    """Strategy 4: Parse awesome lists for tool links."""
    logger.info("=" * 50)
    logger.info("STRATEGY 4: Awesome list parsing (%d lists)", len(AWESOME_REPOS))
    logger.info("=" * 50)

    headers = _github_headers()
    all_entries = {}  # url -> entry

    for repo_name in AWESOME_REPOS:
        logger.info("  Parsing: %s", repo_name)

        readme = None
        for branch in ["main", "master"]:
            url = f"https://raw.githubusercontent.com/{repo_name}/{branch}/README.md"
            readme = await fetch_text(session, url, headers=headers, rate_limiter=RATE_LIMITER)
            if readme:
                break

        if not readme:
            logger.warning("  Could not fetch README for %s", repo_name)
            continue

        links = extract_github_urls_from_markdown(readme)

        new_count = 0
        for link in links:
            link_url = link["url"].rstrip("/").lower()
            if link_url in all_entries:
                continue

            # Skip non-repo links
            skip_patterns = [
                "awesome-mcp", "/issues", "/pulls", "/discussions",
                "github.com/topics", "github.com/search",
            ]
            if any(p in link_url for p in skip_patterns):
                continue

            all_entries[link_url] = {
                "name": link["name"],
                "url": link["url"],
                "description": link.get("description", ""),
                "source_list": repo_name,
            }
            new_count += 1

        logger.info("    -> %d links extracted, %d new unique", len(links), new_count)

    # Enrich with repo details (batch — only repos we don't have full data for)
    logger.info("Enriching %d awesome list repos with GitHub stats...", len(all_entries))
    results = []
    batch_count = 0

    for url, entry in all_entries.items():
        # Extract full_name from GitHub URL
        match = re.match(r"https://github\.com/([^/]+/[^/]+)", entry["url"])
        if not match:
            # Non-GitHub link, keep as-is with minimal data
            results.append({
                "name": entry["name"],
                "url": entry["url"],
                "description": entry["description"],
                "stars": 0,
                "forks": 0,
                "last_commit_date": "",
                "topics": [],
                "license": "",
                "primary_language": "",
                "full_name": "",
                "source_list": entry.get("source_list", ""),
            })
            continue

        full_name = match.group(1)
        repo_data = await _fetch_repo_details(session, full_name)

        if repo_data:
            enriched = _repo_to_entry(repo_data)
            enriched["source_list"] = entry.get("source_list", "")
            if not enriched["archived"]:
                results.append(enriched)
        else:
            # API failure — keep with basic info
            results.append({
                "name": entry["name"],
                "url": entry["url"],
                "description": entry["description"],
                "stars": 0,
                "forks": 0,
                "last_commit_date": "",
                "topics": [],
                "license": "",
                "primary_language": "",
                "full_name": full_name,
                "source_list": entry.get("source_list", ""),
            })

        batch_count += 1
        if batch_count % 50 == 0:
            logger.info("  Enriched %d/%d repos...", batch_count, len(all_entries))

    logger.info("Strategy 4 total: %d repos from awesome lists", len(results))
    return results


# =============================================================================
# Merge, normalize, categorize
# =============================================================================


def _classify_category(entry: dict) -> str:
    """Classify a repo into a tool category based on signals."""
    name_lower = (entry.get("name") or "").lower()
    desc_lower = (entry.get("description") or "").lower()
    topics = [t.lower() for t in entry.get("topics", [])]

    # Check for skills
    skill_signals = ["skill", "skills", "claude-skill", "codex-skill", "agent-skill"]
    if any(s in name_lower or s in desc_lower for s in skill_signals):
        return "skill"
    if any(s in topics for s in skill_signals):
        return "skill"

    # Check for MCP server
    mcp_signals = ["mcp-server", "mcp", "model-context-protocol"]
    if any(s in name_lower for s in mcp_signals):
        return "mcp_server"
    if any(s in topics for s in mcp_signals):
        return "mcp_server"
    if "mcp" in desc_lower and ("server" in desc_lower or "tool" in desc_lower):
        return "mcp_server"

    # Check for agent tool
    agent_signals = ["agent-tool", "ai-tool", "llm-tool"]
    if any(s in name_lower or s in desc_lower for s in agent_signals):
        return "agent_tool"

    # Default
    return "mcp_server"


def merge_and_normalize(
    topics_results: list[dict],
    deps_results: list[dict],
    files_results: list[dict],
    awesome_results: list[dict],
) -> list[dict]:
    """Merge results from all strategies, deduplicate, and normalize."""
    # Merge by URL (first occurrence wins for metadata, but we pick best stats)
    merged = {}  # normalized url -> entry

    strategy_labels = [
        ("topics", topics_results),
        ("dependency_graph", deps_results),
        ("file_search", files_results),
        ("awesome_list", awesome_results),
    ]

    for label, entries in strategy_labels:
        for entry in entries:
            url = entry.get("url", "").rstrip("/").lower()
            if not url:
                continue

            if url in merged:
                # Keep the one with more stars (better enrichment)
                existing = merged[url]
                if entry.get("stars", 0) > existing.get("stars", 0):
                    entry["_strategies"] = existing.get("_strategies", []) + [label]
                    merged[url] = entry
                else:
                    existing.setdefault("_strategies", []).append(label)
            else:
                entry["_strategies"] = [label]
                merged[url] = entry

    # Normalize to Clarvia schema
    discoveries = []
    for url, entry in merged.items():
        category = _classify_category(entry)
        strategies = entry.get("_strategies", [])

        discoveries.append(normalize_tool(
            name=entry.get("name", ""),
            url=entry.get("url", ""),
            description=entry.get("description", ""),
            source="github_comprehensive",
            category=category,
            extra={
                "stars": entry.get("stars", 0),
                "forks": entry.get("forks", 0),
                "last_commit_date": entry.get("last_commit_date", ""),
                "topics": entry.get("topics", []),
                "license": entry.get("license", ""),
                "primary_language": entry.get("primary_language", ""),
                "full_name": entry.get("full_name", ""),
                "discovery_strategies": strategies,
                "source_list": entry.get("source_list", ""),
            },
        ))

    return discoveries


# =============================================================================
# Main entry point
# =============================================================================


async def run(
    dry_run: bool = False,
    strategy: str | None = None,
) -> dict:
    """Run the comprehensive GitHub crawler.

    Args:
        dry_run: If True, discover but don't queue results.
        strategy: Run only a specific strategy (topics, dependencies, files, awesome).
    """
    known_urls = load_known_urls()
    start_time = time.monotonic()

    topics_results = []
    deps_results = []
    files_results = []
    awesome_results = []

    strategy_stats = {}

    async with aiohttp.ClientSession() as session:
        # Check rate limit before starting
        await _check_rate_limit(session)

        # Run requested strategies
        strategies_to_run = (
            [strategy] if strategy
            else ["topics", "dependencies", "files", "awesome"]
        )

        if "topics" in strategies_to_run:
            topics_results = await strategy_topics(session)
            strategy_stats["topics"] = len(topics_results)

        if "dependencies" in strategies_to_run:
            deps_results = await strategy_dependencies(session)
            strategy_stats["dependencies"] = len(deps_results)

        if "files" in strategies_to_run:
            files_results = await strategy_files(session)
            strategy_stats["files"] = len(files_results)

        if "awesome" in strategies_to_run:
            awesome_results = await strategy_awesome_lists(session)
            strategy_stats["awesome"] = len(awesome_results)

        # Final rate limit check
        await _check_rate_limit(session)

    # Merge and normalize
    discoveries = merge_and_normalize(
        topics_results, deps_results, files_results, awesome_results,
    )

    unique = dedup_discoveries(discoveries, known_urls)

    elapsed = time.monotonic() - start_time

    # Build stats
    stats = {
        "source": "github_comprehensive",
        "total_found": len(discoveries),
        "new_unique": len(unique),
        "duplicates_skipped": len(discoveries) - len(unique),
        "per_strategy": strategy_stats,
        "elapsed_seconds": round(elapsed, 1),
    }

    # Log comprehensive summary
    logger.info("\n" + "=" * 60)
    logger.info("GITHUB COMPREHENSIVE CRAWLER SUMMARY")
    logger.info("=" * 60)
    logger.info("Strategies run: %s", ", ".join(strategies_to_run))
    for strat, count in strategy_stats.items():
        logger.info("  %-15s: %5d repos", strat, count)
    logger.info("-" * 40)
    logger.info("Total found (pre-dedup): %d", len(discoveries))
    logger.info("New unique:              %d", len(unique))
    logger.info("Duplicates skipped:      %d", len(discoveries) - len(unique))
    logger.info("Elapsed:                 %.1fs", elapsed)

    # Category breakdown
    categories = {}
    for d in unique:
        cat = d.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    if categories:
        logger.info("Category breakdown:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            logger.info("  %-15s: %5d", cat, count)

    # Top repos by stars
    starred = sorted(unique, key=lambda x: x.get("stars", 0), reverse=True)
    if starred[:10]:
        logger.info("Top discoveries by stars:")
        for d in starred[:10]:
            logger.info(
                "  %s (%d stars) — %s",
                d.get("name", ""),
                d.get("stars", 0),
                d.get("url", ""),
            )

    logger.info("=" * 60)

    if not dry_run:
        saved = save_discoveries(unique)
        stats["queued"] = saved
        logger.info("Queued %d new tools", saved)
    else:
        stats["dry_run"] = True
        logger.info("[DRY RUN] Would queue %d new tools", len(unique))
        for d in unique[:10]:
            logger.info(
                "  [NEW] %s (%d stars) — %s",
                d.get("name", ""), d.get("stars", 0), d.get("url", ""),
            )
        if len(unique) > 10:
            logger.info("  ... and %d more", len(unique) - 10)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Comprehensive MCP/Skills Discovery Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Strategies:
  topics        Search by GitHub topics (mcp-server, ai-agent, etc.)
  dependencies  Search by code dependencies (@modelcontextprotocol/sdk, etc.)
  files         Search by config files (mcp.json, SKILL.md, etc.)
  awesome       Parse awesome-mcp-servers lists

Examples:
  github_comprehensive_crawler.py --dry-run
  github_comprehensive_crawler.py --dry-run --strategy topics
  github_comprehensive_crawler.py --strategy dependencies
""",
    )
    parser.add_argument("--dry-run", action="store_true", help="Discover but don't queue")
    parser.add_argument(
        "--strategy",
        choices=["topics", "dependencies", "files", "awesome"],
        help="Run a single strategy only",
    )
    args = parser.parse_args()

    result = asyncio.run(run(dry_run=args.dry_run, strategy=args.strategy))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
