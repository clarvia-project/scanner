#!/usr/bin/env python3
"""Batch probe top tools for liveness and feature detection.

Usage:
    python3 scripts/batch_probe.py [--limit 100] [--concurrency 10]
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.live_prober import probe_batch, load_probe_cache, save_probe_cache


async def main():
    limit = 100
    concurrency = 10

    args = sys.argv[1:]
    if "--limit" in args:
        idx = args.index("--limit")
        limit = int(args[idx + 1])
    if "--concurrency" in args:
        idx = args.index("--concurrency")
        concurrency = int(args[idx + 1])

    # Load services
    data_dir = Path(__file__).resolve().parent.parent / "backend" / "data"
    scans_file = data_dir / "prebuilt-scans.json"

    with open(scans_file) as f:
        services = json.load(f)

    # Sort by score, take top N with valid URLs
    services = [s for s in services if s.get("url", "").startswith("http")]
    services.sort(key=lambda s: s.get("clarvia_score", 0), reverse=True)
    services = services[:limit]

    print(f"Probing top {len(services)} services (concurrency={concurrency})...")

    load_probe_cache()
    results = await probe_batch(services, concurrency=concurrency)

    reachable = sum(1 for r in results if r.get("reachable"))
    fast = sum(1 for r in results if (r.get("response_time_ms") or 99999) < 500)
    has_openapi = sum(1 for r in results if r.get("has_openapi"))
    has_agents = sum(1 for r in results if r.get("has_agents_json"))

    print(f"\nResults:")
    print(f"  Reachable: {reachable}/{len(results)}")
    print(f"  Fast (<500ms): {fast}/{len(results)}")
    print(f"  Has OpenAPI: {has_openapi}")
    print(f"  Has agents.json: {has_agents}")
    print(f"\nCache saved to probe-cache.json")


if __name__ == "__main__":
    asyncio.run(main())
