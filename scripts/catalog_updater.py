#!/usr/bin/env python3
"""Clarvia Catalog Auto-Updater.

Keeps the tool catalog fresh by:
1. Pulling new tools from MCP Registry API
2. Re-scanning existing tools on a schedule
3. Detecting dead/unreachable services
4. Updating scores and ratings

Designed to run as a cron job or scheduled task.
Usage: python scripts/catalog_updater.py [--mode full|incremental|registry-sync]
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

API_BASE = "https://clarvia-api.onrender.com"
MCP_REGISTRY_API = "https://registry.modelcontextprotocol.io/v0/servers"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PREBUILT_PATH = DATA_DIR / "prebuilt-scans.json"
REGISTRY_PATH = DATA_DIR / "mcp-registry-all.json"
UPDATE_LOG_PATH = DATA_DIR / "catalog-update-log.json"

MAX_CONCURRENT = 3
SCAN_TIMEOUT = 30


async def fetch_mcp_registry() -> list[dict[str, Any]]:
    """Fetch all servers from the official MCP Registry."""
    servers = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(MCP_REGISTRY_API, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        servers = data
                    elif isinstance(data, dict) and "servers" in data:
                        servers = data["servers"]
                    logger.info("Fetched %d servers from MCP Registry", len(servers))
                else:
                    logger.warning("MCP Registry returned %d", resp.status)
    except Exception as e:
        logger.error("Failed to fetch MCP Registry: %s", e)
    return servers


async def scan_url(session: aiohttp.ClientSession, url: str) -> dict[str, Any] | None:
    """Scan a single URL via the Clarvia API."""
    try:
        async with session.post(
            f"{API_BASE}/api/scan",
            json={"url": url},
            timeout=aiohttp.ClientTimeout(total=SCAN_TIMEOUT),
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            elif resp.status == 429:
                logger.warning("Rate limited — pausing")
                await asyncio.sleep(60)
                return None
            else:
                logger.warning("Scan failed for %s: HTTP %d", url, resp.status)
                return None
    except Exception as e:
        logger.warning("Scan error for %s: %s", url, e)
        return None


async def rescan_existing(max_items: int = 50) -> dict[str, Any]:
    """Re-scan existing prebuilt services, oldest first."""
    if not PREBUILT_PATH.exists():
        return {"rescanned": 0, "error": "prebuilt-scans.json not found"}

    with open(PREBUILT_PATH) as f:
        services = json.load(f)

    # Sort by scanned_at, oldest first
    services.sort(key=lambda s: s.get("scanned_at", ""))
    to_rescan = services[:max_items]

    updated = 0
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def _scan_one(session: aiohttp.ClientSession, svc: dict) -> dict | None:
        async with semaphore:
            url = svc.get("url", "")
            if not url:
                return None
            result = await scan_url(session, url)
            if result:
                logger.info("Rescanned %s: %d -> %d",
                    url, svc.get("clarvia_score", 0), result.get("clarvia_score", 0))
            return result

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[_scan_one(session, s) for s in to_rescan])

    # Merge results back
    url_to_result = {}
    for r in results:
        if r and r.get("url"):
            url_to_result[r["url"]] = r
            updated += 1

    # Update the services list
    for i, svc in enumerate(services):
        url = svc.get("url", "")
        if url in url_to_result:
            services[i] = url_to_result[url]

    # Save
    with open(PREBUILT_PATH, "w") as f:
        json.dump(services, f, indent=2, default=str)

    return {"rescanned": updated, "total": len(services)}


async def sync_registry() -> dict[str, Any]:
    """Sync new servers from MCP Registry into our catalog."""
    registry_servers = await fetch_mcp_registry()
    if not registry_servers:
        return {"synced": 0, "error": "No servers from registry"}

    # Load existing
    existing_urls = set()
    if PREBUILT_PATH.exists():
        with open(PREBUILT_PATH) as f:
            existing = json.load(f)
        existing_urls = {s.get("url", "").rstrip("/").lower() for s in existing}
    else:
        existing = []

    # Find new servers
    new_servers = []
    for srv in registry_servers:
        url = ""
        if isinstance(srv, dict):
            url = srv.get("url", "") or srv.get("homepage", "") or srv.get("repository", {}).get("url", "")
        if url and url.rstrip("/").lower() not in existing_urls:
            new_servers.append(url)

    logger.info("Found %d new servers to scan", len(new_servers))

    # Scan new servers (limit to 20 per run)
    scanned = 0
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def _scan(session: aiohttp.ClientSession, url: str) -> dict | None:
        async with semaphore:
            return await scan_url(session, url)

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[_scan(session, u) for u in new_servers[:20]])

    for r in results:
        if r:
            existing.append(r)
            scanned += 1

    # Save
    with open(PREBUILT_PATH, "w") as f:
        json.dump(existing, f, indent=2, default=str)

    # Save registry data
    if registry_servers:
        with open(REGISTRY_PATH, "w") as f:
            json.dump(registry_servers, f, indent=2, default=str)

    return {"new_found": len(new_servers), "scanned": scanned}


async def full_update() -> dict[str, Any]:
    """Full catalog update: registry sync + rescan existing."""
    logger.info("Starting full catalog update...")

    sync_result = await sync_registry()
    logger.info("Registry sync: %s", sync_result)

    rescan_result = await rescan_existing(max_items=30)
    logger.info("Rescan: %s", rescan_result)

    summary = {
        "mode": "full",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "registry_sync": sync_result,
        "rescan": rescan_result,
    }

    # Save update log
    log_entries = []
    if UPDATE_LOG_PATH.exists():
        try:
            with open(UPDATE_LOG_PATH) as f:
                log_entries = json.load(f)
        except Exception:
            pass
    log_entries.append(summary)
    log_entries = log_entries[-100:]  # Keep last 100 entries
    with open(UPDATE_LOG_PATH, "w") as f:
        json.dump(log_entries, f, indent=2, default=str)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Clarvia Catalog Updater")
    parser.add_argument(
        "--mode",
        choices=["full", "incremental", "registry-sync"],
        default="full",
        help="Update mode",
    )
    args = parser.parse_args()

    if args.mode == "full":
        result = asyncio.run(full_update())
    elif args.mode == "registry-sync":
        result = asyncio.run(sync_registry())
    elif args.mode == "incremental":
        result = asyncio.run(rescan_existing(max_items=20))

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
