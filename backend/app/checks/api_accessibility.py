"""API Accessibility checks (25 points).

Sub-factors:
- Endpoint Existence (7 pts)
- Response Speed (7 pts)
- Auth Documentation (3 pts)
- Rate Limit Info (3 pts)
- API Versioning (2 pts)
- SDK Availability (2 pts)
- Free Tier / Trial (1 pt)
"""

import asyncio
import time
from typing import Any

import aiohttp

from ..config import settings


async def check_endpoint_existence(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Probe common API paths for a reachable endpoint (7 pts max)."""
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
                    return (7, {
                        "endpoint": probe_url,
                        "status": status,
                        "content_type": ct,
                        "reason": "Publicly reachable endpoint returning 2xx",
                    })
                elif status in (401, 403):
                    return (7, {
                        "endpoint": probe_url,
                        "status": status,
                        "reason": "Endpoint exists, requires authentication",
                    })
                elif status >= 500 and best_score < 3:
                    best_score = 3
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
    """Measure p50 latency with HEAD requests (7 pts max)."""
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
        score = 7
    elif p50 < 500:
        score = 5
    elif p50 < 1000:
        score = 3
    elif p50 < 3000:
        score = 1
    else:
        score = 0

    return (score, {"p50_ms": round(p50), "samples": [round(x) for x in latencies]})


async def check_auth_documentation(
    session: aiohttp.ClientSession, base_url: str, openapi_spec: dict | None
) -> tuple[int, dict[str, Any]]:
    """Check for auth documentation (3 pts max)."""
    if openapi_spec:
        components = openapi_spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        if security_schemes:
            return (3, {
                "reason": "OpenAPI spec with security schemes defined",
                "schemes": list(security_schemes.keys()),
            })

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
                    auth_keywords = [
                        "authentication", "authorization", "api key",
                        "bearer token", "oauth", "api_key", "access token",
                    ]
                    matches = [kw for kw in auth_keywords if kw in text_lower]
                    if len(matches) >= 2:
                        return (2, {
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


async def check_rate_limit_info(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check if rate limit info is publicly exposed (3 pts max).

    3 pts = X-RateLimit-* headers present in responses
    2 pts = Rate limit documented on docs pages
    0 pts = No rate limit info
    """
    # Check headers on actual API responses
    probe_urls = [
        base_url,
        f"{base_url}/api",
        f"{base_url}/api/v1",
        f"{base_url}/v1",
    ]

    rate_limit_headers = [
        "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
        "x-rate-limit-limit", "x-rate-limit-remaining", "x-rate-limit-reset",
        "ratelimit-limit", "ratelimit-remaining", "ratelimit-reset",
        "retry-after",
    ]

    for probe_url in probe_urls:
        try:
            async with session.get(
                probe_url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                found_headers = {
                    h: resp.headers[h]
                    for h in rate_limit_headers
                    if h in {k.lower() for k in resp.headers}
                }
                if found_headers:
                    return (3, {
                        "reason": "Rate limit headers exposed in API response",
                        "url": probe_url,
                        "headers": found_headers,
                    })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Check docs for rate limit mentions
    docs_paths = [
        f"{base_url}/docs",
        f"{base_url}/docs/rate-limits",
        f"{base_url}/docs/rate-limiting",
        f"{base_url}/docs/api",
    ]
    for path in docs_paths:
        try:
            async with session.get(
                path, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    text = (await resp.text()).lower()
                    rl_keywords = ["rate limit", "rate-limit", "ratelimit", "throttl", "requests per"]
                    if any(kw in text for kw in rl_keywords):
                        return (2, {
                            "reason": "Rate limit info documented",
                            "url": path,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (0, {"reason": "No rate limit information found"})


async def check_api_versioning(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for API versioning patterns (2 pts max).

    2 pts = Multiple versioned endpoints (v1, v2) or version header
    1 pt  = Single version in URL
    0 pts = No versioning detected
    """
    version_paths = [
        (f"{base_url}/v1", "v1"),
        (f"{base_url}/v2", "v2"),
        (f"{base_url}/v3", "v3"),
        (f"{base_url}/api/v1", "api/v1"),
        (f"{base_url}/api/v2", "api/v2"),
    ]

    found_versions: list[str] = []

    for path, label in version_paths:
        try:
            async with session.head(
                path, timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 500:
                    found_versions.append(label)
                    # Check for API-Version header
                    api_version = resp.headers.get("api-version") or resp.headers.get("x-api-version")
                    if api_version:
                        return (2, {
                            "reason": "API versioning with version header",
                            "versions": found_versions,
                            "header_version": api_version,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    if len(found_versions) >= 2:
        return (2, {
            "reason": "Multiple API versions detected",
            "versions": found_versions,
        })
    elif found_versions:
        return (1, {
            "reason": "Single API version in URL",
            "versions": found_versions,
        })

    return (0, {"reason": "No API versioning detected"})


async def check_sdk_availability(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check if official SDKs exist on PyPI/npm (2 pts max).

    2 pts = SDK found on PyPI or npm
    1 pt  = SDK mentioned in docs
    0 pts = No SDK detected
    """
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    domain = parsed.hostname or ""
    company = domain.replace("www.", "").split(".")[0]

    # Check PyPI
    pypi_url = f"https://pypi.org/pypi/{company}/json"
    npm_url = f"https://registry.npmjs.org/{company}"

    checks = [
        (pypi_url, "pypi"),
        (npm_url, "npm"),
    ]

    for url, registry in checks:
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    return (2, {
                        "reason": f"Official SDK found on {registry}",
                        "url": url,
                        "registry": registry,
                    })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Check docs pages for SDK mentions
    docs_paths = [f"{base_url}/docs", f"{base_url}/docs/sdk", f"{base_url}/docs/libraries"]
    for path in docs_paths:
        try:
            async with session.get(
                path, timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    text = (await resp.text()).lower()
                    sdk_keywords = ["pip install", "npm install", "sdk", "client library", "official library"]
                    if any(kw in text for kw in sdk_keywords):
                        return (1, {
                            "reason": "SDK/library mentioned in documentation",
                            "url": path,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (0, {"reason": "No SDK/library detected"})


async def check_free_tier(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for free tier or trial availability (1 pt max)."""
    paths = [
        f"{base_url}/pricing",
        f"{base_url}/plans",
        f"{base_url}/docs",
        base_url,
    ]

    for path in paths:
        try:
            async with session.get(
                path, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    text = (await resp.text()).lower()
                    free_keywords = [
                        "free tier", "free plan", "free trial", "freemium",
                        "no credit card", "get started free", "start free",
                        "free forever", "open source",
                    ]
                    if any(kw in text for kw in free_keywords):
                        return (1, {
                            "reason": "Free tier or trial available",
                            "url": path,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (0, {"reason": "No free tier or trial detected"})


async def run_api_accessibility(
    session: aiohttp.ClientSession, base_url: str, openapi_spec: dict | None = None
) -> dict:
    """Run all API Accessibility checks. Returns dimension result dict."""
    # Endpoint existence
    endpoint_score, endpoint_evidence = await check_endpoint_existence(session, base_url)

    # Determine best endpoint for latency test
    latency_endpoint = endpoint_evidence.get("endpoint", base_url)

    # Run remaining checks concurrently
    (latency_score, latency_ev), (auth_score, auth_ev), \
        (rate_score, rate_ev), (ver_score, ver_ev), \
        (sdk_score, sdk_ev), (free_score, free_ev) = await asyncio.gather(
        measure_latency(session, latency_endpoint),
        check_auth_documentation(session, base_url, openapi_spec),
        check_rate_limit_info(session, base_url),
        check_api_versioning(session, base_url),
        check_sdk_availability(session, base_url),
        check_free_tier(session, base_url),
    )

    total = endpoint_score + latency_score + auth_score + rate_score + ver_score + sdk_score + free_score

    return {
        "score": total,
        "max": 25,
        "sub_factors": {
            "endpoint_existence": {
                "score": endpoint_score,
                "max": 7,
                "label": "Endpoint Existence",
                "evidence": endpoint_evidence,
            },
            "response_speed": {
                "score": latency_score,
                "max": 7,
                "label": "Response Speed",
                "evidence": latency_ev,
            },
            "auth_documentation": {
                "score": auth_score,
                "max": 3,
                "label": "Auth Documentation",
                "evidence": auth_ev,
            },
            "rate_limit_info": {
                "score": rate_score,
                "max": 3,
                "label": "Rate Limit Transparency",
                "evidence": rate_ev,
            },
            "api_versioning": {
                "score": ver_score,
                "max": 2,
                "label": "API Versioning",
                "evidence": ver_ev,
            },
            "sdk_availability": {
                "score": sdk_score,
                "max": 2,
                "label": "SDK Availability",
                "evidence": sdk_ev,
            },
            "free_tier": {
                "score": free_score,
                "max": 1,
                "label": "Free Tier / Trial",
                "evidence": free_ev,
            },
        },
    }
