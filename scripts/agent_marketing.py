#!/usr/bin/env python3
"""Agent Marketing Automation — targets AI agents, not humans.

Marketing channels (all agent-facing):
1. MCP Registry directories (awesome-lists, Smithery, Glama)
2. npm package optimization (keywords, description)
3. PyPI package optimization
4. .well-known/agents.json on clarvia.art
5. OpenAPI spec SEO (agent-discoverable descriptions)
6. GitHub repo optimization (topics, description)
7. MCP directory PRs
"""

import json
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
LOG_FILE = PROJECT_DIR / "data" / "marketing-log.jsonl"
API_URL = "https://clarvia-api.onrender.com"


def log_activity(activity: str, channel: str, detail: str = "", success: bool = True):
    """Log marketing activity."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "activity": activity,
        "channel": channel,
        "detail": detail,
        "success": success,
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info("[%s] %s: %s", channel, activity, detail or "OK")
    return entry


def get_todays_activities() -> list[dict]:
    """Get marketing activities done today."""
    if not LOG_FILE.exists():
        return []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    activities = []
    with open(LOG_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("ts", "").startswith(today):
                    activities.append(entry)
            except json.JSONDecodeError:
                continue
    return activities


def optimize_npm_package():
    """Ensure npm package has optimal keywords and description for agent discovery."""
    pkg_json = PROJECT_DIR / "mcp-server" / "package.json"
    if not pkg_json.exists():
        return log_activity("npm_optimize", "npm", "package.json not found", False)

    with open(pkg_json) as f:
        pkg = json.load(f)

    # Optimal keywords for agent discovery
    target_keywords = [
        "mcp", "mcp-server", "model-context-protocol", "ai-agent",
        "agent-tools", "tool-discovery", "aeo", "clarvia",
        "ai-tools", "llm-tools", "agent-compatibility",
        "tool-scoring", "api-scanner", "agent-friendly",
        "claude", "cursor", "windsurf", "cline"
    ]

    current_kw = set(pkg.get("keywords", []))
    target_kw = set(target_keywords)

    if not target_kw.issubset(current_kw):
        pkg["keywords"] = sorted(list(current_kw | target_kw))
        # Update description for agent discoverability
        pkg["description"] = (
            "MCP server for Clarvia — AI agent tool discovery and AEO scoring. "
            "Search 15,400+ indexed tools (MCP servers, APIs, CLIs), check agent-compatibility scores, "
            "find alternatives, audit dependencies, and get real-time enrichment data."
        )
        with open(pkg_json, "w") as f:
            json.dump(pkg, f, indent=2)
        return log_activity("npm_keywords_updated", "npm", f"Added {len(target_kw - current_kw)} keywords")
    return log_activity("npm_keywords_check", "npm", "Already optimized")


def ensure_agents_json():
    """Ensure .well-known/agents.json exists in frontend public dir."""
    agents_json_path = PROJECT_DIR / "frontend" / "public" / ".well-known" / "agents.json"
    agents_json_path.parent.mkdir(parents=True, exist_ok=True)

    agents_data = {
        "name": "Clarvia",
        "description": "AI agent tool discovery and AEO scoring platform. 15,400+ indexed tools.",
        "url": "https://clarvia.art",
        "api": {
            "base_url": "https://clarvia-api.onrender.com",
            "openapi": "https://clarvia-api.onrender.com/openapi.json",
            "docs": "https://clarvia-api.onrender.com/docs"
        },
        "mcp": {
            "npm_package": "clarvia-mcp-server",
            "install": "npx clarvia-mcp-server",
            "tools_count": 24,
            "transport": "stdio"
        },
        "capabilities": [
            "tool_discovery",
            "tool_scoring",
            "vulnerability_check",
            "dependency_audit",
            "compliance_checklist",
            "tool_comparison",
            "trend_analysis"
        ],
        "pricing": "free",
        "rate_limits": {
            "requests_per_minute": 100,
            "batch_max": 100
        }
    }

    with open(agents_json_path, "w") as f:
        json.dump(agents_data, f, indent=2)
    return log_activity("agents_json_updated", "web", str(agents_json_path))


def optimize_github_repo():
    """Optimize GitHub repo for agent discoverability."""
    try:
        # Update repo description and topics
        result = subprocess.run(
            ["gh", "repo", "edit", "clarvia-project/scanner",
             "--description", "AI agent tool discovery & AEO scoring — 15,400+ indexed MCP servers, APIs, CLIs. Free API + 24 MCP tools.",
             "--add-topic", "mcp", "--add-topic", "ai-agents", "--add-topic", "tool-discovery",
             "--add-topic", "aeo", "--add-topic", "agent-tools", "--add-topic", "llm-tools",
             "--add-topic", "mcp-server", "--add-topic", "ai-tools"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return log_activity("github_repo_optimized", "github", "Topics and description updated")
        return log_activity("github_repo_optimize", "github", result.stderr[:200], False)
    except Exception as e:
        return log_activity("github_repo_optimize", "github", str(e)[:200], False)


def submit_to_mcp_directories():
    """Submit Clarvia to MCP directory awesome-lists via PRs."""
    try:
        result = subprocess.run(
            ["bash", str(SCRIPT_DIR / "submit_to_directories.sh"), "--dry-run"],
            capture_output=True, text=True, timeout=60
        )
        return log_activity("directory_submission_check", "mcp_directories",
                          "Dry run complete" if result.returncode == 0 else result.stderr[:200])
    except Exception as e:
        return log_activity("directory_submission", "mcp_directories", str(e)[:200], False)


def check_npm_listing():
    """Verify npm package is discoverable with key search terms."""
    import urllib.request
    searches = ["mcp tool discovery", "ai agent tools", "mcp server scoring"]
    found_count = 0
    for query in searches:
        try:
            url = f"https://registry.npmjs.org/-/v1/search?text={query.replace(' ', '+')}&size=20"
            req = urllib.request.Request(url, headers={"User-Agent": "clarvia-marketing/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                names = [p["package"]["name"] for p in data.get("objects", [])]
                if "clarvia-mcp-server" in names:
                    found_count += 1
        except Exception:
            pass
    return log_activity("npm_search_visibility", "npm", f"Found in {found_count}/{len(searches)} searches")


def run_daily_marketing():
    """Run all daily marketing activities."""
    logger.info("=== Starting daily agent marketing ===")
    activities = []

    activities.append(optimize_npm_package())
    activities.append(ensure_agents_json())
    activities.append(optimize_github_repo())
    activities.append(check_npm_listing())
    activities.append(submit_to_mcp_directories())

    success_count = sum(1 for a in activities if a.get("success"))
    logger.info("=== Daily marketing complete: %d/%d successful ===", success_count, len(activities))
    return activities


if __name__ == "__main__":
    run_daily_marketing()
