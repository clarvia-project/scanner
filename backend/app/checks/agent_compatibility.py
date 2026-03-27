"""Agent Compatibility checks (25 points).

# Scoring Methodology v1.1 (2026-03-25)
# Weights are based on agent-builder pain frequency:
# - MCP support: important but not required for agent compatibility (7pts)
# - Robot policy: agents need explicit permission signals (5pts)
# - Discovery mechanism: agents need to find API capabilities (5pts)
# - Idempotency: critical for agent retry safety (3pts)
# - Pagination: agents process large datasets, must paginate (2pts)
# - Streaming: real-time data critical for agentic workflows (3pts)
# Full methodology: clarvia.art/methodology

Sub-factors:
- MCP Server Exists (7 pts)
- robots.txt Agent Policy (5 pts)
- Discovery Mechanism (5 pts)  — sitemap + ai-plugin + well-known configs
- Idempotency Support (3 pts)  — Idempotency-Key header support
- Pagination Pattern (2 pts)   — cursor/offset pagination in responses
- Streaming Support (3 pts)    — SSE/streaming endpoints
"""

import asyncio
import json as _json
import time
from typing import Any
from urllib.parse import urlparse

import aiohttp
from cachetools import TTLCache

from ..config import settings

# ---------------------------------------------------------------------------
# Retry helper & in-memory cache for external registry lookups
# ---------------------------------------------------------------------------

# TTLCache: max 500 entries, auto-evicted after 1 hour.
# Reduced from 2000 to save memory on 512MB instance.
CACHE_TTL = 3600  # 1 hour
_registry_cache: TTLCache = TTLCache(maxsize=500, ttl=CACHE_TTL)


def _get_cached(key: str) -> Any | None:
    return _registry_cache.get(key)  # Returns None on miss or after TTL eviction


def _set_cached(key: str, val: Any) -> None:
    _registry_cache[key] = val  # TTLCache manages expiry automatically


async def _fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    method: str = "GET",
    retries: int = 2,
    delay: float = 1.5,
    **kwargs: Any,
) -> tuple[int | None, str | None]:
    """HTTP request with retry logic.  Returns (status, body_text)."""
    for attempt in range(retries + 1):
        try:
            async with session.request(method, url, **kwargs) as resp:
                return resp.status, await resp.text()
        except (asyncio.TimeoutError, aiohttp.ClientError):
            if attempt < retries:
                await asyncio.sleep(delay)
    return None, None  # All retries failed


async def check_mcp_server(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check if this service has an MCP server in public registries (7 pts max).

    7 pts = Listed in registry with verified connectivity
    6 pts = MCP server listed in public registry
    5 pts = MCP server config with tool definitions on domain
    4 pts = MCP server config found on domain
    3 pts = MCP server mentioned with installation instructions
    2 pts = MCP server mentioned but not verified
    1 pt  = MCP package found on npm
    0 pts = No MCP server
    """
    domain = urlparse(base_url).hostname or ""
    search_domain = domain.replace("www.", "")

    registry_checks = [
        f"https://mcp.so/api/search?q={search_domain}",
        f"https://registry.smithery.ai/api/search?q={search_domain}",
        f"https://glama.ai/mcp/servers?search={search_domain}",
    ]

    registry_found = False
    registry_details: dict[str, Any] = {}
    any_registry_failed = False

    for registry_url in registry_checks:
        cache_key = f"registry:{registry_url}"
        cached = _get_cached(cache_key)
        if cached is not None:
            status_code, body = cached["status"], cached["body"]
            confidence = "cached"
        else:
            status_code, body = await _fetch_with_retry(
                session, registry_url,
                timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            )
            if status_code is not None:
                _set_cached(cache_key, {"status": status_code, "body": body})
                confidence = "high"
            else:
                any_registry_failed = True
                confidence = "low"
                continue

        if status_code is not None and status_code < 300 and body:
            try:
                data = _json.loads(body)
                results = data if isinstance(data, list) else data.get("results", data.get("items", []))
                if isinstance(results, list) and len(results) > 0:
                    registry_found = True
                    registry_details = {
                        "registry": registry_url.split("/api")[0],
                        "matches": len(results),
                        "confidence": confidence,
                    }
                    if len(results) >= 3:
                        return (7, {
                            "reason": "MCP server widely listed across registries with multiple entries",
                            **registry_details,
                        })
            except Exception:
                pass

    if registry_found:
        return (6, {
            "reason": "MCP server listed in public registry",
            **registry_details,
        })

    # Check for MCP indicators on the site itself
    mcp_indicators = [
        f"{base_url}/.well-known/mcp.json",
        f"{base_url}/mcp",
        f"{base_url}/mcp.json",
    ]

    for url in mcp_indicators:
        status, body = await _fetch_with_retry(
            session, url,
            timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
            allow_redirects=True, ssl=False,
        )
        if status is not None and status < 300 and body:
            if "json" in body[:200].lower() or url.endswith(".json"):
                try:
                    mcp_data = _json.loads(body)
                    if isinstance(mcp_data, dict):
                        has_tools = "tools" in mcp_data or "capabilities" in mcp_data
                        if has_tools:
                            return (5, {
                                "reason": "MCP server config with tool definitions on domain",
                                "url": url,
                                "fields": list(mcp_data.keys())[:10],
                                "confidence": "high",
                            })
                except Exception:
                    pass
                return (4, {
                    "reason": "MCP server config found on domain",
                    "url": url,
                    "confidence": "high",
                })

    # Check main page and docs for MCP mentions
    mcp_search_urls = [base_url, f"{base_url}/docs", f"{base_url}/integrations"]
    for search_url in mcp_search_urls:
        status, body = await _fetch_with_retry(
            session, search_url,
            timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
            allow_redirects=True, ssl=False,
        )
        if status is not None and status < 300 and body:
            text_lower = body.lower()
            has_mcp = "model context protocol" in text_lower or "mcp server" in text_lower
            has_install = "npm install" in text_lower or "npx" in text_lower or "pip install" in text_lower
            if has_mcp and has_install:
                return (3, {
                    "reason": "MCP server mentioned with installation instructions",
                    "url": search_url,
                    "confidence": "high",
                })
            elif has_mcp:
                return (2, {
                    "reason": "MCP server mentioned but not verified",
                    "url": search_url,
                    "confidence": "high",
                })

    # Check npm for MCP package
    company = urlparse(base_url).hostname.replace("www.", "").split(".")[0] if urlparse(base_url).hostname else ""
    npm_mcp_url = f"https://registry.npmjs.org/@{company}/mcp-server"
    npm_cache_key = f"npm:{npm_mcp_url}"
    npm_cached = _get_cached(npm_cache_key)
    if npm_cached is not None:
        npm_status = npm_cached
        npm_confidence = "cached"
    else:
        npm_status_raw, _ = await _fetch_with_retry(
            session, npm_mcp_url,
            timeout=aiohttp.ClientTimeout(total=5),
            allow_redirects=True, ssl=False,
        )
        npm_status = npm_status_raw
        if npm_status is not None:
            _set_cached(npm_cache_key, npm_status)
            npm_confidence = "high"
        else:
            npm_confidence = "low"

    if npm_status is not None and npm_status < 300:
        return (1, {
            "reason": "MCP server package found on npm",
            "url": npm_mcp_url,
            "confidence": npm_confidence,
        })

    # If all external registries failed, return low-confidence fallback
    if any_registry_failed:
        return (0, {
            "reason": "No MCP server found (some registries unreachable)",
            "confidence": "low",
        })

    return (0, {"reason": "No MCP server found", "confidence": "high"})


async def check_robots_txt(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Parse robots.txt for AI agent policies (5 pts max).

    5 pts = Explicit AI agent rules (allow) with crawl-delay or specific paths
    4 pts = Explicit AI agent rules (allow)
    3 pts = AI agent rules (block — still agent-aware)
    2 pts = Standard permissive robots.txt with sitemap reference
    1 pt  = Standard permissive robots.txt
    0 pts = No robots.txt or blocks all
    """
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.hostname}/robots.txt"

    status, text = await _fetch_with_retry(
        session, robots_url,
        timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
        allow_redirects=True, ssl=False,
    )

    if status is None:
        return (0, {"reason": "Could not fetch robots.txt", "confidence": "low"})
    if status >= 300:
        return (0, {"reason": "No robots.txt found", "url": robots_url, "confidence": "high"})

    confidence = "high"

    text_lower = text.lower()

    ai_agents = [
        "gptbot", "chatgpt", "anthropic", "claude",
        "google-extended", "ccbot", "ai", "llm",
        "bingbot", "cohere-ai", "perplexitybot",
    ]

    found_ai_rules = []
    lines = text_lower.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            for ai_agent in ai_agents:
                if ai_agent in agent:
                    found_ai_rules.append(agent)

    if found_ai_rules:
        allows_ai = False
        blocks_ai = False
        current_agent = ""
        for line in lines:
            line = line.strip()
            if line.startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
            elif any(a in current_agent for a in ai_agents):
                if line.startswith("allow:"):
                    allows_ai = True
                elif line.startswith("disallow:"):
                    blocks_ai = True

        if allows_ai:
            has_crawl_delay = "crawl-delay" in text_lower
            has_specific_paths = text_lower.count("allow:") >= 2 or text_lower.count("disallow:") >= 3
            if has_crawl_delay or has_specific_paths:
                return (5, {
                    "reason": "robots.txt explicitly ALLOWS AI agents with detailed path rules",
                    "url": robots_url,
                    "ai_agents": found_ai_rules[:10],
                    "policy": "allow",
                    "confidence": confidence,
                })
            return (4, {
                "reason": "robots.txt explicitly ALLOWS AI agents",
                "url": robots_url,
                "ai_agents": found_ai_rules[:10],
                "policy": "allow",
                "confidence": confidence,
            })
        else:
            return (3, {
                "reason": "robots.txt addresses AI agents but blocks them (agent-aware)",
                "url": robots_url,
                "ai_agents": found_ai_rules[:10],
                "policy": "block",
                "confidence": confidence,
            })

    has_disallow_all = "disallow: /" in text_lower and "disallow: / " not in text_lower
    has_allow_all = "user-agent: *" in text_lower
    has_sitemap = "sitemap:" in text_lower

    if has_allow_all and not has_disallow_all:
        if has_sitemap:
            return (2, {
                "reason": "Standard robots.txt with permissive defaults and sitemap",
                "url": robots_url,
                "confidence": confidence,
            })
        return (1, {
            "reason": "Standard robots.txt with permissive defaults",
            "url": robots_url,
            "confidence": confidence,
        })

    if has_disallow_all:
        return (0, {
            "reason": "robots.txt blocks automated access",
            "url": robots_url,
            "confidence": confidence,
        })

    return (1, {
        "reason": "Standard robots.txt without agent-specific rules",
        "url": robots_url,
        "confidence": confidence,
    })


async def check_discovery_mechanism(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for API discovery mechanisms (5 pts max).

    Combines: sitemap, ai-plugin.json, .well-known/mcp.json, and other
    discovery endpoints that help agents find API capabilities.

    5 pts = Multiple discovery mechanisms (ai-plugin + sitemap + well-known)
    4 pts = ai-plugin.json with API reference
    3 pts = .well-known/mcp.json with tool definitions or sitemap with API docs
    2 pts = Sitemap exists or partial ai-plugin/mcp config
    1 pt  = Basic sitemap without API references
    0 pts = No discovery mechanisms
    """
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.hostname}"

    discovery_signals: list[str] = []

    # Check ai-plugin.json
    plugin_url = f"{root}/.well-known/ai-plugin.json"
    status, body = await _fetch_with_retry(
        session, plugin_url,
        timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
        allow_redirects=True, ssl=False,
    )
    if status is not None and status < 300 and body:
        try:
            data = _json.loads(body)
            if isinstance(data, dict):
                has_api = "api" in data
                has_name = "name_for_human" in data or "name_for_model" in data
                if has_api and has_name:
                    discovery_signals.append("ai-plugin.json (complete)")
                else:
                    discovery_signals.append("ai-plugin.json (partial)")
        except Exception:
            discovery_signals.append("ai-plugin.json (invalid)")

    # Check .well-known/mcp.json
    mcp_url = f"{root}/.well-known/mcp.json"
    status, body = await _fetch_with_retry(
        session, mcp_url,
        timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
        allow_redirects=True, ssl=False,
    )
    if status is not None and status < 300 and body:
        try:
            data = _json.loads(body)
            if isinstance(data, dict):
                has_tools = "tools" in data or "capabilities" in data
                if has_tools:
                    discovery_signals.append("mcp.json (with tools)")
                else:
                    discovery_signals.append("mcp.json (minimal)")
        except Exception:
            discovery_signals.append("mcp.json (invalid)")

    # Check sitemap.xml
    sitemap_url = f"{root}/sitemap.xml"
    status, body = await _fetch_with_retry(
        session, sitemap_url,
        timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
        allow_redirects=True, ssl=False,
    )
    if status is not None and status < 300 and body:
        text_lower = body.lower()
        if "api" in text_lower or "docs" in text_lower or "reference" in text_lower:
            discovery_signals.append("sitemap (with API docs)")
        else:
            discovery_signals.append("sitemap (basic)")

    # Check .well-known/clarvia.json
    clarvia_url = f"{root}/.well-known/clarvia.json"
    status, _ = await _fetch_with_retry(
        session, clarvia_url,
        timeout=aiohttp.ClientTimeout(total=5),
        allow_redirects=True, ssl=False,
    )
    if status is not None and status < 300:
        discovery_signals.append("clarvia.json")

    # Score based on signals
    confidence = "high" if discovery_signals else "high"
    complete_signals = [s for s in discovery_signals if "complete" in s or "with tools" in s or "with API" in s]

    if len(complete_signals) >= 2 or (complete_signals and len(discovery_signals) >= 3):
        return (5, {
            "reason": "Multiple discovery mechanisms found",
            "signals": discovery_signals,
            "confidence": confidence,
        })
    elif any("ai-plugin.json (complete)" in s for s in discovery_signals):
        return (4, {
            "reason": "ai-plugin.json with API reference",
            "signals": discovery_signals,
            "confidence": confidence,
        })
    elif any("with tools" in s or "with API" in s for s in discovery_signals):
        return (3, {
            "reason": "Discovery mechanism with API/tool definitions",
            "signals": discovery_signals,
            "confidence": confidence,
        })
    elif len(discovery_signals) >= 1:
        has_meaningful = any("complete" not in s and "basic" not in s for s in discovery_signals)
        if has_meaningful or len(discovery_signals) >= 2:
            return (2, {
                "reason": "Discovery mechanism(s) found",
                "signals": discovery_signals,
                "confidence": confidence,
            })
        return (1, {
            "reason": "Basic discovery mechanism found",
            "signals": discovery_signals,
            "confidence": confidence,
        })

    return (0, {"reason": "No discovery mechanisms found", "confidence": confidence})


async def check_idempotency_support(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for Idempotency-Key header support (3 pts max).

    Critical for agent retry safety — agents that retry failed requests
    must not cause duplicate side effects.

    3 pts = Idempotency-Key header accepted (returned in response or OPTIONS)
    2 pts = Idempotency documented in API docs
    1 pt  = Idempotency mentioned on site
    0 pts = No idempotency support detected
    """
    probe_urls = [
        base_url,
        f"{base_url}/api",
        f"{base_url}/api/v1",
        f"{base_url}/v1",
    ]

    # Check OPTIONS responses for Idempotency-Key in allowed headers
    # Note: OPTIONS can't easily use _fetch_with_retry (need headers), keep direct but add retry
    for probe_url in probe_urls:
        for _attempt in range(3):
            try:
                async with session.options(
                    probe_url,
                    timeout=aiohttp.ClientTimeout(total=5),
                    allow_redirects=True, ssl=False,
                    headers={"Origin": "https://agent.example.com", "Access-Control-Request-Method": "POST"},
                ) as resp:
                    allow_headers = resp.headers.get("access-control-allow-headers", "").lower()
                    if "idempotency" in allow_headers:
                        return (3, {
                            "reason": "Idempotency-Key header accepted in CORS preflight",
                            "url": probe_url,
                            "allow_headers": allow_headers,
                            "confidence": "high",
                        })
                break  # success (no idempotency found), move to next URL
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if _attempt < 2:
                    await asyncio.sleep(1.5)
                continue

    # Check GET responses for idempotency-related headers
    for probe_url in probe_urls:
        for _attempt in range(3):
            try:
                async with session.get(
                    probe_url, timeout=aiohttp.ClientTimeout(total=5),
                    allow_redirects=True, ssl=False,
                ) as resp:
                    resp_headers_lower = {k.lower() for k in resp.headers}
                    if any("idempotency" in h or "idempotent" in h for h in resp_headers_lower):
                        return (3, {
                            "reason": "Idempotency header found in API response",
                            "url": probe_url,
                            "confidence": "high",
                        })
                break
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if _attempt < 2:
                    await asyncio.sleep(1.5)
                continue

    # Check docs for idempotency mentions
    docs_paths = [
        f"{base_url}/docs",
        f"{base_url}/docs/api",
        f"{base_url}/docs/idempotency",
        f"{base_url}/reference",
    ]
    for path in docs_paths:
        status, body = await _fetch_with_retry(
            session, path,
            timeout=aiohttp.ClientTimeout(total=5),
            allow_redirects=True, ssl=False,
        )
        if status is not None and status < 300 and body:
            text = body.lower()
            idempotency_keywords = ["idempotency-key", "idempotent", "idempotency"]
            detailed_keywords = ["idempotency-key", "idempotent request", "retry safe"]
            has_detailed = any(kw in text for kw in detailed_keywords)
            has_general = any(kw in text for kw in idempotency_keywords)
            if has_detailed:
                return (2, {
                    "reason": "Idempotency documented in API docs",
                    "url": path,
                    "confidence": "high",
                })
            elif has_general:
                return (1, {
                    "reason": "Idempotency mentioned on site",
                    "url": path,
                    "confidence": "high",
                })

    return (0, {"reason": "No idempotency support detected", "confidence": "high"})


async def check_pagination_pattern(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for cursor/offset pagination in API responses (2 pts max).

    Agents processing large datasets must paginate — APIs without
    pagination force agents to handle unbounded responses.

    2 pts = Pagination indicators in API responses (cursor, next_page, offset)
    1 pt  = Pagination mentioned in docs
    0 pts = No pagination pattern detected
    """
    probe_urls = [
        base_url,
        f"{base_url}/api",
        f"{base_url}/api/v1",
        f"{base_url}/v1",
    ]

    pagination_keys = [
        "next_cursor", "next_page", "next_page_token", "cursor",
        "page_token", "next_url", "next", "has_more", "has_next",
        "total_pages", "page_count", "offset", "pagination",
    ]

    # Check API responses for pagination fields
    for probe_url in probe_urls:
        status, body = await _fetch_with_retry(
            session, probe_url,
            timeout=aiohttp.ClientTimeout(total=5),
            allow_redirects=True, ssl=False,
        )
        if status is not None and status < 300 and body:
            try:
                data = _json.loads(body)
                if isinstance(data, dict):
                    found = [k for k in pagination_keys if k in data]
                    if found:
                        return (2, {
                            "reason": "Pagination indicators in API response",
                            "url": probe_url,
                            "pagination_fields": found,
                            "confidence": "high",
                        })
            except Exception:
                pass

    # Check docs for pagination mentions
    docs_paths = [
        f"{base_url}/docs",
        f"{base_url}/docs/api",
        f"{base_url}/docs/pagination",
        f"{base_url}/reference",
    ]
    for path in docs_paths:
        status, body = await _fetch_with_retry(
            session, path,
            timeout=aiohttp.ClientTimeout(total=5),
            allow_redirects=True, ssl=False,
        )
        if status is not None and status < 300 and body:
            text = body.lower()
            pg_keywords = ["pagination", "paginate", "cursor", "next_page", "page_token", "offset"]
            if any(kw in text for kw in pg_keywords):
                return (1, {
                    "reason": "Pagination mentioned in docs",
                    "url": path,
                    "confidence": "high",
                })

    return (0, {"reason": "No pagination pattern detected", "confidence": "high"})


async def check_streaming_support(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for SSE/streaming endpoint support (3 pts max).

    Streaming is critical for agentic workflows — real-time data feeds,
    LLM token streaming, and event-driven architectures.

    3 pts = Streaming endpoint found (text/event-stream content-type)
    2 pts = Streaming documented in API docs with specific details
    1 pt  = Streaming/SSE mentioned on site
    0 pts = No streaming support detected
    """
    # Check common streaming endpoint paths
    streaming_paths = [
        f"{base_url}/stream",
        f"{base_url}/events",
        f"{base_url}/sse",
        f"{base_url}/api/stream",
        f"{base_url}/api/events",
        f"{base_url}/v1/stream",
        f"{base_url}/v1/chat/completions",  # OpenAI-style streaming
    ]

    # Note: streaming endpoint detection needs content-type headers which
    # _fetch_with_retry doesn't return. Use direct retry loop for these.
    for path in streaming_paths:
        for _attempt in range(3):
            try:
                async with session.get(
                    path, timeout=aiohttp.ClientTimeout(total=5),
                    allow_redirects=True, ssl=False,
                ) as resp:
                    ct = resp.headers.get("content-type", "").lower()
                    if "text/event-stream" in ct or "stream" in ct:
                        return (3, {
                            "reason": "Streaming endpoint found (SSE/event-stream)",
                            "url": path,
                            "content_type": ct,
                            "confidence": "high",
                        })
                    if resp.status < 300 and "json" in ct:
                        try:
                            data = await resp.json()
                            if isinstance(data, dict) and "stream" in str(data).lower():
                                return (2, {
                                    "reason": "Streaming capability indicated in API response",
                                    "url": path,
                                    "confidence": "high",
                                })
                        except Exception:
                            pass
                break  # request succeeded, move to next path
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if _attempt < 2:
                    await asyncio.sleep(1.5)
                continue

    # Check docs for streaming mentions
    docs_paths = [
        f"{base_url}/docs",
        f"{base_url}/docs/api",
        f"{base_url}/docs/streaming",
        f"{base_url}/reference",
    ]
    for path in docs_paths:
        status, body = await _fetch_with_retry(
            session, path,
            timeout=aiohttp.ClientTimeout(total=5),
            allow_redirects=True, ssl=False,
        )
        if status is not None and status < 300 and body:
            text = body.lower()
            detailed_keywords = [
                "text/event-stream", "server-sent events",
                "streaming api", "stream response", "event stream",
            ]
            general_keywords = ["streaming", "sse", "real-time", "realtime"]
            if any(kw in text for kw in detailed_keywords):
                return (2, {
                    "reason": "Streaming documented in API docs",
                    "url": path,
                    "confidence": "high",
                })
            elif any(kw in text for kw in general_keywords):
                return (1, {
                    "reason": "Streaming/SSE mentioned on site",
                    "url": path,
                    "confidence": "high",
                })

    return (0, {"reason": "No streaming support detected", "confidence": "high"})


async def run_agent_compatibility(
    session: aiohttp.ClientSession, base_url: str
) -> dict:
    """Run all Agent Compatibility checks concurrently."""
    (mcp_score, mcp_ev), (robots_score, robots_ev), \
        (discovery_score, discovery_ev), \
        (idempotency_score, idempotency_ev), \
        (pagination_score, pagination_ev), \
        (streaming_score, streaming_ev) = await asyncio.gather(
        check_mcp_server(session, base_url),
        check_robots_txt(session, base_url),
        check_discovery_mechanism(session, base_url),
        check_idempotency_support(session, base_url),
        check_pagination_pattern(session, base_url),
        check_streaming_support(session, base_url),
    )

    total = (mcp_score + robots_score + discovery_score
             + idempotency_score + pagination_score + streaming_score)

    return {
        "score": total,
        "max": 25,
        "sub_factors": {
            "mcp_server_exists": {
                "score": mcp_score,
                "max": 7,
                "label": "MCP Server Exists",
                "evidence": mcp_ev,
            },
            "robot_policy": {
                "score": robots_score,
                "max": 5,
                "label": "robots.txt Agent Policy",
                "evidence": robots_ev,
            },
            "discovery_mechanism": {
                "score": discovery_score,
                "max": 5,
                "label": "Discovery Mechanism",
                "evidence": discovery_ev,
            },
            "idempotency_support": {
                "score": idempotency_score,
                "max": 3,
                "label": "Idempotency Support",
                "evidence": idempotency_ev,
            },
            "pagination_pattern": {
                "score": pagination_score,
                "max": 2,
                "label": "Pagination Pattern",
                "evidence": pagination_ev,
            },
            "streaming_support": {
                "score": streaming_score,
                "max": 3,
                "label": "Streaming Support",
                "evidence": streaming_ev,
            },
        },
    }
