#!/usr/bin/env python3
"""Clarvia Comprehensive Endpoint Monitor.

Tests all 18 critical API endpoints, records results to JSONL,
prints a summary table, and sends Telegram alerts on any failure.

Usage:
    python scripts/endpoint_monitor.py           # single run
    python scripts/endpoint_monitor.py --dry-run  # no Telegram alerts
    python scripts/endpoint_monitor.py --verbose   # show response bodies
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

# --- Paths ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_PATH = DATA_DIR / "endpoint-monitor.jsonl"

# --- Telegram ---
sys.path.insert(0, str(SCRIPT_DIR))
from telegram_notifier import send_message

TELEGRAM_CHAT_ID = "6558975935"

# --- Config ---
BASE_URL = "https://clarvia-api.onrender.com"
DEFAULT_TIMEOUT = 15
SCAN_TIMEOUT = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
# Endpoint definitions
# ============================================================

def _expect_200_json(resp: requests.Response) -> tuple[bool, str]:
    """Basic 200 + valid JSON check."""
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    try:
        resp.json()
        return True, "OK"
    except (json.JSONDecodeError, ValueError):
        return False, "invalid JSON"


def check_health(resp: requests.Response) -> tuple[bool, str]:
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    try:
        data = resp.json()
        status = data.get("status", "unknown")
        if status == "healthy":
            return True, f"status={status}"
        return False, f"status={status}"
    except (json.JSONDecodeError, ValueError):
        return False, "invalid JSON"


def check_stats(resp: requests.Response) -> tuple[bool, str]:
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    try:
        data = resp.json()
        total = data.get("total_services", data.get("total", 0))
        if total > 0:
            return True, f"total_services={total}"
        return False, f"total_services={total}"
    except (json.JSONDecodeError, ValueError):
        return False, "invalid JSON"


def check_non_empty_list(key: str):
    """Return a validator that checks for non-empty list at `key`."""
    def _check(resp: requests.Response) -> tuple[bool, str]:
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
        try:
            data = resp.json()
            items = data.get(key) or data.get("results") or data.get("services") or []
            if isinstance(data, list):
                items = data
            if len(items) > 0:
                return True, f"{len(items)} items"
            return False, "empty results"
        except (json.JSONDecodeError, ValueError):
            return False, "invalid JSON"
    return _check


def check_categories(resp: requests.Response) -> tuple[bool, str]:
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    try:
        data = resp.json()
        # Could be list or dict with count
        if isinstance(data, list) and len(data) > 0:
            return True, f"{len(data)} categories"
        if isinstance(data, dict):
            count = data.get("count", data.get("total", len(data)))
            if count > 0:
                return True, f"{count} categories"
        return False, "empty categories"
    except (json.JSONDecodeError, ValueError):
        return False, "invalid JSON"


def check_scan(resp: requests.Response) -> tuple[bool, str]:
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    try:
        data = resp.json()
        score = data.get("score") or data.get("clarvia_score")
        if score is not None:
            return True, f"score={score}"
        # Check for error in response
        if data.get("error"):
            return False, f"scan error: {data['error'][:80]}"
        return False, "no score in response"
    except (json.JSONDecodeError, ValueError):
        return False, "invalid JSON"


def check_feed_scores(resp: requests.Response) -> tuple[bool, str]:
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    try:
        data = resp.json()
        total = data.get("total", 0)
        if total > 0:
            return True, f"total={total}"
        return False, f"total={total}"
    except (json.JSONDecodeError, ValueError):
        return False, "invalid JSON"


def check_200_any(resp: requests.Response) -> tuple[bool, str]:
    """Just check for HTTP 200."""
    if resp.status_code == 200:
        return True, "HTTP 200"
    return False, f"HTTP {resp.status_code}"


def check_redirect_307(resp: requests.Response) -> tuple[bool, str]:
    """Check for 307 redirect (not following redirects)."""
    if resp.status_code == 307:
        return True, "HTTP 307 redirect"
    return False, f"HTTP {resp.status_code} (expected 307)"


def check_badge_svg(resp: requests.Response) -> tuple[bool, str]:
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    ct = resp.headers.get("content-type", "")
    if "svg" in ct or "<svg" in resp.text[:200]:
        return True, "SVG OK"
    return False, f"not SVG (content-type: {ct[:50]})"


# Endpoint spec: (name, method, path, validator, timeout, kwargs)
ENDPOINTS: list[dict[str, Any]] = [
    {
        "name": "GET /health",
        "method": "GET",
        "path": "/health",
        "validate": check_health,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /v1/stats",
        "method": "GET",
        "path": "/v1/stats",
        "validate": check_stats,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /v1/services?q=weather",
        "method": "GET",
        "path": "/v1/services?q=weather&limit=3",
        "validate": check_non_empty_list("services"),
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /v1/services?service_type=mcp",
        "method": "GET",
        "path": "/v1/services?service_type=mcp_server&limit=3",
        "validate": check_non_empty_list("services"),
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /v1/categories",
        "method": "GET",
        "path": "/v1/categories",
        "validate": check_categories,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /v1/leaderboard",
        "method": "GET",
        "path": "/v1/leaderboard",
        "validate": check_non_empty_list("leaderboard"),
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /v1/recommend?intent=email",
        "method": "GET",
        "path": "/v1/recommend?intent=email",
        "validate": check_non_empty_list("recommendations"),
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /v1/featured/top",
        "method": "GET",
        "path": "/v1/featured/top",
        "validate": check_200_any,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "POST /api/scan",
        "method": "POST",
        "path": "/api/scan",
        "json_body": {"url": "https://api.github.com"},
        "validate": check_scan,
        "timeout": SCAN_TIMEOUT,
    },
    {
        "name": "GET /v1/profiles (list)",
        "method": "GET",
        "path": "/v1/profiles?limit=1",
        "validate": check_200_any,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /v1/compare",
        "method": "GET",
        "path": "/v1/compare?ids=io.github.mcmurrym-virga-weather",
        "validate": check_200_any,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /v1/feed/scores",
        "method": "GET",
        "path": "/v1/feed/scores",
        "validate": check_feed_scores,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /v1/traffic/stats",
        "method": "GET",
        "path": "/v1/traffic/stats",
        "validate": check_200_any,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /v1/history/{slug}",
        "method": "GET",
        "path": "/v1/history/io.github.mcmurrym-virga-weather",
        "validate": check_200_any,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /api/badge/test.svg",
        "method": "GET",
        "path": "/api/badge/test.svg",
        "validate": check_badge_svg,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /.well-known/agents.json",
        "method": "GET",
        "path": "/.well-known/agents.json",
        "validate": check_200_any,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /openapi.json",
        "method": "GET",
        "path": "/openapi.json",
        "validate": check_200_any,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "name": "GET /api/v1/stats (redirect)",
        "method": "GET",
        "path": "/api/v1/stats",
        "validate": check_redirect_307,
        "timeout": DEFAULT_TIMEOUT,
        "allow_redirects": False,
    },
]


# ============================================================
# Runner
# ============================================================

def test_endpoint(ep: dict) -> dict:
    """Test a single endpoint and return result dict."""
    url = BASE_URL + ep["path"]
    method = ep["method"]
    timeout = ep.get("timeout", DEFAULT_TIMEOUT)
    allow_redirects = ep.get("allow_redirects", True)

    result = {
        "endpoint": ep["name"],
        "url": url,
        "method": method,
        "http_status": None,
        "response_time_ms": None,
        "pass": False,
        "error_detail": None,
    }

    try:
        start = time.monotonic()

        if method == "POST":
            resp = requests.post(
                url,
                json=ep.get("json_body", {}),
                timeout=timeout,
                allow_redirects=allow_redirects,
            )
        else:
            resp = requests.get(
                url,
                timeout=timeout,
                allow_redirects=allow_redirects,
            )

        elapsed_ms = round((time.monotonic() - start) * 1000)

        result["http_status"] = resp.status_code
        result["response_time_ms"] = elapsed_ms

        passed, detail = ep["validate"](resp)
        result["pass"] = passed
        if not passed:
            result["error_detail"] = detail
        else:
            result["error_detail"] = detail  # store detail even on pass

    except requests.Timeout:
        result["error_detail"] = f"timeout ({timeout}s)"
        result["response_time_ms"] = timeout * 1000
    except requests.ConnectionError:
        result["error_detail"] = "connection refused"
    except requests.RequestException as exc:
        result["error_detail"] = str(exc)[:200]
    except Exception as exc:
        result["error_detail"] = f"unexpected: {exc}"

    return result


def run_all_tests() -> list[dict]:
    """Run all endpoint tests and return results."""
    results = []
    for ep in ENDPOINTS:
        result = test_endpoint(ep)
        results.append(result)
    return results


def save_results(results: list[dict]) -> None:
    """Append run results to JSONL log file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    run_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": sum(1 for r in results if r["pass"]),
        "failed": sum(1 for r in results if not r["pass"]),
        "results": results,
    }

    with open(RESULTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(run_entry, ensure_ascii=False) + "\n")

    logger.info("Results saved to %s", RESULTS_PATH)


def print_summary(results: list[dict]) -> None:
    """Print a formatted summary table to stdout."""
    passed = sum(1 for r in results if r["pass"])
    failed = len(results) - passed

    print()
    print("=" * 80)
    print(f"  Clarvia Endpoint Monitor — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Passed: {passed}/{len(results)}  |  Failed: {failed}/{len(results)}")
    print("=" * 80)
    print(f"  {'Status':<6}  {'Endpoint':<35}  {'HTTP':<5}  {'Time':>7}  {'Detail'}")
    print("-" * 80)

    for r in results:
        status = "PASS" if r["pass"] else "FAIL"
        marker = "  " if r["pass"] else "!!"
        http = str(r["http_status"] or "---")
        time_ms = f"{r['response_time_ms']}ms" if r["response_time_ms"] is not None else "---"
        detail = (r["error_detail"] or "")[:30]
        print(f"{marker}{status:<6}  {r['endpoint']:<35}  {http:<5}  {time_ms:>7}  {detail}")

    print("=" * 80)
    print()


def send_telegram_alert(results: list[dict], *, dry_run: bool = False) -> None:
    """Send Telegram alert if any endpoints failed."""
    failures = [r for r in results if not r["pass"]]
    passed = len(results) - len(failures)

    if not failures:
        return

    lines = ["\U0001f6a8 *Clarvia API Alert*", ""]

    for f in failures:
        endpoint = f["endpoint"]
        error = f["error_detail"] or "unknown"
        http = f["http_status"] or "N/A"
        lines.append(f"\u274c `{endpoint}` — HTTP {http}: {error}")

    lines.append("")
    lines.append(f"Passed: {passed}/{len(results)}")
    lines.append(f"Time: {datetime.now(timezone.utc).strftime('%H:%M UTC')}")

    msg = "\n".join(lines)

    if dry_run:
        logger.info("[DRY RUN] Telegram alert:\n%s", msg)
        return

    ok = send_message(msg, chat_id=TELEGRAM_CHAT_ID)
    if ok:
        logger.info("Telegram alert sent (%d failures)", len(failures))
    else:
        logger.error("Failed to send Telegram alert")


def send_telegram_recovery(results: list[dict], *, dry_run: bool = False) -> None:
    """Send recovery notice when all endpoints pass after previous failure."""
    # Check if previous run had failures
    if not RESULTS_PATH.exists():
        return

    try:
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) < 2:
            return
        prev = json.loads(lines[-2])  # second-to-last (current is already appended)
        if prev.get("failed", 0) > 0 and all(r["pass"] for r in results):
            msg = (
                "\u2705 *Clarvia API Recovered*\n\n"
                f"All {len(results)} endpoints passing.\n"
                f"Time: {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
            )
            if dry_run:
                logger.info("[DRY RUN] Recovery alert:\n%s", msg)
            else:
                send_message(msg, chat_id=TELEGRAM_CHAT_ID)
    except (json.JSONDecodeError, IndexError, KeyError):
        pass


# ============================================================
# Main
# ============================================================

def main() -> int:
    """Run endpoint monitor. Returns 0 if all pass, 1 if any fail."""
    import argparse

    parser = argparse.ArgumentParser(description="Clarvia endpoint monitor")
    parser.add_argument("--dry-run", action="store_true", help="Skip Telegram alerts")
    parser.add_argument("--verbose", action="store_true", help="Show extra details")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of table")
    args = parser.parse_args()

    logger.info("Starting Clarvia endpoint monitor (%d endpoints)", len(ENDPOINTS))

    results = run_all_tests()
    save_results(results)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print_summary(results)

    # Alerts
    send_telegram_alert(results, dry_run=args.dry_run)
    send_telegram_recovery(results, dry_run=args.dry_run)

    all_passed = all(r["pass"] for r in results)

    if all_passed:
        logger.info("All %d endpoints passed", len(results))
    else:
        failed_count = sum(1 for r in results if not r["pass"])
        logger.warning("%d/%d endpoints FAILED", failed_count, len(results))

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
