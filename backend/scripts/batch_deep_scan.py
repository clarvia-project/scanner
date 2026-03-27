#!/usr/bin/env python3
"""Batch deep-scan all tools that lack dimension scores.

Calls the local scan engine directly (not HTTP) to fill in dimensions
for all tools in prebuilt-scans.json that only have metadata-based scores.

Usage:
    cd scanner/backend
    python scripts/batch_deep_scan.py
    python scripts/batch_deep_scan.py --workers 20 --limit 1000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add parent dirs for imports
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("batch_scan")


def find_data_dir() -> Path:
    for p in [BACKEND_DIR.parent / "data", BACKEND_DIR / "data", Path("/app/data")]:
        if p.is_dir():
            return p
    raise FileNotFoundError("Could not find data directory")


def load_prebuilt(data_dir: Path) -> list[dict]:
    fp = data_dir / "prebuilt-scans.json"
    if not fp.exists():
        raise FileNotFoundError(f"{fp} not found")
    data = json.load(open(fp))
    return data if isinstance(data, list) else data.get("services", [])


def needs_scan(tool: dict) -> bool:
    """Check if tool needs dimension scoring."""
    dims = tool.get("dimensions", {})
    # Has no dimensions or dimensions is empty
    if not dims:
        return True
    # Has dimensions but they're empty (no actual dimension keys)
    if not any(k in dims for k in ["api_accessibility", "data_structuring",
                                     "agent_compatibility", "trust_signals"]):
        return True
    return False


async def scan_one(tool: dict, semaphore: asyncio.Semaphore, scanner_func) -> dict | None:
    """Scan a single tool, return updated tool or None on failure."""
    url = tool.get("url", "")
    name = tool.get("name", "unknown")
    if not url:
        return None

    async with semaphore:
        try:
            # Run the sync scanner in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, scanner_func, url)

            if result and result.get("dimensions"):
                # Merge dimensions into existing tool
                tool["dimensions"] = result["dimensions"]
                # Update score from scan if available
                if result.get("score") is not None:
                    tool["clarvia_score"] = result["score"]
                # Update rating
                score = tool.get("clarvia_score", 0)
                if score >= 70:
                    tool["rating"] = "Strong"
                elif score >= 40:
                    tool["rating"] = "Moderate"
                elif score >= 20:
                    tool["rating"] = "Basic"
                else:
                    tool["rating"] = "Low"
                tool["last_scanned"] = datetime.now(timezone.utc).isoformat()
                return tool
        except Exception as e:
            logger.debug(f"Failed to scan {name} ({url}): {e}")
    return None


def create_scanner():
    """Create the scan function. Uses HTTP API (local or remote)."""
    import urllib.request

    # Use production API by default, local if running
    api_base = "https://clarvia-api.onrender.com"

    def do_scan(url: str) -> dict | None:
        try:
            payload = json.dumps({"url": url}).encode()
            req = urllib.request.Request(
                f"{api_base}/api/scan",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                if data.get("dimensions"):
                    return data
                return None
        except Exception:
            return None
    return do_scan


async def run_batch(
    tools: list[dict],
    workers: int = 10,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run batch scanning."""
    to_scan = [t for t in tools if needs_scan(t)]
    if limit:
        to_scan = to_scan[:limit]

    total = len(to_scan)
    logger.info(f"Tools needing scan: {total} (of {len(tools)} total)")
    if dry_run:
        logger.info("DRY RUN — no scanning performed")
        return {"total": total, "scanned": 0, "dry_run": True}

    scanner = create_scanner()
    semaphore = asyncio.Semaphore(workers)

    scanned = 0
    failed = 0
    start = time.time()

    # Process in batches of 100 for progress reporting
    batch_size = 100
    for i in range(0, total, batch_size):
        batch = to_scan[i:i + batch_size]
        tasks = [scan_one(t, semaphore, scanner) for t in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, dict):
                scanned += 1
            elif r is None or isinstance(r, Exception):
                failed += 1

        elapsed = time.time() - start
        rate = (i + len(batch)) / elapsed if elapsed > 0 else 0
        remaining = (total - i - len(batch)) / rate if rate > 0 else 0
        logger.info(
            f"Progress: {i + len(batch)}/{total} "
            f"(scanned: {scanned}, failed: {failed}) "
            f"[{rate:.1f}/s, ~{remaining/60:.0f}m remaining]"
        )

    elapsed = time.time() - start
    return {
        "total": total,
        "scanned": scanned,
        "failed": failed,
        "elapsed_seconds": round(elapsed, 1),
        "rate_per_second": round(total / elapsed, 2) if elapsed > 0 else 0,
    }


def save_tools(tools: list[dict], data_dir: Path):
    """Save updated tools back to prebuilt-scans.json."""
    fp = data_dir / "prebuilt-scans.json"
    # Backup
    backup = data_dir / f"prebuilt-scans.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    if fp.exists():
        import shutil
        shutil.copy2(fp, backup)
        logger.info(f"Backup saved to {backup.name}")

    json.dump(tools, open(fp, "w"), ensure_ascii=False, separators=(",", ":"))
    logger.info(f"Saved {len(tools)} tools to {fp}")

    # Sync to frontend
    frontend_dir = data_dir.parent.parent / "frontend" / "public" / "data"
    if frontend_dir.exists():
        import shutil
        shutil.copy2(fp, frontend_dir / "prebuilt-scans.json")
        logger.info("Synced to frontend/public/data/")


def main():
    parser = argparse.ArgumentParser(description="Batch deep-scan tools")
    parser.add_argument("--workers", type=int, default=10, help="Parallel workers")
    parser.add_argument("--limit", type=int, default=None, help="Max tools to scan")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no scanning")
    args = parser.parse_args()

    data_dir = find_data_dir()
    tools = load_prebuilt(data_dir)

    logger.info(f"Loaded {len(tools)} tools from prebuilt-scans.json")
    logger.info(f"Workers: {args.workers}, Limit: {args.limit or 'all'}")

    result = asyncio.run(run_batch(tools, args.workers, args.limit, args.dry_run))
    logger.info(f"Result: {json.dumps(result, indent=2)}")

    if not args.dry_run and result.get("scanned", 0) > 0:
        save_tools(tools, data_dir)

    # Summary
    final_with_dims = sum(1 for t in tools if not needs_scan(t))
    logger.info(f"\nFinal state: {final_with_dims}/{len(tools)} tools have dimensions ({final_with_dims/len(tools)*100:.1f}%)")


if __name__ == "__main__":
    main()
