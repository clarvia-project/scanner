"""Ingestion API — Pipeline statistics, new/trending tools, and manual triggers."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response

from ..auth import ApiKeyDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["ingestion"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_all_tools() -> list[dict[str, Any]]:
    """Get merged scanned + collected tools (same pattern as trending_routes)."""
    from . import index_routes

    index_routes._ensure_loaded()
    index_routes._load_collected()
    scanned_ids = {s["scan_id"] for s in index_routes._services}
    return list(index_routes._services) + [
        t for t in index_routes._collected_tools if t["scan_id"] not in scanned_ids
    ]


def _get_submissions() -> list[dict[str, Any]]:
    """Load submissions from the JSONL file."""
    from .submission_routes import _submissions_path
    import json

    path = _submissions_path()
    if not path.exists():
        return []
    submissions: list[dict[str, Any]] = []
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line:
                submissions.append(json.loads(line))
    except Exception as exc:
        logger.warning("Failed to load submissions: %s", exc)
    return submissions


def _compact_tool(t: dict[str, Any]) -> dict[str, Any]:
    """Compact tool representation for ingestion endpoints."""
    clarvia_score = t.get("clarvia_score", 0)
    return {
        "name": t.get("service_name", t.get("name", "")),
        "scan_id": t.get("scan_id", ""),
        "url": t.get("url", ""),
        "description": (t.get("description", "") or "")[:150],
        "category": t.get("category", "other"),
        "service_type": t.get("service_type", "general"),
        "score": t.get("score") or clarvia_score,
        "clarvia_score": clarvia_score,
        "rating": t.get("rating", "Low"),
        "scanned_at": t.get("scanned_at"),
        "indexed_at": t.get("indexed_at", t.get("scanned_at")),
    }


# ---------------------------------------------------------------------------
# GET /v1/ingestion/stats — Pipeline statistics
# ---------------------------------------------------------------------------

@router.get("/ingestion/stats")
async def ingestion_stats(response: Response, _key: ApiKeyDep):
    """Return ingestion pipeline statistics. Requires API key."""
    all_tools = _get_all_tools()
    submissions = _get_submissions()

    # Count submissions by status
    sub_total = len(submissions)
    sub_indexed = len([s for s in submissions if s.get("status") == "indexed"])

    # Derive source breakdown from tool data
    scanned_tools = [t for t in all_tools if not t.get("scan_id", "").startswith("tool_")]
    collected_tools = [t for t in all_tools if t.get("scan_id", "").startswith("tool_")]

    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)

    # Recently indexed (tools with scanned_at in last 24h)
    recent_indexed = [
        t for t in all_tools
        if t.get("scanned_at") and t["scanned_at"] > last_24h.isoformat()
    ]

    response.headers["X-Clarvia-Version"] = "1.0"
    return {
        "queue_size": 0,  # No active queue in current architecture
        "sources": {
            "github_watch": {
                "last_run": None,
                "items_found": 0,
                "items_indexed": 0,
                "status": "not_configured",
            },
            "registry_sync": {
                "last_run": None,
                "items_found": len(collected_tools),
                "items_indexed": len(collected_tools),
                "status": "active",
            },
            "self_submit": {
                "total": sub_total,
                "indexed": sub_indexed,
                "status": "active",
            },
            "community_crawl": {
                "last_run": None,
                "items_found": 0,
                "items_indexed": 0,
                "status": "not_configured",
            },
        },
        "totals": {
            "queued": 0,
            "processed": len(all_tools),
            "indexed": len(all_tools),
            "skipped": 0,
            "failed": 0,
        },
        "recently_indexed_24h": len(recent_indexed),
        "catalog_size": len(all_tools),
        "last_updated": now.isoformat(),
    }


# ---------------------------------------------------------------------------
# GET /v1/ingestion/recent — Recently ingested tools
# ---------------------------------------------------------------------------

@router.get("/ingestion/recent")
async def ingestion_recent(
    response: Response,
    period: str = Query("24h", description="Time period: 24h or 7d"),
    limit: int = Query(20, ge=1, le=100),
):
    """Return recently ingested tools within the given period."""
    all_tools = _get_all_tools()

    now = datetime.now(timezone.utc)
    if period == "7d":
        cutoff = now - timedelta(days=7)
    else:
        cutoff = now - timedelta(hours=24)

    cutoff_iso = cutoff.isoformat()

    # Filter tools with a timestamp after cutoff
    recent = [
        t for t in all_tools
        if (t.get("indexed_at") or t.get("scanned_at", "")) > cutoff_iso
    ]
    recent.sort(
        key=lambda t: t.get("indexed_at") or t.get("scanned_at") or "",
        reverse=True,
    )

    response.headers["X-Clarvia-Version"] = "1.0"
    return {
        "period": period,
        "count": len(recent[:limit]),
        "total_in_period": len(recent),
        "tools": [_compact_tool(t) for t in recent[:limit]],
    }


# ---------------------------------------------------------------------------
# GET /v1/tools/new — New tools feed (sorted by indexed_at desc)
# ---------------------------------------------------------------------------

@router.get("/tools/new")
async def new_tools(
    response: Response,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None, description="Filter by category"),
):
    """Return newest tools, sorted by indexed_at descending."""
    all_tools = _get_all_tools()

    if category:
        all_tools = [t for t in all_tools if t.get("category") == category]

    # Sort by indexed_at or scanned_at (newest first, None → empty string)
    all_tools.sort(
        key=lambda t: t.get("indexed_at") or t.get("scanned_at") or "",
        reverse=True,
    )

    page = all_tools[offset : offset + limit]

    response.headers["X-Clarvia-Version"] = "1.0"
    return {
        "tools": [_compact_tool(t) for t in page],
        "total": len(all_tools),
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < len(all_tools),
    }


# ---------------------------------------------------------------------------
# GET /v1/tools/trending — Trending tools (score-based, recent focus)
# ---------------------------------------------------------------------------

@router.get("/tools/trending")
async def trending_tools(
    response: Response,
    limit: int = Query(20, ge=1, le=50),
    category: str | None = Query(None, description="Filter by category"),
    min_score: int = Query(0, ge=0, le=100, description="Minimum score filter"),
):
    """Trending tools — high-scored recent tools.

    Without historical score data, returns top-scored tools that were
    recently indexed. When score history is available, this will show
    tools with the largest score increase over the last 7 days.
    """
    all_tools = _get_all_tools()

    if category:
        all_tools = [t for t in all_tools if t.get("category") == category]

    if min_score > 0:
        all_tools = [t for t in all_tools if t.get("clarvia_score", 0) >= min_score]

    # Combine recency and score for a trending signal
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()

    def _trending_key(t: dict) -> float:
        score = t.get("clarvia_score", 0)
        ts = t.get("indexed_at") or t.get("scanned_at") or ""
        # Boost tools indexed in the last 7 days
        recency_boost = 1.5 if ts > week_ago else 1.0
        return score * recency_boost

    all_tools.sort(key=_trending_key, reverse=True)

    response.headers["X-Clarvia-Version"] = "1.0"
    return {
        "tools": [_compact_tool(t) for t in all_tools[:limit]],
        "total_candidates": len(all_tools),
        "algorithm": "score_with_recency_boost",
        "note": "Historical score tracking not yet active; using score * recency as proxy.",
    }


# ---------------------------------------------------------------------------
# POST /v1/ingestion/trigger — Manual ingestion trigger (admin only)
# ---------------------------------------------------------------------------

@router.post("/ingestion/trigger")
async def trigger_ingestion(_key: ApiKeyDep):
    """Manually trigger an ingestion run. Requires API key.

    Currently a placeholder — returns acknowledgement.
    When the ingestion pipeline is implemented, this will kick off
    a full registry sync + GitHub watch cycle.
    """
    logger.info("Manual ingestion trigger requested")

    return {
        "status": "accepted",
        "message": "Ingestion trigger acknowledged. Pipeline not yet automated.",
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "note": "Full pipeline automation coming soon. Currently data is synced via prebuilt scans.",
    }
