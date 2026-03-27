"""Admin analytics API — /api/admin/analytics endpoints for traffic monitoring.

All endpoints require ADMIN_API_KEY authentication via X-API-Key header.
Data is read from persistent JSONL files in backend/data/analytics/.

Endpoints:
- GET /api/admin/analytics/summary   — daily/weekly/monthly traffic summary
- GET /api/admin/analytics/agents    — unique AI agent breakdown
- GET /api/admin/analytics/endpoints — most used API endpoints
- GET /api/admin/analytics/tools     — tool search/scan activity breakdown
- GET /api/admin/analytics/realtime  — real-time in-memory analytics snapshot
"""

import logging
from typing import Any

from fastapi import APIRouter, Query

from ..auth import ApiKeyDep
from ..services.analytics import analytics
from ..services.analytics_writer import (
    get_agent_breakdown,
    get_endpoint_breakdown,
    get_summary,
    get_tool_activity,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/analytics",
    tags=["admin-analytics"],
)


@router.get("/summary")
async def analytics_summary(
    _key: ApiKeyDep,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include"),
) -> dict[str, Any]:
    """Traffic summary with daily/weekly breakdowns.

    Returns request counts, agent ratios, error rates, response times,
    and daily time series for the specified period.
    """
    return get_summary(days=days)


@router.get("/agents")
async def analytics_agents(
    _key: ApiKeyDep,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include"),
) -> dict[str, Any]:
    """Unique AI agent breakdown.

    Shows which AI agents (Claude, GPT, Cursor, etc.) are using the API,
    their request volumes, top endpoints, and daily trends.
    """
    return get_agent_breakdown(days=days)


@router.get("/endpoints")
async def analytics_endpoints(
    _key: ApiKeyDep,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include"),
) -> dict[str, Any]:
    """Most used API endpoints.

    Returns endpoints ranked by request count with error rates,
    response times, and which agents use them most.
    """
    return get_endpoint_breakdown(days=days)


@router.get("/tools")
async def analytics_tools(
    _key: ApiKeyDep,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include"),
) -> dict[str, Any]:
    """Tool search/scan activity breakdown.

    Shows how often tools are being searched, scanned, scored, etc.
    with per-agent and daily trend breakdowns.
    """
    return get_tool_activity(days=days)


@router.get("/realtime")
async def analytics_realtime(
    _key: ApiKeyDep,
) -> dict[str, Any]:
    """Real-time in-memory analytics snapshot.

    Returns the current in-memory KPI data (since last server restart).
    For historical data, use the other analytics endpoints which read
    from persistent JSONL files.
    """
    return analytics.get_kpi()
