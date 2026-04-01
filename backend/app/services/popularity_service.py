"""Popularity data service — fetches npm downloads, GitHub stars, PyPI downloads.

Designed for batch usage (daily cron), not real-time per-request.
Results are cached in a local JSON file and loaded on API startup.
"""

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

_CACHE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "popularity-cache.json"
_cache: dict[str, dict[str, Any]] = {}


def load_cache() -> None:
    """Load popularity cache from disk on startup."""
    global _cache
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE) as f:
                _cache = json.load(f)
            logger.info("Loaded popularity cache: %d entries", len(_cache))
        except Exception as e:
            logger.warning("Failed to load popularity cache: %s", e)
            _cache = {}


def save_cache() -> None:
    """Save popularity cache to disk."""
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_FILE, "w") as f:
        json.dump(_cache, f, separators=(",", ":"), ensure_ascii=False)
    logger.info("Saved popularity cache: %d entries", len(_cache))


def get_popularity(identifier: str) -> dict[str, Any] | None:
    """Get cached popularity data for a tool (by name or scan_id)."""
    return _cache.get(identifier)


async def fetch_npm_downloads(package_name: str, session: aiohttp.ClientSession) -> int | None:
    """Fetch weekly downloads from npm registry."""
    url = f"https://api.npmjs.org/downloads/point/last-week/{package_name}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("downloads", 0)
    except Exception as e:
        logger.debug("npm downloads fetch failed for %s: %s", package_name, e)
    return None


async def fetch_github_stars(repo_url: str, session: aiohttp.ClientSession, token: str | None = None) -> int | None:
    """Fetch star count from GitHub API."""
    # Extract owner/repo from URL
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        return None
    owner, repo = parts[-2], parts[-1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("stargazers_count", 0)
    except Exception as e:
        logger.debug("GitHub stars fetch failed for %s: %s", repo_url, e)
    return None


async def fetch_pypi_downloads(package_name: str, session: aiohttp.ClientSession) -> int | None:
    """Fetch recent downloads from PyPI stats."""
    url = f"https://pypistats.org/api/packages/{package_name}/recent"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", {}).get("last_week", 0)
    except Exception as e:
        logger.debug("PyPI downloads fetch failed for %s: %s", package_name, e)
    return None


def compute_popularity_score(npm_downloads: int | None, github_stars: int | None, pypi_downloads: int | None) -> int:
    """Compute a 0-100 popularity score from raw metrics."""
    score = 0.0

    if npm_downloads and npm_downloads > 0:
        # log10 scale: 10 downloads = 15, 100 = 30, 1000 = 45, 10000 = 60
        score += min(60, math.log10(max(1, npm_downloads)) * 15)

    if github_stars and github_stars > 0:
        # log10 scale: 10 stars = 20, 100 = 40
        score += min(40, math.log10(max(1, github_stars)) * 20)

    if pypi_downloads and pypi_downloads > 0:
        # Bonus for PyPI presence (capped at 20)
        score += min(20, math.log10(max(1, pypi_downloads)) * 5)

    return min(100, int(score))
