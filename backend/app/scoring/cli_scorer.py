"""CLI Tool Scorer — 0-100 scoring for command-line tools.

Four dimensions, 25 points each:
  - Usability (0-25): install method, cross-platform, help indicators
  - Agent Integration (0-25): machine-readable output, scriptability, MCP wrapper
  - Documentation (0-25): README, homepage, examples, changelog
  - Ecosystem (0-25): downloads/stars, maintainer activity, license, known org
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def score_cli_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Score a CLI tool and return structured result with dimension breakdown."""
    usability = _score_usability(tool)
    agent_integration = _score_agent_integration(tool)
    documentation = _score_documentation(tool)
    ecosystem = _score_ecosystem(tool)

    total = usability + agent_integration + documentation + ecosystem

    # Completeness bonus for well-rounded tools
    # Note: agent_integration is structurally harder to score from metadata
    # alone (CLI descriptions rarely mention "json output" or "machine-readable"),
    # so we also reward tools strong in the other 3 dimensions.
    dims = [usability, agent_integration, documentation, ecosystem]
    other_dims = [usability, documentation, ecosystem]
    dims_above_15 = sum(1 for d in dims if d >= 15)
    dims_above_12 = sum(1 for d in dims if d >= 12)
    others_above_15 = sum(1 for d in other_dims if d >= 15)
    others_above_12 = sum(1 for d in other_dims if d >= 12)
    if dims_above_15 >= 3:
        total += 10  # Strong across 3+ dimensions including agent
    elif others_above_15 >= 3:
        total += 9  # Strong in usability+docs+ecosystem (all 3)
    elif dims_above_15 >= 2 and dims_above_12 >= 3:
        total += 9  # Strong in 2, solid in 3+
    elif others_above_15 >= 2 and others_above_12 >= 3:
        total += 8  # Strong in 2 non-agent dims, solid in all 3
    elif dims_above_12 >= 3:
        total += 5  # Solid across 3+ dimensions
    elif others_above_12 >= 3:
        total += 4  # Solid across non-agent dimensions

    total = min(total, 100)

    if total >= 70:
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
            "usability": {"score": usability, "max": 25},
            "agent_integration": {"score": agent_integration, "max": 25},
            "documentation": {"score": documentation, "max": 25},
            "ecosystem": {"score": ecosystem, "max": 25},
        },
    }


def _score_usability(tool: dict[str, Any]) -> int:
    """Usability (0-25): how easy is it to install and use?"""
    score = 0
    install_cmd = tool.get("install_command") or ""
    name = (tool.get("name") or "").lower()
    desc = (tool.get("description") or "").lower()
    keywords = tool.get("keywords") or tool.get("topics") or []
    version = tool.get("version") or ""

    # --- Install method (0-10) ---
    if install_cmd:
        score += 5  # has any install command
        # Package manager bonus (easier than manual)
        if any(pm in install_cmd for pm in ["npm install", "npx", "yarn add", "pnpm add"]):
            score += 3  # npm ecosystem = widest reach
        elif any(pm in install_cmd for pm in ["pip install", "pipx install"]):
            score += 3
        elif any(pm in install_cmd for pm in ["brew install", "apt install", "cargo install"]):
            score += 2
        elif "go install" in install_cmd:
            score += 2
        # Global install hint (more CLI-like)
        if "-g" in install_cmd or "npx" in install_cmd or "pipx" in install_cmd:
            score += 2
    elif tool.get("npm_url"):
        score += 3  # npm listing implies installable
    elif tool.get("repository") or tool.get("url"):
        score += 2  # has source repo = buildable from source

    # --- Cross-platform signals (0-5) ---
    language = (tool.get("language") or "").lower()
    # Languages/runtimes that are inherently cross-platform
    if language in ("typescript", "javascript", "python", "java", "go", "rust"):
        score += 3
    elif language in ("ruby", "php", "c#", "dart"):
        score += 2
    # Keywords hinting at platform support
    platform_kw = ["cross-platform", "windows", "linux", "macos", "docker"]
    if any(kw in str(keywords).lower() for kw in platform_kw):
        score += 2

    # --- CLI indicators (0-5) ---
    cli_signals = ["cli", "command-line", "terminal", "shell", "console", "binary"]
    kw_lower = " ".join(str(k).lower() for k in keywords)
    combined = f"{name} {desc} {kw_lower}"
    if any(sig in combined for sig in cli_signals):
        score += 3
    # Version exists = packaged properly
    if version and version != "0.0.0":
        score += 2

    # --- Interactive/help signals (0-5) ---
    help_signals = ["--help", "interactive", "wizard", "prompt", "autocomplete",
                    "completion", "config"]
    if any(sig in combined for sig in help_signals):
        score += 3
    # Scoped package = org-maintained, usually good UX
    if name.startswith("@") and "/" in name:
        score += 2

    return min(score, 25)


def _score_agent_integration(tool: dict[str, Any]) -> int:
    """Agent Integration (0-25): can an AI agent use this tool programmatically?"""
    score = 0
    name = (tool.get("name") or "").lower()
    desc = (tool.get("description") or "").lower()
    keywords = tool.get("keywords") or tool.get("topics") or []
    kw_lower = " ".join(str(k).lower() for k in keywords)
    combined = f"{name} {desc} {kw_lower}"
    install_cmd = tool.get("install_command") or ""

    # --- CLI baseline (0-5) ---
    # All CLI tools are inherently agent-usable: they accept arguments,
    # return exit codes, and produce output that can be captured.
    cli_signals = ["cli", "command-line", "terminal", "shell", "console", "binary"]
    if any(sig in combined for sig in cli_signals):
        score += 3  # Explicitly a CLI tool
    elif install_cmd:
        score += 2  # Installable = runnable by agent
    else:
        score += 1  # Registered as CLI = likely runnable

    # Global install = easier for agents (no project context needed)
    if "-g" in install_cmd or "npx" in install_cmd or "pipx" in install_cmd:
        score += 2

    # --- Machine-readable output (0-8) ---
    output_signals = ["json", "structured output", "machine-readable", "yaml",
                      "csv", "ndjson", "jsonl", "--format", "--output-format",
                      "output", "format", "export", "report", "table"]
    matched = sum(1 for sig in output_signals if sig in combined)
    score += min(matched * 2, 8)

    # --- MCP/Agent keywords (0-6) ---
    agent_keywords = ["mcp", "model-context-protocol", "modelcontextprotocol",
                      "agent", "ai-agent", "llm", "claude", "openai",
                      "automation", "automate"]
    agent_matched = sum(1 for kw in agent_keywords if kw in combined)
    score += min(agent_matched * 2, 6)

    # --- Scriptability signals (0-5) ---
    script_signals = ["pipe", "stdin", "stdout", "exit code", "non-interactive",
                      "batch", "headless", "programmatic", "api", "sdk",
                      "scriptable", "ci/cd", "ci", "pipeline", "transform",
                      "convert", "parse", "generate", "compile", "lint",
                      "test", "check", "validate", "run", "execute"]
    script_matched = sum(1 for sig in script_signals if sig in combined)
    score += min(script_matched * 2, 5)

    # --- MCP server/wrapper exists (0-4) ---
    # Only award if not already counted via agent_keywords above
    if ("mcp" in name or "mcp" in kw_lower) and agent_matched == 0:
        score += 4  # IS an MCP tool or has MCP wrapper

    return min(score, 25)


def _score_documentation(tool: dict[str, Any]) -> int:
    """Documentation (0-25): how well documented is this tool?"""
    score = 0
    homepage = tool.get("homepage") or ""
    repo = tool.get("repository") or tool.get("url") or ""
    if isinstance(repo, dict):
        repo = repo.get("url", "")
    version = tool.get("version") or ""
    desc = tool.get("description") or ""
    keywords = tool.get("keywords") or tool.get("topics") or []
    npm_url = tool.get("npm_url") or ""

    # --- Homepage/website (0-6) ---
    if homepage and repo and homepage != repo:
        score += 6  # dedicated website separate from repo
    elif homepage:
        score += 4  # has homepage (may be repo readme link)
    elif repo:
        score += 2  # at least a repo

    # --- Repository presence (0-5) ---
    repo_str = str(repo)
    if "github.com" in repo_str:
        score += 5
    elif "gitlab.com" in repo_str or "bitbucket.org" in repo_str:
        score += 4
    elif repo_str:
        score += 2

    # --- npm/PyPI listing (0-3) ---
    if npm_url:
        score += 3  # npm = has package.json, readme rendered
    elif tool.get("pypi_url"):
        score += 3

    # --- Description quality (0-5) ---
    desc_len = len(desc)
    if desc_len > 100:
        score += 5
    elif desc_len > 50:
        score += 3
    elif desc_len > 15:
        score += 2
    elif desc_len > 0:
        score += 1

    # --- Keywords/topics (0-3) ---
    kw_count = len(keywords)
    if kw_count >= 5:
        score += 3
    elif kw_count >= 3:
        score += 2
    elif kw_count >= 1:
        score += 1

    # --- Version maturity (0-3) ---
    if version:
        parts = version.split(".")
        if len(parts) >= 1 and parts[0].isdigit():
            major = int(parts[0])
            if major >= 1:
                score += 3  # stable release
            else:
                score += 1  # pre-1.0

    return min(score, 25)


def _score_ecosystem(tool: dict[str, Any]) -> int:
    """Ecosystem (0-25): community adoption, maintainer health, trust."""
    score = 0
    name = (tool.get("name") or "").lower()
    source = tool.get("source") or ""
    stars = tool.get("stars") or 0
    npm_score = tool.get("score") or 0  # npm search relevance
    license_val = tool.get("license") or ""
    version = tool.get("version") or ""
    updated_at = tool.get("updated_at") or ""
    repo = tool.get("repository") or ""
    if isinstance(repo, dict):
        repo = repo.get("url", "")

    # --- Popularity proxy (0-10) ---
    # GitHub stars — strong signal of community adoption
    if stars >= 10000:
        score += 10
    elif stars >= 5000:
        score += 8
    elif stars >= 1000:
        score += 6
    elif stars >= 100:
        score += 4
    elif stars >= 10:
        score += 2
    elif stars > 0:
        score += 1
    # npm search relevance score (when no stars)
    # Actual range: 1-1353, p75=155, p50=59
    if stars == 0 and npm_score:
        if npm_score > 500:
            score += 7
        elif npm_score > 200:
            score += 5
        elif npm_score > 100:
            score += 4
        elif npm_score > 50:
            score += 3
        elif npm_score > 10:
            score += 2

    # --- Maintainer activity (0-5) ---
    if updated_at:
        try:
            updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - updated).days
            if days_ago <= 30:
                score += 5
            elif days_ago <= 90:
                score += 4
            elif days_ago <= 180:
                score += 3
            elif days_ago <= 365:
                score += 2
            else:
                score += 1
        except (ValueError, TypeError):
            pass
    elif version:
        score += 1  # at least has a version = some maintenance

    # --- License (0-4) ---
    oss_licenses = ["mit", "apache", "bsd", "gpl", "isc", "mpl", "unlicense", "lgpl"]
    if license_val and any(l in license_val.lower() for l in oss_licenses):
        score += 4
    elif license_val:
        score += 2
    elif "github.com" in str(repo):
        score += 1  # GitHub = likely has license

    # --- Known org/project (0-5) ---
    well_known = ["anthropic", "google", "microsoft", "aws", "stripe", "github",
                  "slack", "notion", "vercel", "supabase", "cloudflare", "docker",
                  "openai", "langchain", "sentry", "datadog", "hashicorp",
                  "modelcontextprotocol", "hubspot", "twilio", "mongodb",
                  "postgres", "redis", "firebase"]
    if any(wk in name for wk in well_known):
        score += 5

    # --- Source reliability (0-3) ---
    source_points = {
        "npm": 3,
        "github": 2,
        "homebrew": 3,
        "mcp_registry": 3,
        "glama": 2,
    }
    score += source_points.get(source, 1)

    # --- Version maturity (0-2) ---
    if version:
        parts = version.split(".")
        if len(parts) >= 1 and parts[0].isdigit():
            major = int(parts[0])
            if major >= 2:
                score += 2  # Multiple major versions = long-lived
            elif major >= 1:
                score += 1

    # --- Homepage / website presence (0-2) ---
    homepage = tool.get("homepage") or ""
    if homepage and "github.com" not in homepage:
        score += 2  # Dedicated website = invested maintainer
    elif homepage:
        score += 1

    # --- Metadata completeness (0-3) ---
    # Tools with rich metadata show invested maintainers
    keywords = tool.get("keywords") or tool.get("topics") or []
    desc = tool.get("description") or ""
    completeness = 0
    if len(keywords) >= 10:
        completeness += 1
    if len(desc) > 100:
        completeness += 1
    if version and repo and homepage:
        completeness += 1
    score += completeness

    return min(score, 25)
