"""Index API — Agent-facing service discovery endpoints."""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["index"])

# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------
_CATEGORY_MAP: dict[str, list[str]] = {
    "ai": [
        "openai", "anthropic", "google ai", "mistral", "cohere",
        "replicate", "hugging face", "together", "groq", "perplexity",
    ],
    "developer_tools": [
        "github", "gitlab", "vercel", "netlify", "supabase",
        "firebase", "aws", "cloudflare", "railway", "render",
    ],
    "payments": [
        "stripe", "paypal", "squareup", "plaid", "coinbase", "circle",
    ],
    "communication": [
        "slack", "discord", "twilio", "sendgrid", "resend",
    ],
    "data": [
        "snowflake", "databricks", "mixpanel", "amplitude", "segment",
    ],
    "productivity": [
        "notion", "linear", "atlassian", "asana", "figma", "canva",
    ],
    "blockchain": [
        "solana", "ethereum", "helius", "alchemy", "moralis", "dune",
    ],
    "mcp": [
        "mcp", "smithery", "glama",
    ],
}

# Reverse lookup: lowercase service name -> category
_SERVICE_CATEGORY: dict[str, str] = {}
for cat, names in _CATEGORY_MAP.items():
    for name in names:
        _SERVICE_CATEGORY[name.lower()] = cat


def _classify(service_name: str) -> str:
    key = service_name.lower()
    if key in _SERVICE_CATEGORY:
        return _SERVICE_CATEGORY[key]
    # Partial match fallback
    for name, cat in _SERVICE_CATEGORY.items():
        if name in key or key in name:
            return cat
    return "other"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
_services: list[dict[str, Any]] = []
_by_scan_id: dict[str, dict[str, Any]] = {}


class SortOrder(str, Enum):
    score_desc = "score_desc"
    score_asc = "score_asc"
    name_asc = "name_asc"


def _load_data() -> None:
    global _services, _by_scan_id
    # Try multiple paths: Docker (/app/data/), local dev
    candidates = [Path("/app/data/prebuilt-scans.json")]
    base = Path(__file__).resolve()
    for i in range(2, 6):
        try:
            candidates.append(base.parents[i] / "data" / "prebuilt-scans.json")
        except IndexError:
            break
    data_path = None
    for p in candidates:
        if p.exists():
            data_path = p
            break
    if data_path is None:
        logger.error("prebuilt-scans.json not found in any candidate path")
        return
    with open(data_path, "r") as f:
        raw = json.load(f)

    for entry in raw:
        entry["category"] = _classify(entry.get("service_name", ""))
    _services = raw
    _by_scan_id = {s["scan_id"]: s for s in _services}
    logger.info("Loaded %d services for Index API", len(_services))

    # Merge scanned profiles into the services index
    _merge_profiles()


def _merge_profiles() -> None:
    """Load scanned profiles and add them to the services index."""
    global _services, _by_scan_id
    try:
        from .profile_routes import get_all_profiles

        for profile in get_all_profiles():
            if profile.get("status") != "scanned" or profile.get("scan_result") is None:
                continue

            scan_result = profile["scan_result"]
            scan_id = scan_result.get("scan_id")
            if not scan_id or scan_id in _by_scan_id:
                continue  # already present or no scan_id

            entry = {
                "scan_id": scan_id,
                "url": profile["url"],
                "service_name": profile["name"],
                "clarvia_score": profile.get("clarvia_score", 0),
                "rating": scan_result.get("rating", "unknown"),
                "dimensions": scan_result.get("dimensions", {}),
                "category": profile.get("category", "other"),
                "scanned_at": scan_result.get("scanned_at"),
                "source": "profile",
                "profile_id": profile["profile_id"],
                "tags": profile.get("tags", []),
            }
            _services.append(entry)
            _by_scan_id[scan_id] = entry

        logger.info("Merged profiles, total services: %d", len(_services))
    except Exception as e:
        logger.warning("Failed to merge profiles: %s", e)


def _ensure_loaded() -> None:
    if not _services:
        _load_data()


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _compact_service(s: dict[str, Any]) -> dict[str, Any]:
    """Return a compact representation (no sub_factors)."""
    dims = s.get("dimensions", {})
    return {
        "name": s["service_name"],
        "url": s["url"],
        "category": s.get("category", "other"),
        "clarvia_score": s["clarvia_score"],
        "rating": s["rating"],
        "dimensions": {k: v["score"] for k, v in dims.items()},
        "scan_id": s["scan_id"],
        "last_scanned": s.get("scanned_at"),
    }


def _full_service(s: dict[str, Any]) -> dict[str, Any]:
    """Return a full representation with sub_factors."""
    return {
        "name": s["service_name"],
        "url": s["url"],
        "category": s.get("category", "other"),
        "clarvia_score": s["clarvia_score"],
        "rating": s["rating"],
        "dimensions": s.get("dimensions", {}),
        "scan_id": s["scan_id"],
        "last_scanned": s.get("scanned_at"),
    }


def _add_headers(response: Response) -> None:
    _ensure_loaded()
    response.headers["X-Clarvia-Version"] = "1.0"
    response.headers["X-Clarvia-Total-Services"] = str(len(_services))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/services")
async def list_services(
    response: Response,
    category: str | None = Query(None, description="Filter by category"),
    min_score: int = Query(0, ge=0, le=100, description="Minimum Clarvia Score"),
    max_score: int | None = Query(None, ge=0, le=100, description="Maximum Clarvia Score"),
    sort: SortOrder = Query(SortOrder.score_desc, description="Sort order"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Search and filter services for agent consumption."""
    _ensure_loaded()
    _add_headers(response)

    filtered = _services

    if category:
        filtered = [s for s in filtered if s.get("category") == category]

    filtered = [s for s in filtered if s["clarvia_score"] >= min_score]

    if max_score is not None:
        filtered = [s for s in filtered if s["clarvia_score"] <= max_score]

    if sort == SortOrder.score_desc:
        filtered.sort(key=lambda s: s["clarvia_score"], reverse=True)
    elif sort == SortOrder.score_asc:
        filtered.sort(key=lambda s: s["clarvia_score"])
    elif sort == SortOrder.name_asc:
        filtered.sort(key=lambda s: s["service_name"].lower())

    total = len(filtered)
    page = filtered[offset : offset + limit]

    return {
        "total": total,
        "services": [_compact_service(s) for s in page],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        },
    }


@router.get("/services/{scan_id}")
async def get_service(scan_id: str, response: Response):
    """Get full details for a specific service by scan_id."""
    _ensure_loaded()
    _add_headers(response)

    service = _by_scan_id.get(scan_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return _full_service(service)


@router.get("/categories")
async def list_categories(response: Response):
    """List available categories with service counts."""
    _ensure_loaded()
    _add_headers(response)

    counts: dict[str, int] = {}
    for s in _services:
        cat = s.get("category", "other")
        counts[cat] = counts.get(cat, 0) + 1

    return {
        "categories": [
            {"name": cat, "count": counts.get(cat, 0)}
            for cat in sorted(_CATEGORY_MAP.keys())
        ],
    }


@router.get("/stats")
async def get_stats(response: Response):
    """Overall statistics across all indexed services."""
    _ensure_loaded()
    _add_headers(response)

    total = len(_services)
    if total == 0:
        return {"total_services": 0, "avg_score": 0, "by_category": {}}

    avg = sum(s["clarvia_score"] for s in _services) / total

    by_cat: dict[str, list[int]] = {}
    for s in _services:
        cat = s.get("category", "other")
        by_cat.setdefault(cat, []).append(s["clarvia_score"])

    return {
        "total_services": total,
        "avg_score": round(avg, 1),
        "score_distribution": {
            "excellent": len([s for s in _services if s["clarvia_score"] >= 90]),
            "strong": len([s for s in _services if 75 <= s["clarvia_score"] < 90]),
            "moderate": len([s for s in _services if 50 <= s["clarvia_score"] < 75]),
            "weak": len([s for s in _services if s["clarvia_score"] < 50]),
        },
        "by_category": {
            cat: {
                "count": len(scores),
                "avg_score": round(sum(scores) / len(scores), 1),
            }
            for cat, scores in sorted(by_cat.items())
        },
    }
