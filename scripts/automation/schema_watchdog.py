#!/usr/bin/env python3
"""Clarvia Schema Watchdog — API Schema Change Detector.

Monitors external APIs that Clarvia depends on for structural changes.
Detects field additions, removals, type changes, and endpoint failures.

Monitored APIs:
  1. GitHub API         — /search/repositories
  2. npm Registry API   — /-/v1/search
  3. PyPI API           — /pypi/{package}/json
  4. MCP Registry API   — /v0/servers

Severity levels:
  MINOR    — New field added (auto-update golden schema)
  MAJOR    — Field removed or type changed (disable source + alert)
  CRITICAL — Endpoint 404/5xx or unreachable (disable source + alert)

Usage:
    python scripts/automation/schema_watchdog.py
    python scripts/automation/schema_watchdog.py --dry-run
    python scripts/automation/schema_watchdog.py --init   # Generate initial golden schemas
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
WATCHDOG_DIR = DATA_DIR / "watchdog"
SCHEMA_DIR = WATCHDOG_DIR / "schemas"
CHECKS_LOG = WATCHDOG_DIR / "checks.jsonl"

sys.path.insert(0, str(SCRIPT_DIR.parent))
from telegram_notifier import send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# GitHub token for authenticated requests
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# ---------------------------------------------------------------------------
# API endpoint definitions
# ---------------------------------------------------------------------------

API_ENDPOINTS = [
    {
        "name": "github_search",
        "display_name": "GitHub Search API",
        "url": "https://api.github.com/search/repositories?q=mcp-server&per_page=1",
        "headers": {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Clarvia-Watchdog/1.0",
        },
        "schema_key": "items[0]",  # Extract schema from first item
        "source_name": "github",   # Maps to circuit breaker source
    },
    {
        "name": "npm_search",
        "display_name": "npm Registry Search API",
        "url": "https://registry.npmjs.org/-/v1/search?text=mcp-server&size=1",
        "headers": {},
        "schema_key": "objects[0]",
        "source_name": "npm",
    },
    {
        "name": "pypi_package",
        "display_name": "PyPI Package JSON API",
        "url": "https://pypi.org/pypi/requests/json",
        "headers": {},
        "schema_key": "info",
        "source_name": "pypi",
    },
    {
        "name": "mcp_registry",
        "display_name": "MCP Registry API",
        "url": "https://registry.modelcontextprotocol.io/v0/servers",
        "headers": {},
        "schema_key": "[0]",  # First element if array
        "source_name": "mcp_registry",
    },
]


# ---------------------------------------------------------------------------
# Schema extraction
# ---------------------------------------------------------------------------

def extract_type_schema(obj: Any, max_depth: int = 5, _depth: int = 0) -> Any:
    """Recursively extract the type-structure of a JSON object.

    Returns a dict mirroring the structure but with type names as values.
    Example: {"name": "str", "stars": "int", "topics": ["str"]}
    """
    if _depth >= max_depth:
        return type(obj).__name__ if obj is not None else "null"

    if isinstance(obj, dict):
        return {
            k: extract_type_schema(v, max_depth, _depth + 1)
            for k, v in sorted(obj.items())
        }
    elif isinstance(obj, list):
        if not obj:
            return ["empty"]
        # Use first element as representative
        return [extract_type_schema(obj[0], max_depth, _depth + 1)]
    elif obj is None:
        return "null"
    else:
        return type(obj).__name__


def navigate_json(data: Any, path: str) -> Any:
    """Navigate into a JSON structure using a dotted path.

    Supports:
      - "key"        — dict key access
      - "[0]"        — list index access
      - "key[0]"     — dict key then list index
      - "items[0]"   — access items key, then first element
    """
    if not path:
        return data

    current = data
    parts = path.replace("]", "").split("[")

    for part in parts:
        if not part:
            continue
        if part.isdigit():
            idx = int(part)
            if isinstance(current, list) and len(current) > idx:
                current = current[idx]
            else:
                return None
        else:
            # Could be "key.subkey" or just "key"
            subparts = part.split(".")
            for sp in subparts:
                if not sp:
                    continue
                if isinstance(current, dict):
                    current = current.get(sp)
                    if current is None:
                        return None
                else:
                    return None

    return current


# ---------------------------------------------------------------------------
# Schema comparison
# ---------------------------------------------------------------------------

class SchemaChange:
    """Represents a detected schema change."""

    def __init__(self, severity: str, path: str, detail: str):
        self.severity = severity  # MINOR, MAJOR, CRITICAL
        self.path = path
        self.detail = detail

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "path": self.path,
            "detail": self.detail,
        }


def compare_schemas(
    golden: Any, current: Any, path: str = ""
) -> list[SchemaChange]:
    """Compare golden schema to current schema, returning changes.

    MINOR:    New field added (additive)
    MAJOR:    Field removed or type changed
    """
    changes: list[SchemaChange] = []

    if isinstance(golden, dict) and isinstance(current, dict):
        golden_keys = set(golden.keys())
        current_keys = set(current.keys())

        # New fields (MINOR)
        for key in current_keys - golden_keys:
            changes.append(SchemaChange(
                "MINOR",
                f"{path}.{key}" if path else key,
                f"New field added: {key} (type: {current[key]})",
            ))

        # Removed fields (MAJOR)
        for key in golden_keys - current_keys:
            changes.append(SchemaChange(
                "MAJOR",
                f"{path}.{key}" if path else key,
                f"Field removed: {key} (was type: {golden[key]})",
            ))

        # Recurse on shared keys
        for key in golden_keys & current_keys:
            sub_path = f"{path}.{key}" if path else key
            changes.extend(compare_schemas(golden[key], current[key], sub_path))

    elif isinstance(golden, list) and isinstance(current, list):
        if golden and current:
            changes.extend(compare_schemas(golden[0], current[0], f"{path}[]"))

    elif isinstance(golden, str) and isinstance(current, str):
        if golden != current and golden != "null" and current != "null":
            changes.append(SchemaChange(
                "MAJOR",
                path,
                f"Type changed: {golden} -> {current}",
            ))

    elif type(golden) != type(current):
        changes.append(SchemaChange(
            "MAJOR",
            path,
            f"Structure changed: {type(golden).__name__} -> {type(current).__name__}",
        ))

    return changes


# ---------------------------------------------------------------------------
# Schema persistence
# ---------------------------------------------------------------------------

def load_golden_schema(api_name: str) -> Optional[dict]:
    """Load the golden schema for an API."""
    path = SCHEMA_DIR / f"{api_name}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Corrupt golden schema for %s", api_name)
        return None


def save_golden_schema(api_name: str, schema: Any, metadata: dict = None) -> None:
    """Save a golden schema snapshot."""
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "schema": schema,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    path = SCHEMA_DIR / f"{api_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, default=str)
    logger.info("Saved golden schema for %s", api_name)


def log_check(result: dict) -> None:
    """Append a check result to the JSONL log."""
    WATCHDOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHECKS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, default=str) + "\n")


# ---------------------------------------------------------------------------
# API fetch + check
# ---------------------------------------------------------------------------

def fetch_api(endpoint: dict) -> tuple[Optional[Any], Optional[str]]:
    """Fetch an API response.

    Returns:
        (response_data, error_string) — one will be None.
    """
    url = endpoint["url"]
    headers = dict(endpoint.get("headers", {}))

    # Inject GitHub token if available
    if endpoint["name"] == "github_search" and GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        resp = requests.get(url, headers=headers, timeout=15)

        if resp.status_code >= 500:
            return None, f"Server error: HTTP {resp.status_code}"
        if resp.status_code == 404:
            return None, f"Endpoint not found: HTTP 404"
        if resp.status_code == 403:
            return None, f"Rate limited or forbidden: HTTP 403"
        if resp.status_code != 200:
            return None, f"Unexpected status: HTTP {resp.status_code}"

        data = resp.json()
        return data, None

    except requests.ConnectionError:
        return None, "Connection refused"
    except requests.Timeout:
        return None, "Timeout (15s)"
    except requests.RequestException as exc:
        return None, f"Request error: {exc}"
    except (json.JSONDecodeError, ValueError) as exc:
        return None, f"Invalid JSON response: {exc}"


def check_api(endpoint: dict, *, dry_run: bool = False) -> dict:
    """Check a single API endpoint for schema changes.

    Returns a check result dict.
    """
    name = endpoint["name"]
    display = endpoint["display_name"]
    source = endpoint["source_name"]

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api": name,
        "display_name": display,
        "source": source,
    }

    # Fetch current response
    data, error = fetch_api(endpoint)

    if error:
        result["status"] = "error"
        result["severity"] = "CRITICAL"
        result["error"] = error
        logger.error("[%s] CRITICAL — %s", display, error)

        if not dry_run:
            send_alert(
                f"Schema Watchdog: {display} CRITICAL",
                f"API endpoint unreachable or error.\n"
                f"URL: `{endpoint['url']}`\n"
                f"Error: {error}\n\n"
                f"Source `{source}` should be checked.",
                level="CRITICAL",
            )

        return result

    # Navigate to the relevant sub-object
    target = navigate_json(data, endpoint.get("schema_key", ""))
    if target is None:
        result["status"] = "error"
        result["severity"] = "MAJOR"
        result["error"] = f"Could not navigate to schema_key: {endpoint.get('schema_key')}"
        logger.warning("[%s] MAJOR — schema_key navigation failed", display)
        return result

    # Extract type schema
    current_schema = extract_type_schema(target)

    # Load golden schema
    golden_data = load_golden_schema(name)
    if golden_data is None:
        # No golden schema yet — initialize it
        logger.info("[%s] No golden schema found, initializing", display)
        save_golden_schema(name, current_schema, {
            "url": endpoint["url"],
            "schema_key": endpoint.get("schema_key", ""),
        })
        result["status"] = "initialized"
        result["severity"] = "none"
        return result

    golden_schema = golden_data.get("schema")

    # Compare
    changes = compare_schemas(golden_schema, current_schema)

    if not changes:
        result["status"] = "ok"
        result["severity"] = "none"
        logger.info("[%s] OK — no schema changes detected", display)
        return result

    # Classify changes
    minor_changes = [c for c in changes if c.severity == "MINOR"]
    major_changes = [c for c in changes if c.severity == "MAJOR"]

    result["changes"] = [c.to_dict() for c in changes]
    result["minor_count"] = len(minor_changes)
    result["major_count"] = len(major_changes)

    if major_changes:
        result["status"] = "drift"
        result["severity"] = "MAJOR"

        detail_lines = []
        for c in major_changes[:5]:
            detail_lines.append(f"  - [{c.severity}] {c.path}: {c.detail}")
        detail_str = "\n".join(detail_lines)

        logger.warning(
            "[%s] MAJOR — %d major, %d minor changes:\n%s",
            display, len(major_changes), len(minor_changes), detail_str,
        )

        if not dry_run:
            send_alert(
                f"Schema Watchdog: {display} MAJOR DRIFT",
                f"Detected {len(major_changes)} major + {len(minor_changes)} minor changes.\n\n"
                f"Major changes:\n{detail_str}\n\n"
                f"Source `{source}` may need harvester updates.",
                level="ERROR",
            )

    elif minor_changes:
        result["status"] = "minor_drift"
        result["severity"] = "MINOR"

        detail_lines = [f"  - {c.path}: {c.detail}" for c in minor_changes[:5]]
        detail_str = "\n".join(detail_lines)

        logger.info(
            "[%s] MINOR — %d new fields added:\n%s",
            display, len(minor_changes), detail_str,
        )

        # Auto-update golden schema for additive changes
        if not dry_run:
            save_golden_schema(name, current_schema, {
                "url": endpoint["url"],
                "schema_key": endpoint.get("schema_key", ""),
                "auto_updated_reason": f"{len(minor_changes)} minor additive changes",
            })
            logger.info("[%s] Golden schema auto-updated (additive changes only)", display)

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_watchdog(*, dry_run: bool = False, init: bool = False) -> list[dict]:
    """Run schema checks on all monitored APIs.

    Args:
        dry_run: If True, don't send alerts or update schemas.
        init: If True, force regenerate all golden schemas.

    Returns:
        List of check result dicts.
    """
    results = []

    if init:
        logger.info("Initializing golden schemas for all APIs")
        for endpoint in API_ENDPOINTS:
            data, error = fetch_api(endpoint)
            if error:
                logger.error("[%s] Failed to fetch: %s", endpoint["display_name"], error)
                continue
            target = navigate_json(data, endpoint.get("schema_key", ""))
            if target is not None:
                schema = extract_type_schema(target)
                save_golden_schema(endpoint["name"], schema, {
                    "url": endpoint["url"],
                    "schema_key": endpoint.get("schema_key", ""),
                    "initialized": True,
                })
        logger.info("Golden schema initialization complete")
        return results

    for endpoint in API_ENDPOINTS:
        try:
            result = check_api(endpoint, dry_run=dry_run)
            results.append(result)
            log_check(result)
        except Exception as exc:
            logger.exception("Error checking %s", endpoint["name"])
            error_result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "api": endpoint["name"],
                "status": "error",
                "severity": "CRITICAL",
                "error": str(exc),
            }
            results.append(error_result)
            log_check(error_result)

    # Summary
    ok = sum(1 for r in results if r.get("status") == "ok")
    minor = sum(1 for r in results if r.get("severity") == "MINOR")
    major = sum(1 for r in results if r.get("severity") == "MAJOR")
    critical = sum(1 for r in results if r.get("severity") == "CRITICAL")

    logger.info(
        "Watchdog complete: %d OK, %d MINOR, %d MAJOR, %d CRITICAL",
        ok, minor, major, critical,
    )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Clarvia Schema Watchdog")
    parser.add_argument("--dry-run", action="store_true", help="Don't send alerts or update schemas")
    parser.add_argument("--init", action="store_true", help="Initialize golden schemas")
    args = parser.parse_args()

    results = run_watchdog(dry_run=args.dry_run, init=args.init)

    if results:
        print(json.dumps(results, indent=2, default=str))

    # Exit with error code if any MAJOR or CRITICAL issues
    has_issues = any(
        r.get("severity") in ("MAJOR", "CRITICAL") for r in results
    )
    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
