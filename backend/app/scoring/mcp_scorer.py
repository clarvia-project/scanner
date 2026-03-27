"""MCP Server Scorer — type-specific scoring for MCP servers (0-100 scale).

Scores MCP servers from metadata only (no web scraping) across 4 dimensions:
  - Tool Quality (0-25): tools count, description quality, parameter schemas
  - Integration Readiness (0-25): transport, remote hosting, packages, install ease
  - Documentation & Discovery (0-25): README signals, homepage, version, license, schema
  - Trust & Ecosystem (0-25): registry source, org backing, update recency, maturity

Data shape (from mcp-registry-all.json):
  {
    "server": {
      "name": str, "description": str, "title": str, "version": str,
      "websiteUrl": str, "repository": {"url": str, "source": str},
      "packages": [{"registryType": str, "identifier": str, "transport": {"type": str}, ...}],
      "remotes": [{"type": str, "url": str}],
      "tools": [...], "prompts": [...], "resources": [...], "icons": [...]
    },
    "_meta": {"io.modelcontextprotocol.registry/official": {
      "status": str, "publishedAt": str, "updatedAt": str, "isLatest": bool
    }}
  }

Registry stats (4224 servers):
  - packages: 69.4%  (npm 2077, pypi 775, oci 199, mcpb 226, nuget 25)
  - remotes: 31.9%   (streamable-http 1293, sse 252)
  - websiteUrl: 16.0%
  - repo w/url: 86.3%
  - title: 36.1%
  - tools: 0% (not populated in registry dump, but may exist in enriched data)
  - icons: 4.0%
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


# Well-known organizations that signal higher trust
WELL_KNOWN_ORGS = frozenset([
    "anthropic", "google", "microsoft", "aws", "amazon", "stripe", "github",
    "slack", "notion", "vercel", "supabase", "cloudflare", "docker",
    "postgres", "mongodb", "redis", "openai", "langchain", "firebase",
    "twilio", "sendgrid", "datadog", "sentry", "hashicorp", "elastic",
    "grafana", "linear", "figma", "shopify", "atlassian", "jetbrains",
    "gitlab", "bitbucket", "heroku", "netlify", "digitalocean",
])

# Package registry quality tiers
REGISTRY_TIERS = {
    "npm": 5,        # Most mature ecosystem
    "pypi": 5,       # Large ecosystem
    "nuget": 4,      # .NET ecosystem
    "oci": 3,        # Docker/OCI — less standardized for MCP
    "mcpb": 2,       # MCP-specific bundler, newer
}

# Transport protocol maturity
TRANSPORT_SCORES = {
    "streamable-http": 5,   # Latest spec, bidirectional
    "sse": 3,               # Older but functional
    "stdio": 4,             # Standard local transport
}


def score_mcp_server(entry: dict[str, Any]) -> dict[str, Any]:
    """Score an MCP server entry and return per-dimension scores.

    Args:
        entry: A dict from mcp-registry-all.json or enriched MCP server data.

    Returns:
        {
            "clarvia_score": int (0-100),
            "rating": str,
            "dimensions": {
                "tool_quality": {"score": int, "max": 25, "details": {...}},
                "integration_readiness": {"score": int, "max": 25, "details": {...}},
                "documentation_discovery": {"score": int, "max": 25, "details": {...}},
                "trust_ecosystem": {"score": int, "max": 25, "details": {...}},
            }
        }
    """
    server = entry.get("server", {})
    meta = entry.get("_meta", {})
    registry_meta = meta.get("io.modelcontextprotocol.registry/official", {})

    tq_score, tq_details = _score_tool_quality(server, entry)
    ir_score, ir_details = _score_integration_readiness(server)
    dd_score, dd_details = _score_documentation_discovery(server, entry)
    te_score, te_details = _score_trust_ecosystem(server, registry_meta, entry)

    total = tq_score + ir_score + dd_score + te_score

    # Completeness bonus: servers strong across multiple dimensions
    # deserve extra credit. This compensates for tool_quality being
    # structurally limited when registry data lacks tools metadata.
    dims = [tq_score, ir_score, dd_score, te_score]
    dims_above_18 = sum(1 for d in dims if d >= 18)
    dims_above_15 = sum(1 for d in dims if d >= 15)
    dims_above_12 = sum(1 for d in dims if d >= 12)
    dims_above_10 = sum(1 for d in dims if d >= 10)
    if dims_above_18 >= 3:
        total += 12  # Exceptional across 3+ dimensions
    elif dims_above_15 >= 3:
        total += 9   # Strong across 3+ dimensions
    elif dims_above_15 >= 2 and dims_above_12 >= 3:
        total += 8   # Strong in 2, solid in 3+
    elif dims_above_12 >= 3:
        total += 6   # Solid across 3+ dimensions
    elif dims_above_12 >= 2 and dims_above_10 >= 4:
        total += 4   # Decent across all 4

    total = min(total, 100)

    if total >= 80:
        rating = "Excellent"
    elif total >= 60:
        rating = "Strong"
    elif total >= 35:
        rating = "Moderate"
    elif total >= 20:
        rating = "Basic"
    else:
        rating = "Low"

    return {
        "clarvia_score": total,
        "rating": rating,
        "dimensions": {
            "tool_quality": {"score": tq_score, "max": 25, "details": tq_details},
            "integration_readiness": {"score": ir_score, "max": 25, "details": ir_details},
            "documentation_discovery": {"score": dd_score, "max": 25, "details": dd_details},
            "trust_ecosystem": {"score": te_score, "max": 25, "details": te_details},
        },
    }


# ---------------------------------------------------------------------------
# Dimension 1: Tool Quality (0-25)
# ---------------------------------------------------------------------------

def _score_tool_quality(server: dict, entry: dict) -> tuple[int, dict]:
    """How well does this server expose tools to agents?

    Sub-factors:
    - Tool count (0-8): more tools = more capable
    - Description quality (0-8): length, keywords, clarity
    - Per-tool schema quality (0-5): parameter schemas defined
    - Prompts & resources (0-4): additional MCP primitives
    """
    details: dict[str, Any] = {}
    score = 0

    # --- Tool count (0-8) ---
    # Note: 0% of registry entries currently have tools populated,
    # but enriched data from scanning may have them.
    tools = server.get("tools", [])
    tool_count = len(tools) if isinstance(tools, list) else 0
    details["tool_count"] = tool_count

    if tool_count == 0:
        # No tools in metadata — the registry dump never populates tools.
        # Award points based on server completeness as a proxy for tool quality.
        # The fact that a server is registered and has deployment infrastructure
        # is strong evidence it provides tools — that's the entire purpose of MCP.
        has_packages = bool(server.get("packages"))
        has_remotes = bool(server.get("remotes"))
        has_website = bool(server.get("websiteUrl"))
        has_title = bool(server.get("title"))
        desc = (server.get("description") or "").lower()

        # Base: 3 for being registered, up to 8 for completeness
        tc_score = 3  # Baseline — registered as MCP server
        if has_packages:
            tc_score += 2  # Installable
        if has_remotes:
            tc_score += 2  # Hosted/deployable
        if has_website:
            tc_score += 1  # Has documentation site
    elif tool_count == 1:
        tc_score = 3
    elif tool_count <= 3:
        tc_score = 4
    elif tool_count <= 5:
        tc_score = 5
    elif tool_count <= 10:
        tc_score = 6
    elif tool_count <= 20:
        tc_score = 7
    else:
        tc_score = 8
    details["tool_count_score"] = tc_score
    score += tc_score

    # --- Description quality (0-8) ---
    desc = server.get("description") or ""
    desc_len = len(desc)
    details["description_length"] = desc_len

    dq_score = 0
    # Length tiers
    if desc_len >= 10:
        dq_score += 1
    if desc_len >= 30:
        dq_score += 1
    if desc_len >= 60:
        dq_score += 1
    if desc_len >= 80:
        dq_score += 1  # Near the 100-char max seen in registry

    # Keyword richness — does the description tell agents what it does?
    action_words = ["manage", "query", "search", "create", "read", "write",
                    "analyze", "monitor", "deploy", "connect", "integrate",
                    "automate", "generate", "transform", "fetch", "send",
                    "access", "control", "track", "process", "build"]
    desc_lower = desc.lower()
    action_hits = sum(1 for w in action_words if w in desc_lower)
    dq_score += min(action_hits, 2)  # +0-2

    # Specificity — contains specific nouns (APIs, services, data types)
    specific_nouns = ["api", "database", "file", "email", "message", "code",
                      "image", "document", "payment", "workflow", "data",
                      "metrics", "campaign", "repository", "calendar"]
    noun_hits = sum(1 for w in specific_nouns if w in desc_lower)
    dq_score += min(noun_hits, 2)  # +0-2

    # When no tools metadata available, description is the primary quality signal
    dq_max = 10 if tool_count == 0 else 8
    dq_score = min(dq_score, dq_max)
    details["description_quality_score"] = dq_score
    score += dq_score

    # --- Per-tool schema quality (0-5) ---
    schema_score = 0
    if tools and isinstance(tools, list):
        tools_with_desc = sum(1 for t in tools if isinstance(t, dict) and t.get("description"))
        tools_with_schema = sum(
            1 for t in tools
            if isinstance(t, dict) and t.get("inputSchema", t.get("parameters"))
        )
        ratio_desc = tools_with_desc / tool_count if tool_count else 0
        ratio_schema = tools_with_schema / tool_count if tool_count else 0

        if ratio_desc >= 0.8:
            schema_score += 2
        elif ratio_desc >= 0.5:
            schema_score += 1

        if ratio_schema >= 0.8:
            schema_score += 3
        elif ratio_schema >= 0.5:
            schema_score += 2
        elif ratio_schema > 0:
            schema_score += 1

        details["tools_with_description"] = tools_with_desc
        details["tools_with_schema"] = tools_with_schema
    else:
        # No tools metadata — redistribute schema points based on server sophistication.
        # Servers with env vars, auth, multiple registries are likely to have
        # well-structured tools even though the registry dump doesn't include them.
        has_env = any(
            isinstance(pkg, dict) and pkg.get("environmentVariables")
            for pkg in server.get("packages", [])
        )
        has_auth = any(
            isinstance(r, dict) and r.get("headers")
            for r in server.get("remotes", [])
        )
        if has_env and has_auth:
            schema_score = 4  # Production-grade config = likely good schemas
        elif has_env or has_auth:
            schema_score = 2
    details["schema_quality_score"] = schema_score
    score += schema_score

    # --- Prompts & resources (0-4) ---
    pr_score = 0
    prompts = server.get("prompts", [])
    resources = server.get("resources", [])
    if prompts and isinstance(prompts, list) and len(prompts) > 0:
        pr_score += 2
        details["has_prompts"] = True
    else:
        details["has_prompts"] = False

    if resources and isinstance(resources, list) and len(resources) > 0:
        pr_score += 2
        details["has_resources"] = True
    else:
        details["has_resources"] = False

    # When no prompts/resources metadata, give partial credit for title + icons
    # (these signal a polished server that likely exposes good primitives)
    if pr_score == 0:
        if server.get("title") and server.get("icons"):
            pr_score = 2  # Polished branding = likely polished server
        elif server.get("title"):
            pr_score = 1

    details["prompts_resources_score"] = pr_score
    score += pr_score

    return min(score, 25), details


# ---------------------------------------------------------------------------
# Dimension 2: Integration Readiness (0-25)
# ---------------------------------------------------------------------------

def _score_integration_readiness(server: dict) -> tuple[int, dict]:
    """How easy is it for an agent to actually use this server?

    Sub-factors:
    - Transport support (0-7): stdio/SSE/streamable-http availability
    - Remote hosting (0-7): hosted endpoints available
    - Package manager presence (0-7): npm/pip/oci installability
    - Install simplicity (0-4): single-command install signals
    """
    details: dict[str, Any] = {}
    score = 0

    packages = server.get("packages", [])
    remotes = server.get("remotes", [])

    # --- Transport support (0-7) ---
    transport_score = 0
    seen_transports: set[str] = set()

    # Transports from packages
    for pkg in (packages if isinstance(packages, list) else []):
        t = pkg.get("transport", {})
        if isinstance(t, dict):
            seen_transports.add(t.get("type", ""))

    # Transports from remotes
    for r in (remotes if isinstance(remotes, list) else []):
        seen_transports.add(r.get("type", ""))

    seen_transports.discard("")
    details["transports"] = sorted(seen_transports)

    if not seen_transports:
        transport_score = 0
    else:
        # Best transport score
        best = max(TRANSPORT_SCORES.get(t, 1) for t in seen_transports)
        transport_score += best
        # Bonus for multiple transports (flexibility)
        if len(seen_transports) >= 2:
            transport_score += 2
    transport_score = min(transport_score, 7)
    details["transport_score"] = transport_score
    score += transport_score

    # --- Remote hosting (0-7) ---
    remote_score = 0
    remote_count = len(remotes) if isinstance(remotes, list) else 0
    details["remote_count"] = remote_count

    if remote_count > 0:
        remote_score += 4  # Has at least one hosted endpoint
        if remote_count > 1:
            remote_score += 2  # Multiple deployment options
        # Check if remote has auth (more production-ready)
        has_auth = any(
            r.get("headers") for r in remotes if isinstance(r, dict)
        )
        if has_auth:
            remote_score += 1
            details["remote_has_auth"] = True
    else:
        # No remote — but having repo means it CAN be self-hosted
        repo = server.get("repository", {})
        if isinstance(repo, dict) and repo.get("url"):
            remote_score += 2  # Self-hostable from source
    remote_score = min(remote_score, 7)
    details["remote_score"] = remote_score
    score += remote_score

    # --- Package manager presence (0-7) ---
    pkg_score = 0
    pkg_count = len(packages) if isinstance(packages, list) else 0
    details["package_count"] = pkg_count

    if pkg_count > 0:
        # Best registry tier
        best_registry = 0
        registry_types_seen: list[str] = []
        for pkg in packages:
            rt = pkg.get("registryType", "")
            registry_types_seen.append(rt)
            best_registry = max(best_registry, REGISTRY_TIERS.get(rt, 1))

        pkg_score += best_registry  # 2-5 from registry tier
        details["registry_types"] = registry_types_seen

        # Bonus for multiple registries (cross-platform)
        unique_registries = set(registry_types_seen)
        if len(unique_registries) >= 2:
            pkg_score += 2
    pkg_score = min(pkg_score, 7)
    details["package_score"] = pkg_score
    score += pkg_score

    # --- Install simplicity (0-6) ---
    install_score = 0

    # Has packages at all = installable
    if pkg_count > 0:
        install_score += 2

    # Has remotes = zero-install (just connect)
    if remote_count > 0:
        install_score += 2

    # Both = maximum accessibility (user can choose install or hosted)
    if pkg_count > 0 and remote_count > 0:
        install_score += 2  # Dual-mode is the gold standard

    # Edge case: neither packages nor remotes
    if pkg_count == 0 and remote_count == 0:
        # Check if repo exists (can still clone + build)
        repo = server.get("repository", {})
        if isinstance(repo, dict) and repo.get("url"):
            install_score += 1  # Can build from source

    install_score = min(install_score, 6)
    details["install_score"] = install_score
    score += install_score

    return min(score, 25), details


# ---------------------------------------------------------------------------
# Dimension 3: Documentation & Discovery (0-25)
# ---------------------------------------------------------------------------

def _score_documentation_discovery(server: dict, entry: dict) -> tuple[int, dict]:
    """How discoverable and well-documented is this server?

    Sub-factors:
    - Homepage/website (0-5): has a dedicated website
    - Version quality (0-5): semver, maturity
    - Repository signals (0-5): GitHub presence, README proxy
    - Naming & branding (0-5): title, icons, description completeness
    - Schema reference (0-5): $schema version, license
    """
    details: dict[str, Any] = {}
    score = 0

    # --- Homepage/website (0-5) ---
    website = server.get("websiteUrl", "")
    hp_score = 0
    if website:
        hp_score += 3
        # HTTPS bonus
        if website.startswith("https://"):
            hp_score += 1
        # Dedicated domain (not just a GitHub URL)
        if "github.com" not in website and "github.io" not in website:
            hp_score += 1
    details["has_website"] = bool(website)
    details["homepage_score"] = hp_score
    score += hp_score

    # --- Version quality (0-5) ---
    version = server.get("version", "")
    details["version"] = version
    ver_score = 0

    if version:
        ver_score += 1  # Has any version
        # Valid semver-like
        if re.match(r"^\d+\.\d+", version):
            ver_score += 1
            parts = version.split(".")
            if len(parts) >= 3:
                ver_score += 1  # Full semver (x.y.z)
            major = int(parts[0]) if parts[0].isdigit() else 0
            if major >= 1:
                ver_score += 1  # Production version (1.0+)
            if major >= 2:
                ver_score += 1  # Mature (2.0+, multiple iterations)
    details["version_score"] = ver_score
    score += ver_score

    # --- Repository signals (0-5) ---
    repo = server.get("repository", {})
    repo_url = ""
    if isinstance(repo, dict):
        repo_url = repo.get("url", "")
    repo_score = 0

    if repo_url:
        repo_score += 2
        if "github.com" in repo_url:
            repo_score += 2  # GitHub = most discoverable
        elif "gitlab.com" in repo_url:
            repo_score += 1
        # Has specific subfolder = monorepo awareness
        if isinstance(repo, dict) and repo.get("subfolder"):
            repo_score += 1
    details["has_repo"] = bool(repo_url)
    details["repo_score"] = repo_score
    score += repo_score

    # --- Naming & branding (0-5) ---
    brand_score = 0
    has_title = bool(server.get("title"))
    has_icons = bool(server.get("icons"))
    has_desc = bool(server.get("description"))
    name = server.get("name", "")

    if has_desc:
        brand_score += 1
    if has_title:
        brand_score += 2  # Extra effort to provide human-readable title
    if has_icons:
        brand_score += 1  # Visual branding
    # Name follows convention (org/name format)
    if "/" in name and len(name.split("/")) == 2:
        brand_score += 1
    brand_score = min(brand_score, 5)
    details["branding_score"] = brand_score
    details["has_title"] = has_title
    details["has_icons"] = has_icons
    score += brand_score

    # --- Schema reference (0-5) ---
    schema_score = 0
    schema_url = server.get("$schema", "")
    if schema_url:
        schema_score += 2
        # Newer schema versions signal maintenance
        if "2025-12-11" in schema_url:
            schema_score += 2  # Latest schema
        elif "2025-09-29" in schema_url:
            schema_score += 1  # Previous schema
        elif "2025-07-09" in schema_url:
            schema_score += 0  # Older schema

    # License from entry-level data
    license_val = entry.get("license", "")
    if license_val:
        schema_score += 1

    schema_score = min(schema_score, 5)
    details["schema_score"] = schema_score
    details["schema_version"] = schema_url
    score += schema_score

    return min(score, 25), details


# ---------------------------------------------------------------------------
# Dimension 4: Trust & Ecosystem (0-25)
# ---------------------------------------------------------------------------

def _score_trust_ecosystem(
    server: dict, registry_meta: dict, entry: dict
) -> tuple[int, dict]:
    """How trustworthy and ecosystem-embedded is this server?

    Sub-factors:
    - Registry presence (0-5): official registry listing, status
    - Organization backing (0-6): well-known org, GitHub org pattern
    - Update recency (0-6): how recently updated/published
    - Maturity signals (0-4): version stability, env vars, auth
    - Cross-platform presence (0-4): multiple registries, sources
    """
    details: dict[str, Any] = {}
    score = 0

    # --- Registry presence (0-5) ---
    reg_score = 0
    status = registry_meta.get("status", "")
    is_latest = registry_meta.get("isLatest", False)

    if registry_meta:
        reg_score += 3  # In official MCP registry
    if status == "active":
        reg_score += 1
    elif status in ("inactive", "deprecated"):
        reg_score -= 2  # Penalize non-active entries
    if is_latest:
        reg_score += 1
    reg_score = max(reg_score, 0)
    details["registry_status"] = status
    details["is_latest"] = is_latest
    details["registry_score"] = reg_score
    score += reg_score

    # --- Organization backing (0-6) ---
    org_score = 0
    name = server.get("name", "").lower()

    # Check against well-known orgs
    # Exclude "github" from name matching — "io.github.user/name" doesn't
    # mean it's backed by GitHub, it's just hosted there.
    matched_org = None
    name_match_orgs = WELL_KNOWN_ORGS - {"github"}
    for org in name_match_orgs:
        if org in name:
            matched_org = org
            org_score += 6
            break

    # GitHub org pattern (com.github.org/name or org.domain/name)
    if not matched_org:
        repo = server.get("repository", {})
        repo_url = repo.get("url", "") if isinstance(repo, dict) else ""
        if repo_url and "github.com" in repo_url:
            # Extract org from github URL
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 4:
                gh_org = parts[3].lower()
                if gh_org in WELL_KNOWN_ORGS:
                    org_score += 6
                    matched_org = gh_org

    # Name follows reverse-domain convention = more professional
    name_parts = name.split("/")
    if len(name_parts) >= 2 and "." in name_parts[0]:
        org_score += 2  # e.g., "ai.company/server-name"

    org_score = min(org_score, 8)
    details["org_score"] = org_score
    details["matched_org"] = matched_org
    score += org_score

    # --- Update recency (0-6) ---
    recency_score = 0
    updated_at = registry_meta.get("updatedAt", "")
    published_at = registry_meta.get("publishedAt", "")

    if updated_at:
        try:
            updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_since = (now - updated_dt).days

            if days_since <= 7:
                recency_score = 6    # Updated this week
            elif days_since <= 30:
                recency_score = 5    # Updated this month
            elif days_since <= 90:
                recency_score = 4    # Updated this quarter
            elif days_since <= 180:
                recency_score = 3    # Updated in 6 months
            elif days_since <= 365:
                recency_score = 2    # Updated this year
            else:
                recency_score = 1    # Stale but exists

            details["days_since_update"] = days_since
        except (ValueError, TypeError):
            recency_score = 0
            details["days_since_update"] = None
    details["recency_score"] = recency_score
    score += recency_score

    # --- Maturity signals (0-4) ---
    mat_score = 0

    # Version maturity
    version = server.get("version", "")
    if version:
        parts = version.split(".")
        if parts[0].isdigit():
            major = int(parts[0])
            if major >= 1:
                mat_score += 1  # Stable release
            if major >= 2:
                mat_score += 1  # Multiple major iterations

    # Has environment variables defined = production-aware
    for pkg in server.get("packages", []):
        if isinstance(pkg, dict) and pkg.get("environmentVariables"):
            mat_score += 1
            details["has_env_vars"] = True
            break

    # Remote auth headers = production-grade security
    for remote in server.get("remotes", []):
        if isinstance(remote, dict) and remote.get("headers"):
            mat_score += 1
            details["has_remote_auth"] = True
            break

    mat_score = min(mat_score, 4)
    details["maturity_score"] = mat_score
    score += mat_score

    # --- Cross-platform presence (0-4) ---
    cross_score = 0

    # Multiple package registries
    pkg_registries = set()
    for pkg in server.get("packages", []):
        if isinstance(pkg, dict):
            pkg_registries.add(pkg.get("registryType", ""))
    pkg_registries.discard("")

    if len(pkg_registries) >= 2:
        cross_score += 2  # Available on multiple registries
    elif len(pkg_registries) == 1:
        cross_score += 1

    # Both packages AND remotes = maximum accessibility
    has_packages = bool(server.get("packages"))
    has_remotes = bool(server.get("remotes"))
    if has_packages and has_remotes:
        cross_score += 2  # Only 3.6% have both

    cross_score = min(cross_score, 4)
    details["cross_platform_score"] = cross_score
    details["package_registries"] = sorted(pkg_registries)
    score += cross_score

    return min(score, 25), details


# ---------------------------------------------------------------------------
# Convenience: batch scoring
# ---------------------------------------------------------------------------

def score_mcp_servers(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score a list of MCP server entries. Returns list of score dicts."""
    return [score_mcp_server(e) for e in entries]
