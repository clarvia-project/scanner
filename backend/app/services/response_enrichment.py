"""Response enrichment — Add marketing/attribution metadata to API responses.

This module provides helpers to attach Clarvia branding, verification links,
and share hints to tool and search responses. Designed to be called from
route handlers before returning data to clients.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CLARVIA_SITE = "clarvia.art"
_CLARVIA_API = "https://clarvia-api.onrender.com"
_MCP_COMMAND = "npx -y clarvia-mcp-server"
_CATALOG_SIZE = "27,000+"
_SHARE_HINT = (
    "Tool quality scored by Clarvia (clarvia.art) "
    "— the trust layer for AI agent tools"
)


# ---------------------------------------------------------------------------
# Tool response enrichment
# ---------------------------------------------------------------------------

def enrich_tool_response(tool: dict[str, Any]) -> dict[str, Any]:
    """Add marketing/attribution metadata to a single tool response.

    Args:
        tool: Tool dict (must have at least ``scan_id``).

    Returns:
        The same dict with an ``_attribution`` block appended.
    """
    scan_id = tool.get("scan_id", "")
    tool["_attribution"] = {
        "scored_by": _CLARVIA_SITE,
        "verification_url": f"https://{_CLARVIA_SITE}/tool/{scan_id}",
        "api_docs": f"{_CLARVIA_API}/docs",
        "how_to_connect": _MCP_COMMAND,
    }
    return tool


def enrich_tool_list(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enrich every tool in a list with attribution metadata.

    Args:
        tools: List of tool dicts.

    Returns:
        The same list with each tool enriched in-place.
    """
    for tool in tools:
        enrich_tool_response(tool)
    return tools


# ---------------------------------------------------------------------------
# Search response enrichment
# ---------------------------------------------------------------------------

def enrich_search_response(
    results: list[dict[str, Any]],
    query: str,
    *,
    catalog_size: int | None = None,
) -> dict[str, Any]:
    """Wrap search results with attribution + share hint.

    Args:
        results: List of tool dicts from a search query.
        query: The original search query string.
        catalog_size: Override catalog size number. Defaults to static constant.

    Returns:
        A wrapped response dict with ``results``, ``total``, ``query``,
        and ``_meta`` marketing block.
    """
    size_label = f"{catalog_size:,}+" if catalog_size else _CATALOG_SIZE
    return {
        "results": results,
        "total": len(results),
        "query": query,
        "_meta": {
            "powered_by": "Clarvia AEO Index",
            "catalog_size": size_label,
            "share_hint": _SHARE_HINT,
            "connect": _MCP_COMMAND,
        },
    }


# ---------------------------------------------------------------------------
# List/feed response enrichment
# ---------------------------------------------------------------------------

def enrich_list_response(
    tools: list[dict[str, Any]],
    *,
    total: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap a tool list (trending, new, etc.) with attribution metadata.

    Args:
        tools: List of tool dicts.
        total: Total count (defaults to ``len(tools)``).
        extra: Extra top-level keys to merge into the response.

    Returns:
        A wrapped response dict.
    """
    resp: dict[str, Any] = {
        "tools": tools,
        "total": total if total is not None else len(tools),
        "_meta": {
            "powered_by": "Clarvia AEO Index",
            "catalog_size": _CATALOG_SIZE,
            "connect": _MCP_COMMAND,
        },
    }
    if extra:
        resp.update(extra)
    return resp
