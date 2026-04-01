"""Tool Scorer — proxy AEO scores for collected tools without full website scans.

Assigns a 0–100 Clarvia-compatible score based on available metadata:
  - Description quality (0–20)
  - Documentation signals (0–20)
  - Ecosystem presence (0–20)
  - Agent compatibility signals (0–25)
  - Metadata quality / trust signals (0–15)
"""

from __future__ import annotations

import re
from typing import Any


def score_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """DEPRECATED: Use app.scoring.score_tool() instead.

    This function is kept as a backward-compatible proxy.
    All scoring logic now lives in app/scoring/ with type-specific scorers.
    """
    from .scoring import score_tool as _new_score_tool
    result = _new_score_tool(tool)
    # Map new 4x25 dimensions to legacy 5-dimension format for any old callers
    dims = result.get("dimensions", {})
    dim_scores = [v.get("score", 0) for v in dims.values()]
    total = result.get("clarvia_score", sum(dim_scores))
    return {
        "clarvia_score": total,
        "rating": result.get("rating", "Low"),
        "dimensions": result.get("dimensions", {}),
        "source": result.get("source", "unknown"),
        "scoring_confidence": result.get("scoring_confidence", 0),
    }


def detect_pricing(tool: dict[str, Any]) -> str:
    """Auto-detect pricing tier from tool metadata."""
    name = (tool.get("name") or "").lower()
    desc = (tool.get("description") or "").lower()
    combined = f"{name} {desc}"

    # Open source indicators
    repo = tool.get("repository") or ""
    if isinstance(repo, dict):
        repo = repo.get("url", "")
    license_val = tool.get("license") or ""
    if license_val and any(l in license_val.lower() for l in ["mit", "apache", "bsd", "gpl", "isc", "mpl", "unlicense"]):
        return "open_source"
    if "github.com" in str(repo) and any(w in combined for w in ["open source", "free", "open-source"]):
        return "open_source"

    # Free indicators
    free_signals = ["free", "no cost", "gratis", "libre", "community edition"]
    if any(s in combined for s in free_signals):
        return "free"

    # Freemium indicators
    freemium_signals = ["free tier", "free plan", "starter plan", "hobby plan",
                        "free forever", "generous free", "free to start"]
    if any(s in combined for s in freemium_signals):
        return "freemium"

    # Paid indicators
    paid_signals = ["enterprise", "pricing", "subscription", "per month",
                    "per year", "commercial", "license required", "paid"]
    if any(s in combined for s in paid_signals):
        return "paid"

    # MCP servers from registries are typically open source
    if tool.get("source") in ("mcp_registry",) or "server" in tool:
        if repo:
            return "open_source"
        return "free"

    # npm packages with GitHub repos are typically open source
    if tool.get("source") == "npm" and repo:
        return "open_source"

    return "unknown"


def extract_capabilities(tool: dict[str, Any]) -> list[str]:
    """Extract machine-readable capabilities from tool metadata."""
    desc = (tool.get("description") or "").lower()
    server = tool.get("server", {})
    name = (tool.get("name") or "").lower()
    combined = f"{name} {desc}"

    capability_map = {
        "read_files": ["read file", "file access", "file system", "filesystem", "read document"],
        "write_files": ["write file", "create file", "save file", "file creation"],
        "send_email": ["send email", "email sending", "smtp", "transactional email"],
        "send_message": ["send message", "messaging", "chat", "slack", "discord", "notification"],
        "web_search": ["search", "web search", "google", "bing", "serp"],
        "web_scrape": ["scrape", "crawl", "extract data", "web scraping"],
        "database_query": ["database", "sql", "query", "db access", "postgres", "mysql", "mongodb"],
        "api_call": ["api", "http", "rest", "graphql", "endpoint"],
        "code_execution": ["execute code", "run code", "sandbox", "eval", "repl"],
        "image_generation": ["generate image", "image generation", "dall-e", "stable diffusion", "midjourney"],
        "text_generation": ["generate text", "text generation", "completion", "llm", "gpt"],
        "translation": ["translate", "translation", "multilingual", "i18n"],
        "transcription": ["transcribe", "transcription", "speech-to-text", "stt"],
        "payment_processing": ["payment", "charge", "billing", "checkout", "stripe"],
        "authentication": ["auth", "login", "oauth", "sso", "jwt", "identity"],
        "file_conversion": ["convert", "transform", "pdf", "csv", "json", "format"],
        "scheduling": ["schedule", "calendar", "booking", "appointment", "cron"],
        "monitoring": ["monitor", "alert", "health check", "uptime", "observability"],
        "version_control": ["git", "commit", "branch", "pull request", "merge"],
        "deployment": ["deploy", "release", "ci/cd", "pipeline", "build"],
        "data_analysis": ["analyze", "analytics", "visualization", "chart", "dashboard"],
        "storage": ["store", "upload", "download", "s3", "blob", "cdn"],
    }

    caps = []
    for cap, keywords in capability_map.items():
        if any(kw in combined for kw in keywords):
            caps.append(cap)

    # MCP server tools as capabilities
    if server and server.get("tools"):
        tools_list = server["tools"]
        if isinstance(tools_list, list):
            for t in tools_list[:5]:
                tool_name = t.get("name", "") if isinstance(t, dict) else str(t)
                if tool_name and tool_name not in caps:
                    caps.append(f"tool:{tool_name}")

    return caps[:15]  # Cap at 15


def detect_difficulty(tool: dict[str, Any]) -> str:
    """Estimate integration difficulty."""
    server = tool.get("server", {})
    tool_type = tool.get("type", "general")

    # MCP servers with packages = easy (just npx)
    if tool_type == "mcp_server" or "server" in tool:
        if server.get("packages"):
            return "easy"
        if server.get("remotes"):
            return "easy"
        return "medium"

    # CLI tools with install command = easy
    if tool.get("install_command"):
        return "easy"

    # APIs with OpenAPI spec = medium (well documented)
    if tool.get("openapi_url"):
        return "medium"

    # Tools with good documentation = medium
    if tool.get("homepage") and tool.get("repository"):
        return "medium"

    return "hard"


def estimate_popularity(tool: dict[str, Any]) -> int:
    """Estimate popularity 0-100 from available signals."""
    score = 0
    server = tool.get("server", {})

    # npm download score (if available)
    npm_score = tool.get("score", 0)
    if npm_score > 10000:
        score += 40
    elif npm_score > 1000:
        score += 25
    elif npm_score > 100:
        score += 15
    elif npm_score > 0:
        score += 5

    # Well-known names get popularity boost
    name = (tool.get("name") or "").lower()
    well_known = ["anthropic", "google", "microsoft", "aws", "stripe", "github",
                  "slack", "notion", "vercel", "supabase", "openai", "langchain",
                  "docker", "postgres", "mongodb", "redis", "twilio", "sendgrid"]
    if any(wk in name for wk in well_known):
        score += 30

    # Source signals
    source = tool.get("source", "")
    if source in ("apis_guru", "composio"):
        score += 15  # curated sources = higher visibility
    elif source in ("mcp_registry", "glama"):
        score += 10
    elif source in ("npm", "github"):
        score += 5

    # MCP completeness = community adoption signal
    if server:
        if server.get("remotes"):
            score += 10  # hosted = more accessible
        if server.get("websiteUrl"):
            score += 10  # has website = more established
        if server.get("tools") and len(server.get("tools", [])) > 5:
            score += 5  # feature-rich

    # Keywords signal relevance
    keywords = tool.get("keywords") or []
    if len(keywords) >= 5:
        score += 5

    return min(score, 100)


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

    # Score it — use the new type-specific scoring engine
    from .scoring import score_tool as _new_score_tool
    scored = _new_score_tool(tool)

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

    # Classify category using the shared _classify() from index_routes
    category = tool.get("category", "other")
    if category == "other":
        try:
            from .routes.index_routes import _classify
            category = _classify(name, desc)
        except ImportError:
            # Fallback if import fails (e.g., during testing)
            category = _classify_fallback(name, desc)

    # Generate stable scan_id from source + name
    safe_name = re.sub(r"[^a-z0-9]", "_", name.lower())[:40]
    scan_id = f"tool_{source}_{safe_name}"

    # Cross-reference IDs for research
    cross_refs: dict[str, str] = {}
    if tool.get("npm_url"):
        cross_refs["npm"] = tool["npm_url"]
    if repo_url and "github.com" in repo_url:
        cross_refs["github"] = repo_url
    if tool.get("pypi_url"):
        cross_refs["pypi"] = tool["pypi_url"]
    if server and server.get("name"):
        cross_refs["mcp_registry"] = server["name"]

    result = {
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
        "source": scored.get("source", f"collected:{source}"),
        "scoring_confidence": scored.get("scoring_confidence", 0),
        "tags": tool.get("keywords", [])[:5],
        "pricing": detect_pricing(tool),
        "capabilities": extract_capabilities(tool),
        "difficulty": detect_difficulty(tool),
        "popularity": estimate_popularity(tool),
        "cross_refs": cross_refs,
    }

    # Auto-extract keywords from description when keywords list is empty
    if not result["tags"] and desc:
        from collections import Counter
        stop = {"this", "that", "with", "from", "your", "have", "will", "been",
                "they", "them", "their", "what", "when", "which", "there", "about",
                "into", "than", "also", "more", "some", "very", "just", "other",
                "over", "such", "only", "does", "most", "like", "make", "made",
                "each", "well", "were", "then", "used", "many", "using", "tool",
                "tools", "allows", "provides", "support", "based", "helps", "enable"}
        words = re.findall(r"[a-zA-Z]{4,}", desc.lower())
        filtered = [w for w in words if w not in stop]
        common = [w for w, _ in Counter(filtered).most_common(5)]
        result["tags"] = common

    return result


def _classify_fallback(name: str, desc: str) -> str:
    """Minimal fallback classifier when index_routes is not importable."""
    combined = f"{name.lower()} {desc.lower()}"
    fallback_map = {
        "ai": ["ai", "llm", "gpt", "claude", "openai", "machine learning",
               "neural", "embedding", "vector", "transformer", "model"],
        "developer_tools": ["github", "git", "docker", "ci", "deploy", "dev",
                            "sdk", "framework", "compiler", "linter", "debugger"],
        "communication": ["slack", "discord", "email", "chat", "message",
                          "notification", "sms", "messaging"],
        "data": ["database", "sql", "analytics", "data", "postgres",
                 "warehouse", "pipeline", "etl"],
        "productivity": ["notion", "calendar", "task", "project",
                         "workflow", "collaboration", "kanban"],
        "blockchain": ["solana", "ethereum", "web3", "crypto", "defi",
                       "blockchain", "smart contract", "token", "nft"],
        "payments": ["payment", "stripe", "billing", "invoice",
                     "checkout", "subscription"],
        "mcp": ["mcp", "model context protocol", "smithery", "glama"],
        "security": ["authentication", "oauth", "encryption", "firewall",
                     "vulnerability", "secret", "credential"],
        "testing": ["test", "jest", "pytest", "cypress", "playwright",
                    "selenium", "coverage", "assertion"],
        "monitoring": ["monitoring", "logging", "tracing", "alerting",
                       "observability", "metrics", "uptime"],
        "database": ["database", "sql", "nosql", "orm", "migration",
                     "redis", "mongodb", "postgres"],
        "cloud": ["cloud", "serverless", "deploy", "hosting",
                  "infrastructure", "container", "kubernetes"],
        "automation": ["automation", "automate", "scheduler", "cron",
                       "workflow", "no-code", "low-code"],
        "media": ["image", "video", "audio", "streaming", "social media",
                  "photo", "podcast"],
        "analytics": ["analytics", "tracking", "dashboard", "reporting",
                      "visualization", "seo", "heatmap"],
        "ecommerce": ["ecommerce", "e-commerce", "shop", "cart", "checkout",
                      "inventory", "shipping"],
        "search": ["search", "indexing", "autocomplete", "elasticsearch"],
        "storage": ["storage", "file upload", "cdn", "backup", "s3"],
        "cms": ["cms", "content management", "headless", "blog", "wordpress"],
        "design": ["design", "figma", "ui", "ux", "wireframe", "prototype"],
        "documentation": ["documentation", "docs", "api reference", "openapi"],
        "education": ["learning", "course", "tutorial", "lms", "education"],
        "healthcare": ["health", "medical", "clinical", "fhir", "patient"],
    }
    cat_hits: dict[str, int] = {}
    for cat, kws in fallback_map.items():
        hits = sum(1 for kw in kws if kw in combined)
        if hits > 0:
            cat_hits[cat] = hits
    if cat_hits:
        return max(cat_hits, key=cat_hits.get)  # type: ignore[arg-type]
    return "other"
