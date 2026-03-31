"""Tier-based feature gating for Clarvia.

Defines the free/paid boundary and provides a single function to check
whether a user's plan allows access to a given feature.

Free tier:
- Basic AEO scan (public endpoints only)
- Leaderboard, search, MCP tools
- Top 3 recommendations (blurred sub-factor evidence)
- 10 scans/day (tracked per IP or API key)

Paid tiers (starter+):
- Detailed report with full sub-factor evidence
- Scan history & before/after comparison
- Authenticated scan (user provides target API key)
- Batch scan (10+ URLs)
- PDF export
- Competitive benchmark data
- Unlimited scans (per plan limits)
"""

import logging
import time
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class Feature(str, Enum):
    """Gated features. Each maps to a plan requirement."""
    BASIC_SCAN = "basic_scan"
    DETAILED_REPORT = "detailed_report"
    SCAN_HISTORY = "scan_history"
    AUTHENTICATED_SCAN = "authenticated_scan"
    BATCH_SCAN = "batch_scan"
    PDF_EXPORT = "pdf_export"
    COMPETITIVE_BENCHMARK = "competitive_benchmark"
    CI_CD_CHECK = "ci_cd_check"
    PLAYBOOK = "playbook"
    CODE_FIX = "code_fix"


# Plan -> set of allowed features
_PLAN_FEATURES: dict[str, set[Feature]] = {
    "free": {
        Feature.BASIC_SCAN,
    },
    "starter": {
        Feature.BASIC_SCAN,
        Feature.DETAILED_REPORT,
        Feature.SCAN_HISTORY,
        Feature.AUTHENTICATED_SCAN,
        Feature.PDF_EXPORT,
        Feature.PLAYBOOK,
    },
    "pro": {
        Feature.BASIC_SCAN,
        Feature.DETAILED_REPORT,
        Feature.SCAN_HISTORY,
        Feature.AUTHENTICATED_SCAN,
        Feature.BATCH_SCAN,
        Feature.PDF_EXPORT,
        Feature.COMPETITIVE_BENCHMARK,
        Feature.CI_CD_CHECK,
        Feature.PLAYBOOK,
        Feature.CODE_FIX,
    },
    "enterprise": {
        f for f in Feature  # all features
    },
    "team": {
        f for f in Feature  # all features
    },
}

# Daily scan limits per plan (resets at midnight UTC)
DAILY_SCAN_LIMITS: dict[str, int] = {
    "free": 10,
    "starter": 50,
    "pro": -1,       # unlimited
    "enterprise": -1,  # unlimited
    "team": -1,       # unlimited
}

# Batch scan limits (max URLs per request)
BATCH_LIMITS: dict[str, int] = {
    "free": 0,        # no batch for free
    "starter": 5,
    "pro": 20,
    "enterprise": 50,
    "team": 50,
}

# How many recommendations to show per plan
RECOMMENDATION_LIMITS: dict[str, int] = {
    "free": 3,
    "starter": 5,
    "pro": 10,
    "enterprise": 10,
    "team": 10,
}

# Whether to show sub-factor evidence details
SHOW_EVIDENCE: dict[str, bool] = {
    "free": False,
    "starter": True,
    "pro": True,
    "enterprise": True,
    "team": True,
}


# Simple in-memory daily scan counter: key -> (count, date_str)
_daily_scans: dict[str, tuple[int, str]] = {}


def _today_str() -> str:
    """UTC date string for daily counter reset."""
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def check_daily_scan_limit(key: str, plan: str = "free") -> tuple[bool, int, int]:
    """Check if key (IP or API key) is within daily scan limit.

    Returns (allowed, current_count, limit).
    Limit of -1 means unlimited.
    """
    limit = DAILY_SCAN_LIMITS.get(plan, 10)
    if limit == -1:
        return True, 0, -1

    today = _today_str()
    entry = _daily_scans.get(key)
    if entry is None or entry[1] != today:
        _daily_scans[key] = (0, today)
        return True, 0, limit

    current = entry[0]
    return current < limit, current, limit


def increment_daily_scan(key: str) -> None:
    """Increment the daily scan counter for a key."""
    today = _today_str()
    entry = _daily_scans.get(key)
    if entry is None or entry[1] != today:
        _daily_scans[key] = (1, today)
    else:
        _daily_scans[key] = (entry[0] + 1, today)


def has_feature(plan: str, feature: Feature) -> bool:
    """Check if a plan has access to a feature."""
    features = _PLAN_FEATURES.get(plan, _PLAN_FEATURES["free"])
    return feature in features


def get_plan_info(plan: str) -> dict:
    """Get full plan capabilities for display/API response."""
    features = _PLAN_FEATURES.get(plan, _PLAN_FEATURES["free"])
    return {
        "plan": plan,
        "features": sorted(f.value for f in features),
        "daily_scan_limit": DAILY_SCAN_LIMITS.get(plan, 10),
        "batch_limit": BATCH_LIMITS.get(plan, 0),
        "recommendation_limit": RECOMMENDATION_LIMITS.get(plan, 3),
        "show_evidence": SHOW_EVIDENCE.get(plan, False),
    }


def gate_response(scan_result: dict, plan: str) -> dict:
    """Apply tier gating to a scan response dict.

    Free tier: blur evidence, cap recommendations.
    Paid tier: full details.
    """
    if plan != "free":
        return scan_result

    # Cap recommendations
    rec_limit = RECOMMENDATION_LIMITS.get(plan, 3)
    if "top_recommendations" in scan_result:
        scan_result["top_recommendations"] = scan_result["top_recommendations"][:rec_limit]
        if len(scan_result.get("top_recommendations", [])) < rec_limit:
            pass
        scan_result["recommendations_truncated"] = True
        scan_result["upgrade_hint"] = "Upgrade to see all recommendations and detailed evidence."

    # Blur evidence in sub-factors for free tier
    if not SHOW_EVIDENCE.get(plan, False) and "dimensions" in scan_result:
        dims = scan_result["dimensions"]
        if isinstance(dims, dict):
            for dim_key, dim_val in dims.items():
                sub_factors = None
                if isinstance(dim_val, dict):
                    sub_factors = dim_val.get("sub_factors", {})
                elif hasattr(dim_val, "sub_factors"):
                    sub_factors = dim_val.sub_factors
                if sub_factors and isinstance(sub_factors, dict):
                    for sf_key, sf_val in sub_factors.items():
                        if isinstance(sf_val, dict) and "evidence" in sf_val:
                            sf_val["evidence"] = {"locked": True, "upgrade_to": "starter"}
                        elif hasattr(sf_val, "evidence"):
                            # Pydantic model — we can't easily mutate, skip
                            pass

    return scan_result


def cleanup_daily_counters() -> int:
    """Remove stale daily counters (not today). Returns count removed."""
    today = _today_str()
    stale = [k for k, (_, d) in _daily_scans.items() if d != today]
    for k in stale:
        del _daily_scans[k]
    return len(stale)
