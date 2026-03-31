"""Trending API — Weekly trending tools and category movers."""

import logging
from typing import Any

from fastapi import APIRouter, Query, Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["trending"])


def _get_all_tools() -> list[dict[str, Any]]:
    """Get merged scanned + collected tools."""
    from . import index_routes

    index_routes._ensure_loaded()
    index_routes._load_collected()
    scanned_ids = {s["scan_id"] for s in index_routes._services}
    return list(index_routes._services) + [
        t for t in index_routes._collected_tools if t["scan_id"] not in scanned_ids
    ]


def _compact(t: dict[str, Any]) -> dict[str, Any]:
    """Compact tool representation for trending."""
    # BUG-05 fix: score가 null이면 clarvia_score를 fallback으로 사용
    clarvia_score = t.get("clarvia_score", 0)
    score = t.get("score") or clarvia_score
    return {
        "name": t.get("service_name", t.get("name", "")),
        "scan_id": t.get("scan_id", ""),
        "url": t.get("url", ""),
        "description": (t.get("description", "") or "")[:150],
        "category": t.get("category", "other"),
        "service_type": t.get("service_type", "general"),
        "score": score,
        "clarvia_score": clarvia_score,
        "rating": t.get("rating", "Low"),
    }


@router.get("/trending")
async def get_trending(
    response: Response,
    category: str | None = Query(None, description="Filter by category"),
    service_type: str | None = Query(None, description="Filter by type"),
    limit: int = Query(20, ge=1, le=50),
):
    """Get trending tools — top-scored tools by category with rising stars.

    Returns:
    - top_tools: Overall highest-scored tools
    - by_category: Top tools per category
    - rising_stars: High-quality tools from collected sources (emerging ecosystem)
    - service_type_leaders: Best tool per service type
    """
    all_tools = _get_all_tools()

    # Apply filters
    pool = all_tools
    if category:
        pool = [t for t in pool if t.get("category") == category]
    if service_type:
        pool = [t for t in pool if t.get("service_type") == service_type]

    # Sort by score
    pool.sort(key=lambda t: t.get("clarvia_score", 0), reverse=True)

    # Top tools overall
    top_tools = [_compact(t) for t in pool[:limit]]

    # By category — top 5 per category
    by_category: dict[str, list] = {}
    for t in all_tools:
        cat = t.get("category", "other")
        if cat not in by_category:
            by_category[cat] = []
        if len(by_category[cat]) < 5:
            by_category[cat].append(_compact(t))
    # Sort each category by score
    for cat in by_category:
        by_category[cat].sort(key=lambda x: x["clarvia_score"], reverse=True)

    # Rising stars: collected tools with score >= 50 (from registry/ecosystem)
    rising = [
        t for t in all_tools
        if t.get("scan_id", "").startswith("tool_")
        and t.get("clarvia_score", 0) >= 50
        and len(t.get("description", "")) > 20
    ]
    rising.sort(key=lambda t: t.get("clarvia_score", 0), reverse=True)
    rising_stars = [_compact(t) for t in rising[:10]]

    # Service type leaders
    type_leaders: dict[str, dict] = {}
    for t in all_tools:
        st = t.get("service_type", "general")
        if st not in type_leaders or t.get("clarvia_score", 0) > type_leaders[st].get("clarvia_score", 0):
            type_leaders[st] = _compact(t)

    # Category stats
    cat_stats: dict[str, dict] = {}
    for t in all_tools:
        cat = t.get("category", "other")
        if cat not in cat_stats:
            cat_stats[cat] = {"count": 0, "total_score": 0, "top_score": 0}
        cat_stats[cat]["count"] += 1
        cat_stats[cat]["total_score"] += t.get("clarvia_score", 0)
        cat_stats[cat]["top_score"] = max(cat_stats[cat]["top_score"], t.get("clarvia_score", 0))
    for cat in cat_stats:
        cat_stats[cat]["avg_score"] = round(cat_stats[cat]["total_score"] / cat_stats[cat]["count"], 1)
        del cat_stats[cat]["total_score"]

    response.headers["X-Clarvia-Version"] = "1.0"
    return {
        "top_tools": top_tools,
        "by_category": by_category,
        "rising_stars": rising_stars,
        "service_type_leaders": type_leaders,
        "category_stats": cat_stats,
        "total_indexed": len(all_tools),
    }
