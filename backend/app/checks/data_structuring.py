"""Data Structuring checks (25 points).

Sub-factors:
- Schema Definition (10 pts)
- Pricing Quantified (8 pts)
- Error Structure (7 pts)
"""

import asyncio
import json
from typing import Any

import aiohttp

from ..config import settings


async def _fetch_json(session: aiohttp.ClientSession, url: str) -> dict | None:
    """Try to fetch and parse JSON from a URL. For large files, read only first 64KB to detect structure."""
    if not url:
        return None
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=15),
            allow_redirects=True, ssl=False,
        ) as resp:
            if resp.status < 300:
                ct = resp.headers.get("content-type", "")
                cl = int(resp.headers.get("content-length", "0") or "0")

                is_json_like = "json" in ct or "yaml" in ct or "octet" in ct or "text/plain" in ct or url.endswith(".json")
                if is_json_like:
                    if cl > 500_000:
                        # Large spec — read first 64KB to detect structure
                        chunk = await resp.content.read(65536)
                        text = chunk.decode("utf-8", errors="ignore")
                        # Check if it looks like OpenAPI
                        if '"openapi"' in text or '"swagger"' in text or '"paths"' in text or '"components"' in text or '"schemas"' in text:
                            # Parse a minimal version: extract key fields
                            return {"openapi": "3.x", "paths": {"_large_spec": True}, "_partial": True, "_size": cl}
                    else:
                        text = await resp.text()
                        return json.loads(text)
    except Exception:
        pass
    return None


async def discover_openapi_spec(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[dict | None, str | None]:
    """Try to find and parse an OpenAPI/Swagger spec. Returns (spec_dict, spec_url)."""
    # Extract domain for GitHub raw spec lookup
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    domain_name = parsed.hostname.replace("www.", "").split(".")[0] if parsed.hostname else ""

    candidates = [
        f"{base_url}/openapi.json",
        f"{base_url}/swagger.json",
        f"{base_url}/api/openapi.json",
        f"{base_url}/api-docs",
        f"{base_url}/docs/openapi.json",
        f"{base_url}/.well-known/openapi.json",
        f"{base_url}/v1/openapi.json",
        f"{base_url}/api/swagger.json",
        f"{base_url}/api/v1/swagger.json",
        f"{base_url}/.well-known/ai-plugin.json",
        # Well-known GitHub-hosted specs (try common patterns)
        f"https://raw.githubusercontent.com/{domain_name}/openapi/master/openapi/spec3.json",
        f"https://raw.githubusercontent.com/{domain_name}/openapi/main/openapi/spec3.json",
        f"https://raw.githubusercontent.com/{domain_name}/{domain_name}-openapi/main/openapi.json",
        # Known API docs patterns
        f"https://api.{parsed.hostname}/openapi.json" if parsed.hostname else "",
        f"https://api.{parsed.hostname}/swagger.json" if parsed.hostname else "",
    ]

    # Check all candidates in parallel for speed
    async def _try_candidate(url: str) -> tuple[dict | None, str]:
        spec = await _fetch_json(session, url)
        if spec and ("openapi" in spec or "swagger" in spec or "paths" in spec
                      or "components" in spec or spec.get("_partial")):
            return (spec, url)
        return (None, url)

    results = await asyncio.gather(*[_try_candidate(u) for u in candidates if u])
    for spec, url in results:
        if spec is not None:
            return (spec, url)

    return (None, None)


async def check_schema_definition(
    openapi_spec: dict | None, spec_url: str | None
) -> tuple[int, dict[str, Any]]:
    """Score schema definition quality (10 pts max)."""
    if not openapi_spec:
        return (0, {"reason": "No OpenAPI/Swagger spec found"})

    # Handle large partial specs (detected via chunk reading)
    if openapi_spec.get("_partial"):
        return (8, {
            "reason": "Large OpenAPI spec found (structure verified, full parsing skipped)",
            "spec_url": spec_url,
            "size_bytes": openapi_spec.get("_size", 0),
        })

    paths = openapi_spec.get("paths", {})
    components = openapi_spec.get("components", {}) or openapi_spec.get("definitions", {})
    schemas = components.get("schemas", {}) if isinstance(components, dict) else {}

    total_endpoints = sum(len(methods) for methods in paths.values() if isinstance(methods, dict))

    if total_endpoints > 0 and len(schemas) > 0:
        # Check completeness: do endpoints reference schemas?
        spec_str = json.dumps(openapi_spec)
        has_refs = "$ref" in spec_str

        if total_endpoints >= 5 and len(schemas) >= 3 and has_refs:
            return (10, {
                "reason": "Published OpenAPI spec with complete models",
                "spec_url": spec_url,
                "endpoints": total_endpoints,
                "schemas": len(schemas),
            })
        else:
            return (7, {
                "reason": "Partial schema — some endpoints documented",
                "spec_url": spec_url,
                "endpoints": total_endpoints,
                "schemas": len(schemas),
            })
    elif total_endpoints > 0:
        return (3, {
            "reason": "Example payloads only, no formal schema",
            "spec_url": spec_url,
            "endpoints": total_endpoints,
        })

    return (0, {"reason": "No schema or examples found"})


async def check_pricing(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for machine-readable pricing (8 pts max)."""
    pricing_paths = [
        f"{base_url}/pricing",
        f"{base_url}/api/pricing",
        f"{base_url}/plans",
    ]

    for path in pricing_paths:
        try:
            async with session.get(
                path, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status >= 300:
                    continue

                ct = resp.headers.get("content-type", "")

                # JSON pricing = best case
                if "json" in ct:
                    try:
                        data = await resp.json()
                        if data:
                            return (8, {
                                "reason": "Pricing in structured data (JSON)",
                                "url": path,
                            })
                    except Exception:
                        pass

                # HTML pricing page — check for structured data
                text = await resp.text()
                text_lower = text.lower()

                # Check for JSON-LD or structured data
                if '"@type"' in text and ("pricecurrency" in text_lower or "price" in text_lower):
                    return (8, {
                        "reason": "Pricing page with structured data (JSON-LD)",
                        "url": path,
                    })

                # Check for visible pricing tiers
                price_indicators = ["$/mo", "$/month", "/month", "per month",
                                    "free tier", "free plan", "enterprise",
                                    "pricing", "plan"]
                matches = [kw for kw in price_indicators if kw in text_lower]
                if len(matches) >= 2:
                    return (5, {
                        "reason": "Pricing page with clear tiers but not machine-readable",
                        "url": path,
                        "indicators": matches[:5],
                    })

                if "contact" in text_lower and ("sales" in text_lower or "pricing" in text_lower):
                    return (2, {
                        "reason": "Contact sales or vague pricing",
                        "url": path,
                    })

        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (0, {"reason": "No pricing information found"})


async def check_error_structure(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Probe an endpoint with bad input to check error response structure (7 pts max)."""
    # Try to trigger an error response
    error_probes = [
        f"{base_url}/api/v1/nonexistent-resource-test-12345",
        f"{base_url}/api/nonexistent-resource-test-12345",
        f"{base_url}/v1/nonexistent",
    ]

    for probe in error_probes:
        try:
            async with session.get(
                probe, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                ct = resp.headers.get("content-type", "")

                if resp.status >= 400:
                    if "json" in ct:
                        try:
                            data = await resp.json()
                            # Check for RFC 7807 or structured error format
                            has_type = "type" in data
                            has_status = "status" in data
                            has_error = "error" in data or "message" in data or "detail" in data
                            has_code = "code" in data or "error_code" in data

                            if (has_type and has_status) or (has_error and has_code):
                                return (7, {
                                    "reason": "Standardized error format with codes and messages",
                                    "probe_url": probe,
                                    "status": resp.status,
                                    "error_keys": list(data.keys())[:8],
                                })
                            elif has_error:
                                return (4, {
                                    "reason": "Consistent JSON error shape but undocumented",
                                    "probe_url": probe,
                                    "status": resp.status,
                                    "error_keys": list(data.keys())[:8],
                                })
                        except Exception:
                            pass

                    elif "html" in ct:
                        return (0, {
                            "reason": "HTML error page returned",
                            "probe_url": probe,
                            "status": resp.status,
                        })
                    else:
                        return (2, {
                            "reason": "Error response with some structure",
                            "probe_url": probe,
                            "status": resp.status,
                            "content_type": ct,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Try hitting known API base with no auth — many APIs return structured 401/403
    auth_probes = [
        f"{base_url}/api/v1",
        f"{base_url}/api",
        f"{base_url}/v1",
    ]
    for probe in auth_probes:
        try:
            async with session.get(
                probe, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                ct = resp.headers.get("content-type", "")
                if resp.status in (401, 403) and "json" in ct:
                    try:
                        data = await resp.json()
                        has_error = "error" in data or "message" in data
                        if has_error:
                            return (5, {
                                "reason": "Structured auth error response (JSON 401/403)",
                                "probe_url": probe,
                                "status": resp.status,
                                "error_keys": list(data.keys())[:8],
                            })
                    except Exception:
                        pass
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (2, {"reason": "Could not probe error responses (endpoints may require auth)"})


async def run_data_structuring(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[dict, dict | None]:
    """Run all Data Structuring checks. Returns (dimension_result, openapi_spec)."""
    # Discover OpenAPI spec first (needed by other checks too)
    openapi_spec, spec_url = await discover_openapi_spec(session, base_url)

    # Run checks concurrently
    schema_task = check_schema_definition(openapi_spec, spec_url)
    pricing_task = check_pricing(session, base_url)
    error_task = check_error_structure(session, base_url)

    (schema_score, schema_ev), (pricing_score, pricing_ev), (error_score, error_ev) = (
        await asyncio.gather(schema_task, pricing_task, error_task)
    )

    total = schema_score + pricing_score + error_score

    result = {
        "score": total,
        "max": 25,
        "sub_factors": {
            "schema_definition": {
                "score": schema_score,
                "max": 10,
                "label": "Schema Definition",
                "evidence": schema_ev,
            },
            "pricing_quantified": {
                "score": pricing_score,
                "max": 8,
                "label": "Pricing Quantified",
                "evidence": pricing_ev,
            },
            "error_structure": {
                "score": error_score,
                "max": 7,
                "label": "Error Structure",
                "evidence": error_ev,
            },
        },
    }

    return (result, openapi_spec)
