#!/usr/bin/env python3
"""Batch fetch popularity data (npm downloads, GitHub stars) for top tools.

Run daily via scheduled task. Respects API rate limits.

Usage:
    python3 scripts/batch_popularity.py [--limit 500]
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import aiohttp
from app.services.popularity_service import (
    fetch_npm_downloads, fetch_github_stars, fetch_pypi_downloads,
    compute_popularity_score, _CACHE_FILE,
)


async def main():
    limit = 500
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    # Load services
    data_dir = Path(__file__).resolve().parent.parent / "backend" / "data"
    scans_file = data_dir / "prebuilt-scans.json"

    if not scans_file.exists():
        print("ERROR: prebuilt-scans.json not found")
        sys.exit(1)

    with open(scans_file) as f:
        services = json.load(f)

    # Sort by score descending, take top N
    services.sort(key=lambda s: s.get("clarvia_score", 0), reverse=True)
    services = services[:limit]

    print(f"Fetching popularity for top {len(services)} services...")

    github_token = os.environ.get("GITHUB_TOKEN")
    cache = {}

    # Load existing cache
    if _CACHE_FILE.exists():
        with open(_CACHE_FILE) as f:
            cache = json.load(f)

    async with aiohttp.ClientSession() as session:
        fetched = 0
        for i, svc in enumerate(services):
            scan_id = svc.get("scan_id", "")
            name = svc.get("service_name", "")
            url = svc.get("url", "")
            cross_refs = svc.get("cross_refs", {})

            npm_downloads = None
            github_stars = None
            pypi_downloads = None

            # npm downloads
            npm_pkg = cross_refs.get("npm", "") or ""
            if "npmjs.com/package/" in npm_pkg:
                pkg_name = npm_pkg.split("/package/")[-1].split("/")[0]
                npm_downloads = await fetch_npm_downloads(pkg_name, session)
            elif "npmjs.com" in url:
                pkg_name = url.split("/package/")[-1].split("/")[0] if "/package/" in url else name
                npm_downloads = await fetch_npm_downloads(pkg_name, session)

            # GitHub stars
            github_url = cross_refs.get("github", "") or ""
            if not github_url and "github.com" in url:
                github_url = url
            if github_url and "github.com" in github_url:
                github_stars = await fetch_github_stars(github_url, session, github_token)

            # PyPI
            pypi_url = cross_refs.get("pypi", "") or ""
            if "pypi.org" in pypi_url:
                pkg_name = pypi_url.split("/project/")[-1].strip("/") if "/project/" in pypi_url else ""
                if pkg_name:
                    pypi_downloads = await fetch_pypi_downloads(pkg_name, session)

            popularity_score = compute_popularity_score(npm_downloads, github_stars, pypi_downloads)

            cache[scan_id] = {
                "npm_weekly": npm_downloads,
                "github_stars": github_stars,
                "pypi_weekly": pypi_downloads,
                "popularity_score": popularity_score,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

            fetched += 1
            if fetched % 50 == 0:
                print(f"  Fetched {fetched}/{len(services)}...")
                # Rate limit: ~50 requests per batch, small delay
                await asyncio.sleep(1)

    # Save cache
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_FILE, "w") as f:
        json.dump(cache, f, separators=(",", ":"), ensure_ascii=False)

    non_zero = sum(1 for v in cache.values() if v.get("popularity_score", 0) > 0)
    print(f"\nDone! Cached {len(cache)} entries ({non_zero} with non-zero popularity)")


if __name__ == "__main__":
    asyncio.run(main())
