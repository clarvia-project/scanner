"""API Accessibility checks (25 points).

# Scoring Methodology v1.1 (2026-03-25)
# Weights are based on agent-builder pain frequency:
# - Rate limits: #1 cause of agent failures in production (6pts)
# - Response speed: agents timeout at 30s, target <200ms (6pts)
# - Endpoint existence: fundamental reachability (7pts)
# - Auth documentation: agents need to know how to authenticate (3pts)
# - Versioning: nice-to-have, agents can adapt (1pt)
# - SDK availability: nice-to-have, raw HTTP works (1pt)
# - Free tier: minor signal (1pt)
# Full methodology: clarvia.art/methodology

Sub-factors:
- Endpoint Existence (7 pts)
- Response Speed (6 pts)
- Auth Documentation (3 pts)
- Rate Limit Info (6 pts)  — #1 agent failure cause (429s)
- API Versioning (1 pt)
- SDK Availability (1 pt)
- Free Tier / Trial (1 pt)
"""

import asyncio
import math
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
                    # Differentiate JSON API endpoints from HTML pages
                    is_api = "json" in ct or "xml" in ct or "graphql" in ct

                    # --- Response quality check ---
                    response_quality = "empty"
                    try:
                        body = await resp.read()
                        if body:
                            has_json_ct = "application/json" in ct
                            if has_json_ct:
                                import json as _json
                                _json.loads(body)
                                response_quality = "json_valid"
                            elif is_api:
                                # structured but not json content-type
                                response_quality = "json_valid"
                            else:
                                response_quality = "html_only"
                    except Exception:
                        if response_quality == "empty" and body:
                            response_quality = "html_only"

                    if is_api:
                        return (7, {
                            "endpoint": probe_url,
                            "status": status,
                            "content_type": ct,
                            "response_quality": response_quality,
                            "reason": "Publicly reachable API endpoint returning structured data",
                        })
                    else:
                        return (6, {
                            "endpoint": probe_url,
                            "status": status,
                            "content_type": ct,
                            "response_quality": response_quality,
                            "reason": "Publicly reachable endpoint returning 2xx (HTML/other)",
                        })
                elif status in (401, 403):
                    return (7, {
                        "endpoint": probe_url,
                        "status": status,
                        "reason": "Endpoint exists, requires authentication (API confirmed)",
                    })
                elif status == 404 and "json" in ct and best_score < 5:
                    # 404 with JSON response shows a well-structured API
                    best_score = 5
                    best_evidence = {
                        "endpoint": probe_url,
                        "status": status,
                        "reason": "API endpoint with structured 404 response",
                    }
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
    """Measure p50 latency with HEAD requests (6 pts max)."""
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

    # Graduated latency scoring (6 pts max)
    if p50 < 100:
        score = 6   # Exceptional: <100ms
    elif p50 < 200:
        score = 5   # Excellent: <200ms
    elif p50 < 400:
        score = 4   # Good: <400ms
    elif p50 < 700:
        score = 3   # Acceptable: <700ms
    elif p50 < 1000:
        score = 2   # Slow: <1s
    elif p50 < 2000:
        score = 1   # Very slow: <2s
    else:
        score = 0   # Poor: 2s+

    # --- Consistency check via standard deviation ---
    evidence: dict[str, Any] = {"p50_ms": round(p50), "samples": [round(x) for x in latencies]}
    if len(latencies) >= 2:
        mean = sum(latencies) / len(latencies)
        variance = sum((x - mean) ** 2 for x in latencies) / len(latencies)
        stddev = math.sqrt(variance)
        evidence["stddev_ms"] = round(stddev)
        if stddev > 500:
            evidence["latency_unstable"] = True
        elif stddev < 100:
            evidence["latency_consistent"] = True

    return (score, evidence)


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
                    # Check for code examples in auth docs
                    has_code_examples = any(kw in text_lower for kw in [
                        "curl", "authorization: bearer", "x-api-key",
                        "```", "code example", "import ",
                    ])
                    if len(matches) >= 3 and has_code_examples:
                        return (3, {
                            "reason": "Comprehensive auth documentation with code examples",
                            "url": path,
                            "keywords_found": matches[:5],
                        })
                    elif len(matches) >= 2:
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


async def _verify_ratelimit_dynamic(
    session: aiohttp.ClientSession, probe_url: str, first_headers: dict[str, str],
) -> dict[str, Any]:
    """Make a second request after 100ms to verify rate limit headers update."""
    # Find the 'remaining' header from the first response
    remaining_key = None
    first_remaining: int | None = None
    for key in ("x-ratelimit-remaining", "x-rate-limit-remaining", "ratelimit-remaining"):
        if key in first_headers:
            remaining_key = key
            try:
                first_remaining = int(first_headers[key])
            except (ValueError, TypeError):
                pass
            break

    if first_remaining is None:
        return {"dynamic_verified": False, "dynamic_note": "No parseable remaining header in first response"}

    await asyncio.sleep(0.1)  # 100ms delay

    try:
        async with session.get(
            probe_url,
            timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
            allow_redirects=True, ssl=False,
        ) as resp2:
            resp2_headers_lower = {k.lower(): v for k, v in resp2.headers.items()}
            second_val = resp2_headers_lower.get(remaining_key)  # type: ignore[arg-type]
            if second_val is not None:
                try:
                    second_remaining = int(second_val)
                    if second_remaining < first_remaining:
                        return {"dynamic_verified": True, "remaining_delta": first_remaining - second_remaining}
                    else:
                        return {"dynamic_verified": False, "dynamic_note": "Remaining did not decrease between requests"}
                except (ValueError, TypeError):
                    return {"dynamic_verified": False, "dynamic_note": "Second remaining header not parseable"}
            return {"dynamic_verified": False, "dynamic_note": "Remaining header absent in second response"}
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return {"dynamic_verified": False, "dynamic_note": "Second request failed"}


async def _check_connection_quality(
    session: aiohttp.ClientSession, endpoint: str,
) -> dict[str, Any]:
    """Check keep-alive and compression support (informational, not score-affecting)."""
    result: dict[str, Any] = {}
    try:
        async with session.get(
            endpoint,
            timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
            allow_redirects=True, ssl=False,
            headers={"Accept-Encoding": "gzip, deflate, br"},
        ) as resp:
            # Keep-alive
            conn_header = resp.headers.get("Connection", "").lower()
            result["keep_alive"] = "close" not in conn_header

            # Compression
            content_encoding = resp.headers.get("Content-Encoding", "").lower()
            result["compression"] = content_encoding if content_encoding else None
    except (aiohttp.ClientError, asyncio.TimeoutError):
        result["keep_alive"] = None
        result["compression"] = None

    return result


async def check_rate_limit_info(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check if rate limit info is publicly exposed (6 pts max).

    Rate limits are the #1 cause of agent failures in production (429 errors).
    Agents MUST know limits to self-throttle effectively.

    6 pts = X-RateLimit-* headers + Retry-After header present
    5 pts = X-RateLimit-* headers (limit, remaining, reset) present
    4 pts = Partial rate limit headers (e.g., only limit or only retry-after)
    3 pts = Rate limit documented in docs with specific numbers
    2 pts = Rate limit mentioned in docs (general)
    0 pts = No rate limit info
    """
    # Check headers on actual API responses
    probe_urls = [
        base_url,
        f"{base_url}/api",
        f"{base_url}/api/v1",
        f"{base_url}/v1",
    ]

    ratelimit_header_names = [
        "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
        "x-rate-limit-limit", "x-rate-limit-remaining", "x-rate-limit-reset",
        "ratelimit-limit", "ratelimit-remaining", "ratelimit-reset",
    ]
    retry_after_names = ["retry-after"]

    for probe_url in probe_urls:
        try:
            async with session.get(
                probe_url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                resp_headers_lower = {k.lower(): v for k, v in resp.headers.items()}
                found_rl = {
                    h: resp_headers_lower[h]
                    for h in ratelimit_header_names
                    if h in resp_headers_lower
                }
                has_retry_after = any(
                    h in resp_headers_lower for h in retry_after_names
                )

                if found_rl and has_retry_after:
                    dynamic = await _verify_ratelimit_dynamic(session, probe_url, found_rl)
                    return (6, {
                        "reason": "Full rate limit headers + Retry-After for safe agent throttling",
                        "url": probe_url,
                        "headers": {**found_rl, "retry-after": resp_headers_lower.get("retry-after", "")},
                        **dynamic,
                    })
                elif len(found_rl) >= 2:
                    dynamic = await _verify_ratelimit_dynamic(session, probe_url, found_rl)
                    return (5, {
                        "reason": "Rate limit headers exposed in API response",
                        "url": probe_url,
                        "headers": found_rl,
                        **dynamic,
                    })
                elif found_rl or has_retry_after:
                    headers = found_rl.copy()
                    if has_retry_after:
                        headers["retry-after"] = resp_headers_lower.get("retry-after", "")
                    return (4, {
                        "reason": "Partial rate limit headers found",
                        "url": probe_url,
                        "headers": headers,
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
                    specific_keywords = ["per second", "per minute", "per hour", "requests/", "req/s", "rpm", "rps"]
                    has_general = any(kw in text for kw in rl_keywords)
                    has_specific = any(kw in text for kw in specific_keywords)
                    if has_general and has_specific:
                        return (3, {
                            "reason": "Rate limit documented with specific numbers",
                            "url": path,
                        })
                    elif has_general:
                        return (2, {
                            "reason": "Rate limit info documented (general)",
                            "url": path,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (0, {"reason": "No rate limit information found"})


async def check_api_versioning(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for API versioning patterns (1 pt max).

    1 pt  = Versioned endpoints or version header detected
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
                        return (1, {
                            "reason": "API versioning with version header",
                            "versions": found_versions,
                            "header_version": api_version,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    if found_versions:
        return (1, {
            "reason": "API versioning detected",
            "versions": found_versions,
        })

    return (0, {"reason": "No API versioning detected"})


async def check_sdk_availability(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check if official SDKs exist on PyPI/npm (1 pt max).

    1 pt  = SDK found on PyPI/npm or mentioned in docs
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
                    return (1, {
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
        (sdk_score, sdk_ev), (free_score, free_ev), \
        conn_quality = await asyncio.gather(
        measure_latency(session, latency_endpoint),
        check_auth_documentation(session, base_url, openapi_spec),
        check_rate_limit_info(session, base_url),
        check_api_versioning(session, base_url),
        check_sdk_availability(session, base_url),
        check_free_tier(session, base_url),
        _check_connection_quality(session, latency_endpoint),
    )

    # Merge connection quality info into latency evidence (informational only)
    latency_ev["connection_quality"] = conn_quality

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
                "max": 6,
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
                "max": 6,
                "label": "Rate Limit Transparency",
                "evidence": rate_ev,
            },
            "api_versioning": {
                "score": ver_score,
                "max": 1,
                "label": "API Versioning",
                "evidence": ver_ev,
            },
            "sdk_availability": {
                "score": sdk_score,
                "max": 1,
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
