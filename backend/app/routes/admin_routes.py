"""Admin dashboard API — /admin endpoints for scan overview and system health.

All admin endpoints require API key authentication.
Provides:
- System health overview
- Scan statistics and recent activity
- Service score distribution
- Profile management overview
- Batch rescan trigger
"""

import asyncio
import json
import logging
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..auth import ApiKeyDep
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# Track server start time for uptime calculation
_server_start_time = time.monotonic()
_server_start_dt = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    uptime_seconds: int
    uptime_human: str
    server_time: str
    python_version: str
    services_indexed: int
    profiles_registered: int
    cache_entries: int
    rate_limit_entries: int
    config: dict[str, Any]


class ScanOverview(BaseModel):
    total_services: int
    avg_score: float
    median_score: int
    score_distribution: dict[str, int]
    by_category: dict[str, dict[str, Any]]
    by_rating: dict[str, int]
    top_services: list[dict[str, Any]]
    bottom_services: list[dict[str, Any]]
    recent_scans: list[dict[str, Any]]


class ProfileOverview(BaseModel):
    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    avg_score: float | None
    profiles: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _format_uptime(seconds: int) -> str:
    """Format seconds into human-readable uptime string."""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _load_prebuilt_services() -> list[dict[str, Any]]:
    """Return prebuilt services via index_routes (shared, avoids 16MB re-parse)."""
    from . import index_routes
    index_routes._ensure_loaded()
    return index_routes._services


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def admin_health(_key: ApiKeyDep):
    """System health overview with configuration and resource stats."""
    from ..middleware import _rate_store
    from ..scanner import _scan_cache

    uptime = int(time.monotonic() - _server_start_time)

    # Count services and profiles
    services = _load_prebuilt_services()
    try:
        from .profile_routes import get_all_profiles
        profiles = get_all_profiles()
    except Exception:
        profiles = []

    return HealthResponse(
        status="healthy",
        uptime_seconds=uptime,
        uptime_human=_format_uptime(uptime),
        server_time=datetime.now(timezone.utc).isoformat(),
        python_version=platform.python_version(),
        services_indexed=len(services),
        profiles_registered=len(profiles),
        cache_entries=len(_scan_cache),
        rate_limit_entries=len(_rate_store),
        config={
            "http_timeout": settings.http_timeout,
            "latency_samples": settings.latency_samples,
            "cache_ttl_seconds": settings.cache_ttl_seconds,
            "admin_api_key_set": bool(settings.admin_api_key),
            "supabase_configured": bool(settings.supabase_url),
            "stripe_configured": bool(settings.stripe_secret_key),
        },
    )


@router.get("/scans", response_model=ScanOverview)
async def admin_scan_overview(_key: ApiKeyDep):
    """Comprehensive scan overview with statistics and distributions."""
    services = _load_prebuilt_services()

    if not services:
        return ScanOverview(
            total_services=0,
            avg_score=0.0,
            median_score=0,
            score_distribution={},
            by_category={},
            by_rating={},
            top_services=[],
            bottom_services=[],
            recent_scans=[],
        )

    scores = sorted([s["clarvia_score"] for s in services])
    avg = sum(scores) / len(scores)
    median = scores[len(scores) // 2]

    # Score distribution buckets
    distribution = {
        "0-19": len([s for s in scores if s < 20]),
        "20-39": len([s for s in scores if 20 <= s < 40]),
        "40-59": len([s for s in scores if 40 <= s < 60]),
        "60-79": len([s for s in scores if 60 <= s < 80]),
        "80-100": len([s for s in scores if s >= 80]),
    }

    # By category
    by_cat: dict[str, list[int]] = {}
    for s in services:
        cat = s.get("category", "other")
        by_cat.setdefault(cat, []).append(s["clarvia_score"])
    by_category = {
        cat: {
            "count": len(cat_scores),
            "avg_score": round(sum(cat_scores) / len(cat_scores), 1),
            "min_score": min(cat_scores),
            "max_score": max(cat_scores),
        }
        for cat, cat_scores in sorted(by_cat.items())
    }

    # By rating
    by_rating: dict[str, int] = {}
    for s in services:
        rating = s.get("rating", "Unknown")
        by_rating[rating] = by_rating.get(rating, 0) + 1

    # Top and bottom services
    sorted_services = sorted(services, key=lambda s: s["clarvia_score"], reverse=True)
    top = [
        {
            "name": s["service_name"],
            "url": s["url"],
            "score": s["clarvia_score"],
            "rating": s.get("rating"),
            "category": s.get("category", "other"),
        }
        for s in sorted_services[:10]
    ]
    bottom = [
        {
            "name": s["service_name"],
            "url": s["url"],
            "score": s["clarvia_score"],
            "rating": s.get("rating"),
            "category": s.get("category", "other"),
        }
        for s in sorted_services[-10:]
    ]

    # Recent scans (sorted by scanned_at if available)
    recent = sorted(
        services,
        key=lambda s: s.get("scanned_at", ""),
        reverse=True,
    )[:10]
    recent_scans = [
        {
            "name": s["service_name"],
            "url": s["url"],
            "score": s["clarvia_score"],
            "scanned_at": s.get("scanned_at"),
            "scan_id": s.get("scan_id"),
        }
        for s in recent
    ]

    return ScanOverview(
        total_services=len(services),
        avg_score=round(avg, 1),
        median_score=median,
        score_distribution=distribution,
        by_category=by_category,
        by_rating=by_rating,
        top_services=top,
        bottom_services=bottom,
        recent_scans=recent_scans,
    )


@router.get("/profiles", response_model=ProfileOverview)
async def admin_profiles_overview(_key: ApiKeyDep):
    """Profile management overview."""
    try:
        from .profile_routes import get_all_profiles
        profiles = get_all_profiles()
    except Exception:
        profiles = []

    if not profiles:
        return ProfileOverview(
            total=0,
            by_status={},
            by_category={},
            avg_score=None,
            profiles=[],
        )

    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    scored = []

    for p in profiles:
        status = p.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1

        cat = p.get("category", "other")
        by_category[cat] = by_category.get(cat, 0) + 1

        if p.get("clarvia_score") is not None:
            scored.append(p["clarvia_score"])

    avg_score = round(sum(scored) / len(scored), 1) if scored else None

    profile_list = [
        {
            "profile_id": p["profile_id"],
            "name": p["name"],
            "url": p["url"],
            "category": p.get("category", "other"),
            "status": p.get("status"),
            "clarvia_score": p.get("clarvia_score"),
            "last_scanned_at": p.get("last_scanned_at"),
            "created_at": p.get("created_at"),
        }
        for p in sorted(profiles, key=lambda x: x.get("created_at", ""), reverse=True)
    ]

    return ProfileOverview(
        total=len(profiles),
        by_status=by_status,
        by_category=by_category,
        avg_score=avg_score,
        profiles=profile_list,
    )


@router.post("/rescan-all")
async def admin_rescan_all(
    _key: ApiKeyDep,
    max_concurrent: int = Query(3, ge=1, le=10, description="Max concurrent scans"),
):
    """Trigger a rescan of all prebuilt services. Returns immediately with job info.

    Results are saved to prebuilt-scans.json when complete.
    """
    services = _load_prebuilt_services()
    if not services:
        raise HTTPException(status_code=404, detail="No services found to rescan")

    urls = [s["url"] for s in services]

    # Launch the rescan in the background
    asyncio.create_task(_background_rescan(urls, max_concurrent))

    return {
        "status": "started",
        "total_services": len(urls),
        "max_concurrent": max_concurrent,
        "message": f"Background rescan of {len(urls)} services started.",
    }


async def _background_rescan(urls: list[str], max_concurrent: int = 3) -> None:
    """Background task to rescan all services and save results."""
    from ..scanner import run_scan

    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    async def _scan_one(url: str) -> None:
        async with semaphore:
            try:
                result = await run_scan(url)
                results.append(result.model_dump(mode="json"))
                logger.info("Rescanned %s: score=%d", url, result.clarvia_score)
            except Exception as e:
                logger.warning("Rescan failed for %s: %s", url, e)
                errors.append({"url": url, "error": str(e)})

    await asyncio.gather(*[_scan_one(url) for url in urls])

    # Save results to all prebuilt-scans.json locations
    output_paths = [
        Path(__file__).resolve().parents[3] / "data" / "prebuilt-scans.json",
        Path(__file__).resolve().parents[4] / "data" / "prebuilt-scans.json",
        Path(__file__).resolve().parents[4] / "frontend" / "public" / "data" / "prebuilt-scans.json",
    ]

    for path in output_paths:
        if path.parent.exists():
            try:
                with open(path, "w") as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info("Saved %d scan results to %s", len(results), path)
            except Exception as e:
                logger.error("Failed to save to %s: %s", path, e)

    logger.info(
        "Background rescan complete: %d succeeded, %d failed",
        len(results), len(errors),
    )


@router.get("/kpi")
async def admin_kpi(_key: ApiKeyDep):
    """Real-time KPI dashboard data.

    Returns traffic, agent breakdown, scan metrics, MCP usage,
    performance stats, and time-series data (hourly/daily).
    """
    from ..services.analytics import analytics
    return analytics.get_kpi()


@router.get("/security")
async def admin_security(_key: ApiKeyDep):
    """Security dashboard — abuse detection stats, banned IPs, threat overview."""
    from ..services.security import abuse_detector
    return abuse_detector.get_stats()


@router.get("/dimension-breakdown")
async def admin_dimension_breakdown(_key: ApiKeyDep):
    """Detailed dimension-level breakdown across all services.

    Shows which sub-factors are commonly weak/strong across the index.
    """
    services = _load_prebuilt_services()
    if not services:
        return {"dimensions": {}}

    # Aggregate sub-factor scores
    dim_agg: dict[str, dict[str, list[int]]] = {}

    for s in services:
        dims = s.get("dimensions", {})
        for dim_name, dim_data in dims.items():
            if dim_name not in dim_agg:
                dim_agg[dim_name] = {}
            sub_factors = dim_data.get("sub_factors", {})
            for sf_name, sf_data in sub_factors.items():
                if sf_name not in dim_agg[dim_name]:
                    dim_agg[dim_name][sf_name] = []
                dim_agg[dim_name][sf_name].append(sf_data.get("score", 0))

    # Build response
    dimensions = {}
    for dim_name, sub_factors in dim_agg.items():
        dim_scores = []
        sf_results = {}
        for sf_name, scores in sub_factors.items():
            avg = round(sum(scores) / len(scores), 1) if scores else 0
            sf_results[sf_name] = {
                "avg_score": avg,
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
                "zero_count": scores.count(0),
                "full_count": len([s for s in scores if s > 0]),
                "sample_size": len(scores),
            }
            dim_scores.extend(scores)

        dimensions[dim_name] = {
            "avg_total": round(sum(dim_scores) / max(len(dim_scores), 1), 1),
            "sub_factors": sf_results,
        }

    return {"dimensions": dimensions, "total_services": len(services)}
