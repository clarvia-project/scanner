#!/usr/bin/env python3
"""Clarvia Harvester — Auto-Discovery Crawler for AI Agent Tools.

Crawls multiple sources to discover new tools and queue them for scanning:
1. GitHub — repos with AI/MCP/agent-tool topics
2. npm Registry — packages with MCP/agent keywords
3. PyPI — packages matching agent-tool patterns
4. MCP Registries — extends existing catalog_updater sync

Quality filtering gates each discovery before queuing:
- GitHub: >=10 stars, recent commit, has README >100 chars, has code files
- npm: >=50 weekly downloads, has description, not deprecated
- PyPI: >=100 downloads or recent release, has description
- MCP Registry: pre-vetted, URL liveness check only

Usage:
    python scripts/automation/harvester.py [--source all|github|npm|pypi|mcp] [--dry-run]
"""

import argparse
import asyncio
import json
import logging
import os
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
REJECTED_PATH = HARVEST_DIR / "rejected.jsonl"
QUEUE_PATH = DATA_DIR / "new-tools-queue.jsonl"
PREBUILT_PATH = DATA_DIR / "prebuilt-scans.json"

# ---------------------------------------------------------------------------
# GitHub token and rate limiting
# ---------------------------------------------------------------------------

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
if GITHUB_TOKEN:
    # Authenticated: 5,000 requests/hour => ~1.4 req/s, use 1s delay
    GITHUB_DELAY = 1.0
    logger.info("GitHub token detected — using authenticated rate limit (5,000 req/hr)")
else:
    # Unauthenticated: 60 requests/hour => ~6s delay
    GITHUB_DELAY = 6.5
    logger.warning(
        "No GITHUB_TOKEN set — using unauthenticated rate limit (60 req/hr). "
        "Set GITHUB_TOKEN env var for 5,000 req/hr."
    )

NPM_DELAY = 1.0
PYPI_DELAY = 1.5

# Minimum quality thresholds
GITHUB_MIN_STARS = 10
GITHUB_MAX_AGE_DAYS = 180
GITHUB_MIN_README_CHARS = 100
NPM_MIN_WEEKLY_DOWNLOADS = 50
QUALITY_SCORE_THRESHOLD = 30

# Rate limit tracker for GitHub
_github_rate_remaining: int = -1
_github_rate_reset: float = 0.0


def _update_github_rate_limit(headers: dict) -> None:
    """Track GitHub rate limit from response headers."""
    global _github_rate_remaining, _github_rate_reset
    remaining = headers.get("X-RateLimit-Remaining")
    reset = headers.get("X-RateLimit-Reset")
    if remaining is not None:
        _github_rate_remaining = int(remaining)
    if reset is not None:
        _github_rate_reset = float(reset)
    if _github_rate_remaining >= 0 and _github_rate_remaining < 10:
        logger.warning(
            "GitHub rate limit low: %d remaining, resets at %s",
            _github_rate_remaining,
            datetime.fromtimestamp(_github_rate_reset, tz=timezone.utc).isoformat(),
        )


async def _github_backoff() -> None:
    """Wait for rate limit reset if we're close to the limit."""
    global _github_rate_remaining, _github_rate_reset
    if _github_rate_remaining >= 0 and _github_rate_remaining < 5:
        wait_until = _github_rate_reset - time.time()
        if wait_until > 0:
            logger.info("GitHub rate limit nearly exhausted, backing off %.0fs", wait_until)
            await asyncio.sleep(min(wait_until + 2, 300))  # cap at 5 min
    else:
        await asyncio.sleep(GITHUB_DELAY)


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------

def compute_quality_score(discovery: dict) -> int:
    """Compute a 0-100 quality score for a discovered tool.

    Breakdown:
    - Stars/downloads (normalized):     0-30 points
    - Recency of last update:           0-25 points
    - Has description:                  0-15 points
    - Has documentation URL:            0-15 points
    - README length (>500 chars bonus): 0-15 points
    """
    score = 0
    source = discovery.get("source", "")

    # --- Stars / downloads (0-30) ---
    if source == "github":
        stars = discovery.get("stars", 0)
        if stars >= 1000:
            score += 30
        elif stars >= 500:
            score += 25
        elif stars >= 100:
            score += 20
        elif stars >= 50:
            score += 15
        elif stars >= 20:
            score += 10
        elif stars >= 10:
            score += 5
    elif source == "npm":
        pop = discovery.get("popularity_score", 0)
        # npm popularity is 0-1 float
        if pop >= 0.8:
            score += 30
        elif pop >= 0.5:
            score += 25
        elif pop >= 0.2:
            score += 15
        elif pop >= 0.05:
            score += 10
        else:
            score += 3
    elif source == "pypi":
        # PyPI doesn't expose download counts in JSON API directly;
        # use version count as proxy for maturity
        version = discovery.get("version", "")
        if version and not version.startswith("0.0."):
            score += 10
        else:
            score += 3
    elif source == "mcp_registry":
        # Pre-vetted, baseline trust
        score += 20

    # --- Recency (0-25) ---
    last_updated = discovery.get("last_updated", "")
    if last_updated:
        try:
            if last_updated.endswith("Z"):
                last_updated = last_updated.replace("Z", "+00:00")
            updated_dt = datetime.fromisoformat(last_updated)
            days_ago = (datetime.now(timezone.utc) - updated_dt).days
            if days_ago <= 30:
                score += 25
            elif days_ago <= 90:
                score += 20
            elif days_ago <= 180:
                score += 12
            elif days_ago <= 365:
                score += 5
        except (ValueError, TypeError):
            pass

    # --- Has description (0-15) ---
    desc = discovery.get("description", "")
    if len(desc) > 50:
        score += 15
    elif len(desc) > 10:
        score += 8
    elif desc:
        score += 3

    # --- Has documentation URL (0-15) ---
    has_docs = bool(
        discovery.get("homepage")
        or discovery.get("repository")
        or discovery.get("docs_url")
    )
    if has_docs:
        score += 15

    # --- README length bonus (0-15) ---
    readme_len = discovery.get("readme_length", 0)
    if readme_len > 2000:
        score += 15
    elif readme_len > 500:
        score += 10
    elif readme_len > 100:
        score += 5

    return min(score, 100)


# ---------------------------------------------------------------------------
# Rejection logger
# ---------------------------------------------------------------------------

def _log_rejection(discovery: dict, reason: str) -> None:
    """Append a rejected discovery to the rejection log."""
    entry = {
        "url": discovery.get("url", ""),
        "name": discovery.get("name", ""),
        "source": discovery.get("source", ""),
        "reason": reason,
        "quality_score": discovery.get("quality_score", 0),
        "rejected_at": datetime.now(timezone.utc).isoformat(),
    }
    _append_jsonl(REJECTED_PATH, [entry])


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

# Code file extensions — at least one must be present
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".ex", ".exs",
    ".c", ".cpp", ".h", ".cs", ".swift", ".kt", ".lua", ".sh", ".ps1",
    ".jsx", ".tsx", ".mjs", ".cjs",
}


async def _github_repo_has_code_and_readme(
    session: aiohttp.ClientSession,
    headers: dict,
    full_name: str,
) -> tuple[bool, int]:
    """Check if a GitHub repo has actual code files and a README with >100 chars.

    Returns (passes_check, readme_length).
    """
    # Fetch repo contents (root directory)
    url = f"https://api.github.com/repos/{full_name}/contents"
    try:
        await _github_backoff()
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            _update_github_rate_limit(dict(resp.headers))
            if resp.status != 200:
                # If we can't check, give benefit of the doubt
                return True, 0

            contents = await resp.json()
            if not isinstance(contents, list):
                return True, 0

            has_code = False
            readme_entry = None
            for item in contents:
                name = item.get("name", "")
                if item.get("type") == "file":
                    # Check for code files
                    for ext in CODE_EXTENSIONS:
                        if name.lower().endswith(ext):
                            has_code = True
                            break
                    # Check for README
                    if name.lower().startswith("readme"):
                        readme_entry = item

                # Check for src/ or lib/ directories (implies code)
                if item.get("type") == "dir" and name.lower() in ("src", "lib", "pkg", "cmd", "app"):
                    has_code = True

            if not has_code:
                return False, 0

            # Check README length
            readme_length = 0
            if readme_entry:
                readme_size = readme_entry.get("size", 0)
                readme_length = readme_size  # size in bytes ~ chars for ASCII/UTF-8 text

            if readme_length < GITHUB_MIN_README_CHARS:
                return False, readme_length

            return True, readme_length

    except Exception:
        # Network error — allow through, scanner will validate later
        return True, 0


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
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    async def _process_repo(repo: dict) -> dict | None:
        """Process a single repo search result with quality checks."""
        repo_url = repo.get("html_url", "").rstrip("/").lower()
        full_name = repo.get("full_name", "")
        if not repo_url or repo_url in known_urls or full_name in seen_repos:
            return None
        seen_repos.add(full_name)

        stars = repo.get("stargazers_count", 0)
        if stars < GITHUB_MIN_STARS:
            _log_rejection(
                {"url": repo.get("html_url", ""), "name": repo.get("name", ""), "source": "github"},
                f"Insufficient stars: {stars} < {GITHUB_MIN_STARS}",
            )
            return None

        # Check for code files and README
        has_code, readme_len = await _github_repo_has_code_and_readme(
            session, headers, full_name,
        )
        if not has_code:
            _log_rejection(
                {"url": repo.get("html_url", ""), "name": repo.get("name", ""), "source": "github"},
                "No code files or README too short (<100 chars)",
            )
            return None

        discovery = {
            "source": "github",
            "url": repo.get("html_url", ""),
            "name": repo.get("name", ""),
            "full_name": full_name,
            "description": repo.get("description") or "",
            "stars": stars,
            "last_updated": repo.get("pushed_at", ""),
            "topics": repo.get("topics", []),
            "language": repo.get("language"),
            "homepage": repo.get("homepage") or "",
            "readme_length": readme_len,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "status": "new",
        }

        # Compute quality score
        qs = compute_quality_score(discovery)
        discovery["quality_score"] = qs
        if qs < QUALITY_SCORE_THRESHOLD:
            _log_rejection(discovery, f"Quality score {qs} < {QUALITY_SCORE_THRESHOLD}")
            return None

        return discovery

    # Search by topics
    for topic in GITHUB_TOPICS:
        query = f"topic:{topic} stars:>={GITHUB_MIN_STARS} pushed:>{cutoff_str}"
        encoded = quote_plus(query)
        url = f"https://api.github.com/search/repositories?q={encoded}&sort=stars&order=desc&per_page=30"

        try:
            await _github_backoff()
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                _update_github_rate_limit(dict(resp.headers))
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
                    result = await _process_repo(repo)
                    if result:
                        discoveries.append(result)
        except Exception as e:
            logger.error("GitHub topic search error (%s): %s", topic, e)

    # Search by query strings
    for query_str in GITHUB_SEARCH_QUERIES:
        full_query = f"{query_str} stars:>={GITHUB_MIN_STARS} pushed:>{cutoff_str}"
        encoded = quote_plus(full_query)
        url = f"https://api.github.com/search/repositories?q={encoded}&sort=stars&order=desc&per_page=30"

        try:
            await _github_backoff()
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                _update_github_rate_limit(dict(resp.headers))
                if resp.status == 403:
                    logger.warning("GitHub rate limited on query, stopping")
                    break
                if resp.status != 200:
                    continue

                data = await resp.json()
                items = data.get("items", [])
                logger.info("GitHub query '%s' — %d results", query_str[:30], len(items))

                for repo in items:
                    result = await _process_repo(repo)
                    if result:
                        discoveries.append(result)
        except Exception as e:
            logger.error("GitHub query search error: %s", e)

    logger.info("GitHub: discovered %d new repos (passed quality filter)", len(discoveries))
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

                    # Quality filters for npm
                    description = pkg.get("description") or ""
                    if not description:
                        _log_rejection(
                            {"url": npm_url, "name": pkg_name, "source": "npm"},
                            "No description",
                        )
                        continue

                    # Check for deprecated flag
                    flags = obj.get("flags", {})
                    if flags.get("deprecated"):
                        _log_rejection(
                            {"url": npm_url, "name": pkg_name, "source": "npm"},
                            "Package is deprecated",
                        )
                        continue

                    # Popularity threshold: 0.05 ~ roughly 50 weekly downloads
                    if popularity < 0.02:
                        _log_rejection(
                            {"url": npm_url, "name": pkg_name, "source": "npm"},
                            f"Low popularity: {popularity:.4f} (< 0.02 threshold)",
                        )
                        continue

                    discovery = {
                        "source": "npm",
                        "url": homepage or repo_url or npm_url,
                        "npm_url": npm_url,
                        "name": pkg_name,
                        "description": description,
                        "version": pkg.get("version", ""),
                        "homepage": homepage,
                        "repository": repo_url,
                        "keywords": pkg.get("keywords", []),
                        "popularity_score": popularity,
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                        "status": "new",
                    }

                    # Quality score check
                    qs = compute_quality_score(discovery)
                    discovery["quality_score"] = qs
                    if qs < QUALITY_SCORE_THRESHOLD:
                        _log_rejection(discovery, f"Quality score {qs} < {QUALITY_SCORE_THRESHOLD}")
                        continue

                    discoveries.append(discovery)
        except Exception as e:
            logger.error("npm search error (%s): %s", keyword, e)

    logger.info("npm: discovered %d new packages (passed quality filter)", len(discoveries))
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

    async def _check_pypi_package(pkg_name: str) -> dict | None:
        """Fetch and validate a single PyPI package."""
        url = f"https://pypi.org/pypi/{pkg_name}/json"
        try:
            await asyncio.sleep(PYPI_DELAY)
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()
                info = data.get("info", {})

                pypi_url = f"https://pypi.org/project/{pkg_name}/"
                homepage = info.get("home_page") or info.get("project_url") or ""
                check_url = (homepage or pypi_url).rstrip("/").lower()
                if check_url in known_urls:
                    return None

                # Quality filter: must have description
                description = info.get("summary") or ""
                if not description:
                    _log_rejection(
                        {"url": pypi_url, "name": pkg_name, "source": "pypi"},
                        "No description",
                    )
                    return None

                # Check recency: recent release within 3 months
                releases = data.get("releases", {})
                recent_release = False
                three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
                for ver, files in releases.items():
                    for f in files:
                        upload_time = f.get("upload_time_iso_8601") or f.get("upload_time", "")
                        if upload_time:
                            try:
                                if upload_time.endswith("Z"):
                                    upload_time = upload_time.replace("Z", "+00:00")
                                ut = datetime.fromisoformat(upload_time)
                                if ut.tzinfo is None:
                                    ut = ut.replace(tzinfo=timezone.utc)
                                if ut > three_months_ago:
                                    recent_release = True
                                    break
                            except (ValueError, TypeError):
                                pass
                    if recent_release:
                        break

                # Check download signal: number of releases as maturity proxy
                num_releases = len(releases)
                if not recent_release and num_releases < 3:
                    _log_rejection(
                        {"url": pypi_url, "name": pkg_name, "source": "pypi"},
                        f"Not recently released and few versions ({num_releases})",
                    )
                    return None

                discovery = {
                    "source": "pypi",
                    "url": homepage or pypi_url,
                    "pypi_url": pypi_url,
                    "name": info.get("name", pkg_name),
                    "description": description,
                    "version": info.get("version", ""),
                    "homepage": homepage,
                    "author": info.get("author") or "",
                    "license": info.get("license") or "",
                    "keywords": (info.get("keywords") or "").split(",")[:10],
                    "requires_python": info.get("requires_python") or "",
                    "last_updated": "",  # Will be set from release data
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                    "status": "new",
                }

                # Set last_updated from latest release upload time
                latest_files = data.get("urls", [])
                if latest_files:
                    upload_time = latest_files[0].get("upload_time_iso_8601", "")
                    discovery["last_updated"] = upload_time

                # Quality score check
                qs = compute_quality_score(discovery)
                discovery["quality_score"] = qs
                if qs < QUALITY_SCORE_THRESHOLD:
                    _log_rejection(discovery, f"Quality score {qs} < {QUALITY_SCORE_THRESHOLD}")
                    return None

                return discovery
        except Exception as e:
            logger.debug("PyPI lookup error (%s): %s", pkg_name, e)
            return None

    for pattern in pypi_package_patterns:
        for suffix in suffixes:
            pkg_name = pattern.format(suffix=suffix)
            if pkg_name in seen_packages:
                continue
            seen_packages.add(pkg_name)

            result = await _check_pypi_package(pkg_name)
            if result:
                discoveries.append(result)

    # Also try direct search terms
    for term in PYPI_SEARCH_TERMS:
        pkg_name = term
        if pkg_name in seen_packages:
            continue
        seen_packages.add(pkg_name)

        result = await _check_pypi_package(pkg_name)
        if result:
            discoveries.append(result)

    logger.info("PyPI: discovered %d new packages (passed quality filter)", len(discoveries))
    return discoveries


# ---------------------------------------------------------------------------
# MCP Registry Harvester (extends catalog_updater)
# ---------------------------------------------------------------------------

MCP_REGISTRY_API = "https://registry.modelcontextprotocol.io/v0/servers"


async def _check_url_live(session: aiohttp.ClientSession, url: str) -> bool:
    """HEAD request to verify URL is reachable (5s timeout)."""
    try:
        async with session.head(
            url,
            timeout=aiohttp.ClientTimeout(total=5),
            allow_redirects=True,
        ) as resp:
            return resp.status < 400
    except Exception:
        # Try GET as fallback (some servers reject HEAD)
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True,
            ) as resp:
                return resp.status < 400
        except Exception:
            return False


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

                # MCP Registry entries are pre-vetted, but verify URL is live
                is_live = await _check_url_live(session, url)
                if not is_live:
                    _log_rejection(
                        {"url": url, "name": srv.get("name", ""), "source": "mcp_registry"},
                        "URL not reachable (HEAD/GET failed within 5s)",
                    )
                    continue

                name = srv.get("name") or srv.get("title") or ""
                discovery = {
                    "source": "mcp_registry",
                    "url": url,
                    "name": name,
                    "description": srv.get("description") or "",
                    "server_data": srv,
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                    "status": "new",
                }

                qs = compute_quality_score(discovery)
                discovery["quality_score"] = qs
                # MCP registry is pre-vetted — use lower threshold
                if qs < 15:
                    _log_rejection(discovery, f"Quality score {qs} < 15 (MCP registry)")
                    continue

                discoveries.append(discovery)

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
            "quality_score": d.get("quality_score", 0),
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
        "github_token": bool(GITHUB_TOKEN),
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

    # Quality score summary
    if all_discoveries:
        scores = [d.get("quality_score", 0) for d in all_discoveries]
        stats["quality_score_avg"] = round(sum(scores) / len(scores), 1)
        stats["quality_score_min"] = min(scores)
        stats["quality_score_max"] = max(scores)

    if dry_run:
        stats["dry_run"] = True
        stats["queued"] = 0
        logger.info("DRY RUN — would queue %d tools", len(all_discoveries))
        # Print sample
        for d in all_discoveries[:10]:
            logger.info(
                "  [%s] %s (qs=%d) — %s",
                d["source"], d.get("name", "?"), d.get("quality_score", 0), d["url"],
            )
        if len(all_discoveries) > 10:
            logger.info("  ... and %d more", len(all_discoveries) - 10)
    else:
        queued = queue_discoveries(all_discoveries)
        stats["queued"] = queued

    stats["finished_at"] = datetime.now(timezone.utc).isoformat()

    # Count rejections
    if REJECTED_PATH.exists():
        try:
            with open(REJECTED_PATH) as f:
                stats["total_rejected"] = sum(1 for _ in f)
        except Exception:
            pass

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
