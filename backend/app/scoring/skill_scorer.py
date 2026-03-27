"""Skill Scorer — 0-100 scoring for AI agent skills/plugins.

Four dimensions, 25 points each:
  - Prompt Quality (0-25): description clarity, trigger accuracy, parameter defs
  - Scope & Safety (0-25): permissions, restrictions, error handling, boundaries
  - Integration (0-25): platform compatibility, dependencies, version pinning
  - Documentation (0-25): usage examples, behavior described, limitations noted
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


def score_skill(tool: dict[str, Any]) -> dict[str, Any]:
    """Score a skill/plugin and return structured result with dimension breakdown."""
    prompt_quality = _score_prompt_quality(tool)
    scope_safety = _score_scope_safety(tool)
    integration = _score_integration(tool)
    documentation = _score_documentation(tool)

    total = prompt_quality + scope_safety + integration + documentation

    # Completeness bonus for well-rounded skills
    dims = [prompt_quality, scope_safety, integration, documentation]
    dims_above_15 = sum(1 for d in dims if d >= 15)
    if dims_above_15 >= 3:
        total += 5  # Strong across 3+ dimensions

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
            "prompt_quality": {"score": prompt_quality, "max": 25},
            "scope_safety": {"score": scope_safety, "max": 25},
            "integration": {"score": integration, "max": 25},
            "documentation": {"score": documentation, "max": 25},
        },
    }


def _score_prompt_quality(tool: dict[str, Any]) -> int:
    """Prompt Quality (0-25): how well defined is this skill's purpose?"""
    score = 0
    desc = tool.get("description") or ""
    name = (tool.get("name") or "").lower()
    topics = tool.get("topics") or tool.get("keywords") or []
    topics_lower = " ".join(str(t).lower() for t in topics)

    # --- Description length & clarity (0-10) ---
    desc_len = len(desc)
    if desc_len > 200:
        score += 7
    elif desc_len > 100:
        score += 5
    elif desc_len > 50:
        score += 3
    elif desc_len > 15:
        score += 2
    elif desc_len > 0:
        score += 1

    # Actionable description bonus: contains verbs indicating what it does
    action_verbs = ["automat", "generat", "creat", "manag", "monitor",
                    "analyz", "orchestrat", "execut", "deploy", "build",
                    "connect", "integrat", "transform", "process", "extract"]
    verb_matches = sum(1 for v in action_verbs if v in desc.lower())
    score += min(verb_matches * 2, 3)

    # --- Trigger accuracy / name clarity (0-6) ---
    # Good names clearly indicate function
    name_parts = re.split(r"[-_/\s]", name)
    meaningful_parts = [p for p in name_parts if len(p) > 2]
    if len(meaningful_parts) >= 2:
        score += 3  # descriptive multi-word name
    elif len(meaningful_parts) == 1:
        score += 1

    # Name-description alignment: name words appear in description
    if desc:
        desc_lower = desc.lower()
        aligned = sum(1 for p in meaningful_parts if p in desc_lower)
        if aligned >= 2:
            score += 3
        elif aligned >= 1:
            score += 1

    # --- Parameter/topic specificity (0-6) ---
    topic_count = len(topics)
    if topic_count >= 8:
        score += 4
    elif topic_count >= 5:
        score += 3
    elif topic_count >= 3:
        score += 2
    elif topic_count >= 1:
        score += 1

    # Specific domain topics (not generic)
    specific_domains = ["claude-code", "claude-skills", "plugin", "skill",
                        "agents", "automation", "orchestration", "memory",
                        "context", "workflow", "tool-use"]
    domain_hits = sum(1 for d in specific_domains if d in topics_lower)
    score += min(domain_hits, 2)

    return min(score, 25)


def _score_scope_safety(tool: dict[str, Any]) -> int:
    """Scope & Safety (0-25): are permissions/restrictions well defined?

    Since skills from GitHub lack explicit permission metadata, we infer
    safety signals from description, topics, and project maturity.
    """
    score = 0
    desc = (tool.get("description") or "").lower()
    topics = tool.get("topics") or tool.get("keywords") or []
    topics_lower = " ".join(str(t).lower() for t in topics)
    combined = f"{desc} {topics_lower}"
    stars = tool.get("stars") or 0
    homepage = tool.get("homepage") or ""
    name = (tool.get("name") or "").lower()

    # --- Scope boundaries indicated (0-8) ---
    # Description mentions specific scope (not "do everything")
    scope_signals = ["sandbox", "container", "isolated", "secure", "permission",
                     "restricted", "scoped", "read-only", "safe", "validation",
                     "rate-limit", "throttl"]
    scope_hits = sum(1 for s in scope_signals if s in combined)
    score += min(scope_hits * 3, 8)

    # Focused purpose (short focused desc > vague long one)
    desc_words = desc.split()
    if 5 <= len(desc_words) <= 30:
        score += 2  # concise = likely well-scoped

    # --- Error handling / robustness signals (0-5) ---
    robustness_signals = ["error", "fallback", "retry", "graceful", "timeout",
                          "resilient", "robust", "recovery", "health"]
    robust_hits = sum(1 for r in robustness_signals if r in combined)
    score += min(robust_hits * 2, 5)

    # --- Community trust proxy (0-7) ---
    # High stars = community vetted
    if stars >= 5000:
        score += 7
    elif stars >= 1000:
        score += 5
    elif stars >= 100:
        score += 3
    elif stars >= 10:
        score += 2
    elif stars > 0:
        score += 1

    # --- Known safe patterns (0-5) ---
    # Org-backed projects tend to have better security practices
    full_name = (tool.get("full_name") or "").lower()
    safe_orgs = ["anthropic", "modelcontextprotocol", "langchain", "openai",
                 "vercel", "supabase", "google", "microsoft"]
    if any(org in full_name for org in safe_orgs):
        score += 5
    elif any(org in name for org in safe_orgs):
        score += 4  # org name in skill name
    elif homepage and not homepage.endswith("#readme"):
        score += 2  # dedicated website = more established

    # --- Project maturity as safety proxy (0-5) ---
    # Well-maintained projects with rich metadata are more likely to be safe
    version = tool.get("version") or ""
    repo = tool.get("repository") or tool.get("url") or ""
    if isinstance(repo, dict):
        repo = repo.get("url", "")
    topic_count = len(topics)

    if version and topic_count >= 5:
        score += 3  # versioned + well-tagged = mature
    elif version or topic_count >= 3:
        score += 2
    if "github.com" in str(repo):
        score += 2  # public repo = auditable

    return min(score, 25)


def _score_integration(tool: dict[str, Any]) -> int:
    """Integration (0-25): platform compatibility, dependencies, setup ease."""
    score = 0
    desc = (tool.get("description") or "").lower()
    topics = tool.get("topics") or tool.get("keywords") or []
    topics_lower = " ".join(str(t).lower() for t in topics)
    combined = f"{desc} {topics_lower}"
    language = (tool.get("language") or "").lower()
    homepage = tool.get("homepage") or ""
    url = tool.get("url") or ""

    # --- Platform compatibility (0-10) ---
    platforms = {
        "claude": ["claude", "claude-code", "anthropic", "claude-skills"],
        "openai": ["openai", "gpt", "chatgpt"],
        "general": ["agent", "ai-agent", "llm", "multi-agent"],
        "cursor": ["cursor"],
        "copilot": ["copilot", "github-copilot"],
    }
    platform_count = 0
    for platform, keywords in platforms.items():
        if any(kw in combined for kw in keywords):
            platform_count += 1

    if platform_count >= 3:
        score += 10  # multi-platform = high integration value
    elif platform_count == 2:
        score += 7
    elif platform_count == 1:
        score += 4

    # --- Language/runtime (0-5) ---
    # TypeScript/Python = easiest to integrate with agent frameworks
    if language in ("typescript", "javascript"):
        score += 5
    elif language == "python":
        score += 5
    elif language in ("go", "rust"):
        score += 3
    elif language:
        score += 1

    # --- Dependency clarity (0-5) ---
    # Installable via standard methods
    if tool.get("install_command"):
        score += 3
    if tool.get("npm_url") or tool.get("pypi_url"):
        score += 2  # registry = clear dependency chain

    # --- SDK/framework integration (0-5) ---
    sdk_signals = ["sdk", "api", "framework", "library", "plugin", "extension",
                   "agents-sdk", "agent-sdk", "mcp", "tool-use"]
    sdk_hits = sum(1 for s in sdk_signals if s in combined)
    score += min(sdk_hits * 2, 5)

    return min(score, 25)


def _score_documentation(tool: dict[str, Any]) -> int:
    """Documentation (0-25): usage examples, behavior, limitations."""
    score = 0
    desc = tool.get("description") or ""
    homepage = tool.get("homepage") or ""
    url = tool.get("url") or ""
    repo = tool.get("repository") or tool.get("url") or ""
    if isinstance(repo, dict):
        repo = repo.get("url", "")
    topics = tool.get("topics") or tool.get("keywords") or []
    stars = tool.get("stars") or 0
    updated_at = tool.get("updated_at") or ""

    # --- Has distinct homepage (0-7) ---
    repo_str = str(repo) or str(url)
    if homepage and homepage != repo_str and not homepage.endswith("#readme"):
        score += 7  # dedicated docs site
    elif homepage and "#readme" in homepage:
        score += 4  # at least points to readme
    elif homepage:
        score += 3

    # --- Repository accessible (0-5) ---
    if "github.com" in repo_str:
        score += 5  # GitHub = README rendered, issues, wiki possible
    elif "gitlab.com" in repo_str:
        score += 4
    elif repo_str:
        score += 2

    # --- Description serves as docs (0-5) ---
    desc_len = len(desc)
    if desc_len > 150:
        score += 5
    elif desc_len > 80:
        score += 3
    elif desc_len > 30:
        score += 2
    elif desc_len > 0:
        score += 1

    # --- Topic richness (as doc proxy) (0-4) ---
    # Well-tagged = author cared about discoverability
    if len(topics) >= 8:
        score += 4
    elif len(topics) >= 5:
        score += 3
    elif len(topics) >= 3:
        score += 2
    elif len(topics) >= 1:
        score += 1

    # --- Maintained recently (0-4) ---
    if updated_at:
        try:
            updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - updated).days
            if days_ago <= 30:
                score += 4
            elif days_ago <= 90:
                score += 3
            elif days_ago <= 180:
                score += 2
            elif days_ago <= 365:
                score += 1
        except (ValueError, TypeError):
            pass

    return min(score, 25)
