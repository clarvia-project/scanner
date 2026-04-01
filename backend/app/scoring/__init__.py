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
    "score_tool", "detect_source", "compute_confidence",
    "score_api", "score_cli_tool",
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


def detect_source(tool: dict[str, Any]) -> str:
    """Detect data source from tool metadata."""
    # Explicit _source field (set by collection scripts)
    explicit = tool.get("_source", "")
    if explicit:
        return explicit

    # MCP registry entries
    if "server" in tool and isinstance(tool.get("server"), dict):
        return "mcp_registry"

    source = tool.get("source", "")
    if source and source != "unknown":
        return source

    # Infer from URLs and metadata
    url = tool.get("url", "") or tool.get("homepage", "") or ""
    if "apis.guru" in url:
        return "apis_guru"
    if "composio" in url:
        return "composio"
    if "n8n" in url:
        return "n8n"
    npm_url = tool.get("npm_url", "")
    if npm_url or "npmjs.com" in url:
        return "npm"
    pypi_url = tool.get("pypi_url", "")
    if pypi_url or "pypi.org" in url:
        return "pypi"
    repo = tool.get("repository", "")
    if isinstance(repo, dict):
        repo = repo.get("url", "")
    if "github.com" in str(repo) or "github.com" in url:
        return "github"
    if "gitlab.com" in str(repo) or "gitlab.com" in url:
        return "gitlab"

    return "community"


def compute_confidence(tool: dict[str, Any]) -> int:
    """Compute scoring confidence (0-100) based on available evidence."""
    confidence = 0
    desc = tool.get("description") or (tool.get("server", {}) or {}).get("description", "") or ""

    if desc and len(desc) > 50:
        confidence += 20
    elif desc and len(desc) > 10:
        confidence += 10

    homepage = tool.get("homepage") or tool.get("url") or (tool.get("server", {}) or {}).get("websiteUrl", "")
    if homepage:
        confidence += 15

    repo = tool.get("repository") or ""
    if isinstance(repo, dict):
        repo = repo.get("url", "")
    if repo:
        confidence += 15

    version = tool.get("version") or ""
    if version:
        confidence += 15

    if tool.get("npm_url") or tool.get("pypi_url"):
        confidence += 10

    npm_quality = tool.get("npm_quality", {})
    if npm_quality.get("available"):
        confidence += 10

    keywords = tool.get("keywords") or tool.get("topics") or []
    if len(keywords) >= 3:
        confidence += 5

    if tool.get("license"):
        confidence += 5

    # MCP registry entries get bonus (curated source)
    server = tool.get("server", {})
    if server and isinstance(server, dict):
        if server.get("tools"):
            confidence += 5
        if server.get("packages") or server.get("remotes"):
            confidence += 5

    return min(100, confidence)


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
    result["source"] = detect_source(tool)
    result["scoring_confidence"] = compute_confidence(tool)

    # ── npm quality bonus (applies to all tool types) ──
    # If npm_quality enrichment data is present, boost the score.
    # npms.io provides 0-1 normalized scores for quality, popularity, maintenance.
    # This rewards tools with strong npm ecosystem presence regardless of type.
    npm_quality_data = tool.get("npm_quality", {})
    if npm_quality_data.get("available") and tool_type != "mcp_server":
        # MCP servers handle npm bonus in their own scorer
        nq = npm_quality_data.get("quality", 0)
        np_ = npm_quality_data.get("popularity", 0)
        nm = npm_quality_data.get("maintenance", 0)
        bonus = 0
        # Quality: well-tested, documented code (0-3)
        if nq >= 0.8:
            bonus += 3
        elif nq >= 0.6:
            bonus += 2
        elif nq >= 0.4:
            bonus += 1
        # Popularity: community adoption (0-3)
        if np_ >= 0.5:
            bonus += 3
        elif np_ >= 0.2:
            bonus += 2
        elif np_ >= 0.05:
            bonus += 1
        # Maintenance: actively maintained (0-2)
        if nm >= 0.7:
            bonus += 2
        elif nm >= 0.4:
            bonus += 1
        bonus = min(bonus, 8)
        result["clarvia_score"] = min(100, result["clarvia_score"] + bonus)
        # Re-calculate rating after bonus
        total = result["clarvia_score"]
        if total >= 80:
            result["rating"] = "Excellent"
        elif total >= 60:
            result["rating"] = "Strong"
        elif total >= 35:
            result["rating"] = "Moderate"
        elif total >= 20:
            result["rating"] = "Basic"
        else:
            result["rating"] = "Low"

    return result
