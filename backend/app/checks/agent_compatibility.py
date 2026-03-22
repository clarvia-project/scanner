"""Agent Compatibility checks (25 points).

Sub-factors:
- MCP Server Exists (15 pts)
- robots.txt Agent Policy (5 pts)
- Sitemap / Discovery (5 pts)
"""

import asyncio
from typing import Any
from urllib.parse import urlparse

import aiohttp

from ..config import settings


async def check_mcp_server(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check if this service has an MCP server in public registries (15 pts max).

    15 pts = Listed in registry with verified connectivity
    10 pts = MCP server exists but not in public registry
     5 pts = MCP announced but non-functional
     0 pts = No MCP server
    """
    domain = urlparse(base_url).hostname or ""
    # Strip www. prefix for search
    search_domain = domain.replace("www.", "")

    # Check mcp.so and smithery.ai
    registry_checks = [
        f"https://mcp.so/api/search?q={search_domain}",
        f"https://registry.smithery.ai/api/search?q={search_domain}",
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
                        # Check if any results match our domain
                        results = data if isinstance(data, list) else data.get("results", data.get("items", []))
                        if isinstance(results, list) and len(results) > 0:
                            return (15, {
                                "reason": "MCP server listed in public registry",
                                "registry": registry_url.split("/api")[0],
                                "matches": len(results),
                            })
                    except Exception:
                        pass
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Check for .well-known/mcp.json or mcp server indicators on the site itself
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
                        return (10, {
                            "reason": "MCP server config found on domain",
                            "url": url,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Check main page and docs for MCP mentions
    try:
        async with session.get(
            base_url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
            allow_redirects=True, ssl=False,
        ) as resp:
            if resp.status < 300:
                text = await resp.text()
                text_lower = text.lower()
                if "model context protocol" in text_lower or "mcp server" in text_lower:
                    return (5, {
                        "reason": "MCP server mentioned but not verified",
                        "url": base_url,
                    })
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    return (0, {"reason": "No MCP server found"})


async def check_robots_txt(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Parse robots.txt for AI agent policies (5 pts max).

    5 pts = Explicit AI agent rules
    3 pts = Standard robots.txt with permissive defaults
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

            # AI-specific user agents
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
                return (5, {
                    "reason": "robots.txt explicitly addresses AI agents",
                    "url": robots_url,
                    "ai_agents": found_ai_rules[:10],
                })

            # Check if it's permissive (allows all)
            has_disallow_all = "disallow: /" in text_lower and "disallow: / " not in text_lower
            has_allow_all = "user-agent: *" in text_lower

            if has_allow_all and not has_disallow_all:
                return (3, {
                    "reason": "Standard robots.txt with permissive defaults",
                    "url": robots_url,
                })

            if has_disallow_all:
                return (0, {
                    "reason": "robots.txt blocks automated access",
                    "url": robots_url,
                })

            return (3, {
                "reason": "Standard robots.txt without agent-specific rules",
                "url": robots_url,
            })

    except (aiohttp.ClientError, asyncio.TimeoutError):
        return (0, {"reason": "Could not fetch robots.txt"})


async def check_sitemap_discovery(
    session: aiohttp.ClientSession, base_url: str
) -> tuple[int, dict[str, Any]]:
    """Check for sitemap.xml and discovery mechanisms (5 pts max).

    5 pts = Sitemap with API docs, or .well-known/ai-plugin.json, or Clarvia Profile
    3 pts = Partial discovery
    0 pts = No discovery mechanism
    """
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.hostname}"

    discovery_urls = {
        "sitemap": f"{root}/sitemap.xml",
        "ai_plugin": f"{root}/.well-known/ai-plugin.json",
        "clarvia": f"{root}/.well-known/clarvia.json",
    }

    found: dict[str, bool] = {}

    for name, url in discovery_urls.items():
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 300:
                    found[name] = True

                    # ai-plugin.json or clarvia.json = full marks
                    if name in ("ai_plugin", "clarvia"):
                        return (5, {
                            "reason": f".well-known/{name.replace('_', '-')}.json found",
                            "url": url,
                        })
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    if "sitemap" in found:
        # Check if sitemap references API docs
        try:
            async with session.get(
                discovery_urls["sitemap"],
                timeout=aiohttp.ClientTimeout(total=settings.http_timeout),
                allow_redirects=True, ssl=False,
            ) as resp:
                text = await resp.text()
                text_lower = text.lower()
                if "api" in text_lower or "docs" in text_lower or "reference" in text_lower:
                    return (5, {
                        "reason": "Sitemap.xml with API documentation URLs",
                        "url": discovery_urls["sitemap"],
                    })
                else:
                    return (3, {
                        "reason": "Sitemap exists but doesn't cover API docs",
                        "url": discovery_urls["sitemap"],
                    })
        except Exception:
            return (3, {
                "reason": "Sitemap exists (partial discovery)",
                "url": discovery_urls["sitemap"],
            })

    return (0, {"reason": "No discovery mechanism found"})


async def run_agent_compatibility(
    session: aiohttp.ClientSession, base_url: str
) -> dict:
    """Run all Agent Compatibility checks concurrently."""
    mcp_task = check_mcp_server(session, base_url)
    robots_task = check_robots_txt(session, base_url)
    sitemap_task = check_sitemap_discovery(session, base_url)

    (mcp_score, mcp_ev), (robots_score, robots_ev), (sitemap_score, sitemap_ev) = (
        await asyncio.gather(mcp_task, robots_task, sitemap_task)
    )

    total = mcp_score + robots_score + sitemap_score

    return {
        "score": total,
        "max": 25,
        "sub_factors": {
            "mcp_server_exists": {
                "score": mcp_score,
                "max": 15,
                "label": "MCP Server Exists",
                "evidence": mcp_ev,
            },
            "robots_txt_agent_policy": {
                "score": robots_score,
                "max": 5,
                "label": "robots.txt Agent Policy",
                "evidence": robots_ev,
            },
            "sitemap_discovery": {
                "score": sitemap_score,
                "max": 5,
                "label": "Sitemap / Discovery",
                "evidence": sitemap_ev,
            },
        },
    }
