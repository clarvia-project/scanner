"""Shared base utilities for all Clarvia crawlers.

Provides common schema normalization, dedup, rate limiting, and output helpers.
"""

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
QUEUE_PATH = DATA_DIR / "new-tools-queue.jsonl"
DISCOVERIES_PATH = DATA_DIR / "harvester" / "discoveries.jsonl"
PREBUILT_PATH = DATA_DIR / "prebuilt-scans.json"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Common user-agent for all crawlers
USER_AGENT = "Clarvia-Crawler/2.0 (+https://clarvia.com)"

# Default request timeout
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)


class RateLimiter:
    """Simple async rate limiter with configurable delay between requests."""

    def __init__(self, delay: float = 1.0, name: str = ""):
        self.delay = delay
        self.name = name
        self._last_request = 0.0

    async def wait(self):
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self.delay:
            await asyncio.sleep(self.delay - elapsed)
        self._last_request = time.monotonic()


def normalize_tool(
    *,
    name: str,
    url: str,
    description: str = "",
    source: str,
    category: str = "mcp_server",
    extra: dict | None = None,
) -> dict:
    """Normalize a discovered tool to the common Clarvia schema."""
    entry = {
        "name": name.strip() if name else "",
        "url": url.strip().rstrip("/") if url else "",
        "description": (description or "").strip()[:500],
        "source": source,
        "category": category,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        entry.update(extra)
    return entry


def load_known_urls() -> set[str]:
    """Load all URLs already in the catalog or queue for deduplication."""
    urls: set[str] = set()

    for path in [PREBUILT_PATH, QUEUE_PATH, DISCOVERIES_PATH]:
        if not path.exists():
            continue
        try:
            with open(path) as f:
                if path.suffix == ".json":
                    for entry in json.load(f):
                        u = entry.get("url", "").rstrip("/").lower()
                        if u:
                            urls.add(u)
                else:
                    for line in f:
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            u = entry.get("url", "").rstrip("/").lower()
                            if u:
                                urls.add(u)
        except Exception as e:
            logger.warning("Failed to load %s for dedup: %s", path, e)

    # Also load from all-mcp-urls.json and all-agent-tools.json
    for extra_file in ["all-mcp-urls.json", "all-agent-tools.json"]:
        extra_path = DATA_DIR / extra_file
        if extra_path.exists():
            try:
                with open(extra_path) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for entry in data:
                            if isinstance(entry, str):
                                urls.add(entry.rstrip("/").lower())
                            elif isinstance(entry, dict):
                                u = entry.get("url", "").rstrip("/").lower()
                                if u:
                                    urls.add(u)
            except Exception as e:
                logger.warning("Failed to load %s for dedup: %s", extra_path, e)

    logger.info("Loaded %d known URLs for deduplication", len(urls))
    return urls


def dedup_discoveries(discoveries: list[dict], known_urls: set[str]) -> list[dict]:
    """Remove duplicates from a list of discoveries against known URLs."""
    unique = []
    seen = set()
    for d in discoveries:
        url = d.get("url", "").rstrip("/").lower()
        if not url or url in known_urls or url in seen:
            continue
        seen.add(url)
        unique.append(d)
    return unique


def append_jsonl(path: Path, entries: list[dict]) -> int:
    """Append entries to a JSONL file. Returns count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(path, "a") as f:
        for entry in entries:
            f.write(json.dumps(entry, default=str) + "\n")
            count += 1
    return count


def save_discoveries(discoveries: list[dict], output_path: Path | None = None) -> int:
    """Save new discoveries to the queue file."""
    if not discoveries:
        return 0
    target = output_path or QUEUE_PATH
    return append_jsonl(target, discoveries)


async def fetch_json(
    session: aiohttp.ClientSession,
    url: str,
    *,
    headers: dict | None = None,
    timeout: aiohttp.ClientTimeout | None = None,
    rate_limiter: RateLimiter | None = None,
) -> dict | list | None:
    """Fetch JSON from a URL with error handling and optional rate limiting."""
    if rate_limiter:
        await rate_limiter.wait()

    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)

    try:
        async with session.get(
            url, headers=hdrs, timeout=timeout or DEFAULT_TIMEOUT
        ) as resp:
            if resp.status != 200:
                logger.warning("GET %s returned %d", url, resp.status)
                return None
            return await resp.json(content_type=None)
    except Exception as e:
        logger.error("Failed to fetch %s: %s", url, e)
        return None


async def fetch_text(
    session: aiohttp.ClientSession,
    url: str,
    *,
    headers: dict | None = None,
    timeout: aiohttp.ClientTimeout | None = None,
    rate_limiter: RateLimiter | None = None,
) -> str | None:
    """Fetch text content from a URL with error handling."""
    if rate_limiter:
        await rate_limiter.wait()

    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)

    try:
        async with session.get(
            url, headers=hdrs, timeout=timeout or DEFAULT_TIMEOUT
        ) as resp:
            if resp.status != 200:
                logger.warning("GET %s returned %d", url, resp.status)
                return None
            return await resp.text()
    except Exception as e:
        logger.error("Failed to fetch %s: %s", url, e)
        return None


def extract_github_urls_from_markdown(text: str) -> list[dict]:
    """Extract GitHub repo URLs and their context from markdown text."""
    results = []
    # Match GitHub repo URLs with optional description context
    pattern = re.compile(
        r'\[([^\]]*)\]\((https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+)\)'
    )
    for match in pattern.finditer(text):
        name = match.group(1).strip()
        url = match.group(2).strip().rstrip("/")
        # Get surrounding text for description
        start = max(0, match.start() - 5)
        end = min(len(text), match.end() + 200)
        context = text[start:end]
        # Extract description after the link (often "- description" or " — description")
        desc_match = re.search(r'\)\s*[-–—:]\s*(.+?)(?:\n|$)', context)
        description = desc_match.group(1).strip() if desc_match else ""
        results.append({
            "name": name,
            "url": url,
            "description": description,
        })
    return results
