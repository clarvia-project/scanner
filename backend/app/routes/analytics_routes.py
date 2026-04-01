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


@router.get("/attribution")
async def analytics_attribution(
    _key: ApiKeyDep,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include"),
) -> dict[str, Any]:
    """Channel attribution breakdown — which channels bring traffic.

    Returns visits per referrer channel with percentages and agent visit counts.
    """
    import json
    from collections import Counter
    from datetime import date, timedelta
    from pathlib import Path

    analytics_dir = Path(__file__).resolve().parent.parent.parent / "data" / "analytics"
    channel_visits: Counter = Counter()
    channel_agents: Counter = Counter()  # channels that bring agent traffic

    start_date = date.today() - timedelta(days=days)
    for i in range(days):
        day = start_date + timedelta(days=i)
        filepath = analytics_dir / f"analytics-{day.isoformat()}.jsonl"
        if not filepath.exists():
            continue
        try:
            with open(filepath) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    channel = entry.get("referrer_channel", "direct")
                    channel_visits[channel] += 1
                    if entry.get("agent"):
                        channel_agents[channel] += 1
        except Exception:
            continue

    total = sum(channel_visits.values()) or 1
    channels = []
    for ch, visits in channel_visits.most_common():
        channels.append({
            "channel": ch,
            "visits": visits,
            "percentage": round(visits / total * 100, 1),
            "agent_visits": channel_agents.get(ch, 0),
        })

    return {
        "period_days": days,
        "total_visits": sum(channel_visits.values()),
        "channels": channels,
    }
