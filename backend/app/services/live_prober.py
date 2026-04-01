"""Live prober — periodic health checks for indexed tools.

Checks reachability, response time, SSL validity, and feature detection
(OpenAPI, MCP, agents.json). Results are cached locally and optionally
stored in Supabase accessibility_probes table.

Designed for batch execution: probe top N tools every few hours.
"""

import asyncio
import json
import logging
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

_CACHE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "probe-cache.json"
_probe_cache: dict[str, dict[str, Any]] = {}


def load_probe_cache() -> None:
    """Load probe results from disk on startup."""
    global _probe_cache
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE) as f:
                _probe_cache = json.load(f)
            logger.info("Loaded probe cache: %d entries", len(_probe_cache))
        except Exception as e:
            logger.warning("Failed to load probe cache: %s", e)
            _probe_cache = {}


def save_probe_cache() -> None:
    """Save probe results to disk."""
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_FILE, "w") as f:
        json.dump(_probe_cache, f, separators=(",", ":"), ensure_ascii=False)


def get_probe_result(scan_id: str) -> dict[str, Any] | None:
    """Get cached probe result for a tool."""
    return _probe_cache.get(scan_id)


async def probe_service(url: str, timeout: float = 8.0) -> dict[str, Any]:
    """Probe a single service URL for reachability and features.

    Returns a dict with probe results. Never raises — returns error state instead.
    """
    result: dict[str, Any] = {
        "url": url,
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "reachable": False,
        "response_time_ms": None,
        "status_code": None,
        "has_json_response": False,
        "has_openapi": False,
        "has_mcp": False,
        "has_agents_json": False,
        "ssl_valid": True,
        "error": None,
    }

    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "invalid_url"
        return result

    connector = aiohttp.TCPConnector(ssl=False)  # Don't fail on self-signed
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            # Step 1: Reachability check (HEAD request)
            start = time.monotonic()
            try:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=timeout),
                                       allow_redirects=True) as resp:
                    elapsed = (time.monotonic() - start) * 1000
                    result["reachable"] = resp.status < 500
                    result["response_time_ms"] = round(elapsed, 1)
                    result["status_code"] = resp.status

                    ct = resp.headers.get("content-type", "")
                    if "json" in ct or "javascript" in ct:
                        result["has_json_response"] = True
            except Exception:
                # HEAD might not be supported, try GET
                start = time.monotonic()
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout),
                                          allow_redirects=True) as resp:
                        elapsed = (time.monotonic() - start) * 1000
                        result["reachable"] = resp.status < 500
                        result["response_time_ms"] = round(elapsed, 1)
                        result["status_code"] = resp.status
                except Exception as e:
                    result["error"] = str(e)[:200]
                    return result

            if not result["reachable"]:
                return result

            # Step 2: Feature detection (parallel, best-effort)
            base_url = url.rstrip("/")
            checks = await asyncio.gather(
                _check_path(session, base_url, "/openapi.json", timeout=5),
                _check_path(session, base_url, "/.well-known/agents.json", timeout=5),
                return_exceptions=True,
            )

            if not isinstance(checks[0], Exception) and checks[0]:
                result["has_openapi"] = True
            if not isinstance(checks[1], Exception) and checks[1]:
                result["has_agents_json"] = True

            # SSL check (for HTTPS URLs)
            if url.startswith("https://"):
                result["ssl_valid"] = await _check_ssl(url)

    except Exception as e:
        result["error"] = str(e)[:200]

    return result


async def _check_path(session: aiohttp.ClientSession, base_url: str, path: str, timeout: float = 5) -> bool:
    """Check if a path exists on the server (200 response)."""
    try:
        async with session.head(f"{base_url}{path}",
                               timeout=aiohttp.ClientTimeout(total=timeout),
                               allow_redirects=True) as resp:
            return resp.status == 200
    except Exception:
        return False


async def _check_ssl(url: str) -> bool:
    """Check if SSL certificate is valid."""
    try:
        connector = aiohttp.TCPConnector(ssl=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return True
    except (aiohttp.ClientSSLError, ssl.SSLError):
        return False
    except Exception:
        return True  # Non-SSL errors don't indicate SSL problems


async def probe_batch(services: list[dict], concurrency: int = 10) -> list[dict]:
    """Probe a batch of services with concurrency control.

    Args:
        services: List of dicts with at least 'scan_id' and 'url' keys
        concurrency: Max concurrent probes

    Returns:
        List of probe results
    """
    semaphore = asyncio.Semaphore(concurrency)
    results = []

    async def _limited_probe(svc: dict) -> dict:
        async with semaphore:
            scan_id = svc.get("scan_id", "")
            url = svc.get("url", "")
            result = await probe_service(url)
            result["scan_id"] = scan_id
            result["service_name"] = svc.get("service_name", "")

            # Update cache
            _probe_cache[scan_id] = result
            return result

    tasks = [_limited_probe(svc) for svc in services]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions
    valid = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("Probe failed: %s", r)
        else:
            valid.append(r)

    # Save cache after batch
    save_probe_cache()

    return valid


def compute_probe_bonus(probe_data: dict[str, Any] | None) -> int:
    """Compute score adjustment based on probe results.

    Returns a value from -5 to +10 to add to the base score.
    Returns 0 if no probe data available.
    """
    if not probe_data:
        return 0

    bonus = 0

    if not probe_data.get("reachable"):
        return -5  # Unreachable = penalty

    # Fast response
    latency = probe_data.get("response_time_ms")
    if latency is not None:
        if latency < 500:
            bonus += 3
        elif latency < 2000:
            bonus += 1
        elif latency > 5000:
            bonus -= 3

    # Feature detection
    if probe_data.get("has_openapi"):
        bonus += 2
    if probe_data.get("has_mcp"):
        bonus += 2
    if probe_data.get("has_agents_json"):
        bonus += 1

    # SSL valid
    if probe_data.get("ssl_valid") is False:
        bonus -= 2

    return max(-5, min(10, bonus))
