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
    """DEPRECATED: Legacy scorer. Use app.scoring.score_tool() instead.

    Kept only for backwards compatibility. normalize_tool() now calls the new
    type-specific scoring engine directly.
    """
    source = tool.get("source", "")
    tool_type = tool.get("type", "general")

    # Auto-detect MCP registry entries
    if not source and "server" in tool:
        source = "mcp_registry"
        tool_type = "mcp_server"

    server_data_raw = tool.get("server", {})
    desc = tool.get("description") or (server_data_raw.get("description") if server_data_raw else "") or ""
    name = tool.get("name") or tool.get("title") or (server_data_raw.get("name") if server_data_raw else "") or ""
    homepage = (tool.get("homepage") or tool.get("websiteUrl")
                or (server_data_raw.get("websiteUrl") if server_data_raw else "")
                or "")
    repo = tool.get("repository") or (server_data_raw.get("repository") if server_data_raw else "") or ""
    if isinstance(repo, dict):
        repo = repo.get("url", "")
    version = tool.get("version") or ""
    keywords = tool.get("keywords") or []
    npm_score = tool.get("score", 0)  # npm search relevance score

    # --- Description quality (0-20) ---
    desc_score = 0
    desc_len = len(desc)
    if desc_len > 10:
        desc_score += 5  # Any description at all gets base points
    if desc_len > 30:
        desc_score += 3
    if desc_len > 80:
        desc_score += 3
    if desc_len > 150:
        desc_score += 2
    if desc_len > 300:
        desc_score += 1
    # Bonus for descriptive keywords
    agent_keywords = ["agent", "ai", "llm", "mcp", "tool", "api", "automat",
                      "integration", "workflow", "server", "client", "plugin",
                      "extension", "service", "connect", "interface"]
    matched_kw = sum(1 for k in agent_keywords if k in desc.lower())
    desc_score += min(matched_kw * 2, 6)
    desc_score = min(desc_score, 20)

    # --- Documentation signals (0-20) ---
    doc_score = 0
    has_homepage = bool(homepage)
    has_repo = bool(repo)
    if has_homepage and has_repo:
        doc_score += 14  # Both = 14 points
    elif has_homepage or has_repo:
        doc_score += 8   # Either one = 8 points
    if version and version != "0.0.0":
        doc_score += 3   # Any version (including 0.x) gets 3
        ver_parts = version.split(".")
        if len(ver_parts) >= 1 and ver_parts[0].isdigit() and int(ver_parts[0]) >= 1:
            doc_score += 2  # Mature version bonus
    if tool.get("openapi_url"):
        doc_score += 3
    if tool.get("npm_url"):
        doc_score += 2
    # MCP server registry listing = documentation evidence
    if server_data_raw and (server_data_raw.get("name") or server_data_raw.get("tools")):
        doc_score += 4
    if keywords and len(keywords) >= 2:
        doc_score += 2
    if keywords and len(keywords) >= 5:
        doc_score += 1
    doc_score = min(doc_score, 20)

    # --- Ecosystem presence (0-20) ---
    eco_score = 0
    # Source reliability bonus (increased)
    source_bonuses = {
        "mcp_registry": 10,
        "glama": 9,
        "github": 8,
        "npm": 9,
        "apis_guru": 10,
        "n8n": 8,
        "composio": 10,
    }
    eco_score += source_bonuses.get(source, 6)
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
        eco_score += completeness * 4  # 0, 4, 8, or 12 points spread
    eco_score = min(eco_score, 20)

    # --- Agent compatibility (0-25) ---
    agent_score = 0
    type_bonuses = {
        "mcp_server": 20,
        "skill": 17,
        "cli_tool": 12,
        "api": 16,
        "connector": 14,
    }
    agent_score += type_bonuses.get(tool_type, 8)
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
        trust_score += 5
    if homepage and re.match(r"https?://", homepage):
        trust_score += 4
    if version and re.match(r"\d+\.\d+", version):
        trust_score += 3
    # Official registry = more trust
    if source in ("mcp_registry", "apis_guru"):
        trust_score += 4
    # Well-known org/project names signal trust
    well_known = ["anthropic", "google", "microsoft", "aws", "stripe", "github",
                  "slack", "notion", "vercel", "supabase", "cloudflare", "docker",
                  "postgres", "mongodb", "redis", "openai", "langchain", "firebase",
                  "twilio", "sendgrid", "datadog", "sentry", "hashicorp"]
    name_lower = name.lower()
    if any(wk in name_lower for wk in well_known):
        trust_score += 3

    # Security signals
    if "https" in (homepage or "").lower():
        trust_score += 1  # HTTPS homepage
    if tool.get("license"):
        trust_score += 1  # Has license = more trustworthy
    # Check for security-related keywords in description
    security_positive = ["authentication", "oauth", "encrypted", "secure", "compliance"]
    if any(kw in desc.lower() for kw in security_positive):
        trust_score += 1

    # Dependency/security signals (surface-level checks)
    dep_signals = tool.get("dependencies", {})
    if isinstance(dep_signals, dict) and len(dep_signals) > 0:
        trust_score += 1  # Has declared dependencies = more transparent

    # Check for security-related documentation
    readme = (tool.get("readme") or "").lower()
    if any(w in readme for w in ["security", "vulnerability", "cve", "disclosure"]):
        trust_score += 1

    # Maintained recently (version signal)
    if version:
        ver_parts = version.split(".")
        if len(ver_parts) >= 1 and ver_parts[0].isdigit():
            major = int(ver_parts[0])
            if major >= 2:
                trust_score += 1  # Multiple major versions = long-lived project

    # NOTE: Full security analysis (CVE scanning, SOC2 compliance, GDPR
    # assessment) is planned but not yet available. Current trust scoring
    # is surface-level metadata analysis only.

    trust_score = min(trust_score, 15)

    total = desc_score + doc_score + eco_score + agent_score + trust_score

    # Rating thresholds — unified with scanner.py _get_rating() for consistency.
    # Both systems must use the same labels and thresholds.
    if total >= 90:
        rating = "Exceptional"
    elif total >= 80:
        rating = "Excellent"
    elif total >= 65:
        rating = "Strong"
    elif total >= 45:
        rating = "Moderate"
    elif total >= 25:
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
            "metadata_quality": {"score": trust_score, "max": 15},
        },
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
        "source": f"collected:{source}",
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
