#!/usr/bin/env python3
"""Dead link cleanup automation for Clarvia catalog.

Iterates through all indexed tools and checks URL health:
  - alive (200-399): no action
  - redirect (301/302): update URL if new destination is valid
  - dead (404/5xx/timeout): mark as inactive after 2 consecutive weekly failures

Results stored in: data/link_checks/YYYY-MM-DD.json

Usage:
    python scripts/automation/dead_link_cleaner.py [--dry-run] [--concurrency N]
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from telegram_notifier import send_alert

logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"
LINK_CHECK_DIR = DATA_DIR / "link_checks"
CATALOG_PATH = DATA_DIR / "prebuilt-scans.json"

CHECK_TIMEOUT = 10  # seconds per URL
DEFAULT_CONCURRENCY = 20
CONSECUTIVE_FAILURES_THRESHOLD = 2  # mark inactive after N consecutive dead checks


def _load_catalog() -> list[dict[str, Any]]:
    """Load current catalog."""
    if not CATALOG_PATH.exists():
        return []
    with open(CATALOG_PATH) as f:
        return json.load(f)


def _load_previous_checks() -> dict[str, dict[str, Any]]:
    """Load most recent link check results for consecutive failure tracking."""
    if not LINK_CHECK_DIR.exists():
        return {}

    checks = sorted(LINK_CHECK_DIR.glob("*.json"), reverse=True)
    for cp in checks:
        try:
            with open(cp) as f:
                data = json.load(f)
                # Build URL -> check result mapping
                results: dict[str, dict[str, Any]] = {}
                for item in data.get("results", []):
                    url = item.get("url", "")
                    if url:
                        results[url] = item
                return results
        except (json.JSONDecodeError, OSError):
            continue
    return {}


async def check_url(
    session: aiohttp.ClientSession, url: str
) -> dict[str, Any]:
    """Check a single URL and classify its status."""
    result: dict[str, Any] = {
        "url": url,
        "status": "unknown",
        "status_code": 0,
        "redirect_url": None,
        "error": None,
        "response_time_ms": 0,
    }

    try:
        start = asyncio.get_event_loop().time()
        async with session.head(
            url,
            timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT),
            allow_redirects=False,
        ) as resp:
            elapsed = (asyncio.get_event_loop().time() - start) * 1000
            result["status_code"] = resp.status
            result["response_time_ms"] = round(elapsed, 1)

            if 200 <= resp.status < 400:
                if resp.status in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location", "")
                    result["status"] = "redirect"
                    result["redirect_url"] = location
                else:
                    result["status"] = "alive"
            elif resp.status == 405:
                # HEAD not allowed, try GET
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT),
                    allow_redirects=False,
                ) as get_resp:
                    result["status_code"] = get_resp.status
                    if 200 <= get_resp.status < 400:
                        result["status"] = "alive"
                    else:
                        result["status"] = "dead"
            else:
                result["status"] = "dead"

    except asyncio.TimeoutError:
        result["status"] = "dead"
        result["error"] = "timeout"
    except aiohttp.ClientError as exc:
        result["status"] = "dead"
        result["error"] = str(exc)[:200]
    except Exception as exc:
        result["status"] = "dead"
        result["error"] = f"unexpected: {exc}"[:200]

    return result


async def check_all_urls(
    urls: list[str], concurrency: int
) -> list[dict[str, Any]]:
    """Check all URLs with bounded concurrency."""
    semaphore = asyncio.Semaphore(concurrency)
    results = []

    async def _bounded_check(session: aiohttp.ClientSession, url: str) -> dict[str, Any]:
        async with semaphore:
            return await check_url(session, url)

    connector = aiohttp.TCPConnector(limit=concurrency, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [_bounded_check(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to error results
    cleaned = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            cleaned.append({
                "url": urls[i],
                "status": "dead",
                "status_code": 0,
                "error": str(r)[:200],
                "redirect_url": None,
                "response_time_ms": 0,
            })
        else:
            cleaned.append(r)

    return cleaned


def classify_results(
    results: list[dict[str, Any]],
    previous: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Classify results and determine which tools should be marked inactive."""
    alive = []
    redirects = []
    dead = []
    newly_inactive = []

    for r in results:
        url = r["url"]
        status = r["status"]

        if status == "alive":
            alive.append(r)
        elif status == "redirect":
            redirects.append(r)
        elif status == "dead":
            dead.append(r)

            # Check consecutive failure count
            prev = previous.get(url, {})
            prev_failures = prev.get("consecutive_failures", 0)
            if prev.get("status") == "dead":
                r["consecutive_failures"] = prev_failures + 1
            else:
                r["consecutive_failures"] = 1

            if r["consecutive_failures"] >= CONSECUTIVE_FAILURES_THRESHOLD:
                newly_inactive.append(r)
        else:
            dead.append(r)

    return {
        "alive": alive,
        "redirects": redirects,
        "dead": dead,
        "newly_inactive": newly_inactive,
    }


def update_catalog_status(
    catalog: list[dict[str, Any]],
    newly_inactive: list[dict[str, Any]],
    redirects: list[dict[str, Any]],
    dry_run: bool,
) -> int:
    """Update catalog entries for dead/redirected URLs."""
    inactive_urls = {r["url"] for r in newly_inactive}
    redirect_map = {
        r["url"]: r["redirect_url"]
        for r in redirects
        if r.get("redirect_url")
    }

    changes = 0
    for service in catalog:
        url = service.get("url", "")

        # Mark dead links as inactive
        if url in inactive_urls:
            if not service.get("inactive"):
                service["inactive"] = True
                service["inactive_reason"] = "dead_link"
                service["inactive_since"] = datetime.now(timezone.utc).isoformat()
                changes += 1

        # Update redirected URLs
        if url in redirect_map:
            new_url = redirect_map[url]
            if new_url and new_url.startswith("http"):
                service["url"] = new_url
                service["previous_url"] = url
                changes += 1

    if changes > 0 and not dry_run:
        with open(CATALOG_PATH, "w") as f:
            json.dump(catalog, f, indent=2)
        logger.info("Updated %d catalog entries", changes)

    return changes


def format_report(
    classification: dict[str, Any], changes: int, total: int
) -> str:
    """Format Telegram report message."""
    alive = len(classification["alive"])
    redirects = len(classification["redirects"])
    dead = len(classification["dead"])
    inactive = len(classification["newly_inactive"])

    lines = [
        "🔗 *Clarvia Link Check Report*",
        "",
        f"Total checked: {total}",
        f"✅ Alive: {alive}",
        f"↪️ Redirects: {redirects}",
        f"❌ Dead: {dead}",
        f"🚫 Newly inactive: {inactive}",
        f"📝 Catalog changes: {changes}",
    ]

    if classification["newly_inactive"]:
        lines.append("\n*Newly Inactive:*")
        for r in classification["newly_inactive"][:10]:
            lines.append(f"  • {r['url'][:60]} ({r.get('error', 'dead')})")

    return "\n".join(lines)


async def run(concurrency: int, dry_run: bool) -> int:
    """Main async runner."""
    catalog = _load_catalog()
    if not catalog:
        logger.warning("Empty catalog")
        return 0

    # Extract unique URLs
    urls = list({s.get("url", "") for s in catalog if s.get("url")})
    logger.info("Checking %d unique URLs (concurrency=%d)", len(urls), concurrency)

    # Load previous results
    previous = _load_previous_checks()

    # Run checks
    results = await check_all_urls(urls, concurrency)

    # Classify
    classification = classify_results(results, previous)

    # Update catalog
    changes = update_catalog_status(
        catalog,
        classification["newly_inactive"],
        classification["redirects"],
        dry_run,
    )

    # Save results
    LINK_CHECK_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = LINK_CHECK_DIR / f"{today}.json"

    report_data = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total": len(urls),
        "alive": len(classification["alive"]),
        "redirects": len(classification["redirects"]),
        "dead": len(classification["dead"]),
        "newly_inactive": len(classification["newly_inactive"]),
        "catalog_changes": changes,
        "results": results,
    }

    if not dry_run:
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)
        logger.info("Link check report saved to %s", report_path)

    # Telegram report
    msg = format_report(classification, changes, len(urls))
    if not dry_run:
        send_alert("Link Check Complete", msg, level="INFO")
    else:
        logger.info("[DRY RUN]\n%s", msg)

    return 1 if classification["newly_inactive"] else 0


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Clarvia dead link cleaner")
    parser.add_argument("--dry-run", action="store_true", help="Skip writes and alerts")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Concurrent URL checks (default: {DEFAULT_CONCURRENCY})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    return asyncio.run(run(args.concurrency, args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
