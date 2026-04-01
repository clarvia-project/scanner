"""Marketing KPI API — internal dashboard metrics, channel tracking, referrals."""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ..auth import ApiKeyDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/marketing", tags=["marketing"])


# ---------------------------------------------------------------------------
# Marketing event persistence
# ---------------------------------------------------------------------------

_EVENT_CANDIDATES = [
    Path("/app/data/marketing_events.jsonl"),
    Path(__file__).resolve().parents[3] / "data" / "marketing_events.jsonl",
]


def _events_path() -> Path:
    for p in _EVENT_CANDIDATES:
        if p.parent.exists():
            return p
    return _EVENT_CANDIDATES[0]


def _load_events() -> list[dict[str, Any]]:
    """Load all marketing events from JSONL file."""
    path = _events_path()
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line:
                events.append(json.loads(line))
    except Exception as exc:
        logger.warning("Failed to load marketing events: %s", exc)
    return events


def _append_event(event: dict[str, Any]) -> None:
    """Append a marketing event to the JSONL file."""
    path = _events_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as exc:
        logger.error("Failed to persist marketing event: %s", exc)


class MarketingEvent(BaseModel):
    """Inbound marketing event payload."""
    event_type: str = Field(..., description="Event type: badge_view, tool_shared, referral_click")
    source: str | None = Field(None, description="Source identifier (URL, agent name, etc.)")
    tool_scan_id: str | None = Field(None, description="Related tool scan_id")
    metadata: dict[str, Any] | None = Field(None, description="Extra event metadata")


def _get_index_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Import index data lazily to avoid circular imports."""
    from .index_routes import _services, _collected_tools, _ensure_loaded, _load_collected

    _ensure_loaded()
    _load_collected()
    return _services, _collected_tools


def _get_scan_cache_size() -> int:
    """Get the number of cached scans."""
    try:
        from ..scanner import _scan_cache
        return len(_scan_cache)
    except Exception:
        return 0


@router.get("/kpi")
async def marketing_kpi(_key: ApiKeyDep):
    """Return marketing KPI metrics for the internal dashboard. Requires API key."""
    services, collected_tools = _get_index_data()

    # ---------- Real KPIs from existing data ----------

    total_scans = len(services)
    total_tools = len(services) + len(collected_tools)
    cached_scans = _get_scan_cache_size()

    # Category distribution
    category_dist: dict[str, int] = {}
    for s in services:
        cat = s.get("category", "other")
        category_dist[cat] = category_dist.get(cat, 0) + 1

    # Service type distribution
    type_dist: dict[str, int] = {}
    all_pool = list(services)
    scanned_ids = {s["scan_id"] for s in services}
    all_pool += [t for t in collected_tools if t["scan_id"] not in scanned_ids]
    for s in all_pool:
        st = s.get("service_type", "general")
        type_dist[st] = type_dist.get(st, 0) + 1

    # Recent scanned services (last 10 by scanned_at)
    sorted_by_time = sorted(
        [s for s in services if s.get("scanned_at")],
        key=lambda s: s.get("scanned_at", ""),
        reverse=True,
    )
    recent_services = [
        {
            "name": s["service_name"],
            "scan_id": s["scan_id"],
            "score": s["clarvia_score"],
            "category": s.get("category", "other"),
            "scanned_at": s.get("scanned_at"),
        }
        for s in sorted_by_time[:10]
    ]

    # Score distribution
    score_dist = {
        "excellent": len([s for s in services if s["clarvia_score"] >= 90]),
        "strong": len([s for s in services if 75 <= s["clarvia_score"] < 90]),
        "moderate": len([s for s in services if 50 <= s["clarvia_score"] < 75]),
        "weak": len([s for s in services if s["clarvia_score"] < 50]),
    }

    avg_score = round(
        sum(s["clarvia_score"] for s in services) / max(len(services), 1), 1
    )

    # ---------- Placeholder KPIs (no data yet) ----------
    placeholders = {
        "mcp_server_installs": None,
        "ai_search_citations": None,
        "compare_card_shares": None,
        "llms_txt_hits": None,
    }

    # ---------- Marketing channel readiness ----------
    channels = [
        {"name": "llms.txt 배포", "done": True},
        {"name": "robots.txt AI 크롤러 허용", "done": True},
        {"name": "agents.json 배포", "done": True},
        {"name": "ai-plugin.json 배포", "done": True},
        {"name": "npm 패키지 게시", "done": False},
        {"name": "MCP Registry 등록 (공식)", "done": False},
        {"name": "Smithery 등록", "done": False},
        {"name": "Glama 등록", "done": False},
        {"name": "PulseMCP 등록", "done": False},
        {"name": ".well-known/mcp 구현", "done": False},
        {"name": "Schema.org JSON-LD", "done": True},
        {"name": "프로그래매틱 FAQ 페이지", "done": False},
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kpi": {
            "total_scans": total_scans,
            "total_tools": total_tools,
            "cached_scans": cached_scans,
            "avg_score": avg_score,
            "badge_requests": 0,  # counter, to be wired up
        },
        "placeholders": placeholders,
        "score_distribution": score_dist,
        "category_distribution": category_dist,
        "type_distribution": type_dist,
        "recent_services": recent_services,
        "channels": channels,
    }


# ---------------------------------------------------------------------------
# GET /v1/marketing/kpi/full — Enhanced KPI dashboard with all metrics
# ---------------------------------------------------------------------------

@router.get("/kpi/full")
async def marketing_kpi_full(_key: ApiKeyDep):
    """Return comprehensive marketing KPI metrics. Requires API key."""
    services, collected_tools = _get_index_data()

    total_tools = len(services) + len(collected_tools)

    # Load marketing events for engagement metrics
    events = _load_events()
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()

    events_this_week = [e for e in events if e.get("timestamp", "") > week_ago]
    badge_views = len([e for e in events_this_week if e.get("event_type") == "badge_view"])
    referrals = len([e for e in events_this_week if e.get("event_type") == "referral_click"])

    # Tools added this week
    tools_this_week = len([
        t for t in list(services) + list(collected_tools)
        if (t.get("indexed_at") or t.get("scanned_at", "")) > week_ago
    ])

    # Search analytics (if available)
    try:
        from .index_routes import _search_counter, _search_log
        search_queries = len([s for s in _search_log if s.get("ts", "") > week_ago])
    except ImportError:
        search_queries = 0

    return {
        "generated_at": now.isoformat(),
        "period": "last_7_days",
        "traffic": {
            "api_calls_total": None,  # Needs traffic middleware integration
            "api_calls_daily_avg": None,
            "unique_agent_sessions": None,
            "unique_human_visitors": None,
            "npm_weekly_downloads": None,  # Needs npm API integration
        },
        "engagement": {
            "badge_views": badge_views,
            "tool_page_views": None,
            "search_queries": search_queries,
            "scan_requests": _get_scan_cache_size(),
            "referrals": referrals,
        },
        "growth": {
            "tools_indexed_total": total_tools,
            "tools_added_this_week": tools_this_week,
            "framework_integrations": 0,
            "ai_search_citations": None,
            "directory_listings": 4,  # Smithery, Glama, PulseMCP, MCP Registry
        },
        "funnel": {
            "discovery": {"impressions": None, "clicks": None},
            "evaluation": {"scans": _get_scan_cache_size(), "gate_checks": None},
            "adoption": {"npm_installs": None, "mcp_connections": None},
            "retention": {"repeat_agents": None, "daily_active": None},
        },
        "targets": {
            "april": {
                "daily_api_calls": 500,
                "agent_sessions": 10,
                "npm_weekly": 1500,
            },
            "july": {
                "daily_api_calls": 5000,
                "agent_sessions": 100,
                "npm_weekly": 5000,
            },
        },
    }


# ---------------------------------------------------------------------------
# GET /v1/marketing/channels — Marketing channel status and performance
# ---------------------------------------------------------------------------

@router.get("/channels")
async def marketing_channels(_key: ApiKeyDep):
    """Return marketing channel status and performance. Requires API key."""
    channels = [
        {
            "id": "llms_txt",
            "name": "llms.txt",
            "status": "active",
            "deployed": True,
            "url": "https://clarvia-api.onrender.com/llms.txt",
            "performance": {"hits": None},
        },
        {
            "id": "agents_json",
            "name": "agents.json (Well-known)",
            "status": "active",
            "deployed": True,
            "url": "https://clarvia-api.onrender.com/.well-known/agents.json",
            "performance": {"hits": None},
        },
        {
            "id": "ai_plugin",
            "name": "ai-plugin.json",
            "status": "active",
            "deployed": True,
            "url": "https://clarvia-api.onrender.com/.well-known/ai-plugin.json",
            "performance": {"hits": None},
        },
        {
            "id": "npm_package",
            "name": "npm: clarvia-mcp-server",
            "status": "active",
            "deployed": True,
            "url": "https://www.npmjs.com/package/clarvia-mcp-server",
            "performance": {"weekly_downloads": None},
        },
        {
            "id": "schema_org",
            "name": "Schema.org JSON-LD",
            "status": "active",
            "deployed": True,
            "url": None,
            "performance": {},
        },
        {
            "id": "mcp_registry",
            "name": "MCP Registry (Official)",
            "status": "pending",
            "deployed": False,
            "url": None,
            "performance": {},
        },
        {
            "id": "smithery",
            "name": "Smithery",
            "status": "pending",
            "deployed": False,
            "url": None,
            "performance": {},
        },
        {
            "id": "glama",
            "name": "Glama",
            "status": "pending",
            "deployed": False,
            "url": None,
            "performance": {},
        },
        {
            "id": "pulsemcp",
            "name": "PulseMCP",
            "status": "pending",
            "deployed": False,
            "url": None,
            "performance": {},
        },
        {
            "id": "well_known_mcp",
            "name": ".well-known/mcp",
            "status": "planned",
            "deployed": False,
            "url": None,
            "performance": {},
        },
        {
            "id": "faq_pages",
            "name": "Programmatic FAQ Pages",
            "status": "planned",
            "deployed": False,
            "url": None,
            "performance": {},
        },
    ]

    active_count = len([c for c in channels if c["deployed"]])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channels": channels,
        "summary": {
            "total": len(channels),
            "active": active_count,
            "pending": len([c for c in channels if c["status"] == "pending"]),
            "planned": len([c for c in channels if c["status"] == "planned"]),
        },
    }


# ---------------------------------------------------------------------------
# GET /v1/marketing/referrals — Agent referral tracking data
# ---------------------------------------------------------------------------

@router.get("/referrals")
async def marketing_referrals(
    _key: ApiKeyDep,
    period: str = Query("7d", description="Time period: 24h, 7d, 30d"),
    limit: int = Query(50, ge=1, le=200),
):
    """Return agent referral tracking data. Requires API key."""
    events = _load_events()

    now = datetime.now(timezone.utc)
    if period == "24h":
        cutoff = now - timedelta(hours=24)
    elif period == "30d":
        cutoff = now - timedelta(days=30)
    else:
        cutoff = now - timedelta(days=7)

    cutoff_iso = cutoff.isoformat()

    referral_events = [
        e for e in events
        if e.get("event_type") == "referral_click"
        and e.get("timestamp", "") > cutoff_iso
    ]

    # Aggregate by source
    source_counts: dict[str, int] = {}
    for e in referral_events:
        src = e.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    top_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    return {
        "generated_at": now.isoformat(),
        "period": period,
        "total_referrals": len(referral_events),
        "unique_sources": len(source_counts),
        "top_sources": [
            {"source": src, "count": cnt} for src, cnt in top_sources
        ],
        "recent": referral_events[-10:][::-1],  # Last 10, newest first
    }


# ---------------------------------------------------------------------------
# POST /v1/marketing/track — Track marketing events
# ---------------------------------------------------------------------------

_VALID_EVENT_TYPES = {"badge_view", "tool_shared", "referral_click"}


@router.post("/track")
async def track_marketing_event(event: MarketingEvent):
    """Track a marketing event (badge view, share, referral).

    Public endpoint — no API key required to allow external tracking.
    """
    if event.event_type not in _VALID_EVENT_TYPES:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {', '.join(sorted(_VALID_EVENT_TYPES))}",
        )

    record: dict[str, Any] = {
        "event_type": event.event_type,
        "source": event.source,
        "tool_scan_id": event.tool_scan_id,
        "metadata": event.metadata,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _append_event(record)
    logger.info("Marketing event tracked: %s from %s", event.event_type, event.source)

    return {
        "status": "recorded",
        "event_type": event.event_type,
        "timestamp": record["timestamp"],
    }
