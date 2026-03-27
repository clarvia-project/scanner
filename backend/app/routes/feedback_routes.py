"""Feedback API — agents report success/failure of service usage."""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["feedback"])

# In-memory store (persisted to Supabase when available)
_feedback: list[dict[str, Any]] = []
_stats_cache: dict[str, dict[str, Any]] = {}  # profile_id -> aggregated stats


class FeedbackRequest(BaseModel):
    profile_id: str = Field(..., description="Profile ID of the service used")
    agent_id: str | None = Field(None, description="Optional agent identifier")
    outcome: str = Field(..., description="success|failure|partial")
    error_message: str | None = Field(None, max_length=1000)
    latency_ms: int | None = Field(None, ge=0)
    metadata: dict[str, Any] | None = None


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Submit usage feedback for a service. No auth required."""
    if req.outcome not in ("success", "failure", "partial"):
        raise HTTPException(status_code=400, detail="outcome must be success|failure|partial")

    entry = {
        "profile_id": req.profile_id,
        "agent_id": req.agent_id,
        "outcome": req.outcome,
        "error_message": req.error_message,
        "latency_ms": req.latency_ms,
        "metadata": req.metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    _feedback.append(entry)
    _invalidate_stats(req.profile_id)

    # Persist to Supabase (non-blocking)
    _persist_feedback(entry)

    return {"status": "ok", "total_feedback": len([f for f in _feedback if f["profile_id"] == req.profile_id])}


@router.get("/feedback/{profile_id}/stats")
async def get_feedback_stats(profile_id: str):
    """Get aggregated feedback stats for a service."""
    if profile_id in _stats_cache:
        return _stats_cache[profile_id]

    entries = [f for f in _feedback if f["profile_id"] == profile_id]
    if not entries:
        return {
            "profile_id": profile_id,
            "total_uses": 0,
            "success_rate": None,
            "avg_latency_ms": None,
            "outcomes": {"success": 0, "failure": 0, "partial": 0},
        }

    outcomes = defaultdict(int)
    latencies = []
    for e in entries:
        outcomes[e["outcome"]] += 1
        if e.get("latency_ms") is not None:
            latencies.append(e["latency_ms"])

    total = len(entries)
    success_rate = outcomes["success"] / total if total > 0 else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else None

    stats = {
        "profile_id": profile_id,
        "total_uses": total,
        "success_rate": round(success_rate, 3),
        "avg_latency_ms": round(avg_latency) if avg_latency else None,
        "outcomes": dict(outcomes),
    }

    _stats_cache[profile_id] = stats
    return stats


def _invalidate_stats(profile_id: str) -> None:
    _stats_cache.pop(profile_id, None)


def _persist_feedback(entry: dict) -> None:
    """Persist feedback to Supabase (non-blocking)."""
    import asyncio

    async def _save():
        try:
            from ..services.supabase_client import get_supabase
            sb = get_supabase()
            if sb:
                sb.table("service_feedback").insert({
                    "profile_id": entry["profile_id"],
                    "agent_id": entry.get("agent_id"),
                    "outcome": entry["outcome"],
                    "error_message": entry.get("error_message"),
                    "latency_ms": entry.get("latency_ms"),
                    "metadata": entry.get("metadata"),
                    "created_at": entry["created_at"],
                }).execute()
        except Exception as e:
            logger.warning("Failed to persist feedback: %s", e)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_save())
    except Exception:
        pass
