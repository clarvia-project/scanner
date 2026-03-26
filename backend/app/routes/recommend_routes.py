"""Recommend API — Intent-based tool recommendation."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from ..recommender import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["recommend"])


class RecommendRequest(BaseModel):
    intent: str = Field(..., min_length=2, max_length=500, description="Natural language intent")
    filters: dict[str, Any] | None = Field(None, description="Optional filters: service_type, category, min_score")
    limit: int = Field(10, ge=1, le=50)


@router.post("/recommend")
async def recommend_tools(req: RecommendRequest, response: Response):
    """Recommend tools based on natural language intent.

    Example: {"intent": "I want to automate GitHub PR reviews"}
    """
    engine = get_engine()
    if not engine.is_built:
        # Trigger index build from loaded data
        _ensure_index_built()

    filters = req.filters or {}
    result = engine.recommend(
        req.intent,
        limit=req.limit,
        min_score=filters.get("min_score", 0),
        service_type=filters.get("service_type"),
        category=filters.get("category"),
    )

    response.headers["X-Clarvia-Method"] = result["method"]
    return result


@router.get("/recommend")
async def recommend_tools_get(
    response: Response,
    intent: str = Query(..., min_length=2, max_length=500, description="Natural language intent"),
    service_type: str | None = Query(None),
    category: str | None = Query(None),
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(10, ge=1, le=50),
):
    """GET version of recommend for simple usage.

    Example: /v1/recommend?intent=github+pr+review&limit=5
    """
    engine = get_engine()
    if not engine.is_built:
        _ensure_index_built()

    result = engine.recommend(
        intent,
        limit=limit,
        min_score=min_score,
        service_type=service_type,
        category=category,
    )

    response.headers["X-Clarvia-Method"] = result["method"]
    return result


@router.get("/similar/{scan_id}")
async def get_similar_tools(
    scan_id: str,
    response: Response,
    limit: int = Query(5, ge=1, le=20),
):
    """Get similar tools based on category and type."""
    _ensure_index_built()

    # Find the target tool
    from . import index_routes

    index_routes._ensure_loaded()
    index_routes._load_collected()

    target = index_routes._by_scan_id.get(scan_id)
    if not target:
        for t in index_routes._collected_tools:
            if t["scan_id"] == scan_id:
                target = t
                break

    if not target:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Find similar: same category + same type, sorted by score
    cat = target.get("category", "other")
    stype = target.get("service_type", "general")

    scanned_ids = {s["scan_id"] for s in index_routes._services}
    all_tools = list(index_routes._services) + [
        t for t in index_routes._collected_tools if t["scan_id"] not in scanned_ids
    ]

    similar = [
        t
        for t in all_tools
        if t.get("category") == cat
        and t.get("service_type") == stype
        and t["scan_id"] != scan_id
    ]
    similar.sort(key=lambda x: x.get("clarvia_score", 0), reverse=True)

    from .index_routes import _compact_service

    return {
        "similar": [_compact_service(t) for t in similar[:limit]],
        "based_on": {"category": cat, "service_type": stype},
    }


def _ensure_index_built() -> None:
    """Build index from loaded services if not already built."""
    engine = get_engine()
    if engine.is_built:
        return

    try:
        from . import index_routes

        index_routes._ensure_loaded()
        index_routes._load_collected()

        # Merge: scanned first, then collected (deduped)
        scanned_ids = {s["scan_id"] for s in index_routes._services}
        all_tools = list(index_routes._services) + [
            t for t in index_routes._collected_tools if t["scan_id"] not in scanned_ids
        ]

        # Normalize scanned services to have same fields as collected
        normalized = []
        for t in all_tools:
            normalized.append({
                "scan_id": t.get("scan_id", ""),
                "service_name": t.get("service_name", t.get("name", "")),
                "description": t.get("description", ""),
                "url": t.get("url", ""),
                "category": t.get("category", "other"),
                "service_type": t.get("service_type", "general"),
                "clarvia_score": t.get("clarvia_score", 0),
                "rating": t.get("rating", "Low"),
                "tags": t.get("tags", []),
                "type_config": t.get("type_config"),
                "capabilities": t.get("capabilities", []),
                "popularity": t.get("popularity", 0),
                "cross_refs": t.get("cross_refs", {}),
            })

        engine.build_index(normalized)
        logger.info("Recommendation engine ready: %d tools indexed", engine.tool_count)

    except Exception as e:
        logger.error("Failed to build recommendation index: %s", e)
