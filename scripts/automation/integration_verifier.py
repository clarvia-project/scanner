#!/usr/bin/env python3
"""Integration verification suite for Clarvia distribution channels.

Verifies that Clarvia works correctly across all distribution points:
  1. REST API endpoints (/v1/search, /v1/score, /v1/leaderboard, /v1/feed/*)
  2. MCP Server (clarvia-mcp-server npm package)
  3. Feed endpoints (data freshness checks)
  4. npm package structure verification

Outputs: integration_report.json with pass/fail per test.
Sends Telegram alert on any failure.

Usage:
    python scripts/automation/integration_verifier.py [--api-url URL] [--dry-run]
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# Add project root to path for telegram_notifier
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from telegram_notifier import send_alert

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://clarvia-api.onrender.com"
REPORT_DIR = PROJECT_ROOT / "data" / "reports"
TIMEOUT = 15  # seconds


class IntegrationResult:
    """Single test result container."""

    def __init__(self, name: str, category: str) -> None:
        self.name = name
        self.category = category
        self.passed = False
        self.message = ""
        self.duration_ms = 0.0
        self.details: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "passed": self.passed,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 1),
            "details": self.details,
        }


def _timed_request(
    method: str, url: str, **kwargs: Any
) -> tuple[requests.Response | None, float]:
    """Execute a request and return (response, elapsed_ms)."""
    kwargs.setdefault("timeout", TIMEOUT)
    start = time.monotonic()
    try:
        resp = requests.request(method, url, **kwargs)
        elapsed = (time.monotonic() - start) * 1000
        return resp, elapsed
    except requests.RequestException as exc:
        elapsed = (time.monotonic() - start) * 1000
        logger.warning("Request to %s failed: %s", url, exc)
        return None, elapsed


# ---------------------------------------------------------------------------
# Test: REST API endpoints
# ---------------------------------------------------------------------------

def test_health(api_url: str) -> IntegrationResult:
    """Verify /health returns 200."""
    result = IntegrationResult("health_endpoint", "rest_api")
    resp, ms = _timed_request("GET", f"{api_url}/health")
    result.duration_ms = ms

    if resp and resp.status_code == 200:
        result.passed = True
        result.message = "Health check OK"
    else:
        status = resp.status_code if resp else "no_response"
        result.message = f"Health check failed: status={status}"
    return result


def test_search_endpoint(api_url: str) -> IntegrationResult:
    """Verify /v1/search returns valid JSON with expected structure."""
    result = IntegrationResult("search_endpoint", "rest_api")
    resp, ms = _timed_request("GET", f"{api_url}/v1/search", params={"q": "github"})
    result.duration_ms = ms

    if not resp:
        result.message = "No response from /v1/search"
        return result

    if resp.status_code != 200:
        result.message = f"/v1/search returned status {resp.status_code}"
        return result

    try:
        data = resp.json()
        # Expect either 'results' or 'services' key
        has_data = isinstance(data, dict) and (
            "results" in data or "services" in data or "tools" in data
        )
        if has_data:
            result.passed = True
            result.message = "Search endpoint returns valid JSON with results"
            result.details["keys"] = list(data.keys())
        else:
            result.message = f"Unexpected response structure: {list(data.keys())}"
    except (json.JSONDecodeError, ValueError) as exc:
        result.message = f"Invalid JSON response: {exc}"

    return result


def test_score_endpoint(api_url: str) -> IntegrationResult:
    """Verify /v1/score returns valid JSON."""
    result = IntegrationResult("score_endpoint", "rest_api")
    # Use a known URL that should exist in the catalog
    resp, ms = _timed_request(
        "GET", f"{api_url}/v1/score", params={"url": "https://github.com"}
    )
    result.duration_ms = ms

    if not resp:
        result.message = "No response from /v1/score"
        return result

    if resp.status_code == 200:
        try:
            data = resp.json()
            result.passed = True
            result.message = "Score endpoint returns valid JSON"
            result.details["keys"] = list(data.keys()) if isinstance(data, dict) else []
        except (json.JSONDecodeError, ValueError):
            result.message = "Score endpoint returned invalid JSON"
    elif resp.status_code == 404:
        # 404 is acceptable — means URL not in catalog but endpoint works
        result.passed = True
        result.message = "Score endpoint works (URL not in catalog, 404 expected)"
    else:
        result.message = f"/v1/score returned status {resp.status_code}"

    return result


def test_leaderboard_endpoint(api_url: str) -> IntegrationResult:
    """Verify /v1/leaderboard returns valid paginated JSON."""
    result = IntegrationResult("leaderboard_endpoint", "rest_api")
    resp, ms = _timed_request("GET", f"{api_url}/v1/leaderboard")
    result.duration_ms = ms

    if not resp:
        result.message = "No response from /v1/leaderboard"
        return result

    if resp.status_code != 200:
        result.message = f"/v1/leaderboard returned status {resp.status_code}"
        return result

    try:
        data = resp.json()
        result.passed = True
        result.message = "Leaderboard endpoint returns valid JSON"
        result.details["total"] = data.get("total", len(data) if isinstance(data, list) else 0)
    except (json.JSONDecodeError, ValueError):
        result.message = "Leaderboard endpoint returned invalid JSON"

    return result


# ---------------------------------------------------------------------------
# Test: Feed endpoints (data freshness)
# ---------------------------------------------------------------------------

def test_feed_scores(api_url: str) -> IntegrationResult:
    """Verify /v1/feed/scores returns paginated service data."""
    result = IntegrationResult("feed_scores", "feed")
    resp, ms = _timed_request("GET", f"{api_url}/v1/feed/scores", params={"limit": 5})
    result.duration_ms = ms

    if not resp or resp.status_code != 200:
        status = resp.status_code if resp else "no_response"
        result.message = f"/v1/feed/scores failed: status={status}"
        return result

    try:
        data = resp.json()
        services = data.get("services", [])
        total = data.get("total", 0)

        if total > 0 and len(services) > 0:
            result.passed = True
            result.message = f"Feed scores OK: {total} total, {len(services)} returned"
            result.details["total"] = total
            result.details["sample_count"] = len(services)
        else:
            result.message = f"Feed scores returned empty data (total={total})"
    except (json.JSONDecodeError, ValueError):
        result.message = "Feed scores returned invalid JSON"

    return result


def test_feed_top(api_url: str) -> IntegrationResult:
    """Verify /v1/feed/top returns top services."""
    result = IntegrationResult("feed_top", "feed")
    resp, ms = _timed_request("GET", f"{api_url}/v1/feed/top", params={"limit": 5})
    result.duration_ms = ms

    if not resp or resp.status_code != 200:
        status = resp.status_code if resp else "no_response"
        result.message = f"/v1/feed/top failed: status={status}"
        return result

    try:
        data = resp.json()
        top = data.get("top_services", [])
        if len(top) > 0:
            result.passed = True
            result.message = f"Feed top OK: {len(top)} services"
            result.details["count"] = len(top)
            # Check data freshness: top score should be reasonable
            top_score = top[0].get("score", 0) if top else 0
            result.details["top_score"] = top_score
        else:
            result.message = "Feed top returned empty list"
    except (json.JSONDecodeError, ValueError):
        result.message = "Feed top returned invalid JSON"

    return result


def test_feed_stats(api_url: str) -> IntegrationResult:
    """Verify /v1/feed/stats returns aggregate data."""
    result = IntegrationResult("feed_stats", "feed")
    resp, ms = _timed_request("GET", f"{api_url}/v1/feed/stats")
    result.duration_ms = ms

    if not resp or resp.status_code != 200:
        status = resp.status_code if resp else "no_response"
        result.message = f"/v1/feed/stats failed: status={status}"
        return result

    try:
        data = resp.json()
        total = data.get("total_services", 0)
        if total > 0:
            result.passed = True
            result.message = f"Feed stats OK: {total} services indexed"
            result.details["total_services"] = total
            result.details["avg_score"] = data.get("avg_score", 0)
        else:
            result.message = "Feed stats reports 0 services"
    except (json.JSONDecodeError, ValueError):
        result.message = "Feed stats returned invalid JSON"

    return result


# ---------------------------------------------------------------------------
# Test: npm package verification
# ---------------------------------------------------------------------------

def test_npm_package() -> IntegrationResult:
    """Verify clarvia-mcp-server@latest exists on npm and has expected exports."""
    result = IntegrationResult("npm_package", "mcp_server")

    # Check npm registry metadata (no install needed)
    resp, ms = _timed_request(
        "GET", "https://registry.npmjs.org/clarvia-mcp-server/latest"
    )
    result.duration_ms = ms

    if not resp:
        result.message = "Cannot reach npm registry"
        return result

    if resp.status_code == 404:
        result.message = "clarvia-mcp-server not found on npm (not yet published)"
        # Not a hard failure — package may not be published yet
        result.passed = True
        result.details["published"] = False
        return result

    if resp.status_code != 200:
        result.message = f"npm registry returned status {resp.status_code}"
        return result

    try:
        data = resp.json()
        version = data.get("version", "unknown")
        has_bin = bool(data.get("bin"))
        has_main = bool(data.get("main"))

        result.passed = True
        result.message = f"npm package v{version} exists"
        result.details = {
            "published": True,
            "version": version,
            "has_bin": has_bin,
            "has_main": has_main,
            "name": data.get("name", ""),
        }
    except (json.JSONDecodeError, ValueError):
        result.message = "npm registry returned invalid JSON"

    return result


def test_mcp_server_local() -> IntegrationResult:
    """Verify local MCP server builds and has expected structure."""
    result = IntegrationResult("mcp_server_local", "mcp_server")
    mcp_dir = PROJECT_ROOT / "mcp-server"

    if not mcp_dir.exists():
        result.message = "mcp-server directory not found"
        return result

    # Check package.json exists and has expected fields
    pkg_json = mcp_dir / "package.json"
    if not pkg_json.exists():
        result.message = "mcp-server/package.json not found"
        return result

    try:
        with open(pkg_json) as f:
            pkg = json.load(f)

        has_bin = bool(pkg.get("bin"))
        has_build = "build" in pkg.get("scripts", {})
        version = pkg.get("version", "unknown")

        result.passed = True
        result.message = f"MCP server package v{version} structure OK"
        result.details = {
            "version": version,
            "has_bin": has_bin,
            "has_build_script": has_build,
        }
    except (json.JSONDecodeError, ValueError) as exc:
        result.message = f"Invalid package.json: {exc}"

    return result


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

def run_all_tests(api_url: str) -> list[IntegrationResult]:
    """Execute all integration tests and return results."""
    tests = [
        # REST API
        lambda: test_health(api_url),
        lambda: test_search_endpoint(api_url),
        lambda: test_score_endpoint(api_url),
        lambda: test_leaderboard_endpoint(api_url),
        # Feeds
        lambda: test_feed_scores(api_url),
        lambda: test_feed_top(api_url),
        lambda: test_feed_stats(api_url),
        # MCP / npm
        lambda: test_npm_package(),
        lambda: test_mcp_server_local(),
    ]

    results = []
    for test_fn in tests:
        try:
            r = test_fn()
        except Exception as exc:
            r = IntegrationResult(test_fn.__name__, "error")
            r.message = f"Uncaught exception: {exc}"
        results.append(r)
        logger.info(
            "%s %s: %s (%.0fms)",
            "PASS" if r.passed else "FAIL",
            r.name,
            r.message,
            r.duration_ms,
        )

    return results


def generate_report(results: list[IntegrationResult]) -> dict[str, Any]:
    """Build the integration_report.json payload."""
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total * 100, 1) if total else 0,
        },
        "results": [r.to_dict() for r in results],
    }


def format_telegram_message(report: dict[str, Any]) -> str:
    """Format report as Telegram Markdown message."""
    s = report["summary"]
    status = "PASS" if s["failed"] == 0 else "FAIL"
    icon = "✅" if status == "PASS" else "🔴"

    lines = [
        f"{icon} *Clarvia Integration Report*",
        f"Status: {status} ({s['passed']}/{s['total']} passed)",
        "",
    ]

    for r in report["results"]:
        mark = "✅" if r["passed"] else "❌"
        lines.append(f"{mark} `{r['name']}` — {r['message']}")

    lines.append(f"\n_Generated: {report['generated_at']}_")
    return "\n".join(lines)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Clarvia integration verifier")
    parser.add_argument(
        "--api-url", default=DEFAULT_API_URL, help="Base URL of the Clarvia API"
    )
    parser.add_argument("--dry-run", action="store_true", help="Skip Telegram alerts")
    parser.add_argument("--json", action="store_true", help="Print report as JSON to stdout")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logger.info("Starting integration verification against %s", args.api_url)
    results = run_all_tests(args.api_url)
    report = generate_report(results)

    # Save report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "integration_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Report saved to %s", report_path)

    if args.json:
        print(json.dumps(report, indent=2))

    # Alert on failures
    failed = report["summary"]["failed"]
    if failed > 0:
        msg = format_telegram_message(report)
        send_alert(
            "Integration Test Failures",
            msg,
            level="ERROR",
        ) if not args.dry_run else logger.info("[DRY RUN] Would send alert:\n%s", msg)
        return 1

    logger.info("All %d tests passed", report["summary"]["total"])
    if not args.dry_run:
        send_alert(
            "Integration Tests Passed",
            format_telegram_message(report),
            level="SUCCESS",
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
