"""Main scan orchestrator — async 5-phase pipeline."""

import asyncio
import hashlib
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import aiohttp

from .checks.api_accessibility import run_api_accessibility
from .checks.agent_compatibility import run_agent_compatibility
from .checks.data_structuring import run_data_structuring
from .checks.onchain_bonus import run_onchain_bonus
from .checks.trust_signals import run_trust_signals
from .config import settings
from .models import (
    DimensionResult,
    OnchainBonusResult,
    ScanResponse,
    SubFactorResult,
)

# In-memory cache: scan_id -> (result, timestamp)
_scan_cache: dict[str, tuple[ScanResponse, float]] = {}


def _generate_scan_id(url: str) -> str:
    """Generate a deterministic scan ID from URL + timestamp."""
    ts = str(time.time())
    raw = f"{url}:{ts}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"scn_{h}"


def _normalize_url(url: str) -> str:
    """Normalize input URL: add https://, strip trailing slash."""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"
    url = url.rstrip("/")
    return url


import ipaddress
import socket


def _validate_scan_url(url: str) -> None:
    """Block SSRF: reject private/reserved IP ranges and dangerous schemes."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname")

    blocked_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    if hostname.lower() in blocked_hosts:
        raise ValueError("Cannot scan localhost/loopback addresses")

    try:
        resolved_ip = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(resolved_ip)
        if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
            raise ValueError(f"Cannot scan private/reserved IP range: {resolved_ip}")
    except socket.gaierror:
        pass  # DNS resolution failure — let aiohttp handle it


def _extract_service_name(url: str) -> str:
    """Extract a human-friendly service name from URL."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    # Remove www. and TLD
    parts = hostname.replace("www.", "").split(".")
    if parts:
        name = parts[0].capitalize()
        return name
    return hostname


def _get_rating(score: int) -> str:
    """Map score to rating label."""
    if score >= 90:
        return "Exceptional"
    elif score >= 75:
        return "Strong"
    elif score >= 60:
        return "Moderate"
    elif score >= 40:
        return "Basic"
    else:
        return "Low"


# Scoring Methodology v1.1 (2026-03-25)
# Weights are based on agent-builder pain frequency:
# - Rate limits: #1 cause of agent failures in production (6pts)
# - MCP support: important but not required for agent compatibility (7pts)
# - Idempotency: critical for agent retry safety (3pts)
# - Response speed: agents timeout at 30s, target <200ms (6pts)
# - Streaming: real-time data critical for agentic workflows (3pts)
# Total: 100 base + up to 10 onchain bonus
# Full methodology: clarvia.art/methodology


def _generate_recommendations(
    dimensions: dict, onchain: dict, *, max_recs: int = 5
) -> list[str]:
    """Evidence-based recommendation generator.

    Every recommendation is derived from actual scan data gaps.
    No hardcoded generic advice — all recs tied to measured sub-factors.
    """
    # (potential_gain, recommendation_text)
    recs: list[tuple[int, str]] = []

    # ── API Accessibility (25 pts) ──
    api = dimensions.get("api_accessibility", {})
    api_subs = api.get("sub_factors", {})

    ep = api_subs.get("endpoint_existence", {})
    if ep.get("score", 0) < ep.get("max", 7):
        gap = ep.get("max", 7) - ep.get("score", 0)
        recs.append((gap,
            "Ensure your API has a publicly reachable endpoint returning 2xx "
            "responses to gain up to 7 points in API Accessibility."
        ))

    speed = api_subs.get("response_speed", {})
    if speed.get("score", 0) < speed.get("max", 6):
        gap = speed.get("max", 6) - speed.get("score", 0)
        p50 = speed.get("evidence", {}).get("p50_ms")
        msg = "Optimize API response time to under 200ms for full marks (agents timeout at 30s, target <200ms)."
        if p50:
            msg += f" Current p50: {p50}ms."
        recs.append((gap, msg))

    rate = api_subs.get("rate_limit_info", {})
    if rate.get("score", 0) < rate.get("max", 6):
        gap = rate.get("max", 6) - rate.get("score", 0)
        current = rate.get("score", 0)
        if current == 0:
            recs.append((gap,
                "CRITICAL: Expose X-RateLimit-* headers (limit, remaining, reset) "
                "and Retry-After in API responses. Rate limits are the #1 cause of "
                "agent failures in production — agents need these to self-throttle."
            ))
        elif current < 4:
            recs.append((gap,
                "Add complete rate limit headers: X-RateLimit-Limit, X-RateLimit-Remaining, "
                "X-RateLimit-Reset, AND Retry-After for full 6 points."
            ))
        else:
            recs.append((gap,
                "Add Retry-After header support to complement existing rate limit headers."
            ))

    auth = api_subs.get("auth_documentation", {})
    if auth.get("score", 0) < auth.get("max", 3):
        gap = auth.get("max", 3) - auth.get("score", 0)
        recs.append((gap,
            "Document authentication methods with code examples (curl, "
            "Bearer tokens, API keys) for agent integration."
        ))

    ver = api_subs.get("api_versioning", {})
    if ver.get("score", 0) < ver.get("max", 1):
        gap = ver.get("max", 1) - ver.get("score", 0)
        recs.append((gap,
            "Add versioned API paths (v1, v2) or API-Version header."
        ))

    sdk = api_subs.get("sdk_availability", {})
    if sdk.get("score", 0) < sdk.get("max", 1):
        gap = sdk.get("max", 1) - sdk.get("score", 0)
        recs.append((gap,
            "Publish official SDKs on PyPI/npm for programmatic agent integration."
        ))

    free = api_subs.get("free_tier", {})
    if free.get("score", 0) < free.get("max", 1):
        gap = free.get("max", 1) - free.get("score", 0)
        recs.append((gap,
            "Offer a free tier or trial so agents can test without payment commitment."
        ))

    # ── Data Structuring (25 pts) ──
    ds = dimensions.get("data_structuring", {})
    ds_subs = ds.get("sub_factors", {})

    schema = ds_subs.get("schema_definition", {})
    if schema.get("score", 0) < schema.get("max", 7):
        gap = schema.get("max", 7) - schema.get("score", 0)
        recs.append((gap,
            "Publish a complete OpenAPI 3.x spec with JSON Schema models "
            "to maximize Schema Definition score."
        ))

    json_resp = ds_subs.get("json_response", {})
    if json_resp.get("score", 0) < json_resp.get("max", 5):
        gap = json_resp.get("max", 5) - json_resp.get("score", 0)
        recs.append((gap,
            "Return consistent JSON responses with proper Content-Type headers."
        ))

    errors = ds_subs.get("error_structure", {})
    if errors.get("score", 0) < errors.get("max", 5):
        gap = errors.get("max", 5) - errors.get("score", 0)
        recs.append((gap,
            "Implement standardized error responses (RFC 7807 or similar) "
            "with error codes and remediation hints."
        ))

    webhook = ds_subs.get("webhook_support", {})
    if webhook.get("score", 0) < webhook.get("max", 3):
        gap = webhook.get("max", 3) - webhook.get("score", 0)
        recs.append((gap,
            "Add webhook support so agents receive real-time event "
            "notifications instead of polling."
        ))

    batch = ds_subs.get("batch_api", {})
    if batch.get("score", 0) < batch.get("max", 3):
        gap = batch.get("max", 3) - batch.get("score", 0)
        recs.append((gap,
            "Implement batch/bulk API endpoints to let agents process "
            "multiple items in a single request."
        ))

    content_neg = ds_subs.get("content_negotiation", {})
    if content_neg.get("score", 0) < content_neg.get("max", 2):
        gap = content_neg.get("max", 2) - content_neg.get("score", 0)
        recs.append((gap,
            "Support content negotiation (Accept headers) for multiple formats."
        ))

    # ── Agent Compatibility (25 pts) ──
    ac = dimensions.get("agent_compatibility", {})
    ac_subs = ac.get("sub_factors", {})

    mcp = ac_subs.get("mcp_server_exists", {})
    if mcp.get("score", 0) < mcp.get("max", 7):
        gap = mcp.get("max", 7) - mcp.get("score", 0)
        recs.append((gap,
            "Publish an MCP (Model Context Protocol) server — the highest-impact "
            "improvement for agent compatibility (up to 7 points)."
        ))

    robot = ac_subs.get("robot_policy", {})
    if robot.get("score", 0) < robot.get("max", 5):
        gap = robot.get("max", 5) - robot.get("score", 0)
        recs.append((gap,
            "Add explicit AI agent rules in robots.txt (User-Agent: GPTBot, "
            "Claude, etc.) with Allow directives for API paths."
        ))

    discovery = ac_subs.get("discovery_mechanism", {})
    if discovery.get("score", 0) < discovery.get("max", 5):
        gap = discovery.get("max", 5) - discovery.get("score", 0)
        recs.append((gap,
            "Add discovery mechanisms: .well-known/ai-plugin.json, "
            ".well-known/mcp.json, and sitemap.xml with API doc references."
        ))

    idempotency = ac_subs.get("idempotency_support", {})
    if idempotency.get("score", 0) < idempotency.get("max", 3):
        gap = idempotency.get("max", 3) - idempotency.get("score", 0)
        recs.append((gap,
            "Support Idempotency-Key header for POST/PUT requests — critical "
            "for agent retry safety to prevent duplicate side effects."
        ))

    pagination = ac_subs.get("pagination_pattern", {})
    if pagination.get("score", 0) < pagination.get("max", 2):
        gap = pagination.get("max", 2) - pagination.get("score", 0)
        recs.append((gap,
            "Implement cursor or offset-based pagination in list endpoints "
            "so agents can process large datasets safely."
        ))

    streaming = ac_subs.get("streaming_support", {})
    if streaming.get("score", 0) < streaming.get("max", 3):
        gap = streaming.get("max", 3) - streaming.get("score", 0)
        recs.append((gap,
            "Add SSE (Server-Sent Events) streaming endpoints for real-time "
            "data delivery to agent workflows."
        ))

    # ── Trust Signals (25 pts) ──
    ts = dimensions.get("trust_signals", {})
    ts_subs = ts.get("sub_factors", {})

    uptime = ts_subs.get("success_rate_uptime", {})
    if uptime.get("score", 0) < uptime.get("max", 6):
        gap = uptime.get("max", 6) - uptime.get("score", 0)
        recs.append((gap,
            "Set up a public status page (e.g., statuspage.io) to demonstrate "
            "uptime commitment."
        ))

    consistency = ts_subs.get("response_consistency", {})
    if consistency.get("score", 0) < consistency.get("max", 4):
        gap = consistency.get("max", 4) - consistency.get("score", 0)
        recs.append((gap,
            "Ensure deterministic API responses — agents rely on consistent "
            "outputs for reliable automation."
        ))

    tls = ts_subs.get("tls_security", {})
    if tls.get("score", 0) < tls.get("max", 4):
        gap = tls.get("max", 4) - tls.get("score", 0)
        recs.append((gap,
            "Ensure valid TLS/SSL certificate with strong configuration."
        ))

    error_quality = ts_subs.get("error_response_quality", {})
    if error_quality.get("score", 0) < error_quality.get("max", 3):
        gap = error_quality.get("max", 3) - error_quality.get("score", 0)
        recs.append((gap,
            "Include documentation links in error responses so agents "
            "can self-diagnose and recover from failures."
        ))

    deprecation = ts_subs.get("deprecation_policy", {})
    if deprecation.get("score", 0) < deprecation.get("max", 2):
        gap = deprecation.get("max", 2) - deprecation.get("score", 0)
        recs.append((gap,
            "Publish a deprecation/sunset policy so agents know how long "
            "current API versions will be supported."
        ))

    changelog = ts_subs.get("changelog_exists", {})
    if changelog.get("score", 0) < changelog.get("max", 3):
        gap = changelog.get("max", 3) - changelog.get("score", 0)
        recs.append((gap,
            "Maintain a public changelog so agents can detect API changes."
        ))

    contact = ts_subs.get("contact_info", {})
    if contact.get("score", 0) < contact.get("max", 3):
        gap = contact.get("max", 3) - contact.get("score", 0)
        recs.append((gap,
            "Provide developer contact info or support channel for API issues."
        ))

    # Sort by potential impact (highest gain first) and cap
    recs.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in recs[:max_recs]]


def _build_dimension_result(raw: dict) -> DimensionResult:
    """Convert raw check result dict to DimensionResult model."""
    sub_factors = {}
    for key, sf in raw.get("sub_factors", {}).items():
        sub_factors[key] = SubFactorResult(
            score=sf["score"],
            max=sf["max"],
            label=sf["label"],
            evidence=sf.get("evidence", {}),
        )
    return DimensionResult(
        score=raw["score"],
        max=raw.get("max", 25),
        sub_factors=sub_factors,
    )


async def _discover_api_url(session: aiohttp.ClientSession, base_url: str) -> str | None:
    """Try to find the API subdomain for a given website URL."""
    parsed = urlparse(base_url)
    hostname = parsed.hostname or ""

    # If already an API URL, skip
    if hostname.startswith("api."):
        return None

    # Try common API subdomain patterns
    candidates = [
        f"https://api.{hostname}",
        f"https://api.{hostname}/v1",
        f"https://api.{hostname}/v2",
    ]

    for candidate in candidates:
        try:
            async with session.head(
                candidate,
                timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True,
            ) as resp:
                if resp.status < 500:  # Even 401/403 means API exists
                    return candidate.rstrip("/v1").rstrip("/v2").rstrip("/")
        except Exception:
            continue

    return None


async def run_scan(
    url: str,
    auth_headers: dict[str, str] | None = None,
) -> ScanResponse:
    """Execute the full 5-phase scan pipeline.

    Args:
        url: Target URL to scan.
        auth_headers: Optional auth headers forwarded to the target API.
                      Never stored or logged.
    """
    start_time = time.monotonic()
    authenticated = bool(auth_headers)

    # Normalize and validate URL (SSRF protection)
    url = _normalize_url(url)
    _validate_scan_url(url)
    scan_id = _generate_scan_id(url)
    service_name = _extract_service_name(url)

    # Build session headers — include auth headers if provided
    session_headers: dict[str, str] = {
        "User-Agent": "ClarviaScannerBot/1.0 (+https://clarvia.io/bot)",
    }
    if auth_headers:
        session_headers.update(auth_headers)

    # Validate URL is reachable
    connector = aiohttp.TCPConnector(limit=20, ssl=False)
    async with aiohttp.ClientSession(
        connector=connector,
        headers=session_headers,
    ) as session:
        # Phase 1: Quick reachability check + API URL discovery
        try:
            async with session.head(
                url,
                timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True,
            ):
                pass
        except Exception:
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                    allow_redirects=True,
                ):
                    pass
            except Exception as e:
                raise ValueError(f"URL unreachable: {url} — {type(e).__name__}")

        # Discover API subdomain (api.stripe.com, api.github.com, etc.)
        api_url = await _discover_api_url(session, url)

        # Use both website URL and API URL for comprehensive scanning
        scan_urls = [url]
        if api_url:
            scan_urls.append(api_url)

        # Phase 2+3: Run data structuring on both URLs, take best result
        best_ds_result = None
        best_openapi_spec = None
        for scan_url in scan_urls:
            ds_result, openapi_spec = await run_data_structuring(
                session, scan_url, api_url=api_url,
            )
            if best_ds_result is None or ds_result["score"] > best_ds_result["score"]:
                best_ds_result = ds_result
                best_openapi_spec = openapi_spec
        ds_result = best_ds_result
        openapi_spec = best_openapi_spec

        # Run the rest concurrently
        # For API accessibility: check both website and API URL, take best
        api_tasks = [run_api_accessibility(session, url, openapi_spec)]
        if api_url:
            api_tasks.append(run_api_accessibility(session, api_url, openapi_spec))

        ac_task = run_agent_compatibility(session, url)
        ts_task = run_trust_signals(session, url)
        oc_task = run_onchain_bonus(url)

        all_results = await asyncio.gather(*api_tasks, ac_task, ts_task, oc_task)

        # Pick best API result
        api_results = all_results[:len(api_tasks)]
        api_result = max(api_results, key=lambda r: r["score"])
        ac_result, ts_result, oc_result = all_results[len(api_tasks):]

    # Phase 4: Score calculation
    base_score = (
        api_result["score"]
        + ds_result["score"]
        + ac_result["score"]
        + ts_result["score"]
    )
    onchain_score = oc_result["score"]
    clarvia_score = min(100, base_score + onchain_score)

    # Phase 5: Recommendations (rule-based for MVP)
    dimensions_raw = {
        "api_accessibility": api_result,
        "data_structuring": ds_result,
        "agent_compatibility": ac_result,
        "trust_signals": ts_result,
    }
    recommendations = _generate_recommendations(dimensions_raw, oc_result)

    # Build response
    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    response = ScanResponse(
        scan_id=scan_id,
        url=url,
        service_name=service_name,
        clarvia_score=clarvia_score,
        rating=_get_rating(clarvia_score),
        dimensions={
            "api_accessibility": _build_dimension_result(api_result),
            "data_structuring": _build_dimension_result(ds_result),
            "agent_compatibility": _build_dimension_result(ac_result),
            "trust_signals": _build_dimension_result(ts_result),
        },
        onchain_bonus=OnchainBonusResult(
            score=oc_result["score"],
            max=25,
            applicable=oc_result.get("applicable", False),
            sub_factors={
                k: SubFactorResult(
                    score=v["score"], max=v["max"],
                    label=v["label"], evidence=v.get("evidence", {}),
                )
                for k, v in oc_result.get("sub_factors", {}).items()
            },
        ),
        top_recommendations=recommendations,
        scanned_at=datetime.now(timezone.utc),
        scan_duration_ms=elapsed_ms,
        authenticated_scan=authenticated,
    )

    # Cache result
    _scan_cache[scan_id] = (response, time.time())

    return response


def get_cached_scan(scan_id: str) -> ScanResponse | None:
    """Retrieve a cached scan result by ID. Returns None if expired or missing."""
    entry = _scan_cache.get(scan_id)
    if entry is None:
        return None
    result, ts = entry
    if time.time() - ts > settings.cache_ttl_seconds:
        del _scan_cache[scan_id]
        return None
    return result


def cleanup_cache() -> int:
    """Remove expired cache entries. Returns number of entries removed."""
    now = time.time()
    expired = [
        k for k, (_, ts) in _scan_cache.items()
        if now - ts > settings.cache_ttl_seconds
    ]
    for k in expired:
        del _scan_cache[k]
    return len(expired)
