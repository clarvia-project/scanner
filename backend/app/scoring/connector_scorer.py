"""Connector Scorer — 0-100 scoring for integration connectors (n8n, Zapier, etc.).

Connectors are pre-built integrations that bridge services. They typically have
minimal metadata (name, URL, source) but represent real, working integrations.

Four dimensions, 25 points each:
  - Integration Value (0-25): what service does it connect to, how well-known
  - Agent Readiness (0-25): how useful is this for an AI agent
  - Documentation (0-25): docs URL, description quality, discoverability
  - Ecosystem Trust (0-25): platform maturity, service reliability
"""

from __future__ import annotations

import re
from typing import Any


# Well-known services that connectors integrate with
_TIER1_SERVICES = frozenset([
    "google", "gmail", "sheets", "drive", "calendar",
    "slack", "notion", "github", "gitlab",
    "aws", "azure", "gcp",
    "stripe", "paypal", "shopify",
    "salesforce", "hubspot", "zendesk",
    "postgres", "mysql", "mongodb", "redis",
    "twilio", "sendgrid", "mailchimp",
    "jira", "asana", "linear", "trello",
    "openai", "anthropic",
    "docker", "kubernetes",
    "airtable", "supabase", "firebase",
    "discord", "telegram", "whatsapp",
    "dropbox", "onedrive", "box",
])

_TIER2_SERVICES = frozenset([
    "zoom", "teams", "webex",
    "figma", "canva", "miro",
    "datadog", "sentry", "pagerduty", "grafana",
    "cloudflare", "vercel", "netlify", "heroku",
    "segment", "mixpanel", "amplitude",
    "intercom", "freshdesk", "drift",
    "bamboohr", "workday", "gusto",
    "quickbooks", "xero", "wave",
    "contentful", "sanity", "strapi",
    "elasticsearch", "algolia", "typesense",
    "rabbitmq", "kafka", "sqs",
    "s3", "gcs", "blob",
    "jenkins", "circleci", "travis",
    "bitbucket", "codecommit",
    "okta", "auth0",
    "twitch", "youtube", "spotify",
    "twitter", "linkedin", "facebook", "instagram",
    "medium", "ghost", "wordpress",
])


def score_connector(tool: dict[str, Any]) -> dict[str, Any]:
    """Score a connector tool (0-100) across four dimensions."""
    name = (tool.get("name") or "").lower()
    desc = (tool.get("description") or "").lower()
    url = tool.get("url") or ""
    source = tool.get("source") or ""

    iv = _score_integration_value(name, desc)
    ar = _score_agent_readiness(name, desc, source)
    doc = _score_documentation(name, desc, url, source)
    trust = _score_ecosystem_trust(name, desc, url, source)

    total = iv + ar + doc + trust

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
            "integration_value": {"score": iv, "max": 25},
            "agent_readiness": {"score": ar, "max": 25},
            "documentation": {"score": doc, "max": 25},
            "ecosystem_trust": {"score": trust, "max": 25},
        },
    }


def _get_service_tier(name: str) -> int:
    """Determine the tier of the service this connector integrates with."""
    # Split name into parts for matching
    parts = set(re.split(r"[-_\s/.]", name))

    for part in parts:
        if part in _TIER1_SERVICES:
            return 1
    for part in parts:
        if part in _TIER2_SERVICES:
            return 2

    # Substring check for compound names
    for svc in _TIER1_SERVICES:
        if svc in name:
            return 1
    for svc in _TIER2_SERVICES:
        if svc in name:
            return 2

    return 3


def _score_integration_value(name: str, desc: str) -> int:
    """Integration Value (0-25): how valuable is the service being connected?"""
    score = 0

    # Service tier (0-8)
    tier = _get_service_tier(name)
    if tier == 1:
        score += 8
    elif tier == 2:
        score += 5
    else:
        score += 2  # Unknown but it's still a connector

    # Multi-service connector (0-5) — name suggests multiple services
    multi_signals = ["+", "and", "multi", "universal", "all-in-one", "hub"]
    if any(sig in name for sig in multi_signals):
        score += 5

    # Category value — some categories are more valuable for agents (0-5)
    high_value_categories = ["crm", "database", "email", "messaging", "payment",
                             "analytics", "project", "storage", "code", "deploy"]
    combined = f"{name} {desc}"
    cat_hits = sum(1 for cat in high_value_categories if cat in combined)
    score += min(cat_hits * 2, 5)

    # Description richness (0-3)
    if len(desc) > 50:
        score += 3
    elif len(desc) > 20:
        score += 2
    elif len(desc) > 0:
        score += 1

    return min(score, 25)


def _score_agent_readiness(name: str, desc: str, source: str) -> int:
    """Agent Readiness (0-25): how useful is this for an AI agent?"""
    score = 0

    # Pre-built connector = inherently agent-useful (0-8)
    # Connectors abstract away auth, pagination, error handling
    score += 8  # baseline: all connectors are pre-built

    # Platform with agent support (0-6)
    if source == "n8n":
        score += 5  # n8n has AI agent nodes
    elif source == "composio":
        score += 6  # composio is agent-first
    elif source == "zapier":
        score += 4
    else:
        score += 2

    # CRUD/action signals in name (0-5)
    action_signals = ["read", "write", "create", "update", "delete", "send",
                      "fetch", "search", "list", "sync", "import", "export",
                      "trigger", "webhook"]
    combined = f"{name} {desc}"
    action_hits = sum(1 for a in action_signals if a in combined)
    score += min(action_hits * 2, 5)

    # Well-known service = likely well-structured connector (0-4)
    tier = _get_service_tier(name)
    if tier == 1:
        score += 4
    elif tier == 2:
        score += 2

    return min(score, 25)


def _score_documentation(name: str, desc: str, url: str, source: str) -> int:
    """Documentation (0-25): how discoverable and documented is this?"""
    score = 0

    # Has URL to docs (0-7)
    if url:
        score += 5
        if "docs" in url or "integrations" in url:
            score += 2
    elif source in ("n8n", "composio", "zapier"):
        score += 3  # platform provides standard docs pages

    # Name is descriptive (0-5)
    name_parts = re.split(r"[-_\s]", name)
    if len(name_parts) >= 1 and any(len(p) > 2 for p in name_parts):
        score += 3
    if len(name_parts) >= 2:
        score += 2  # multi-word = more descriptive

    # Description quality (0-5)
    desc_len = len(desc)
    if desc_len > 80:
        score += 5
    elif desc_len > 40:
        score += 3
    elif desc_len > 10:
        score += 2
    elif desc_len > 0:
        score += 1

    # Platform documentation (0-5)
    # n8n/composio/zapier provide standardized documentation for all connectors
    if source == "n8n":
        score += 4  # n8n has good docs for each node
    elif source == "composio":
        score += 5
    elif source == "zapier":
        score += 4
    else:
        score += 1

    # Service recognition = lots of external docs (0-3)
    tier = _get_service_tier(name)
    if tier == 1:
        score += 3
    elif tier == 2:
        score += 1

    return min(score, 25)


def _score_ecosystem_trust(name: str, desc: str, url: str, source: str) -> int:
    """Ecosystem Trust (0-25): how reliable is this connector?"""
    score = 0

    # Platform trust (0-8)
    if source in ("n8n", "composio", "zapier"):
        score += 8  # established platforms with QA
    else:
        score += 2

    # Service reliability (0-6)
    tier = _get_service_tier(name)
    if tier == 1:
        score += 6  # tier-1 services are reliable
    elif tier == 2:
        score += 4
    else:
        score += 2

    # URL is HTTPS (0-3)
    if url and url.startswith("https://"):
        score += 3
    elif url:
        score += 1

    # Platform has active community (0-3)
    if source == "n8n":
        score += 3  # large open-source community
    elif source == "composio":
        score += 3
    elif source == "zapier":
        score += 3
    else:
        score += 1

    # Well-known = battle-tested integration (0-3)
    if tier == 1:
        score += 3
    elif tier == 2:
        score += 1

    return min(score, 25)
