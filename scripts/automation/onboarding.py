#!/usr/bin/env python3
"""Clarvia Auto-Onboarding Pipeline.

Processes the submission queue:
1. Reads pending submissions from data/submissions.jsonl
2. Auto-scans submitted tool URLs via the Clarvia API
3. Auto-indexes tools with score > 0
4. Generates badge embed code for tool makers

Usage:
    python scripts/automation/onboarding.py [--max N] [--dry-run]
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

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SUBMISSIONS_PATH = DATA_DIR / "submissions.jsonl"
PREBUILT_PATH = DATA_DIR / "prebuilt-scans.json"

API_BASE = "https://clarvia-api.onrender.com"
BADGE_BASE = f"{API_BASE}/v1/badge"
SCAN_TIMEOUT = 60
MAX_CONCURRENT = 3


def load_submissions(status_filter: str | None = "queued") -> list[dict]:
    """Load submissions from JSONL file, optionally filtered by status."""
    entries = []
    if not SUBMISSIONS_PATH.exists():
        return entries

    with open(SUBMISSIONS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if status_filter is None or entry.get("status") == status_filter:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue

    return entries


def update_submission_status(submission_id: str, updates: dict) -> None:
    """Update a submission's status in the JSONL file."""
    if not SUBMISSIONS_PATH.exists():
        return

    lines = []
    with open(SUBMISSIONS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("submission_id") == submission_id:
                    entry.update(updates)
                lines.append(json.dumps(entry, default=str))
            except json.JSONDecodeError:
                lines.append(line)

    with open(SUBMISSIONS_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")


async def scan_url(session: aiohttp.ClientSession, url: str) -> dict | None:
    """Scan a URL via the Clarvia API."""
    try:
        async with session.post(
            f"{API_BASE}/api/scan",
            json={"url": url},
            timeout=aiohttp.ClientTimeout(total=SCAN_TIMEOUT),
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            elif resp.status == 429:
                logger.warning("Rate limited — pausing 60s")
                await asyncio.sleep(60)
                return None
            else:
                logger.warning("Scan failed for %s: HTTP %d", url, resp.status)
                return None
    except Exception as e:
        logger.warning("Scan error for %s: %s", url, e)
        return None


async def validate_url(session: aiohttp.ClientSession, url: str) -> bool:
    """Validate that a URL is reachable and not blocked."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = (parsed.hostname or "").lower()

    # Block private/reserved hostnames and IPs
    blocked_exact = {"localhost", "127.0.0.1", "0.0.0.0", "::1", ""}
    if hostname in blocked_exact:
        return False

    blocked_prefixes = ("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                        "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                        "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                        "172.30.", "172.31.", "192.168.", "169.254.")
    for prefix in blocked_prefixes:
        if hostname.startswith(prefix):
            return False

    try:
        async with session.head(
            url,
            timeout=aiohttp.ClientTimeout(total=10),
            allow_redirects=True,
        ) as resp:
            return resp.status < 400
    except Exception:
        # Try GET as fallback (some servers don't support HEAD)
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
                allow_redirects=True,
            ) as resp:
                return resp.status < 400
        except Exception:
            return False


def generate_badge_code(scan_id: str, tool_name: str) -> dict[str, str]:
    """Generate badge embed code for various platforms."""
    badge_url = f"{BADGE_BASE}/{scan_id}"
    tool_page = f"https://clarvia.art/tool/{scan_id}"

    return {
        "markdown": f"[![Clarvia Score]({badge_url})]({tool_page})",
        "html": f'<a href="{tool_page}"><img src="{badge_url}" alt="Clarvia Score for {tool_name}"></a>',
        "badge_url": badge_url,
        "tool_page": tool_page,
    }


async def process_submissions(max_items: int = 20, dry_run: bool = False) -> dict[str, Any]:
    """Process pending submissions: validate, scan, index."""
    submissions = load_submissions(status_filter="queued")
    if not submissions:
        logger.info("No pending submissions")
        return {"processed": 0, "total_pending": 0}

    to_process = submissions[:max_items]
    logger.info("Processing %d/%d pending submissions", len(to_process), len(submissions))

    results = {
        "processed": 0,
        "scanned": 0,
        "indexed": 0,
        "failed": 0,
        "details": [],
    }

    # Load existing catalog for dedup
    existing_urls: set[str] = set()
    existing_services: list[dict] = []
    if PREBUILT_PATH.exists():
        with open(PREBUILT_PATH) as f:
            existing_services = json.load(f)
        existing_urls = {s.get("url", "").rstrip("/").lower() for s in existing_services}

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async with aiohttp.ClientSession() as session:
        for sub in to_process:
            sub_id = sub.get("submission_id", "unknown")
            url = sub.get("url", "")

            if not url:
                results["failed"] += 1
                continue

            async with semaphore:
                # Step 1: Validate URL
                if not dry_run:
                    is_valid = await validate_url(session, url)
                    if not is_valid:
                        logger.warning("URL validation failed: %s", url)
                        update_submission_status(sub_id, {
                            "status": "failed",
                            "error": "URL validation failed",
                            "processed_at": datetime.now(timezone.utc).isoformat(),
                        })
                        results["failed"] += 1
                        continue

                # Step 2: Check for duplicates
                if url.rstrip("/").lower() in existing_urls:
                    logger.info("Already indexed: %s", url)
                    update_submission_status(sub_id, {
                        "status": "duplicate",
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    })
                    results["processed"] += 1
                    continue

                if dry_run:
                    logger.info("DRY RUN — would scan: %s", url)
                    results["processed"] += 1
                    continue

                # Step 3: Scan
                scan_result = await scan_url(session, url)
                results["processed"] += 1

                if scan_result and scan_result.get("clarvia_score", 0) > 0:
                    results["scanned"] += 1

                    # Step 4: Auto-index
                    existing_services.append(scan_result)
                    existing_urls.add(url.rstrip("/").lower())
                    results["indexed"] += 1

                    scan_id = scan_result.get("scan_id", "")
                    badge = generate_badge_code(scan_id, scan_result.get("service_name", ""))

                    update_submission_status(sub_id, {
                        "status": "indexed",
                        "scan_id": scan_id,
                        "clarvia_score": scan_result.get("clarvia_score", 0),
                        "badge": badge,
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    })

                    results["details"].append({
                        "url": url,
                        "scan_id": scan_id,
                        "score": scan_result.get("clarvia_score", 0),
                    })

                    logger.info("Indexed %s (score: %d)", url, scan_result.get("clarvia_score", 0))
                else:
                    update_submission_status(sub_id, {
                        "status": "scan_failed",
                        "error": "Scan returned no result or zero score",
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    })
                    results["failed"] += 1

    # Save updated catalog
    if not dry_run and results["indexed"] > 0:
        with open(PREBUILT_PATH, "w") as f:
            json.dump(existing_services, f, indent=2, default=str)
        logger.info("Updated catalog with %d new entries", results["indexed"])

    return results


def main():
    parser = argparse.ArgumentParser(description="Clarvia Auto-Onboarding Pipeline")
    parser.add_argument("--max", type=int, default=20, help="Max submissions to process per run")
    parser.add_argument("--dry-run", action="store_true", help="Validate but do not scan/index")
    args = parser.parse_args()

    result = asyncio.run(process_submissions(max_items=args.max, dry_run=args.dry_run))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
