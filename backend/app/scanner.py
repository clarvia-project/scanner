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


def _generate_recommendations(dimensions: dict, onchain: dict) -> list[str]:
    """Rule-based recommendation generator (no Claude API for MVP)."""
    recs: list[str] = []

    # API Accessibility
    api = dimensions.get("api_accessibility", {})
    api_subs = api.get("sub_factors", {})

    ep = api_subs.get("endpoint_existence", {})
    if ep.get("score", 0) < 10:
        recs.append(
            "Ensure your API has a publicly reachable endpoint returning 2xx "
            "responses to gain up to 10 points in API Accessibility."
        )

    speed = api_subs.get("response_speed", {})
    if speed.get("score", 0) < 7:
        p50 = speed.get("evidence", {}).get("p50_ms")
        msg = "Optimize API response time to under 200ms for full marks."
        if p50:
            msg += f" Current p50: {p50}ms."
        recs.append(msg)

    auth = api_subs.get("auth_documentation", {})
    if auth.get("score", 0) < 5:
        recs.append(
            "Publish an OpenAPI/Swagger spec with security schemes to earn "
            "5 points in Auth Documentation."
        )

    # Data Structuring
    ds = dimensions.get("data_structuring", {})
    ds_subs = ds.get("sub_factors", {})

    schema = ds_subs.get("schema_definition", {})
    if schema.get("score", 0) < 10:
        recs.append(
            "Publish a complete OpenAPI 3.x spec with JSON Schema models "
            "to maximize Schema Definition score (up to 10 points)."
        )

    pricing = ds_subs.get("pricing_quantified", {})
    if pricing.get("score", 0) < 5:
        recs.append(
            "Add machine-readable pricing (JSON or structured data) "
            f"to improve Pricing score by up to {8 - pricing.get('score', 0)} points."
        )

    errors = ds_subs.get("error_structure", {})
    if errors.get("score", 0) < 4:
        recs.append(
            "Implement standardized error responses (RFC 7807 or similar) "
            "with error codes and remediation hints."
        )

    # Agent Compatibility
    ac = dimensions.get("agent_compatibility", {})
    ac_subs = ac.get("sub_factors", {})

    mcp = ac_subs.get("mcp_server_exists", {})
    if mcp.get("score", 0) < 15:
        recs.append(
            "Publish an MCP (Model Context Protocol) server to gain up to "
            "15 points in Agent Compatibility — the single highest-impact improvement."
        )

    robots = ac_subs.get("robots_txt_agent_policy", {})
    if robots.get("score", 0) < 5:
        recs.append(
            "Add AI-agent-specific User-agent rules to robots.txt "
            "to signal your policy to AI crawlers."
        )

    sitemap = ac_subs.get("sitemap_discovery", {})
    if sitemap.get("score", 0) < 5:
        recs.append(
            "Create a .well-known/ai-plugin.json or ensure sitemap.xml "
            "includes API documentation URLs for agent discovery."
        )

    # Trust Signals
    ts = dimensions.get("trust_signals", {})
    ts_subs = ts.get("sub_factors", {})

    uptime = ts_subs.get("success_rate_uptime", {})
    if uptime.get("score", 0) < 7:
        recs.append(
            "Set up a public status page (e.g., statuspage.io) to demonstrate "
            "uptime commitment and earn up to 10 Trust Signal points."
        )

    docs = ts_subs.get("documentation_quality", {})
    if docs.get("score", 0) < 5:
        recs.append(
            "Expand developer documentation with guides, tutorials, and "
            "code examples in 3+ languages."
        )

    update = ts_subs.get("update_frequency", {})
    if update.get("score", 0) < 5:
        recs.append(
            "Maintain a public changelog updated at least monthly to demonstrate "
            "active maintenance."
        )

    # Sort by potential impact (highest possible gain first) and cap at 5
    return recs[:5]


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


async def run_scan(url: str) -> ScanResponse:
    """Execute the full 5-phase scan pipeline."""
    start_time = time.monotonic()

    # Normalize URL
    url = _normalize_url(url)
    scan_id = _generate_scan_id(url)
    service_name = _extract_service_name(url)

    # Validate URL is reachable
    connector = aiohttp.TCPConnector(limit=20, ssl=False)
    async with aiohttp.ClientSession(
        connector=connector,
        headers={"User-Agent": "ClarviaScannerBot/1.0 (+https://clarvia.io/bot)"},
    ) as session:
        # Phase 1: Quick reachability check
        try:
            async with session.head(
                url,
                timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True,
            ):
                pass
        except Exception:
            # Try GET as fallback (some sites block HEAD)
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                    allow_redirects=True,
                ):
                    pass
            except Exception as e:
                raise ValueError(f"URL unreachable: {url} — {type(e).__name__}")

        # Phase 2+3: Run all dimension checks concurrently
        # Data structuring runs first because it discovers OpenAPI spec needed by API checks
        ds_result, openapi_spec = await run_data_structuring(session, url)

        # Now run the rest concurrently (API accessibility uses the discovered spec)
        api_task = run_api_accessibility(session, url, openapi_spec)
        ac_task = run_agent_compatibility(session, url)
        ts_task = run_trust_signals(session, url)
        oc_task = run_onchain_bonus(url)

        api_result, ac_result, ts_result, oc_result = await asyncio.gather(
            api_task, ac_task, ts_task, oc_task
        )

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
