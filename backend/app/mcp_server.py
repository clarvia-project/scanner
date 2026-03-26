"""Clarvia MCP server — Streamable HTTP transport.

Registers the same 11 tools as the Node.js stdio MCP server, but calls
the Clarvia REST API internally (same process) instead of making HTTP
round-trips.

Mount into the FastAPI app with:
    from .mcp_server import mcp_app
    app.mount("/mcp", mcp_app)
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

BASE_URL = "https://clarvia-api.onrender.com"

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "clarvia",
    instructions=(
        "Clarvia is an AEO (AI Engine Optimization) scanner and directory "
        "for 15,400+ AI agent tools. Use these tools to search, evaluate, "
        "and validate services for AI agent compatibility."
    ),
    stateless_http=True,
    streamable_http_path="/",
)

# ---------------------------------------------------------------------------
# Internal HTTP helper (calls the Clarvia REST API)
# ---------------------------------------------------------------------------

async def _api_request(
    path: str,
    *,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    url = f"{BASE_URL}{path}"
    clean_params = (
        {k: str(v) for k, v in params.items() if v is not None} if params else None
    )
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "clarvia-mcp-server/1.0",
    }
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method,
            url,
            params=clean_params,
            json=json_body,
            headers=headers,
        ) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise RuntimeError(f"Clarvia API error {resp.status}: {text}")
            return await resp.json()


# ---------------------------------------------------------------------------
# Grade helper (mirrors Node.js logic)
# ---------------------------------------------------------------------------

_GRADE_ORDER = ["AGENT_HOSTILE", "AGENT_POSSIBLE", "AGENT_FRIENDLY", "AGENT_NATIVE"]


def _grade_from_score(score: float) -> str:
    if score >= 90:
        return "AGENT_NATIVE"
    if score >= 70:
        return "AGENT_FRIENDLY"
    if score >= 50:
        return "AGENT_POSSIBLE"
    return "AGENT_HOSTILE"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def search_services(
    query: str | None = None,
    category: str | None = None,
    service_type: str | None = None,
    min_score: float | None = None,
    limit: int | None = None,
) -> str:
    """Search 15,400+ AI agent tools (MCP servers, APIs, CLIs) by keyword, category, or score.

    Use when you need to find the best tool for a specific task, compare
    alternatives, or check agent readiness. Returns Clarvia AEO scores (0-100)
    indicating how easily AI agents can discover and use each service.
    """
    data = await _api_request(
        "/v1/services",
        params={
            "q": query,
            "category": category,
            "service_type": service_type,
            "min_score": min_score,
            "limit": limit,
        },
    )
    import json
    return json.dumps(data, indent=2)


@mcp.tool()
async def scan_service(url: str) -> str:
    """Run a full AEO audit on any URL.

    Evaluates agent discoverability, API quality, documentation, and MCP
    readiness. Returns a Clarvia score (0-100) with detailed breakdown.
    """
    data = await _api_request("/api/scan", method="POST", json_body={"url": url})
    import json
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_service_details(scan_id: str) -> str:
    """Get the full AEO evaluation report for a previously scanned service.

    Use when you need detailed scoring breakdown (documentation, API design,
    error handling, auth, MCP support) or want to understand why a tool
    scored high or low. Requires a scan_id from search_services or
    scan_service results.
    """
    data = await _api_request(f"/v1/services/{scan_id}")
    import json
    return json.dumps(data, indent=2)


@mcp.tool()
async def list_categories() -> str:
    """List all tool categories in the Clarvia directory with service counts."""
    data = await _api_request("/v1/categories")
    import json
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_stats() -> str:
    """Get aggregate statistics — total indexed services, average AEO score, score distribution, and category breakdown."""
    data = await _api_request("/v1/stats")
    import json
    return json.dumps(data, indent=2)


@mcp.tool()
async def register_service(
    name: str,
    url: str,
    description: str,
    category: str,
    github_url: str | None = None,
) -> str:
    """Submit a new AI tool, MCP server, API, or CLI for Clarvia indexing and AEO scoring.

    The service will be queued for automated scanning.
    """
    body: dict[str, Any] = {
        "name": name,
        "url": url,
        "description": description,
        "category": category,
    }
    if github_url:
        body["github_url"] = github_url
    data = await _api_request("/v1/profiles", method="POST", json_body=body)
    import json
    return json.dumps(data, indent=2)


@mcp.tool()
async def clarvia_gate_check(
    url: str,
    min_rating: str = "AGENT_FRIENDLY",
) -> str:
    """Quick pass/fail safety check for agent tool-use decisions.

    Returns an agent grade (AGENT_NATIVE / AGENT_FRIENDLY / AGENT_POSSIBLE /
    AGENT_HOSTILE) with a boolean pass result. Use before calling any external
    API or MCP server to verify it meets your minimum quality threshold.
    """
    scan = await _api_request("/api/scan", method="POST", json_body={"url": url})
    score = scan.get("clarvia_score", 0)
    grade = _grade_from_score(score)
    passed = _GRADE_ORDER.index(grade) >= _GRADE_ORDER.index(min_rating)

    alternatives = None
    if not passed:
        try:
            alternatives = await _api_request(
                "/v1/services", params={"min_score": 70, "limit": 5}
            )
        except Exception:
            pass

    result = {
        "url": url,
        "score": score,
        "rating": scan.get("rating", ""),
        "agent_grade": grade,
        "pass": passed,
        "reason": (
            f"Service scored {score} ({grade}), meets minimum {min_rating}"
            if passed
            else f"Service scored {score} ({grade}), below minimum {min_rating}. Consider alternatives."
        ),
    }
    if alternatives and not passed:
        result["alternatives"] = alternatives

    import json
    return json.dumps(result, indent=2)


@mcp.tool()
async def clarvia_batch_check(urls: list[str]) -> str:
    """Batch-check up to 10 service URLs — returns pass/fail and agent grade for each.

    More efficient than calling gate_check repeatedly.
    """
    import json
    from datetime import datetime, timezone

    results = []
    for u in urls[:10]:
        try:
            r = json.loads(await clarvia_gate_check(u))
            results.append(r)
        except Exception as e:
            results.append({"url": u, "error": str(e)})

    return json.dumps(
        {"results": results, "checked_at": datetime.now(timezone.utc).isoformat()},
        indent=2,
    )


@mcp.tool()
async def clarvia_find_alternatives(
    category: str,
    min_score: float = 70,
    limit: int = 10,
) -> str:
    """Find higher-rated alternative tools in a given category, ranked by agent-readiness score."""
    data = await _api_request(
        "/v1/services",
        params={"category": category, "min_score": min_score, "limit": limit},
    )
    import json
    return json.dumps(data, indent=2)


@mcp.tool()
async def clarvia_probe(url: str) -> str:
    """Run a live accessibility probe — checks HTTP reachability, response latency, OpenAPI/Swagger, MCP server-card, and agents.json.

    Use when you need real-time health status (not cached scores).
    """
    data = await _api_request(
        "/api/v1/accessibility-probe", method="POST", json_body={"url": url}
    )
    import json
    return json.dumps(data, indent=2)


@mcp.tool()
async def clarvia_submit_feedback(
    profile_id: str,
    outcome: str,
    agent_id: str | None = None,
    error_message: str | None = None,
    latency_ms: float | None = None,
) -> str:
    """Report the outcome after using a tool (success / failure / partial).

    Contributes to Clarvia's reliability dataset. Improves future agent tool
    selection accuracy for all users.
    """
    body: dict[str, Any] = {"profile_id": profile_id, "outcome": outcome}
    if agent_id:
        body["agent_id"] = agent_id
    if error_message:
        body["error_message"] = error_message
    if latency_ms is not None:
        body["latency_ms"] = latency_ms
    data = await _api_request("/v1/feedback", method="POST", json_body=body)
    import json
    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Starlette ASGI app for mounting
# ---------------------------------------------------------------------------

# Build the app (this also creates _session_manager)
mcp_app = mcp.streamable_http_app()

# Expose session_manager so the host FastAPI app can run its lifespan
mcp_session_manager = mcp.session_manager
