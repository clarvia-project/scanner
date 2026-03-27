"""API Scorer — specialized 0-100 scoring for REST/GraphQL APIs.

Scores APIs from metadata only (no live calls). Four dimensions of 25 points each:
  - Spec Quality (0-25): OpenAPI spec, version, endpoint richness
  - Agent Friendliness (0-25): Auth clarity, rate limits, pagination, error format
  - Documentation & SDKs (0-25): Docs URL, SDKs, versioning, examples
  - Reliability & Trust (0-25): Provider reputation, HTTPS, maintenance signals
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


# --- Well-known provider tiers ---
# Tier 1: Major cloud/infra providers (highest trust)
_TIER1_PROVIDERS = frozenset([
    "amazonaws.com", "google", "googleapis", "microsoft", "azure",
    "github", "cloudflare", "stripe", "twilio", "sendgrid",
    "openai", "anthropic", "slack", "salesforce", "oracle",
    "ibm", "digitalocean", "heroku", "vercel", "netlify",
])

# Tier 2: Well-known SaaS/API companies
_TIER2_PROVIDERS = frozenset([
    "notion", "airtable", "hubspot", "mailchimp", "datadog",
    "sentry", "pagerduty", "okta", "auth0", "plaid",
    "square", "paypal", "shopify", "zendesk", "intercom",
    "segment", "mixpanel", "amplitude", "launchdarkly", "supabase",
    "firebase", "algolia", "elastic", "mongodb", "redis",
    "confluent", "snowflake", "databricks", "cohere", "stability",
    "replicate", "huggingface", "langchain", "pinecone", "weaviate",
    "qdrant", "discord", "telegram", "whatsapp", "jira",
    "asana", "linear", "figma", "canva", "spotify",
])

# Auth type ranking (higher = better for agents)
_AUTH_KEYWORDS_RANKED: list[tuple[str, int]] = [
    ("api_key", 10),
    ("apikey", 10),
    ("api key", 10),
    ("bearer", 9),
    ("token", 8),
    ("basic", 6),
    ("oauth2", 5),
    ("oauth", 5),
    ("jwt", 7),
    ("hmac", 6),
]


def score_api(tool: dict[str, Any]) -> dict[str, Any]:
    """Score an API tool (0-100) across four dimensions.

    Designed for apis_guru, n8n, composio, and similar API metadata.
    """
    name = (tool.get("name") or tool.get("title") or "").lower()
    title = (tool.get("title") or tool.get("name") or "")
    desc = (tool.get("description") or "").lower()
    desc_raw = tool.get("description") or ""
    version = tool.get("version") or ""
    url = tool.get("url") or ""
    homepage = tool.get("homepage") or ""
    openapi_url = tool.get("openapi_url") or ""
    source = tool.get("source") or ""
    category = tool.get("category") or ""
    tool_type = tool.get("type") or ""

    spec = _score_spec_quality(name, desc, version, openapi_url, url, source)
    agent = _score_agent_friendliness(name, desc, openapi_url, source, tool_type)
    docs = _score_documentation(name, desc_raw, version, homepage, url, openapi_url, source, title)
    trust = _score_reliability_trust(name, desc, version, homepage, url, openapi_url, source)

    total = spec["score"] + agent["score"] + docs["score"] + trust["score"]

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
            "spec_quality": {"score": spec["score"], "max": 25, "details": spec["details"]},
            "agent_friendliness": {"score": agent["score"], "max": 25, "details": agent["details"]},
            "documentation": {"score": docs["score"], "max": 25, "details": docs["details"]},
            "reliability_trust": {"score": trust["score"], "max": 25, "details": trust["details"]},
        },
    }


# ---------------------------------------------------------------------------
# Dimension 1: Spec Quality (0-25)
# ---------------------------------------------------------------------------

def _score_spec_quality(
    name: str, desc: str, version: str, openapi_url: str, url: str, source: str,
) -> dict[str, Any]:
    """OpenAPI/Swagger spec presence, version, endpoint signals."""
    score = 0
    details: dict[str, Any] = {}

    # 1a. OpenAPI/Swagger spec presence (0-8)
    if openapi_url:
        score += 6
        details["has_openapi_spec"] = True
        # Bonus for spec hosted on well-known registries
        if "apis.guru" in openapi_url or "swaggerhub" in openapi_url:
            score += 2
            details["spec_registry"] = True
        else:
            score += 1
    elif url and any(kw in url.lower() for kw in ["openapi", "swagger", ".json", ".yaml"]):
        score += 3
        details["has_openapi_spec"] = "inferred"
    else:
        details["has_openapi_spec"] = False

    # 1b. Spec version detection from URL (0-4)
    # OpenAPI 3.x > Swagger 2.x
    spec_version = _detect_spec_version(openapi_url or url)
    details["spec_version"] = spec_version
    if spec_version == "3.x":
        score += 4
    elif spec_version == "2.x":
        score += 2
    elif spec_version == "unknown" and openapi_url:
        score += 1  # Has spec but can't determine version

    # 1c. API version presence (0-4)
    if version:
        details["api_version"] = version
        score += 2
        # Semantic versioning bonus
        if re.match(r"\d+\.\d+\.\d+", version):
            score += 2
        elif re.match(r"\d+\.\d+", version):
            score += 1
        # Date-based versioning (e.g., "2020-09-10") is also valid
        elif re.match(r"\d{4}-\d{2}-\d{2}", version):
            score += 2
    else:
        details["api_version"] = None

    # 1d. Description richness as proxy for spec completeness (0-5)
    desc_len = len(desc)
    if desc_len > 300:
        score += 5
    elif desc_len > 150:
        score += 4
    elif desc_len > 80:
        score += 3
    elif desc_len > 30:
        score += 2
    elif desc_len > 10:
        score += 1
    details["description_length"] = desc_len

    # 1e. Source quality bonus (0-2)
    # Reduced from 0-4: trust dimension already rewards curated sources.
    if source in ("apis_guru", "composio"):
        score += 2
        details["curated_source"] = True
    elif source == "n8n":
        score += 1  # n8n entries are sparse but vetted
        details["curated_source"] = False

    score = min(score, 25)
    return {"score": score, "details": details}


def _detect_spec_version(url: str) -> str:
    """Infer OpenAPI spec version from URL patterns."""
    url_lower = url.lower()
    if "openapi" in url_lower and "3" in url_lower:
        return "3.x"
    if "/v3/" in url_lower or "openapi3" in url_lower:
        return "3.x"
    if "swagger" in url_lower:
        return "2.x"
    if "/v2/" in url_lower:
        return "2.x"
    return "unknown"


# ---------------------------------------------------------------------------
# Dimension 2: Agent Friendliness (0-25)
# ---------------------------------------------------------------------------

def _score_agent_friendliness(
    name: str, desc: str, openapi_url: str, source: str, tool_type: str,
) -> dict[str, Any]:
    """How easy is it for an AI agent to use this API?"""
    score = 0
    details: dict[str, Any] = {}

    # 2a. Auth type clarity (0-8)
    auth_score, auth_type = _detect_auth_type(name, desc)
    score += auth_score
    details["auth_type"] = auth_type

    # 2b. Rate limit documentation signals (0-4)
    rate_limit_kws = ["rate limit", "throttl", "quota", "requests per", "rpm", "rps"]
    has_rate_info = any(kw in desc for kw in rate_limit_kws)
    if has_rate_info:
        score += 4
        details["rate_limit_documented"] = True
    else:
        # Partial credit for well-known providers (they always have rate limits docs)
        provider_tier = _get_provider_tier(name)
        if provider_tier == 1:
            score += 2
            details["rate_limit_documented"] = "inferred"
        else:
            details["rate_limit_documented"] = False

    # 2c. Pagination support signals (0-3)
    pagination_kws = ["pagination", "paginate", "next_page", "cursor", "offset", "limit",
                      "page_token", "pagetoken"]
    has_pagination = any(kw in desc for kw in pagination_kws)
    if has_pagination:
        score += 3
        details["pagination_support"] = True
    else:
        details["pagination_support"] = False

    # 2d. Structured error format signals (0-3)
    error_kws = ["error response", "error code", "error format", "rfc 7807",
                 "problem detail", "error handling", "status code"]
    has_error_format = any(kw in desc for kw in error_kws)
    if has_error_format:
        score += 3
        details["error_format"] = True
    else:
        # Partial credit for OpenAPI spec (likely defines error schemas)
        if openapi_url:
            score += 1
            details["error_format"] = "inferred"
        else:
            details["error_format"] = False

    # 2e. REST/GraphQL type detection (0-3)
    is_rest = bool(openapi_url) or "rest" in desc or source == "apis_guru"
    is_graphql = "graphql" in name or "graphql" in desc
    if is_graphql:
        score += 3  # GraphQL = self-documenting, introspectable
        details["api_style"] = "graphql"
    elif is_rest and openapi_url:
        score += 3  # REST with spec = well-structured
        details["api_style"] = "rest+spec"
    elif is_rest:
        score += 1
        details["api_style"] = "rest"
    else:
        details["api_style"] = "unknown"

    # 2f. Connector/integration type bonus (0-4)
    if tool_type == "connector":
        score += 3  # Pre-built connector = agent-ready
        details["pre_built_connector"] = True
    elif source in ("composio",):
        score += 4  # Composio entries are purpose-built for agent use
        details["agent_native"] = True
    else:
        details["pre_built_connector"] = False

    score = min(score, 25)
    return {"score": score, "details": details}


def _detect_auth_type(name: str, desc: str) -> tuple[int, str]:
    """Detect auth type from metadata, return (score, type)."""
    combined = f"{name} {desc}"
    best_score = 0
    best_type = "unknown"

    for keyword, rank in _AUTH_KEYWORDS_RANKED:
        if keyword in combined:
            if rank > best_score:
                best_score = rank
                best_type = keyword

    # Scale rank (1-10) to score (0-8)
    if best_score >= 8:
        return 8, best_type  # API key / bearer / JWT — best for agents
    elif best_score >= 6:
        return 6, best_type  # Basic / HMAC — usable
    elif best_score >= 4:
        return 4, best_type  # OAuth — requires flow, harder for agents
    elif best_score > 0:
        return 2, best_type

    # Fallback: well-known providers likely have API key auth
    tier = _get_provider_tier(name)
    if tier == 1:
        return 5, "inferred_api_key"
    elif tier == 2:
        return 3, "inferred_standard"

    return 0, "unknown"


# ---------------------------------------------------------------------------
# Dimension 3: Documentation & SDKs (0-25)
# ---------------------------------------------------------------------------

def _score_documentation(
    name: str, desc_raw: str, version: str, homepage: str, url: str,
    openapi_url: str, source: str, title: str = "",
) -> dict[str, Any]:
    """Documentation quality, SDK availability, versioning."""
    score = 0
    details: dict[str, Any] = {}

    # 3a. Documentation URL exists (0-6)
    has_homepage = bool(homepage and homepage.strip())
    has_url = bool(url and url.strip())
    if has_homepage and has_url:
        score += 6
        details["docs_urls"] = 2
    elif has_homepage or has_url:
        score += 4
        details["docs_urls"] = 1
    else:
        details["docs_urls"] = 0

    # 3b. OpenAPI spec = machine-readable docs (0-5)
    if openapi_url:
        score += 5
        details["machine_readable_docs"] = True
    else:
        details["machine_readable_docs"] = False

    # 3c. SDK / client library indicators (0-4)
    desc_lower = desc_raw.lower()
    sdk_kws = ["sdk", "client library", "client libraries", "npm package",
               "pip install", "nuget", "maven", "gem install", "go get"]
    sdk_matches = sum(1 for kw in sdk_kws if kw in desc_lower)
    if sdk_matches >= 2:
        score += 4
        details["sdk_indicators"] = sdk_matches
    elif sdk_matches == 1:
        score += 2
        details["sdk_indicators"] = 1
    else:
        # Well-known providers always have SDKs
        tier = _get_provider_tier(name.lower())
        if tier == 1:
            score += 3
            details["sdk_indicators"] = "inferred"
        elif tier == 2:
            score += 1
            details["sdk_indicators"] = "inferred"
        else:
            details["sdk_indicators"] = 0

    # 3d. Versioning signals (0-4)
    if version:
        score += 2
        # Semantic versioning = mature API
        if re.match(r"\d+\.\d+\.\d+", version):
            score += 2
        elif re.match(r"\d{4}-\d{2}-\d{2}", version):
            score += 2  # Date versioning (AWS style)
        elif re.match(r"\d+\.\d+", version):
            score += 1
        details["versioning"] = version
    else:
        details["versioning"] = None

    # 3e. Description contains getting-started/example indicators (0-3)
    example_kws = ["example", "getting started", "quickstart", "tutorial",
                   "how to", "sample", "code snippet"]
    has_examples = any(kw in desc_lower for kw in example_kws)
    if has_examples:
        score += 3
        details["has_examples"] = True
    else:
        details["has_examples"] = False

    # 3f. Title quality — has human-readable title (0-3)
    display_title = title or name
    if display_title and not _is_slug_only(display_title):
        score += 2
        details["readable_title"] = True
    else:
        details["readable_title"] = False
    # Has separate human-readable display title
    raw_title = desc_raw[:80] if desc_raw else ""
    if raw_title and len(raw_title) > 10:
        score += 1

    score = min(score, 25)
    return {"score": score, "details": details}


def _is_slug_only(name: str) -> bool:
    """Check if name is just a slug (e.g. 'my-api') with no readable parts."""
    # If it's all lowercase with only hyphens/dots/underscores, it's slug-like
    return bool(re.match(r"^[a-z0-9._-]+$", name)) and "." not in name


# ---------------------------------------------------------------------------
# Dimension 4: Reliability & Trust (0-25)
# ---------------------------------------------------------------------------

def _score_reliability_trust(
    name: str, desc: str, version: str, homepage: str, url: str,
    openapi_url: str, source: str,
) -> dict[str, Any]:
    """Provider reputation, HTTPS, maintenance, license signals."""
    score = 0
    details: dict[str, Any] = {}

    # 4a. Provider reputation (0-6)
    # Reduced from 0-8: reputation alone shouldn't dominate trust dimension.
    tier = _get_provider_tier(name)
    if tier == 1:
        score += 6
        details["provider_tier"] = 1
    elif tier == 2:
        score += 4
        details["provider_tier"] = 2
    else:
        score += 1  # Unknown but listed = some baseline trust
        details["provider_tier"] = 3

    # 4b. HTTPS enforcement (0-4)
    urls_to_check = [homepage, url, openapi_url]
    https_count = sum(1 for u in urls_to_check if u and u.startswith("https://"))
    total_urls = sum(1 for u in urls_to_check if u)
    if total_urls > 0:
        https_ratio = https_count / total_urls
        if https_ratio == 1.0:
            score += 4
            details["https_enforced"] = True
        elif https_ratio >= 0.5:
            score += 2
            details["https_enforced"] = "partial"
        else:
            details["https_enforced"] = False
    else:
        details["https_enforced"] = "no_urls"

    # 4c. Source trust (0-4)
    # Being listed in a curated registry = vetted
    if source == "apis_guru":
        score += 4
        details["curated_registry"] = True
    elif source == "composio":
        score += 4
        details["curated_registry"] = True
    elif source == "n8n":
        score += 3  # n8n has community + official nodes
        details["curated_registry"] = True
    else:
        details["curated_registry"] = False

    # 4d. Update frequency / maintenance signals (0-4)
    if version:
        ver_parts = version.replace("-", ".").split(".")
        try:
            major = int(ver_parts[0])
        except (ValueError, IndexError):
            major = 0

        if major >= 3:
            score += 4  # Multiple major versions = long-lived
            details["maturity"] = "established"
        elif major >= 1:
            score += 3  # v1.x+ = production-ready
            details["maturity"] = "production"
        else:
            score += 1  # v0.x = pre-release
            details["maturity"] = "pre_release"

        # Date-based versions indicate active maintenance
        if re.match(r"\d{4}-\d{2}", version):
            score += 1
            details["date_versioned"] = True
    else:
        details["maturity"] = "unknown"

    # 4e. Domain/homepage signals (0-3)
    if homepage:
        parsed = urlparse(homepage)
        domain = parsed.netloc or ""
        # Custom domain (not generic hosting) = invested provider
        generic_hosts = ["github.io", "netlify.app", "vercel.app", "herokuapp.com"]
        if domain and not any(gh in domain for gh in generic_hosts):
            score += 3
            details["custom_domain"] = True
        else:
            score += 1
            details["custom_domain"] = False
    elif url:
        score += 1  # At least has a URL
        details["custom_domain"] = False
    else:
        details["custom_domain"] = False

    # 4f. Category signals (0-2)
    # Certain categories imply higher reliability standards
    high_trust_categories = ["financial", "payments", "security", "healthcare",
                             "cloud", "infrastructure"]
    if any(cat in (desc + " " + (homepage or "")) for cat in high_trust_categories):
        score += 2
        details["high_trust_category"] = True
    else:
        details["high_trust_category"] = False

    score = min(score, 25)
    return {"score": score, "details": details}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_provider_tier(name: str) -> int:
    """Return provider tier: 1 (major), 2 (well-known), 3 (other)."""
    name_lower = name.lower()
    # Check domain-style names (e.g., "amazonaws.com:s3")
    name_parts = re.split(r"[.:/_\-]", name_lower)

    for part in name_parts:
        if part in _TIER1_PROVIDERS:
            return 1
    for part in name_parts:
        if part in _TIER2_PROVIDERS:
            return 2

    # Also check substring for compound names
    for provider in _TIER1_PROVIDERS:
        if provider in name_lower:
            return 1
    for provider in _TIER2_PROVIDERS:
        if provider in name_lower:
            return 2

    return 3
