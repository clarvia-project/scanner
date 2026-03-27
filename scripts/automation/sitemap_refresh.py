#!/usr/bin/env python3
"""Sitemap Refresh — Rebuild XML sitemaps from current catalog.

Pulls all tool IDs from the backend API, generates XML sitemaps in
batches of 1000 URLs (sitemap file limit), and pings Google/Bing
IndexNow for faster crawling.

Sitemaps are written to:
    frontend/public/sitemap-tools-{N}.xml  (tool profiles)
    frontend/public/sitemap-main.xml       (static pages)
    frontend/public/sitemap.xml            (sitemap index)

Usage:
    python scripts/automation/sitemap_refresh.py [--dry-run]
"""

import argparse
import json
import logging
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_PUBLIC = PROJECT_ROOT / "frontend" / "public"
DATA_DIR = PROJECT_ROOT / "data"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from telegram_notifier import send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SITE_BASE = "https://clarvia.art"
API_BASE = "https://clarvia-api.onrender.com"
URLS_PER_FILE = 1000


STATIC_PAGES = [
    ("", "daily", "1.0"),
    ("/tools", "daily", "0.9"),
    ("/scan", "weekly", "0.8"),
    ("/leaderboard", "daily", "0.8"),
    ("/methodology", "monthly", "0.7"),
    ("/for-agents", "monthly", "0.8"),
    ("/compare", "weekly", "0.7"),
    ("/trending", "daily", "0.8"),
    ("/categories", "weekly", "0.7"),
    ("/about", "monthly", "0.5"),
    ("/pricing", "monthly", "0.5"),
    ("/api", "monthly", "0.6"),
]


def fetch_all_tool_slugs() -> list[str]:
    """Fetch all tool slugs from the backend API."""
    slugs = []
    page = 0
    limit = 100  # API max limit per request

    while True:
        try:
            offset = page * limit
            url = f"{API_BASE}/v1/services?limit={limit}&offset={offset}"
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                logger.warning("API returned %d at page %d (offset=%d)", resp.status_code, page, offset)
                break

            data = resp.json()
            # API returns {"total": N, "services": [...]} or {"total": N, "items": [...]}
            items = data.get("services", data.get("items", []))
            if not items:
                break

            for item in items:
                # Use scan_id (scn_xxx) or name as slug
                scan_id = item.get("scan_id", "")
                name = item.get("name", "").lower().replace(" ", "-")
                slug = scan_id or name
                if slug:
                    slugs.append(slug)

            total = data.get("total", 0)
            logger.info("Page %d (offset=%d): +%d slugs, total_collected=%d/%d", page, offset, len(items), len(slugs), total)

            if len(slugs) >= total or len(items) < limit:
                break
            page += 1

        except Exception as exc:
            logger.error("Failed to fetch page %d: %s", page, exc)
            break

    logger.info("Total slugs fetched: %d", len(slugs))
    return slugs


def build_url_entry(loc: str, changefreq: str = "weekly", priority: str = "0.7") -> str:
    return f"  <url><loc>{loc}</loc><changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>"


def write_sitemap_file(path: Path, url_entries: list[str]) -> None:
    content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    content += "\n".join(url_entries)
    content += "\n</urlset>"
    path.write_text(content, encoding="utf-8")
    logger.info("Written %s (%d URLs)", path.name, len(url_entries))


def write_sitemap_index(path: Path, sitemap_paths: list[str], lastmod: str) -> None:
    content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    content += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for sp in sitemap_paths:
        content += f"  <sitemap><loc>{SITE_BASE}/{sp}</loc><lastmod>{lastmod}</lastmod></sitemap>\n"
    content += "</sitemapindex>"
    path.write_text(content, encoding="utf-8")
    logger.info("Written sitemap index with %d sitemaps", len(sitemap_paths))


def ping_search_engines(sitemap_url: str) -> None:
    """Ping Google and Bing with updated sitemap URL."""
    endpoints = [
        f"https://www.google.com/ping?sitemap={sitemap_url}",
        f"https://www.bing.com/ping?sitemap={sitemap_url}",
    ]
    for endpoint in endpoints:
        try:
            resp = requests.get(endpoint, timeout=10)
            logger.info("Pinged %s: %d", endpoint.split("//")[1].split("/")[0], resp.status_code)
        except Exception as exc:
            logger.warning("Ping failed for %s: %s", endpoint, exc)


def run(dry_run: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    lastmod = now.strftime("%Y-%m-%d")
    logger.info("=== Sitemap Refresh: %s ===", now.isoformat())

    # 1. Fetch all tool slugs
    slugs = fetch_all_tool_slugs()
    if not slugs:
        logger.warning("No slugs fetched — aborting sitemap refresh")
        return {"error": "no_slugs"}

    # 2. Build static pages sitemap
    static_entries = [
        build_url_entry(f"{SITE_BASE}{path}", freq, pri)
        for path, freq, pri in STATIC_PAGES
    ]
    static_sitemap_name = "sitemap-main.xml"

    # 3. Build tool sitemaps in batches
    num_files = math.ceil(len(slugs) / URLS_PER_FILE)
    tool_sitemap_names = []

    if not dry_run:
        FRONTEND_PUBLIC.mkdir(parents=True, exist_ok=True)

        write_sitemap_file(FRONTEND_PUBLIC / static_sitemap_name, static_entries)

        for i in range(num_files):
            batch = slugs[i * URLS_PER_FILE : (i + 1) * URLS_PER_FILE]
            entries = [
                build_url_entry(f"{SITE_BASE}/tool/{slug}", "weekly", "0.7")
                for slug in batch
            ]
            fname = f"sitemap-tools-{i + 1}.xml"
            write_sitemap_file(FRONTEND_PUBLIC / fname, entries)
            tool_sitemap_names.append(fname)

        # 4. Write sitemap index
        all_sitemaps = [static_sitemap_name] + tool_sitemap_names
        write_sitemap_index(FRONTEND_PUBLIC / "sitemap.xml", all_sitemaps, lastmod)

        # 5. Ping search engines
        ping_search_engines(f"{SITE_BASE}/sitemap.xml")

    result = {
        "timestamp": now.isoformat(),
        "total_tools": len(slugs),
        "sitemap_files": num_files + 1,  # +1 for static
        "dry_run": dry_run,
    }

    try:
        send_message(
            f"[Sitemap Refresh] {lastmod}\n"
            f"Tools: {len(slugs)} | Files: {num_files + 1} | "
            f"{'DRY RUN' if dry_run else 'Updated + pinged Google/Bing'}"
        )
    except Exception:
        pass

    logger.info("Sitemap refresh complete: %s", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clarvia Sitemap Refresh")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
