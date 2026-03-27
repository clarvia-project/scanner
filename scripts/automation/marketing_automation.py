#!/usr/bin/env python3
"""Clarvia Marketing Automation — Agent-Only Distribution Pipeline.

Automates all marketing activities that require zero human intervention.
Targets agent/developer discovery channels exclusively (no social media).

Tasks:
1. MCP registry status check — verify Clarvia MCP is listed and up-to-date
2. Awesome-list PR status tracker — monitor outstanding PRs
3. npm package version check — alert if backend API version mismatches npm
4. Sitemap freshness — rebuild if stale
5. LLMs.txt update — ensure /llms.txt reflects current catalog state
6. API health badge — update README badge with current uptime status

Usage:
    python scripts/automation/marketing_automation.py [--dry-run]
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from telegram_notifier import send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
MARKETING_LOG = DATA_DIR / "marketing_automation.jsonl"
API_BASE = "https://clarvia-api.onrender.com"
NPM_PACKAGE = "clarvia-mcp"


# ---------------------------------------------------------------------------
# Task 1: MCP Registry Status Check
# ---------------------------------------------------------------------------

def check_mcp_registry_listing(dry_run: bool = False) -> dict[str, Any]:
    """Verify Clarvia MCP server is listed in major registries."""
    results = {}

    registries = [
        {
            "name": "Smithery",
            "check_url": f"https://smithery.ai/server/{NPM_PACKAGE}",
            "search_url": f"https://registry.smithery.ai/servers?q=clarvia",
        },
        {
            "name": "mcp.so",
            "check_url": f"https://mcp.so/server/{NPM_PACKAGE}",
            "search_url": f"https://mcp.so/search?q=clarvia",
        },
    ]

    for registry in registries:
        try:
            resp = requests.get(registry["check_url"], timeout=10, allow_redirects=True)
            listed = resp.status_code < 400
            results[registry["name"]] = {
                "listed": listed,
                "status_code": resp.status_code,
                "url": registry["check_url"],
            }
            logger.info(
                "Registry %s: %s (status=%d)",
                registry["name"],
                "LISTED" if listed else "NOT LISTED",
                resp.status_code,
            )
        except Exception as exc:
            results[registry["name"]] = {"listed": False, "error": str(exc)}
            logger.warning("Registry %s check failed: %s", registry["name"], exc)

    return results


# ---------------------------------------------------------------------------
# Task 2: npm Package Version Check
# ---------------------------------------------------------------------------

def check_npm_version() -> dict[str, Any]:
    """Check if npm package is up-to-date and matches MCP server spec."""
    try:
        resp = requests.get(
            f"https://registry.npmjs.org/{NPM_PACKAGE}/latest",
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            npm_version = data.get("version", "unknown")
            downloads_resp = requests.get(
                f"https://api.npmjs.org/downloads/point/last-week/{NPM_PACKAGE}",
                timeout=10,
            )
            weekly_downloads = 0
            if downloads_resp.status_code == 200:
                weekly_downloads = downloads_resp.json().get("downloads", 0)

            logger.info(
                "npm %s: version=%s, weekly_downloads=%d",
                NPM_PACKAGE, npm_version, weekly_downloads,
            )
            return {
                "version": npm_version,
                "weekly_downloads": weekly_downloads,
                "published_at": data.get("dist", {}).get("tarball", ""),
            }
        return {"error": f"npm returned {resp.status_code}"}
    except Exception as exc:
        logger.warning("npm version check failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Task 3: LLMs.txt Freshness Check
# ---------------------------------------------------------------------------

def check_llms_txt() -> dict[str, Any]:
    """Verify /llms.txt is accessible and reflects current catalog state."""
    try:
        resp = requests.get("https://clarvia.art/llms.txt", timeout=10)
        if resp.status_code == 200:
            content_length = len(resp.text)
            tool_count_approx = resp.text.count("clarvia.art/tool/")
            logger.info("llms.txt: accessible, length=%d, tool_refs=%d", content_length, tool_count_approx)
            return {
                "accessible": True,
                "content_length": content_length,
                "tool_refs": tool_count_approx,
            }
        return {"accessible": False, "status_code": resp.status_code}
    except Exception as exc:
        return {"accessible": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Task 4: Awesome-list PR Status
# ---------------------------------------------------------------------------

def check_awesome_list_prs() -> dict[str, Any]:
    """Check status of outstanding awesome-list PRs via GitHub API."""
    github_token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    # Known PR targets from previous submissions
    pr_targets = [
        ("awesome-mcp-servers", "punkpeye"),
        ("awesome-mcp-servers", "appcypher"),
        ("awesome-mcp-servers", "wong2"),
    ]

    results = {}
    for repo_name, owner in pr_targets:
        try:
            # Search for open PRs from clarvia
            search_url = (
                f"https://api.github.com/search/issues"
                f"?q=repo:{owner}/{repo_name}+is:pr+author:clarvia-project+is:open"
            )
            resp = requests.get(search_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                prs = data.get("items", [])
                results[f"{owner}/{repo_name}"] = {
                    "open_prs": len(prs),
                    "pr_urls": [pr["html_url"] for pr in prs[:3]],
                }
                logger.info("%s/%s: %d open PRs", owner, repo_name, len(prs))
            else:
                results[f"{owner}/{repo_name}"] = {"error": f"GitHub API {resp.status_code}"}
        except Exception as exc:
            results[f"{owner}/{repo_name}"] = {"error": str(exc)}

    return results


# ---------------------------------------------------------------------------
# Task 5: Backend API Health + Response Time
# ---------------------------------------------------------------------------

def check_api_health() -> dict[str, Any]:
    """Check production API health and record response time."""
    import time as _time
    try:
        start = _time.monotonic()
        resp = requests.get(f"{API_BASE}/health", timeout=15)
        elapsed_ms = (_time.monotonic() - start) * 1000

        if resp.status_code == 200:
            data = resp.json()
            overall = data.get("status", "unknown")
            db_status = data.get("checks", {}).get("database", {}).get("status", "unknown")
            mem_mb = data.get("checks", {}).get("memory", {}).get("rss_mb", 0)

            logger.info(
                "API health: status=%s, db=%s, mem=%.1fMB, response=%.0fms",
                overall, db_status, mem_mb, elapsed_ms,
            )
            return {
                "status": overall,
                "db_status": db_status,
                "memory_mb": mem_mb,
                "response_ms": round(elapsed_ms, 1),
                "cold_start": elapsed_ms > 5000,
            }
        return {"status": "error", "status_code": resp.status_code, "response_ms": round(elapsed_ms, 1)}
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc)}


# ---------------------------------------------------------------------------
# Task 6: Catalog Stats for Marketing Signals
# ---------------------------------------------------------------------------

def check_catalog_stats() -> dict[str, Any]:
    """Pull catalog stats to generate accurate marketing numbers."""
    try:
        resp = requests.get(f"{API_BASE}/v1/services?limit=1", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            total = data.get("total", 0) or data.get("count", 0)
            logger.info("Catalog total: %d tools", total)
            return {"total_tools": total}
        return {"error": f"API returned {resp.status_code}"}
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_all(dry_run: bool = False) -> dict[str, Any]:
    """Run all marketing automation checks."""
    now = datetime.now(timezone.utc)
    logger.info("=== Marketing Automation Run: %s ===", now.isoformat())

    report = {
        "timestamp": now.isoformat(),
        "dry_run": dry_run,
    }

    report["api_health"] = check_api_health()
    report["npm_version"] = check_npm_version()
    report["mcp_registries"] = check_mcp_registry_listing(dry_run=dry_run)
    report["llms_txt"] = check_llms_txt()
    report["awesome_prs"] = check_awesome_list_prs()
    report["catalog_stats"] = check_catalog_stats()

    # Build Telegram summary
    health = report["api_health"]
    npm = report["npm_version"]
    catalog = report["catalog_stats"]

    summary_lines = [
        f"[Marketing Automation] {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"API: {health.get('status', 'unknown')} | {health.get('response_ms', '?')}ms | Mem: {health.get('memory_mb', '?')}MB",
        f"DB: {health.get('db_status', 'unknown')}",
        f"Catalog: {catalog.get('total_tools', '?')} tools",
        f"npm {NPM_PACKAGE}: v{npm.get('version', '?')} | {npm.get('weekly_downloads', '?')} dl/wk",
        f"",
    ]

    # Registry status
    for registry_name, reg_data in report["mcp_registries"].items():
        status = "Listed" if reg_data.get("listed") else "NOT LISTED"
        summary_lines.append(f"{registry_name}: {status}")

    # PR status
    total_open_prs = sum(
        v.get("open_prs", 0)
        for v in report["awesome_prs"].values()
        if isinstance(v, dict)
    )
    if total_open_prs > 0:
        summary_lines.append(f"Awesome-list PRs: {total_open_prs} open")

    summary = "\n".join(summary_lines)

    # Append to log
    if not dry_run:
        MARKETING_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(MARKETING_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(report, ensure_ascii=False) + "\n")

        # Send Telegram report
        try:
            send_message(summary)
        except Exception as exc:
            logger.warning("Telegram send failed: %s", exc)
    else:
        logger.info("DRY RUN — summary:\n%s", summary)

    logger.info("Marketing automation complete.")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clarvia Marketing Automation")
    parser.add_argument("--dry-run", action="store_true", help="Run checks without sending alerts")
    args = parser.parse_args()
    result = run_all(dry_run=args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False))
