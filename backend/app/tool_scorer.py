"""Tool Scorer — proxy AEO scores for collected tools without full website scans.

Assigns a 0–100 Clarvia-compatible score based on available metadata:
  - Description quality (0–20)
  - Documentation signals (0–20)
  - Ecosystem presence (0–20)
  - Agent compatibility signals (0–25)
  - Trust signals (0–15)
"""

from __future__ import annotations

import re
from typing import Any


def score_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Score a collected tool and return a service-compatible dict."""
    source = tool.get("source", "")
    tool_type = tool.get("type", "general")

    # Auto-detect MCP registry entries
    if not source and "server" in tool:
        source = "mcp_registry"
        tool_type = "mcp_server"

    desc = tool.get("description") or ""
    name = tool.get("name") or tool.get("title") or ""
    homepage = tool.get("homepage") or tool.get("websiteUrl") or ""
    repo = tool.get("repository") or ""
    if isinstance(repo, dict):
        repo = repo.get("url", "")
    version = tool.get("version") or ""
    keywords = tool.get("keywords") or []
    npm_score = tool.get("score", 0)  # npm search relevance score

    # --- Description quality (0-20) ---
    desc_score = 0
    desc_len = len(desc)
    if desc_len > 10:
        desc_score += 3
    if desc_len > 30:
        desc_score += 3
    if desc_len > 80:
        desc_score += 3
    if desc_len > 150:
        desc_score += 3
    if desc_len > 300:
        desc_score += 2
    # Bonus for descriptive keywords
    agent_keywords = ["agent", "ai", "llm", "mcp", "tool", "api", "automat", "integration", "workflow"]
    matched_kw = sum(1 for k in agent_keywords if k in desc.lower())
    desc_score += min(matched_kw * 2, 6)
    desc_score = min(desc_score, 20)

    # --- Documentation signals (0-20) ---
    doc_score = 0
    if homepage:
        doc_score += 5
    if repo:
        doc_score += 5
    if version and version != "0.0.0":
        ver_parts = version.split(".")
        doc_score += 3
        # Higher version = more mature
        if len(ver_parts) >= 1 and ver_parts[0].isdigit() and int(ver_parts[0]) >= 1:
            doc_score += 2
    if tool.get("openapi_url"):
        doc_score += 3
    if tool.get("npm_url"):
        doc_score += 2
    if keywords and len(keywords) >= 2:
        doc_score += 2
    if keywords and len(keywords) >= 5:
        doc_score += 1
    doc_score = min(doc_score, 20)

    # --- Ecosystem presence (0-20) ---
    eco_score = 0
    # Source reliability bonus
    source_bonuses = {
        "mcp_registry": 6,
        "glama": 6,
        "github": 5,
        "npm": 5,
        "apis_guru": 7,
        "n8n": 6,
        "composio": 7,
    }
    eco_score += source_bonuses.get(source, 3)
    # npm popularity signal
    if npm_score > 5000:
        eco_score += 6
    elif npm_score > 1000:
        eco_score += 4
    elif npm_score > 100:
        eco_score += 2
    # Has install command = published
    if tool.get("install_command"):
        eco_score += 4
    # MCP completeness tier (drives score spread for registry entries)
    server_data_eco = tool.get("server", {})
    if server_data_eco:
        has_website = bool(server_data_eco.get("websiteUrl"))
        has_remotes = bool(server_data_eco.get("remotes"))
        has_packages = bool(server_data_eco.get("packages"))
        completeness = sum([has_website, has_remotes, has_packages])
        eco_score += completeness * 3  # 0, 3, 6, or 9 points spread
    eco_score = min(eco_score, 20)

    # --- Agent compatibility (0-25) ---
    agent_score = 0
    type_bonuses = {
        "mcp_server": 18,
        "skill": 14,
        "cli_tool": 8,
        "api": 12,
        "connector": 10,
    }
    agent_score += type_bonuses.get(tool_type, 5)
    # MCP-specific signals (key differentiators for registry entries)
    server_data = tool.get("server", {})
    if server_data:
        if server_data.get("tools"):
            agent_score += 4
        if server_data.get("prompts"):
            agent_score += 2
        if server_data.get("resources"):
            agent_score += 1
        # remotes = hosted/deployable (only 32% have it)
        remotes = server_data.get("remotes")
        if remotes:
            agent_score += 4
            if isinstance(remotes, list) and len(remotes) > 1:
                agent_score += 2  # multiple deployment options
        # packages = installable (69% have it)
        packages = server_data.get("packages")
        if packages:
            agent_score += 2
        # websiteUrl = well-maintained (only 16% have it)
        if server_data.get("websiteUrl"):
            agent_score += 3
        # title = extra polish
        if server_data.get("title"):
            agent_score += 1
    if tool.get("openapi_url"):
        agent_score += 5
    agent_score = min(agent_score, 25)

    # --- Trust signals (0-15) ---
    trust_score = 0
    if repo and "github.com" in str(repo):
        trust_score += 4
    if homepage and re.match(r"https?://", homepage):
        trust_score += 3
    if version and re.match(r"\d+\.\d+", version):
        trust_score += 2
    # Official registry = more trust
    if source in ("mcp_registry", "apis_guru"):
        trust_score += 3
    # Well-known org/project names signal trust
    well_known = ["anthropic", "google", "microsoft", "aws", "stripe", "github",
                  "slack", "notion", "vercel", "supabase", "cloudflare", "docker",
                  "postgres", "mongodb", "redis", "openai", "langchain", "firebase"]
    name_lower = name.lower()
    if any(wk in name_lower for wk in well_known):
        trust_score += 3
    trust_score = min(trust_score, 15)

    total = desc_score + doc_score + eco_score + agent_score + trust_score

    # Rating
    if total >= 75:
        rating = "Strong"
    elif total >= 50:
        rating = "Moderate"
    elif total >= 30:
        rating = "Basic"
    else:
        rating = "Low"

    return {
        "clarvia_score": total,
        "rating": rating,
        "dimensions": {
            "description_quality": {"score": desc_score, "max": 20},
            "documentation": {"score": doc_score, "max": 20},
            "ecosystem_presence": {"score": eco_score, "max": 20},
            "agent_compatibility": {"score": agent_score, "max": 25},
            "trust_signals": {"score": trust_score, "max": 15},
        },
    }


def normalize_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Normalize a collected tool into a service-compatible format."""
    source = tool.get("source", "unknown")
    tool_type = tool.get("type", "general")

    # Auto-detect MCP registry entries (have "server" key with schema)
    if source == "unknown" and "server" in tool:
        source = "mcp_registry"
        tool_type = "mcp_server"

    # Extract name
    server = tool.get("server", {})
    name = server.get("name") or tool.get("name") or tool.get("title") or "Unknown"

    # Extract description
    desc = server.get("description") or tool.get("description") or ""

    # Extract URL
    url = (
        tool.get("homepage")
        or tool.get("url")
        or tool.get("npm_url")
        or server.get("websiteUrl")
        or ""
    )
    repo = tool.get("repository") or server.get("repository", {})
    repo_url = repo.get("url", "") if isinstance(repo, dict) else (repo or "")
    if not url and repo_url:
        url = repo_url

    # Score it
    scored = score_tool(tool)

    # Map to service_type
    type_map = {
        "mcp_server": "mcp_server",
        "skill": "skill",
        "cli_tool": "cli_tool",
        "api": "api",
        "connector": "api",
    }
    service_type = type_map.get(tool_type, "general")

    # Build type_config for connection info
    type_config: dict[str, Any] = {}
    if service_type == "mcp_server":
        if tool.get("install_command"):
            type_config["npm_package"] = tool.get("install_command", "").replace("npm install ", "")
        if server.get("websiteUrl"):
            type_config["endpoint_url"] = server["websiteUrl"]
        tools_list = server.get("tools")
        if tools_list:
            type_config["tools"] = tools_list[:10]  # cap for response size
    elif service_type == "cli_tool":
        if tool.get("install_command"):
            type_config["install_command"] = tool["install_command"]
        type_config["binary_name"] = name.split("/")[-1]
    elif service_type == "api":
        if tool.get("openapi_url"):
            type_config["openapi_url"] = tool["openapi_url"]
        if tool.get("url"):
            type_config["base_url"] = tool["url"]

    # Classify category
    category = tool.get("category", "other")
    if category == "other":
        name_lower = name.lower()
        desc_lower = desc.lower()
        combined = f"{name_lower} {desc_lower}"
        cat_keywords = {
            "ai": ["ai", "llm", "gpt", "claude", "openai", "ml", "model"],
            "developer_tools": ["github", "git", "docker", "ci", "deploy", "dev"],
            "communication": ["slack", "discord", "email", "chat", "message"],
            "data": ["database", "sql", "analytics", "data", "postgres"],
            "productivity": ["notion", "calendar", "task", "project"],
            "blockchain": ["solana", "ethereum", "web3", "crypto", "defi"],
            "payments": ["payment", "stripe", "billing", "invoice"],
        }
        for cat, kws in cat_keywords.items():
            if any(kw in combined for kw in kws):
                category = cat
                break

    # Generate stable scan_id from source + name
    safe_name = re.sub(r"[^a-z0-9]", "_", name.lower())[:40]
    scan_id = f"tool_{source}_{safe_name}"

    return {
        "scan_id": scan_id,
        "url": url,
        "service_name": name,
        "description": desc,
        "clarvia_score": scored["clarvia_score"],
        "rating": scored["rating"],
        "dimensions": scored["dimensions"],
        "category": category,
        "service_type": service_type,
        "type_config": type_config if type_config else None,
        "scanned_at": None,
        "source": f"collected:{source}",
        "tags": tool.get("keywords", [])[:5],
    }
