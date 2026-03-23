"""Agent Compatibility checks (25 points).

Sub-factors:
- MCP Server Exists (10 pts)
- robots.txt Agent Policy (3 pts)
- Sitemap / Discovery (3 pts)
- AI Plugin Manifest (3 pts)
- Well-Known MCP Config (2 pts)
- API Playground / Sandbox (2 pts)
- CORS Policy (2 pts)
"""

import asyncio
from typing import Any
from urllib.parse import urlparse

import aiohttp

from ..config import settings


async def check_mcp_server(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check if this service has an MCP server in public registries (10 pts max).

    10 pts = Listed in registry with verified connectivity
     7 pts = MCP server exists but not in public registry
     3 pts = MCP announced but non-functional
     0 pts = No MCP server
    """
    domain = urlparse(base_url).hostname or ""
    search_domain = domain.replace("www.", "")

    registry_checks = [
        f"https://mcp.so/api/search?q={search_domain}",
        f"https://registry.smithery.ai/api/search?q={search_domain}",
        f"https://glama.ai/mcp/servers?search={search_domain}",
    ]

    for registry_url in registry_checks:
        try:
            async with session.get(
                registry_url,
                timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    try:
                        data = await resp.json()
                        results = data if isinstance(data, list) else data.get("results", data.get("items", []))
                        if isinstance(results, list) and len(results) > 0:
                            return (10, {
                                "reason": "MCP server listed in public registry",
                                "registry": registry_url.split("/api")[0],
                                "matches": len(results),
                            })
                    except Exception:
                        pass
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Check for MCP indicators on the site itself
    mcp_indicators = [
        f"{base_url}/.well-known/mcp.json",
        f"{base_url}/mcp",
    ]

    for url in mcp_indicators:
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    ct = resp.headers.get("content-type", "")
                    if "json" in ct:
                        return (7, {
                            "reason": "MCP server config found on domain",
                            "url": url,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Check main page for MCP mentions
    try:
        async with session.get(
            base_url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
            allow_redirects=True, ssl=False,
        ) as resp:
            if resp.status < 300:
                text = await resp.text()
                text_lower = text.lower()
                if "model context protocol" in text_lower or "mcp server" in text_lower:
                    return (3, {
                        "reason": "MCP server mentioned but not verified",
                        "url": base_url,
                    })
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    return (0, {"reason": "No MCP server found"})


async def check_robots_txt(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Parse robots.txt for AI agent policies (3 pts max).

    3 pts = Explicit AI agent rules (allow)
    2 pts = AI agent rules (block — still agent-aware)
    1 pt  = Standard permissive robots.txt
    0 pts = No robots.txt or blocks all
    """
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.hostname}/robots.txt"

    try:
        async with session.get(
            robots_url,
            timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
            allow_redirects=True, ssl=False,
        ) as resp:
            if resp.status >= 300:
                return (0, {"reason": "No robots.txt found", "url": robots_url})

            text = await resp.text()
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
                    return (3, {
                        "reason": "robots.txt explicitly ALLOWS AI agents",
                        "url": robots_url,
                        "ai_agents": found_ai_rules[:10],
                        "policy": "allow",
                    })
                else:
                    return (2, {
                        "reason": "robots.txt addresses AI agents but blocks them (agent-aware)",
                        "url": robots_url,
                        "ai_agents": found_ai_rules[:10],
                        "policy": "block",
                    })

            has_disallow_all = "disallow: /" in text_lower and "disallow: / " not in text_lower
            has_allow_all = "user-agent: *" in text_lower

            if has_allow_all and not has_disallow_all:
                return (1, {
                    "reason": "Standard robots.txt with permissive defaults",
                    "url": robots_url,
                })

            if has_disallow_all:
                return (0, {
                    "reason": "robots.txt blocks automated access",
                    "url": robots_url,
                })

            return (1, {
                "reason": "Standard robots.txt without agent-specific rules",
                "url": robots_url,
            })

    except (aiohttp.ClientError, asyncio.TimeoutError):
        return (0, {"reason": "Could not fetch robots.txt"})


async def check_sitemap_discovery(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for sitemap.xml and discovery mechanisms (3 pts max).

    3 pts = Sitemap with API docs references
    2 pts = Sitemap exists
    0 pts = No sitemap
    """
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.hostname}"
    sitemap_url = f"{root}/sitemap.xml"

    try:
        async with session.get(
            sitemap_url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
            allow_redirects=True, ssl=False,
        ) as resp:
            if resp.status < 300:
                text = await resp.text()
                text_lower = text.lower()
                if "api" in text_lower or "docs" in text_lower or "reference" in text_lower:
                    return (3, {
                        "reason": "Sitemap.xml with API documentation URLs",
                        "url": sitemap_url,
                    })
                else:
                    return (2, {
                        "reason": "Sitemap exists but doesn't cover API docs",
                        "url": sitemap_url,
                    })
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    return (0, {"reason": "No sitemap found"})


async def check_ai_plugin_manifest(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for .well-known/ai-plugin.json (ChatGPT plugin standard) (3 pts max).

    3 pts = Valid ai-plugin.json with API reference
    1 pt  = ai-plugin.json exists but incomplete
    0 pts = Not found
    """
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.hostname}"
    plugin_url = f"{root}/.well-known/ai-plugin.json"

    try:
        async with session.get(
            plugin_url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
            allow_redirects=True, ssl=False,
        ) as resp:
            if resp.status < 300:
                ct = resp.headers.get("content-type", "")
                if "json" in ct or plugin_url.endswith(".json"):
                    try:
                        data = await resp.json()
                        if isinstance(data, dict):
                            has_api = "api" in data
                            has_name = "name_for_human" in data or "name_for_model" in data
                            has_desc = "description_for_human" in data or "description_for_model" in data

                            if has_api and (has_name or has_desc):
                                return (3, {
                                    "reason": "Valid ai-plugin.json with API reference",
                                    "url": plugin_url,
                                    "fields": list(data.keys())[:10],
                                })
                            else:
                                return (1, {
                                    "reason": "ai-plugin.json exists but incomplete",
                                    "url": plugin_url,
                                    "fields": list(data.keys())[:10],
                                })
                    except Exception:
                        return (1, {
                            "reason": "ai-plugin.json found but not valid JSON",
                            "url": plugin_url,
                        })
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    return (0, {"reason": "No ai-plugin.json found"})


async def check_wellknown_mcp(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for .well-known/mcp.json (2 pts max).

    2 pts = Valid mcp.json with tool definitions
    1 pt  = mcp.json exists but minimal
    0 pts = Not found
    """
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.hostname}"
    mcp_url = f"{root}/.well-known/mcp.json"

    try:
        async with session.get(
            mcp_url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
            allow_redirects=True, ssl=False,
        ) as resp:
            if resp.status < 300:
                ct = resp.headers.get("content-type", "")
                if "json" in ct or mcp_url.endswith(".json"):
                    try:
                        data = await resp.json()
                        if isinstance(data, dict):
                            has_tools = "tools" in data or "capabilities" in data
                            if has_tools:
                                return (2, {
                                    "reason": "Valid mcp.json with tool definitions",
                                    "url": mcp_url,
                                    "fields": list(data.keys())[:10],
                                })
                            else:
                                return (1, {
                                    "reason": "mcp.json exists but minimal",
                                    "url": mcp_url,
                                })
                    except Exception:
                        return (1, {
                            "reason": "mcp.json found but not valid JSON",
                            "url": mcp_url,
                        })
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    return (0, {"reason": "No .well-known/mcp.json found"})


async def check_api_playground(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for API playground or sandbox (2 pts max).

    2 pts = Interactive API playground/sandbox found
    1 pt  = Try-it page or interactive docs
    0 pts = No playground
    """
    playground_paths = [
        f"{base_url}/playground",
        f"{base_url}/sandbox",
        f"{base_url}/try",
        f"{base_url}/api/playground",
        f"{base_url}/docs/playground",
        f"{base_url}/explorer",
        f"{base_url}/console",
    ]

    for path in playground_paths:
        try:
            async with session.get(
                path, timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    text = (await resp.text()).lower()
                    playground_keywords = [
                        "playground", "sandbox", "try it", "interactive",
                        "test api", "api console", "explorer",
                    ]
                    if any(kw in text for kw in playground_keywords):
                        return (2, {
                            "reason": "API playground/sandbox found",
                            "url": path,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Check if Swagger UI or similar is available (interactive docs)
    swagger_paths = [
        f"{base_url}/swagger-ui",
        f"{base_url}/docs",
        f"{base_url}/api-docs",
        f"{base_url}/redoc",
    ]

    for path in swagger_paths:
        try:
            async with session.get(
                path, timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    text = (await resp.text()).lower()
                    if "swagger" in text or "redoc" in text or "try it out" in text:
                        return (1, {
                            "reason": "Interactive API documentation (Swagger/Redoc)",
                            "url": path,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (0, {"reason": "No API playground found"})


async def check_cors_policy(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check CORS policy for browser-based agent access (2 pts max).

    2 pts = Permissive CORS (Access-Control-Allow-Origin: *)
    1 pt  = CORS headers present (restricted origins)
    0 pts = No CORS headers
    """
    # Send an OPTIONS preflight request
    probe_urls = [
        base_url,
        f"{base_url}/api",
        f"{base_url}/api/v1",
        f"{base_url}/v1",
    ]

    for probe_url in probe_urls:
        try:
            async with session.options(
                probe_url,
                timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
                headers={"Origin": "https://agent.example.com", "Access-Control-Request-Method": "GET"},
            ) as resp:
                acao = resp.headers.get("access-control-allow-origin", "")
                acam = resp.headers.get("access-control-allow-methods", "")

                if acao == "*":
                    return (2, {
                        "reason": "Permissive CORS policy (allows all origins)",
                        "url": probe_url,
                        "allow_origin": acao,
                        "allow_methods": acam,
                    })
                elif acao:
                    return (1, {
                        "reason": "CORS enabled with restricted origins",
                        "url": probe_url,
                        "allow_origin": acao,
                        "allow_methods": acam,
                    })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Also check GET responses for CORS headers
    for probe_url in probe_urls:
        try:
            async with session.get(
                probe_url,
                timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True, ssl=False,
            ) as resp:
                acao = resp.headers.get("access-control-allow-origin", "")
                if acao == "*":
                    return (2, {
                        "reason": "Permissive CORS in GET response",
                        "url": probe_url,
                        "allow_origin": acao,
                    })
                elif acao:
                    return (1, {
                        "reason": "CORS headers present in GET response",
                        "url": probe_url,
                        "allow_origin": acao,
                    })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    return (0, {"reason": "No CORS headers detected"})


async def run_agent_compatibility(
    session: aiohttp.ClientSession, base_url: str
) -> dict:
    """Run all Agent Compatibility checks concurrently."""
    (mcp_score, mcp_ev), (robots_score, robots_ev), (sitemap_score, sitemap_ev), \
        (plugin_score, plugin_ev), (wk_mcp_score, wk_mcp_ev), \
        (playground_score, playground_ev), (cors_score, cors_ev) = await asyncio.gather(
        check_mcp_server(session, base_url),
        check_robots_txt(session, base_url),
        check_sitemap_discovery(session, base_url),
        check_ai_plugin_manifest(session, base_url),
        check_wellknown_mcp(session, base_url),
        check_api_playground(session, base_url),
        check_cors_policy(session, base_url),
    )

    total = mcp_score + robots_score + sitemap_score + plugin_score + wk_mcp_score + playground_score + cors_score

    return {
        "score": total,
        "max": 25,
        "sub_factors": {
            "mcp_server_exists": {
                "score": mcp_score,
                "max": 10,
                "label": "MCP Server Exists",
                "evidence": mcp_ev,
            },
            "robots_txt_agent_policy": {
                "score": robots_score,
                "max": 3,
                "label": "robots.txt Agent Policy",
                "evidence": robots_ev,
            },
            "sitemap_discovery": {
                "score": sitemap_score,
                "max": 3,
                "label": "Sitemap / Discovery",
                "evidence": sitemap_ev,
            },
            "ai_plugin_manifest": {
                "score": plugin_score,
                "max": 3,
                "label": "AI Plugin Manifest",
                "evidence": plugin_ev,
            },
            "wellknown_mcp": {
                "score": wk_mcp_score,
                "max": 2,
                "label": ".well-known/mcp.json",
                "evidence": wk_mcp_ev,
            },
            "api_playground": {
                "score": playground_score,
                "max": 2,
                "label": "API Playground / Sandbox",
                "evidence": playground_ev,
            },
            "cors_policy": {
                "score": cors_score,
                "max": 2,
                "label": "CORS Policy",
                "evidence": cors_ev,
            },
        },
    }
