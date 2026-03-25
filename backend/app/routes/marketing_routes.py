"""Marketing KPI API — internal dashboard metrics."""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from ..auth import ApiKeyDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/marketing", tags=["marketing"])


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
        {"name": "Schema.org JSON-LD", "done": False},
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
