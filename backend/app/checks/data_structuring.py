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


async def _score_error_response(
    resp_status: int, resp_ct: str, resp_data: Any,
    probe_url: str, method: str,
) -> tuple[int, dict[str, Any]] | None:
    """Evaluate a single error response for structured error format.

    Returns (score, evidence) if the response is scoreable, or None to keep probing.
    """
    if resp_status < 400:
        return None

    if "json" in resp_ct:
        if not isinstance(resp_data, dict):
            return (2, {
                "reason": "JSON error response but not a dict object",
                "probe_url": probe_url,
                "method": method,
                "status": resp_status,
            })

        # Check for RFC 7807 (Problem Details) fields
        rfc7807_fields = {"type", "title", "status", "detail"}
        rfc7807_count = len(rfc7807_fields & set(resp_data.keys()))

        has_error = "error" in resp_data or "message" in resp_data or "detail" in resp_data
        has_code = "code" in resp_data or "error_code" in resp_data

        if rfc7807_count >= 3 or (has_error and has_code):
            return (7, {
                "reason": "Standardized error format (RFC 7807 or equivalent)",
                "probe_url": probe_url,
                "method": method,
                "status": resp_status,
                "error_keys": list(resp_data.keys())[:8],
            })
        elif has_error:
            return (4, {
                "reason": "Consistent JSON error shape but undocumented",
                "probe_url": probe_url,
                "method": method,
                "status": resp_status,
                "error_keys": list(resp_data.keys())[:8],
            })
        else:
            return (2, {
                "reason": "JSON error response with minimal structure",
                "probe_url": probe_url,
                "method": method,
                "status": resp_status,
                "error_keys": list(resp_data.keys())[:8],
            })

    elif "html" in resp_ct:
        return (0, {
            "reason": "HTML error page returned",
            "probe_url": probe_url,
            "method": method,
            "status": resp_status,
        })
    else:
        return (2, {
            "reason": "Error response with some structure",
            "probe_url": probe_url,
            "method": method,
            "status": resp_status,
            "content_type": resp_ct,
        })


async def check_error_structure(
    session: aiohttp.ClientSession, base_url: str,
    api_url: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Probe an endpoint with bad input to check error response structure (7 pts max).

    Probes both the website URL and a separate API URL (e.g. api.stripe.com) if provided.
    Uses both GET and POST methods since many APIs return structured errors on POST without body.
    """
    # Build probe URLs: prioritize api_url if available
    probe_bases = []
    if api_url:
        probe_bases.append(api_url)
    probe_bases.append(base_url)

    best_score = 0
    best_evidence: dict[str, Any] = {
        "reason": "Could not probe error responses (endpoints may require auth)",
    }

    for probe_base in probe_bases:
        # Phase 1: Trigger 404/400 errors with nonexistent paths
        error_paths = [
            f"{probe_base}/nonexistent-resource-test-12345",
            f"{probe_base}/v1/nonexistent-resource-test-12345",
            f"{probe_base}/api/v1/nonexistent-resource-test-12345",
            f"{probe_base}/api/nonexistent-resource-test-12345",
        ]

        for probe in error_paths:
            # Try GET first
            for method in ("GET", "POST"):
                try:
                    if method == "GET":
                        async with session.get(
                            probe, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                            allow_redirects=True, ssl=False,
                        ) as resp:
                            ct = resp.headers.get("content-type", "")
                            data = None
                            if "json" in ct:
                                try:
                                    data = await resp.json()
                                except Exception:
                                    pass
                            result = await _score_error_response(resp.status, ct, data, probe, method)
                    else:
                        async with session.post(
                            probe, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                            allow_redirects=True, ssl=False,
                            json={"invalid": True},
                        ) as resp:
                            ct = resp.headers.get("content-type", "")
                            data = None
                            if "json" in ct:
                                try:
                                    data = await resp.json()
                                except Exception:
                                    pass
                            result = await _score_error_response(resp.status, ct, data, probe, method)

                    if result is not None:
                        score, evidence = result
                        if score >= 7:
                            return result  # Best possible, return immediately
                        if score > best_score:
                            best_score = score
                            best_evidence = evidence
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    continue

        # Phase 2: POST to API base with empty/invalid body (triggers 400/422)
        post_probes = [
            probe_base,
            f"{probe_base}/v1",
            f"{probe_base}/api/v1",
            f"{probe_base}/api",
        ]
        for probe in post_probes:
            try:
                async with session.post(
                    probe, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                    allow_redirects=True, ssl=False,
                    json={},
                ) as resp:
                    ct = resp.headers.get("content-type", "")
                    data = None
                    if "json" in ct:
                        try:
                            data = await resp.json()
                        except Exception:
                            pass
                    result = await _score_error_response(resp.status, ct, data, probe, "POST")
                    if result is not None:
                        score, evidence = result
                        if score >= 7:
                            return result
                        if score > best_score:
                            best_score = score
                            best_evidence = evidence
            except (aiohttp.ClientError, asyncio.TimeoutError):
                continue

        # Phase 3: GET to API base without auth (triggers 401/403)
        auth_probes = [
            probe_base,
            f"{probe_base}/v1",
            f"{probe_base}/api/v1",
            f"{probe_base}/api",
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
                            has_error = isinstance(data, dict) and (
                                "error" in data or "message" in data
                            )
                            if has_error:
                                score = 5
                                evidence = {
                                    "reason": "Structured auth error response (JSON 401/403)",
                                    "probe_url": probe,
                                    "method": "GET",
                                    "status": resp.status,
                                    "error_keys": list(data.keys())[:8],
                                }
                                if score > best_score:
                                    best_score = score
                                    best_evidence = evidence
                        except Exception:
                            pass
            except (aiohttp.ClientError, asyncio.TimeoutError):
                continue

    return (best_score, best_evidence)


async def check_graphql_introspection(
    session: aiohttp.ClientSession, base_url: str,
    api_url: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Check for GraphQL introspection support (bonus evidence for schema definition).

    Returns score contribution (0-3) and evidence dict.
    This is additive to the schema_definition score (capped at 10 total).
    """
    INTROSPECTION_QUERY = json.dumps({
        "query": "{ __schema { types { name } } }",
    })

    probe_bases = [api_url, base_url] if api_url else [base_url]
    graphql_paths = ["/graphql", "/api/graphql", "/v1/graphql"]

    for probe_base in probe_bases:
        for path in graphql_paths:
            url = f"{probe_base}{path}"
            try:
                async with session.post(
                    url,
                    timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                    data=INTROSPECTION_QUERY,
                    headers={"Content-Type": "application/json"},
                    allow_redirects=True, ssl=False,
                ) as resp:
                    if resp.status < 300:
                        ct = resp.headers.get("content-type", "")
                        if "json" in ct:
                            data = await resp.json()
                            if isinstance(data, dict) and "data" in data:
                                schema_data = data.get("data", {}).get("__schema", {})
                                types = schema_data.get("types", [])
                                if types:
                                    return (3, {
                                        "reason": "GraphQL introspection enabled",
                                        "url": url,
                                        "type_count": len(types),
                                    })
                    elif resp.status in (400, 401, 403):
                        # GraphQL endpoint exists but auth required or introspection disabled
                        ct = resp.headers.get("content-type", "")
                        if "json" in ct:
                            return (1, {
                                "reason": "GraphQL endpoint found but introspection disabled or requires auth",
                                "url": url,
                            })
            except (aiohttp.ClientError, asyncio.TimeoutError):
                continue

    return (0, {"reason": "No GraphQL endpoint found"})


async def run_data_structuring(
    session: aiohttp.ClientSession, base_url: str,
    api_url: str | None = None,
) -> tuple[dict, dict | None]:
    """Run all Data Structuring checks. Returns (dimension_result, openapi_spec)."""
    # Discover OpenAPI spec first (needed by other checks too)
    openapi_spec, spec_url = await discover_openapi_spec(session, base_url)

    # Run checks concurrently
    schema_task = check_schema_definition(openapi_spec, spec_url)
    pricing_task = check_pricing(session, base_url)
    error_task = check_error_structure(session, base_url, api_url=api_url)
    graphql_task = check_graphql_introspection(session, base_url, api_url=api_url)

    (schema_score, schema_ev), (pricing_score, pricing_ev), (error_score, error_ev), (gql_score, gql_ev) = (
        await asyncio.gather(schema_task, pricing_task, error_task, graphql_task)
    )

    # GraphQL bonus: add to schema score (capped at 10)
    if gql_score > 0 and schema_score < 10:
        bonus = min(gql_score, 10 - schema_score)
        schema_score += bonus
        schema_ev["graphql_bonus"] = bonus
        schema_ev["graphql_evidence"] = gql_ev

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
