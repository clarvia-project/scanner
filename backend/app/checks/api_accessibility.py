"""API Accessibility checks (25 points).

Sub-factors:
- Endpoint Existence (10 pts)
- Response Speed (10 pts)
- Auth Documentation (5 pts)
"""

import asyncio
import time
from typing import Any

import aiohttp

from ..config import settings


async def check_endpoint_existence(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Probe common API paths for a reachable endpoint (10 pts max)."""
    probes = [
        base_url,
        f"{base_url}/health",
        f"{base_url}/api",
        f"{base_url}/api/v1",
        f"{base_url}/v1",
        f"{base_url}/v2",
        f"{base_url}/graphql",
        f"{base_url}/status",
    ]

    best_score = 0
    best_evidence: dict[str, Any] = {"reason": "No reachable API endpoint found"}

    for probe_url in probes:
        try:
            async with session.get(
                probe_url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                ct = resp.headers.get("content-type", "")
                status = resp.status

                if status < 300:
                    return (10, {
                        "endpoint": probe_url,
                        "status": status,
                        "content_type": ct,
                        "reason": "Publicly reachable endpoint returning 2xx",
                    })
                elif status in (401, 403):
                    # Endpoint exists, requires auth — still full credit
                    return (10, {
                        "endpoint": probe_url,
                        "status": status,
                        "reason": "Endpoint exists, requires authentication",
                    })
                elif status >= 500 and best_score < 5:
                    best_score = 5
                    best_evidence = {
                        "endpoint": probe_url,
                        "status": status,
                        "reason": "Endpoint exists but returning server errors",
                    }
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (best_score, best_evidence)


async def measure_latency(
    session: aiohttp.ClientSession, endpoint: str
) -> tuple[int, dict[str, Any]]:
    """Measure p50 latency with HEAD requests (10 pts max)."""
    latencies: list[float] = []

    for _ in range(settings.latency_samples):
        start = time.monotonic()
        try:
            async with session.head(
                endpoint,
                timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ):
                elapsed_ms = (time.monotonic() - start) * 1000
                latencies.append(elapsed_ms)
        except Exception:
            latencies.append(10_000)
        await asyncio.sleep(settings.latency_delay)

    if not latencies:
        return (0, {"reason": "All latency probes failed", "p50_ms": None})

    latencies.sort()
    p50 = latencies[len(latencies) // 2]

    if p50 < 200:
        score = 10
    elif p50 < 500:
        score = 7
    elif p50 < 1000:
        score = 4
    elif p50 < 3000:
        score = 1
    else:
        score = 0

    return (score, {"p50_ms": round(p50), "samples": [round(x) for x in latencies]})


async def check_auth_documentation(
    session: aiohttp.ClientSession, base_url: str, openapi_spec: dict | None
) -> tuple[int, dict[str, Any]]:
    """Check for auth documentation (5 pts max).

    5 pts = OpenAPI spec with security schemes
    3 pts = Docs page with auth section
    1 pt  = Auth mentioned
    0 pts = No auth docs
    """
    # If we have an OpenAPI spec with security schemes
    if openapi_spec:
        components = openapi_spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        if security_schemes:
            return (5, {
                "reason": "OpenAPI spec with security schemes defined",
                "schemes": list(security_schemes.keys()),
            })

    # Check docs pages for auth content
    auth_paths = [
        f"{base_url}/docs",
        f"{base_url}/docs/authentication",
        f"{base_url}/docs/auth",
        f"{base_url}/docs/api",
        f"{base_url}/reference",
        f"{base_url}/api",
    ]

    for path in auth_paths:
        try:
            async with session.get(
                path, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    text = await resp.text()
                    text_lower = text.lower()
                    # Look for auth-related keywords
                    auth_keywords = [
                        "authentication", "authorization", "api key",
                        "bearer token", "oauth", "api_key", "access token",
                    ]
                    matches = [kw for kw in auth_keywords if kw in text_lower]
                    if len(matches) >= 2:
                        return (3, {
                            "reason": "Docs page with auth section found",
                            "url": path,
                            "keywords_found": matches[:5],
                        })
                    elif matches:
                        return (1, {
                            "reason": "Auth mentioned but limited detail",
                            "url": path,
                            "keywords_found": matches,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (0, {"reason": "No auth documentation found"})


async def run_api_accessibility(
    session: aiohttp.ClientSession, base_url: str, openapi_spec: dict | None = None
) -> dict:
    """Run all API Accessibility checks. Returns dimension result dict."""
    # Endpoint existence
    endpoint_score, endpoint_evidence = await check_endpoint_existence(session, base_url)

    # Determine best endpoint for latency test
    latency_endpoint = endpoint_evidence.get("endpoint", base_url)

    # Latency measurement
    latency_score, latency_evidence = await measure_latency(session, latency_endpoint)

    # Auth documentation
    auth_score, auth_evidence = await check_auth_documentation(
        session, base_url, openapi_spec
    )

    total = endpoint_score + latency_score + auth_score

    return {
        "score": total,
        "max": 25,
        "sub_factors": {
            "endpoint_existence": {
                "score": endpoint_score,
                "max": 10,
                "label": "Endpoint Existence",
                "evidence": endpoint_evidence,
            },
            "response_speed": {
                "score": latency_score,
                "max": 10,
                "label": "Response Speed",
                "evidence": latency_evidence,
            },
            "auth_documentation": {
                "score": auth_score,
                "max": 5,
                "label": "Auth Documentation",
                "evidence": auth_evidence,
            },
        },
    }
