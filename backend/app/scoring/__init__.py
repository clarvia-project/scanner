"""Unified scoring entry point for all tool types.

Routes tools to the appropriate type-specific scorer based on metadata,
returning a standardized output format.

Usage:
    from scoring import score_tool
    result = score_tool(tool_dict)
    # Returns: {score, rating, dimensions: {name: {score, max, evidence}}, tool_type}
"""

from __future__ import annotations

from typing import Any

from .api_scorer import score_api
from .cli_scorer import score_cli_tool
from .connector_scorer import score_connector
from .mcp_scorer import score_mcp_server
from .skill_scorer import score_skill

__all__ = [
    "score_tool", "score_api", "score_cli_tool",
    "score_connector", "score_mcp_server", "score_skill",
]


def detect_tool_type(tool: dict[str, Any]) -> str:
    """Auto-detect tool type from metadata.

    Priority order:
    1. MCP server: has "server" key (from mcp-registry-all.json)
    2. Explicit type field: "api", "connector", "cli_tool", "skill"
    3. Source-based inference: npm/github/homebrew -> cli_tool
    4. Fallback: "general"
    """
    # MCP server detection (registry entries always have "server" dict)
    if "server" in tool and isinstance(tool.get("server"), dict):
        return "mcp_server"

    # Explicit type
    explicit = tool.get("type", "")
    if explicit in ("mcp_server", "api", "connector", "cli_tool", "skill"):
        return explicit

    # Source-based inference
    source = tool.get("source", "")
    if source in ("apis_guru", "composio"):
        return "api"
    if source == "n8n":
        return "connector"
    if source in ("npm", "homebrew"):
        return "cli_tool"
    if source == "github":
        # GitHub repos with skill-related topics -> skill
        topics = tool.get("topics") or tool.get("keywords") or []
        topics_str = " ".join(str(t).lower() for t in topics)
        if any(kw in topics_str for kw in ["skill", "claude-skills", "plugin", "agent-skill"]):
            return "skill"
        return "cli_tool"

    return "general"


def score_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Score any tool by auto-detecting its type and routing to the right scorer.

    Returns:
        {
            "clarvia_score": int (0-100),
            "rating": str ("Strong" | "Moderate" | "Basic" | "Low"),
            "dimensions": {
                "<dim_name>": {"score": int, "max": int, ...}
            },
            "tool_type": str
        }
    """
    tool_type = detect_tool_type(tool)

    if tool_type == "mcp_server":
        result = score_mcp_server(tool)
    elif tool_type == "api":
        result = score_api(tool)
    elif tool_type == "connector":
        result = score_connector(tool)
    elif tool_type == "cli_tool":
        result = score_cli_tool(tool)
    elif tool_type == "skill":
        result = score_skill(tool)
    else:
        # General fallback: use API scorer as it handles the widest range
        result = score_api(tool)
        tool_type = "general"

    result["tool_type"] = tool_type
    return result
