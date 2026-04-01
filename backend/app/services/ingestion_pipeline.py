"""Ingestion Pipeline — discovers, queues, and processes new AI agent tools.

Sources:
  1. GitHub Watcher — searches for new MCP server repos
  2. Registry Sync — syncs from mcp.so, smithery.ai, glama.ai, pulsemcp.com
  3. Community Crawl — discovers from npm and PyPI
  4. Dead Tool Cleanup — archives unreachable tools older than 90 days

Queue items flow through: discover → queue → validate → score → index
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import IntEnum
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
QUEUE_FILE = DATA_DIR / "ingestion-queue.jsonl"
MAX_QUEUE_SIZE = 5000
HTTP_TIMEOUT = 10.0
USER_AGENT = "Clarvia-Ingestion/1.0 (+https://clarvia.com)"


class Priority(IntEnum):
    """Queue priority levels. Lower value = higher priority."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


# ---------------------------------------------------------------------------
# Queue Item
# ---------------------------------------------------------------------------

@dataclass
class QueueItem:
    """A single item in the ingestion queue."""
    url: str
    source: str
    priority: int = Priority.MEDIUM
    metadata: dict[str, Any] = field(default_factory=dict)
    submitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    retry_count: int = 0
    _url_key: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        self._url_key = _normalize_url(self.url)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("_url_key", None)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> QueueItem:
        d.pop("_url_key", None)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def _normalize_url(url: str) -> str:
    """Normalize URL for dedup: lowercase host, strip trailing slash, remove fragments."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/") or ""
    return f"{parsed.scheme}://{host}{path}"


# ---------------------------------------------------------------------------
# Ingestion Queue
# ---------------------------------------------------------------------------

class IngestionQueue:
    """In-memory priority queue with JSONL persistence and URL dedup.

    Thread-safe via asyncio lock. Persists to data/ingestion-queue.jsonl.
    Max capacity: 5000 items.
    """

    def __init__(self, persist_path: Path = QUEUE_FILE, max_size: int = MAX_QUEUE_SIZE) -> None:
        self._items: dict[str, QueueItem] = {}  # url_key -> item
        self._persist_path = persist_path
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._dirty = False

    async def load(self) -> None:
        """Load queue from JSONL file on disk."""
        async with self._lock:
            self._items.clear()
            if not self._persist_path.exists():
                return
            try:
                with open(self._persist_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            item = QueueItem.from_dict(json.loads(line))
                            self._items[item._url_key] = item
                        except (json.JSONDecodeError, TypeError, KeyError) as e:
                            logger.warning("Skipping malformed queue entry: %s", e)
                logger.info("Loaded %d items from ingestion queue", len(self._items))
            except OSError as e:
                logger.error("Failed to load queue file: %s", e)

    async def save(self) -> None:
        """Persist queue to JSONL file."""
        async with self._lock:
            if not self._dirty:
                return
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._persist_path.with_suffix(".tmp")
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    for item in self._items.values():
                        f.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
                tmp.replace(self._persist_path)
                self._dirty = False
                logger.debug("Saved %d items to ingestion queue", len(self._items))
            except OSError as e:
                logger.error("Failed to save queue: %s", e)

    async def add(self, item: QueueItem) -> bool:
        """Add item to queue. Returns True if added, False if duplicate or full."""
        async with self._lock:
            key = item._url_key
            if key in self._items:
                # Update priority if new one is higher
                existing = self._items[key]
                if item.priority < existing.priority:
                    existing.priority = item.priority
                    existing.metadata.update(item.metadata)
                    self._dirty = True
                return False
            if len(self._items) >= self._max_size:
                # Evict lowest-priority item
                worst_key = max(self._items, key=lambda k: (self._items[k].priority, self._items[k].submitted_at))
                if self._items[worst_key].priority > item.priority:
                    del self._items[worst_key]
                else:
                    return False
            self._items[key] = item
            self._dirty = True
            return True

    async def add_batch(self, items: list[QueueItem]) -> int:
        """Add multiple items. Returns count of newly added."""
        added = 0
        for item in items:
            if await self.add(item):
                added += 1
        return added

    async def next_batch(self, size: int = 20) -> list[QueueItem]:
        """Return priority-sorted batch of items (does not remove them)."""
        async with self._lock:
            sorted_items = sorted(
                self._items.values(),
                key=lambda i: (i.priority, i.submitted_at),
            )
            return sorted_items[:size]

    async def remove(self, url: str) -> bool:
        """Remove an item from the queue by URL."""
        key = _normalize_url(url)
        async with self._lock:
            if key in self._items:
                del self._items[key]
                self._dirty = True
                return True
            return False

    async def mark_retry(self, url: str) -> None:
        """Increment retry count for an item."""
        key = _normalize_url(url)
        async with self._lock:
            if key in self._items:
                self._items[key].retry_count += 1
                if self._items[key].retry_count > 3:
                    del self._items[key]
                    logger.info("Evicted %s after max retries", url)
                self._dirty = True

    @property
    def size(self) -> int:
        return len(self._items)

    @property
    def items(self) -> list[QueueItem]:
        return list(self._items.values())


# ---------------------------------------------------------------------------
# Stats Tracker
# ---------------------------------------------------------------------------

@dataclass
class IngestionStats:
    """Tracks ingestion pipeline metrics."""
    items_queued: int = 0
    items_processed: int = 0
    items_indexed: int = 0
    items_skipped: int = 0
    items_failed: int = 0
    by_source: dict[str, dict[str, int]] = field(default_factory=dict)
    last_run: dict[str, str] = field(default_factory=dict)  # source -> ISO timestamp

    def record(self, source: str, *, queued: int = 0, processed: int = 0,
               indexed: int = 0, skipped: int = 0, failed: int = 0) -> None:
        self.items_queued += queued
        self.items_processed += processed
        self.items_indexed += indexed
        self.items_skipped += skipped
        self.items_failed += failed

        if source not in self.by_source:
            self.by_source[source] = {"queued": 0, "processed": 0, "indexed": 0, "skipped": 0, "failed": 0}
        src = self.by_source[source]
        src["queued"] += queued
        src["processed"] += processed
        src["indexed"] += indexed
        src["skipped"] += skipped
        src["failed"] += failed
        self.last_run[source] = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_queue: IngestionQueue | None = None
_stats = IngestionStats()


async def get_queue() -> IngestionQueue:
    """Get or initialize the global ingestion queue."""
    global _queue
    if _queue is None:
        _queue = IngestionQueue()
        await _queue.load()
    return _queue


def get_ingestion_stats() -> dict[str, Any]:
    """Return current ingestion pipeline metrics."""
    return _stats.to_dict()


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _http_client() -> httpx.AsyncClient:
    """Create a configured httpx client."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(HTTP_TIMEOUT),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    )


# ---------------------------------------------------------------------------
# Source 1: GitHub Watcher
# ---------------------------------------------------------------------------

async def github_watcher() -> int:
    """Search GitHub for new MCP server repositories.

    Uses GitHub Search API (unauthenticated, 10 req/min).
    Returns count of items added to queue.
    """
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    queries = [
        f"mcp-server created:>={yesterday}",
        f"model-context-protocol created:>={yesterday}",
        "topic:mcp-server sort:updated",
    ]

    queue = await get_queue()
    total_added = 0

    async with _http_client() as client:
        for query in queries:
            try:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params={"q": query, "per_page": 50, "sort": "updated"},
                    headers={"Accept": "application/vnd.github.v3+json"},
                )
                if resp.status_code == 403:
                    logger.warning("GitHub rate limit hit for query: %s", query)
                    break
                if resp.status_code != 200:
                    logger.warning("GitHub search returned %d for query: %s", resp.status_code, query)
                    continue

                data = resp.json()
                items = data.get("items", [])
                logger.info("GitHub search '%s': %d results", query, len(items))

                batch: list[QueueItem] = []
                for repo in items:
                    html_url = repo.get("html_url", "")
                    if not html_url:
                        continue
                    batch.append(QueueItem(
                        url=html_url,
                        source="github_watcher",
                        priority=Priority.HIGH,
                        metadata={
                            "name": repo.get("full_name", ""),
                            "description": repo.get("description") or "",
                            "stars": repo.get("stargazers_count", 0),
                            "language": repo.get("language") or "",
                            "topics": repo.get("topics", []),
                            "created_at": repo.get("created_at", ""),
                            "updated_at": repo.get("updated_at", ""),
                        },
                    ))

                added = await queue.add_batch(batch)
                total_added += added

            except httpx.HTTPError as e:
                logger.error("GitHub watcher HTTP error: %s", e)
            except Exception as e:
                logger.error("GitHub watcher unexpected error: %s", e)

    _stats.record("github_watcher", queued=total_added)
    logger.info("GitHub watcher: added %d items to queue", total_added)
    return total_added


# ---------------------------------------------------------------------------
# Source 2: Registry Sync
# ---------------------------------------------------------------------------

async def registry_sync() -> int:
    """Sync tools from known MCP registries.

    Sources: mcp.so, smithery.ai, glama.ai, pulsemcp.com.
    Each registry is tried independently — failures don't block others.
    Returns count of items added to queue.
    """
    queue = await get_queue()
    total_added = 0

    async with _http_client() as client:
        # --- mcp.so ---
        total_added += await _sync_mcp_so(client, queue)
        # --- smithery.ai ---
        total_added += await _sync_smithery(client, queue)
        # --- glama.ai ---
        total_added += await _sync_glama(client, queue)
        # --- pulsemcp.com ---
        total_added += await _sync_pulsemcp(client, queue)

    _stats.record("registry_sync", queued=total_added)
    logger.info("Registry sync: added %d items to queue", total_added)
    return total_added


async def _sync_mcp_so(client: httpx.AsyncClient, queue: IngestionQueue) -> int:
    """Sync from mcp.so registry."""
    try:
        # mcp.so exposes a JSON API listing servers
        resp = await client.get("https://mcp.so/api/servers", params={"limit": 100})
        if resp.status_code != 200:
            logger.warning("mcp.so returned %d", resp.status_code)
            return 0

        data = resp.json()
        servers = data if isinstance(data, list) else data.get("servers", data.get("data", []))
        batch: list[QueueItem] = []
        for srv in servers:
            url = srv.get("url") or srv.get("github_url") or srv.get("homepage") or ""
            if not url:
                continue
            batch.append(QueueItem(
                url=url,
                source="mcp.so",
                priority=Priority.MEDIUM,
                metadata={
                    "name": srv.get("name", ""),
                    "description": srv.get("description", ""),
                    "registry": "mcp.so",
                },
            ))
        return await queue.add_batch(batch)
    except Exception as e:
        logger.warning("mcp.so sync failed: %s", e)
        return 0


async def _sync_smithery(client: httpx.AsyncClient, queue: IngestionQueue) -> int:
    """Sync from smithery.ai registry."""
    try:
        resp = await client.get("https://smithery.ai/api/servers", params={"limit": 100})
        if resp.status_code != 200:
            logger.warning("smithery.ai returned %d", resp.status_code)
            return 0

        data = resp.json()
        servers = data if isinstance(data, list) else data.get("servers", data.get("data", []))
        batch: list[QueueItem] = []
        for srv in servers:
            url = srv.get("url") or srv.get("github_url") or srv.get("repo") or ""
            if not url:
                continue
            batch.append(QueueItem(
                url=url,
                source="smithery.ai",
                priority=Priority.MEDIUM,
                metadata={
                    "name": srv.get("name", ""),
                    "description": srv.get("description", ""),
                    "registry": "smithery.ai",
                },
            ))
        return await queue.add_batch(batch)
    except Exception as e:
        logger.warning("smithery.ai sync failed: %s", e)
        return 0


async def _sync_glama(client: httpx.AsyncClient, queue: IngestionQueue) -> int:
    """Sync from glama.ai registry."""
    try:
        resp = await client.get("https://glama.ai/api/mcp/servers", params={"limit": 100})
        if resp.status_code != 200:
            logger.warning("glama.ai returned %d", resp.status_code)
            return 0

        data = resp.json()
        servers = data if isinstance(data, list) else data.get("servers", data.get("data", []))
        batch: list[QueueItem] = []
        for srv in servers:
            url = srv.get("url") or srv.get("github_url") or srv.get("repo") or ""
            if not url:
                continue
            batch.append(QueueItem(
                url=url,
                source="glama.ai",
                priority=Priority.MEDIUM,
                metadata={
                    "name": srv.get("name", ""),
                    "description": srv.get("description", ""),
                    "registry": "glama.ai",
                },
            ))
        return await queue.add_batch(batch)
    except Exception as e:
        logger.warning("glama.ai sync failed: %s", e)
        return 0


async def _sync_pulsemcp(client: httpx.AsyncClient, queue: IngestionQueue) -> int:
    """Sync from pulsemcp.com registry."""
    try:
        resp = await client.get("https://pulsemcp.com/api/servers", params={"limit": 100})
        if resp.status_code != 200:
            logger.warning("pulsemcp.com returned %d", resp.status_code)
            return 0

        data = resp.json()
        servers = data if isinstance(data, list) else data.get("servers", data.get("data", []))
        batch: list[QueueItem] = []
        for srv in servers:
            url = srv.get("url") or srv.get("github_url") or srv.get("repo") or ""
            if not url:
                continue
            batch.append(QueueItem(
                url=url,
                source="pulsemcp.com",
                priority=Priority.MEDIUM,
                metadata={
                    "name": srv.get("name", ""),
                    "description": srv.get("description", ""),
                    "registry": "pulsemcp.com",
                },
            ))
        return await queue.add_batch(batch)
    except Exception as e:
        logger.warning("pulsemcp.com sync failed: %s", e)
        return 0


# ---------------------------------------------------------------------------
# Source 3: Community Crawl (npm + PyPI)
# ---------------------------------------------------------------------------

async def community_crawl() -> int:
    """Discover MCP tools from npm and PyPI package registries.

    Returns count of items added to queue.
    """
    queue = await get_queue()
    total_added = 0

    async with _http_client() as client:
        total_added += await _crawl_npm(client, queue)
        total_added += await _crawl_pypi(client, queue)

    _stats.record("community_crawl", queued=total_added)
    logger.info("Community crawl: added %d items to queue", total_added)
    return total_added


async def _crawl_npm(client: httpx.AsyncClient, queue: IngestionQueue) -> int:
    """Search npm registry for MCP server packages."""
    search_terms = ["mcp-server", "model-context-protocol", "@modelcontextprotocol"]
    batch: list[QueueItem] = []

    for term in search_terms:
        try:
            resp = await client.get(
                "https://registry.npmjs.org/-/v1/search",
                params={"text": term, "size": 100},
            )
            if resp.status_code != 200:
                logger.warning("npm search returned %d for '%s'", resp.status_code, term)
                continue

            data = resp.json()
            for obj in data.get("objects", []):
                pkg = obj.get("package", {})
                name = pkg.get("name", "")
                npm_url = f"https://www.npmjs.com/package/{name}"

                # Prefer GitHub repo link if available
                repo_url = ""
                links = pkg.get("links", {})
                repo_url = links.get("repository") or links.get("homepage") or ""

                batch.append(QueueItem(
                    url=repo_url or npm_url,
                    source="npm",
                    priority=Priority.MEDIUM,
                    metadata={
                        "name": name,
                        "description": pkg.get("description", ""),
                        "version": pkg.get("version", ""),
                        "npm_url": npm_url,
                        "package_manager": "npm",
                    },
                ))

        except httpx.HTTPError as e:
            logger.warning("npm crawl HTTP error for '%s': %s", term, e)
        except Exception as e:
            logger.warning("npm crawl error for '%s': %s", term, e)

    added = await queue.add_batch(batch)
    return added


async def _crawl_pypi(client: httpx.AsyncClient, queue: IngestionQueue) -> int:
    """Search PyPI for MCP server packages via the JSON API and simple search."""
    search_terms = ["mcp-server", "mcp server", "model-context-protocol"]
    batch: list[QueueItem] = []

    for term in search_terms:
        try:
            # PyPI doesn't have a great search API, use the warehouse search endpoint
            resp = await client.get(
                "https://pypi.org/search/",
                params={"q": term},
                headers={"Accept": "text/html"},
            )
            if resp.status_code != 200:
                logger.warning("PyPI search returned %d for '%s'", resp.status_code, term)
                continue

            # Extract package names from search results HTML
            # Pattern: /project/{package_name}/
            html = resp.text
            pkg_pattern = re.compile(r'href="/project/([^/"]+)/"')
            found_names = set(pkg_pattern.findall(html))

            for pkg_name in list(found_names)[:50]:  # Cap at 50 per term
                pypi_url = f"https://pypi.org/project/{pkg_name}/"
                batch.append(QueueItem(
                    url=pypi_url,
                    source="pypi",
                    priority=Priority.MEDIUM,
                    metadata={
                        "name": pkg_name,
                        "pypi_url": pypi_url,
                        "package_manager": "pypi",
                    },
                ))

        except httpx.HTTPError as e:
            logger.warning("PyPI crawl HTTP error for '%s': %s", term, e)
        except Exception as e:
            logger.warning("PyPI crawl error for '%s': %s", term, e)

    added = await queue.add_batch(batch)
    return added


# ---------------------------------------------------------------------------
# Process Pipeline
# ---------------------------------------------------------------------------

async def process_queue(
    batch_size: int = 20,
    existing_urls_fn: Callable[[], set[str]] | None = None,
) -> dict[str, int]:
    """Process a batch of queued items through the ingestion pipeline.

    Steps per item:
      1. Validate URL (HEAD request)
      2. Check if already in catalog
      3. Extract metadata
      4. Score the tool
      5. Quality gate (score > 10)
      6. Add to collected tools catalog

    Args:
        batch_size: Number of items to process per run.
        existing_urls_fn: Callable returning set of URLs already in catalog.

    Returns:
        Dict with counts: indexed, skipped, failed.
    """
    queue = await get_queue()
    batch = await queue.next_batch(batch_size)

    if not batch:
        logger.info("Process queue: nothing to process")
        return {"indexed": 0, "skipped": 0, "failed": 0}

    # Build existing URL set once
    existing_urls: set[str] = set()
    if existing_urls_fn is not None:
        try:
            existing_urls = existing_urls_fn()
        except Exception as e:
            logger.warning("Failed to get existing URLs: %s", e)

    results = {"indexed": 0, "skipped": 0, "failed": 0}

    async with _http_client() as client:
        for item in batch:
            try:
                result = await _process_single(client, item, existing_urls)
                if result == "indexed":
                    results["indexed"] += 1
                    await queue.remove(item.url)
                elif result == "skipped":
                    results["skipped"] += 1
                    await queue.remove(item.url)
                else:  # "failed"
                    results["failed"] += 1
                    await queue.mark_retry(item.url)
            except Exception as e:
                logger.error("Unexpected error processing %s: %s", item.url, e)
                results["failed"] += 1
                await queue.mark_retry(item.url)

    _stats.record(
        "process_pipeline",
        processed=len(batch),
        indexed=results["indexed"],
        skipped=results["skipped"],
        failed=results["failed"],
    )

    await queue.save()
    logger.info(
        "Process queue: %d indexed, %d skipped, %d failed (of %d)",
        results["indexed"], results["skipped"], results["failed"], len(batch),
    )
    return results


async def _process_single(
    client: httpx.AsyncClient,
    item: QueueItem,
    existing_urls: set[str],
) -> str:
    """Process a single queue item. Returns 'indexed', 'skipped', or 'failed'."""

    normalized = _normalize_url(item.url)

    # 1. Check duplicate against existing catalog
    if normalized in existing_urls:
        logger.debug("Skipping duplicate: %s", item.url)
        return "skipped"

    # 2. Validate URL is reachable
    try:
        resp = await client.head(item.url, follow_redirects=True)
        if resp.status_code >= 400:
            # Try GET as fallback (some servers don't support HEAD)
            resp = await client.get(item.url)
            if resp.status_code >= 400:
                logger.info("URL unreachable (%d): %s", resp.status_code, item.url)
                return "failed"
    except httpx.HTTPError:
        logger.info("URL unreachable (connection error): %s", item.url)
        return "failed"

    # 3. Extract metadata based on URL type
    metadata = dict(item.metadata)
    parsed = urlparse(item.url)
    hostname = (parsed.hostname or "").lower()

    if "github.com" in hostname:
        metadata = await _enrich_github(client, item.url, metadata)
    elif "npmjs.com" in hostname or "npmjs.org" in hostname:
        metadata = await _enrich_npm(client, item.url, metadata)
    elif "pypi.org" in hostname:
        metadata = await _enrich_pypi(client, item.url, metadata)

    # 4. Score the tool
    score = _compute_ingestion_score(metadata)
    metadata["ingestion_score"] = score

    # 5. Quality gate
    if score < 10:
        logger.info("Below quality gate (score=%d): %s", score, item.url)
        return "skipped"

    # 6. Add to collected tools catalog
    tool_entry = _build_tool_entry(item, metadata, score)
    _append_to_catalog(tool_entry)

    # Track the URL as indexed so we don't re-add within the same batch
    existing_urls.add(normalized)

    logger.info("Indexed tool (score=%d): %s", score, metadata.get("name", item.url))
    return "indexed"


async def _enrich_github(client: httpx.AsyncClient, url: str, metadata: dict) -> dict:
    """Enrich metadata from GitHub API."""
    try:
        # Extract owner/repo from URL
        match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", url)
        if not match:
            return metadata
        owner, repo = match.group(1), match.group(2).rstrip(".git")

        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        if resp.status_code != 200:
            return metadata

        data = resp.json()
        metadata.update({
            "name": metadata.get("name") or data.get("name", ""),
            "description": metadata.get("description") or data.get("description") or "",
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "language": data.get("language") or "",
            "license": (data.get("license") or {}).get("spdx_id", ""),
            "topics": data.get("topics", []),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "pushed_at": data.get("pushed_at", ""),
            "has_readme": True,  # GitHub repos generally have one
            "github_owner": owner,
            "github_repo": repo,
        })
    except Exception as e:
        logger.debug("GitHub enrichment failed for %s: %s", url, e)
    return metadata


async def _enrich_npm(client: httpx.AsyncClient, url: str, metadata: dict) -> dict:
    """Enrich metadata from npm registry."""
    try:
        # Extract package name from URL
        match = re.match(r"https?://(?:www\.)?npmjs\.com/package/(.+)", url)
        if not match:
            return metadata
        pkg_name = match.group(1).strip("/")

        resp = await client.get(f"https://registry.npmjs.org/{pkg_name}/latest")
        if resp.status_code != 200:
            return metadata

        data = resp.json()
        metadata.update({
            "name": metadata.get("name") or data.get("name", ""),
            "description": metadata.get("description") or data.get("description") or "",
            "version": data.get("version", ""),
            "license": data.get("license") or "",
            "keywords": data.get("keywords", []),
            "has_readme": bool(data.get("readme")),
        })

        # Extract repo URL
        repo = data.get("repository", {})
        if isinstance(repo, dict) and repo.get("url"):
            repo_url = repo["url"]
            # Clean git+https:// prefixes
            repo_url = re.sub(r"^git\+", "", repo_url)
            repo_url = re.sub(r"\.git$", "", repo_url)
            metadata["repository_url"] = repo_url
    except Exception as e:
        logger.debug("npm enrichment failed for %s: %s", url, e)
    return metadata


async def _enrich_pypi(client: httpx.AsyncClient, url: str, metadata: dict) -> dict:
    """Enrich metadata from PyPI JSON API."""
    try:
        match = re.match(r"https?://pypi\.org/project/([^/]+)", url)
        if not match:
            return metadata
        pkg_name = match.group(1)

        resp = await client.get(f"https://pypi.org/pypi/{pkg_name}/json")
        if resp.status_code != 200:
            return metadata

        data = resp.json()
        info = data.get("info", {})
        metadata.update({
            "name": metadata.get("name") or info.get("name", ""),
            "description": metadata.get("description") or info.get("summary") or "",
            "version": info.get("version", ""),
            "license": info.get("license") or "",
            "keywords": (info.get("keywords") or "").split(",") if info.get("keywords") else [],
            "has_readme": bool(info.get("description")),
            "author": info.get("author") or "",
        })

        # Extract project URLs
        project_urls = info.get("project_urls") or {}
        for key in ("Repository", "Source", "Homepage", "GitHub"):
            if key in project_urls:
                metadata["repository_url"] = project_urls[key]
                break
    except Exception as e:
        logger.debug("PyPI enrichment failed for %s: %s", url, e)
    return metadata


def _compute_ingestion_score(metadata: dict[str, Any]) -> int:
    """Compute a simplified quality score for ingested tools.

    Scoring breakdown (0-100):
      - Description quality: 0-20
      - Ecosystem signals: 0-20 (stars, downloads, keywords)
      - Documentation: 0-20 (readme, license)
      - MCP relevance: 0-25 (name/topic/keyword match)
      - Freshness: 0-15 (recently updated)
    """
    score = 0
    desc = metadata.get("description", "")
    name = metadata.get("name", "")

    # --- Description quality (0-20) ---
    if desc:
        word_count = len(desc.split())
        if word_count >= 20:
            score += 15
        elif word_count >= 10:
            score += 10
        elif word_count >= 3:
            score += 5
        # Bonus for mentioning key concepts
        desc_lower = desc.lower()
        if any(kw in desc_lower for kw in ("mcp", "model context protocol", "ai agent", "tool")):
            score += 5

    # --- Ecosystem signals (0-20) ---
    stars = metadata.get("stars", 0)
    if stars >= 100:
        score += 10
    elif stars >= 20:
        score += 7
    elif stars >= 5:
        score += 4
    elif stars >= 1:
        score += 2

    forks = metadata.get("forks", 0)
    if forks >= 10:
        score += 5
    elif forks >= 3:
        score += 3
    elif forks >= 1:
        score += 1

    keywords = metadata.get("keywords", []) + metadata.get("topics", [])
    if keywords:
        score += min(5, len(keywords))

    # --- Documentation (0-20) ---
    if metadata.get("has_readme"):
        score += 10
    license_val = metadata.get("license", "")
    if license_val and license_val.lower() not in ("", "unknown", "none", "noassertion"):
        score += 5
    if metadata.get("repository_url") or "github.com" in metadata.get("url", ""):
        score += 5

    # --- MCP relevance (0-25) ---
    name_lower = (name or "").lower()
    combined = f"{name_lower} {desc.lower()} {' '.join(str(k).lower() for k in keywords)}"
    mcp_signals = 0
    if "mcp" in combined:
        mcp_signals += 10
    if "model-context-protocol" in combined or "model context protocol" in combined:
        mcp_signals += 8
    if any(kw in combined for kw in ("mcp-server", "mcp_server")):
        mcp_signals += 7
    score += min(25, mcp_signals)

    # --- Freshness (0-15) ---
    for date_key in ("pushed_at", "updated_at", "created_at"):
        date_str = metadata.get(date_key, "")
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - dt).days
                if age_days <= 7:
                    score += 15
                elif age_days <= 30:
                    score += 10
                elif age_days <= 90:
                    score += 5
                elif age_days <= 365:
                    score += 2
                break
            except (ValueError, TypeError):
                continue

    return min(100, score)


def _build_tool_entry(item: QueueItem, metadata: dict[str, Any], score: int) -> dict[str, Any]:
    """Build a tool catalog entry from a processed queue item."""
    name = metadata.get("name", "")
    if not name:
        # Derive name from URL
        parsed = urlparse(item.url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        name = path_parts[-1] if path_parts else parsed.hostname or "unknown"

    # Generate a deterministic scan_id
    scan_id = "ingested-" + hashlib.sha256(
        _normalize_url(item.url).encode()
    ).hexdigest()[:12]

    return {
        "scan_id": scan_id,
        "service_name": name,
        "url": item.url,
        "description": metadata.get("description", ""),
        "service_type": _detect_service_type(metadata),
        "clarvia_score": score,
        "source": f"ingestion:{item.source}",
        "ingestion_metadata": {
            "discovered_at": item.submitted_at,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "source": item.source,
            "stars": metadata.get("stars", 0),
            "language": metadata.get("language", ""),
            "license": metadata.get("license", ""),
            "topics": metadata.get("topics", []),
            "package_manager": metadata.get("package_manager", ""),
        },
    }


def _detect_service_type(metadata: dict[str, Any]) -> str:
    """Detect the tool's service type from metadata."""
    combined = " ".join([
        str(metadata.get("name", "")),
        str(metadata.get("description", "")),
        " ".join(str(t) for t in metadata.get("topics", [])),
        " ".join(str(k) for k in metadata.get("keywords", [])),
    ]).lower()

    if any(kw in combined for kw in ("mcp-server", "mcp_server", "model-context-protocol", "mcp server")):
        return "mcp_server"
    if any(kw in combined for kw in ("cli", "command-line", "command line")):
        return "cli"
    if any(kw in combined for kw in ("api", "rest", "graphql", "grpc")):
        return "api"
    if any(kw in combined for kw in ("sdk", "library", "package")):
        return "sdk"
    return "mcp_server"  # Default for ingestion pipeline (MCP-focused)


def _append_to_catalog(tool: dict[str, Any]) -> None:
    """Append a tool entry to the collected tools JSON file."""
    catalog_path = DATA_DIR / "all-agent-tools.json"
    try:
        existing: list[dict[str, Any]] = []
        if catalog_path.exists():
            with open(catalog_path, "r", encoding="utf-8") as f:
                existing = json.load(f)

        # Check for duplicates by scan_id
        existing_ids = {t.get("scan_id") for t in existing}
        if tool["scan_id"] in existing_ids:
            return

        existing.append(tool)

        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        logger.debug("Appended tool %s to catalog", tool["scan_id"])
    except Exception as e:
        logger.error("Failed to append tool to catalog: %s", e)


# ---------------------------------------------------------------------------
# Dead Tool Cleanup
# ---------------------------------------------------------------------------

async def dead_tool_cleanup(
    existing_tools_fn: Callable[[], list[dict[str, Any]]] | None = None,
    max_age_days: int = 90,
) -> dict[str, int]:
    """Archive tools that have been unreachable for too long.

    Probes tools older than max_age_days and marks unreachable ones as archived.

    Args:
        existing_tools_fn: Callable returning list of all tool dicts.
        max_age_days: Only check tools older than this many days.

    Returns:
        Dict with counts: checked, archived.
    """
    if existing_tools_fn is None:
        logger.info("Dead tool cleanup: no tools provider, skipping")
        return {"checked": 0, "archived": 0}

    try:
        tools = existing_tools_fn()
    except Exception as e:
        logger.error("Dead tool cleanup: failed to get tools: %s", e)
        return {"checked": 0, "archived": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    candidates: list[dict[str, Any]] = []

    for tool in tools:
        # Check indexed_at or discovered_at from ingestion metadata
        ingestion_meta = tool.get("ingestion_metadata", {})
        indexed_at = ingestion_meta.get("indexed_at", "")
        if not indexed_at:
            continue
        try:
            dt = datetime.fromisoformat(indexed_at.replace("Z", "+00:00"))
            if dt < cutoff:
                candidates.append(tool)
        except (ValueError, TypeError):
            continue

    if not candidates:
        logger.info("Dead tool cleanup: no tools older than %d days", max_age_days)
        return {"checked": 0, "archived": 0}

    checked = 0
    archived = 0

    async with _http_client() as client:
        for tool in candidates[:50]:  # Cap per run to avoid long operations
            url = tool.get("url", "")
            if not url:
                continue
            checked += 1
            try:
                resp = await client.head(url, follow_redirects=True)
                if resp.status_code >= 400:
                    # Double-check with GET
                    resp = await client.get(url)
                    if resp.status_code >= 400:
                        tool["archived"] = True
                        tool["archived_at"] = datetime.now(timezone.utc).isoformat()
                        tool["archive_reason"] = f"HTTP {resp.status_code}"
                        archived += 1
            except httpx.HTTPError:
                tool["archived"] = True
                tool["archived_at"] = datetime.now(timezone.utc).isoformat()
                tool["archive_reason"] = "unreachable"
                archived += 1
            except Exception:
                pass  # Skip on unexpected errors

    _stats.record("dead_tool_cleanup", processed=checked, skipped=archived)
    logger.info("Dead tool cleanup: checked %d, archived %d", checked, archived)
    return {"checked": checked, "archived": archived}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def run_all_sources() -> dict[str, int]:
    """Run all 4 discovery sources and persist the queue.

    Returns per-source counts of items added to queue.
    """
    logger.info("=== Ingestion pipeline: running all sources ===")
    results: dict[str, int] = {}

    # Run sources concurrently
    tasks = [
        ("github_watcher", github_watcher()),
        ("registry_sync", registry_sync()),
        ("community_crawl", community_crawl()),
    ]

    for name, coro in tasks:
        try:
            count = await coro
            results[name] = count
        except Exception as e:
            logger.error("Source %s failed: %s", name, e)
            results[name] = 0

    # Persist queue after all sources ran
    queue = await get_queue()
    await queue.save()

    total = sum(results.values())
    logger.info(
        "Ingestion sources complete: %d total items queued (%s). Queue size: %d",
        total,
        ", ".join(f"{k}={v}" for k, v in results.items()),
        queue.size,
    )
    return results


async def run_full_pipeline(
    existing_urls_fn: Callable[[], set[str]] | None = None,
    batch_size: int = 20,
) -> dict[str, Any]:
    """Run complete ingestion cycle: discover -> queue -> process.

    Convenience method that runs all sources then processes a batch.
    """
    source_results = await run_all_sources()
    process_results = await process_queue(
        batch_size=batch_size,
        existing_urls_fn=existing_urls_fn,
    )

    return {
        "sources": source_results,
        "processing": process_results,
        "stats": get_ingestion_stats(),
    }
