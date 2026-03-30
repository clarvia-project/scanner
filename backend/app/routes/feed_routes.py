"""Public scores feed API — machine-readable bulk data for registries and agents.

Endpoints:
- GET /v1/feed/scores      — All scored services (JSON, paginated)
- GET /v1/feed/scores.csv  — CSV export for data consumers
- GET /v1/feed/top         — Top services by score (for embedding in registries)
- GET /v1/feed/stats       — Aggregate statistics for ecosystem reporting
- GET /v1/feed/badge-data  — Embeddable badge data for any service URL

No authentication required. Designed for:
1. MCP registries (PulseMCP, mcp.so, Glama) to show Clarvia scores
2. Agent frameworks to bulk-load trust data
3. CI/CD systems to validate tool dependencies
"""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/feed", tags=["feed"])


def _load_all_services() -> list[dict[str, Any]]:
    """Return all services (prebuilt + collected) via index_routes."""
    from . import index_routes
    index_routes._ensure_loaded()
    index_routes._load_collected()
    scanned_ids = {s["scan_id"] for s in index_routes._services}
    return list(index_routes._services) + [
        t for t in index_routes._collected_tools if t["scan_id"] not in scanned_ids
    ]


@router.get("/scores")
async def feed_scores(
    min_score: int = Query(0, ge=0, le=100),
    category: str | None = Query(None),
    service_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Paginated JSON feed of all scored services.

    Designed for registries and agent frameworks to bulk-consume scores.
    Cache-friendly (24h TTL recommended).
    """
    services = _load_all_services()

    # Filters
    if min_score > 0:
        services = [s for s in services if s.get("clarvia_score", 0) >= min_score]
    if category:
        services = [s for s in services if s.get("category", "").lower() == category.lower()]
    if service_type:
        services = [s for s in services if s.get("service_type", "").lower() == service_type.lower()]

    total = len(services)
    services = sorted(services, key=lambda s: s.get("clarvia_score", 0), reverse=True)
    page = services[offset:offset + limit]

    from .index_routes import _classify

    results = [
        {
            "name": s.get("service_name", ""),
            "url": s.get("url", ""),
            "score": s.get("clarvia_score", 0),
            "rating": s.get("rating", ""),
            "category": _classify(s.get("service_name", "")) if s.get("category", "other") == "other" else s.get("category", "other"),
            "service_type": s.get("service_type", "general"),
            "scan_id": s.get("scan_id", ""),
            "scanned_at": s.get("scanned_at", ""),
        }
        for s in page
    ]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "services": results,
        "meta": {
            "source": "clarvia.art",
            "api_version": "1.0",
            "docs": "https://clarvia.art/docs",
            "attribution": "Scores by Clarvia AEO Scanner — clarvia.art",
        },
    }


@router.get("/scores.csv")
async def feed_scores_csv(
    min_score: int = Query(0, ge=0, le=100, description="Minimum score threshold"),
    max_score: int = Query(100, ge=0, le=100, description="Maximum score threshold"),
    category: str | None = Query(None, description="Filter by category (e.g. ai, devtools, fintech)"),
    service_type: str | None = Query(None, description="Filter by service type (e.g. mcp_server, api)"),
    limit: int = Query(0, ge=0, le=10000, description="Max rows to return (0 = all)"),
    sort: str = Query("score_desc", description="Sort order: score_desc, score_asc, name_asc"),
):
    """CSV export of scored services with filtering.

    Supports filtering by score range, category, service type, and row limit.
    Returns RFC 4180-compliant CSV with Content-Disposition header for download.
    Ideal for data pipelines, spreadsheets, and bulk analysis.
    """

    services = _load_all_services()

    # Apply filters
    if min_score > 0:
        services = [s for s in services if s.get("clarvia_score", 0) >= min_score]
    if max_score < 100:
        services = [s for s in services if s.get("clarvia_score", 0) <= max_score]
    if category:
        services = [s for s in services if s.get("category", "other").lower() == category.lower()]
    if service_type:
        services = [s for s in services if s.get("service_type", "general").lower() == service_type.lower()]

    # Sort
    if sort == "score_asc":
        services = sorted(services, key=lambda s: s.get("clarvia_score", 0))
    elif sort == "name_asc":
        services = sorted(services, key=lambda s: s.get("service_name", "").lower())
    else:  # score_desc (default)
        services = sorted(services, key=lambda s: s.get("clarvia_score", 0), reverse=True)

    # Limit
    if limit > 0:
        services = services[:limit]

    # RFC 4180 CSV: quote fields that contain commas, quotes, or newlines
    def _csv_escape(val: str) -> str:
        if "," in val or '"' in val or "\n" in val:
            return '"' + val.replace('"', '""') + '"'
        return val

    lines = ["name,url,score,rating,category,service_type,scan_id,scanned_at"]
    for s in services:
        name = _csv_escape(s.get("service_name", ""))
        url = _csv_escape(s.get("url", ""))
        score = str(s.get("clarvia_score", 0))
        rating = s.get("rating", "")
        cat = s.get("category", "other")
        stype = s.get("service_type", "general")
        scan_id = s.get("scan_id", "")
        scanned = s.get("scanned_at", "")
        lines.append(f"{name},{url},{score},{rating},{cat},{stype},{scan_id},{scanned}")

    csv_content = "\n".join(lines) + "\n"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="clarvia-scores.csv"',
            "Cache-Control": "public, max-age=86400",
            "X-Total-Count": str(len(services)),
        },
    )


@router.get("/top")
async def feed_top(
    limit: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
):
    """Top-scoring services. Ideal for registry widgets and "powered by Clarvia" embeds."""
    services = _load_all_services()
    if category:
        services = [s for s in services if s.get("category", "").lower() == category.lower()]
    services = sorted(services, key=lambda s: s.get("clarvia_score", 0), reverse=True)[:limit]

    return {
        "top_services": [
            {
                "name": s.get("service_name", ""),
                "url": s.get("url", ""),
                "score": s.get("clarvia_score", 0),
                "rating": s.get("rating", ""),
                "badge_url": f"https://clarvia-api.onrender.com/v1/badge/{s.get('scan_id', '')}",
            }
            for s in services
        ],
        "attribution": "Clarvia AEO Scanner — clarvia.art",
    }


@router.get("/stats")
async def feed_stats():
    """Aggregate ecosystem statistics. For reporting and dashboards."""
    services = _load_all_services()
    if not services:
        return {"total": 0}

    scores = [s.get("clarvia_score", 0) for s in services]
    by_rating: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for s in services:
        r = s.get("rating", "Unknown")
        by_rating[r] = by_rating.get(r, 0) + 1
        c = s.get("category", "other")
        by_category[c] = by_category.get(c, 0) + 1

    return {
        "total_services": len(services),
        "avg_score": round(sum(scores) / len(scores), 1),
        "median_score": sorted(scores)[len(scores) // 2],
        "by_rating": by_rating,
        "by_category": by_category,
        "score_distribution": {
            "0-19": len([s for s in scores if s < 20]),
            "20-39": len([s for s in scores if 20 <= s < 40]),
            "40-59": len([s for s in scores if 40 <= s < 60]),
            "60-79": len([s for s in scores if 60 <= s < 80]),
            "80-100": len([s for s in scores if s >= 80]),
        },
        "attribution": "Clarvia AEO Scanner — clarvia.art",
    }


@router.get("/top50")
async def feed_top50():
    """Curated Top 50 AI agent tools, selected by composite score.

    Cached for 24 hours. Returns the best tools per category with
    curation score and selection reason.
    """
    import time

    # Simple in-memory cache (24h TTL)
    cache_attr = "_top50_cache"
    cache_ts_attr = "_top50_cache_ts"
    now = time.time()
    cached = getattr(feed_top50, cache_attr, None)
    cached_ts = getattr(feed_top50, cache_ts_attr, 0)

    if cached and (now - cached_ts) < 86400:
        return cached

    # Load curated data from file
    candidates = [Path("/app/data")]
    base = Path(__file__).resolve()
    for i in range(2, 6):
        try:
            candidates.append(base.parents[i] / "data")
        except IndexError:
            break

    curated_data = None
    for p in candidates:
        curated_path = p / "curated" / "top50.json"
        if curated_path.exists():
            try:
                with open(curated_path) as f:
                    curated_data = json.load(f)
                break
            except Exception as exc:
                logger.warning("Failed to load top50.json from %s: %s", curated_path, exc)

    if not curated_data or not curated_data.get("tools"):
        return {
            "total": 0,
            "tools": [],
            "message": "Curation data not yet generated. Run: python scripts/automation/curator.py",
            "meta": {
                "source": "clarvia.art",
                "cache_ttl_hours": 24,
            },
        }

    result = {
        "total": curated_data.get("total", 0),
        "categories": curated_data.get("categories", 0),
        "generated_at": curated_data.get("generated_at", ""),
        "tools": [
            {
                "name": t.get("name", ""),
                "category": t.get("category", ""),
                "clarvia_score": t.get("clarvia_score", 0),
                "curation_score": t.get("curation_score", 0),
                "reason": t.get("reason", ""),
                "url": t.get("url", ""),
                "rating": t.get("rating", ""),
            }
            for t in curated_data.get("tools", [])
        ],
        "meta": {
            "source": "clarvia.art",
            "api_version": "1.0",
            "cache_ttl_hours": 24,
            "docs": "https://clarvia.art/docs",
        },
    }

    # Cache the result
    setattr(feed_top50, cache_attr, result)
    setattr(feed_top50, cache_ts_attr, now)

    return result


@router.get("/badge-data")
async def feed_badge_data(
    url: str = Query(..., description="Service URL to get badge data for"),
):
    """Badge data for any URL. Registries can use this to show inline Clarvia scores."""
    services = _load_all_services()
    url_lower = url.lower().rstrip("/")

    # Also check live index (includes recent scans not yet in prebuilt file)
    try:
        from .index_routes import _services as live_services
        all_services = services + [s for s in live_services if s.get("scan_id") not in {x.get("scan_id") for x in services}]
    except Exception:
        all_services = services

    # Find best match (highest score if multiple scans)
    best = None
    for s in all_services:
        s_url = s.get("url", "").lower().rstrip("/")
        if s_url == url_lower:
            if best is None or s.get("clarvia_score", 0) > best.get("clarvia_score", 0):
                best = s

    if best:
        return {
            "url": url,
            "score": best.get("clarvia_score", 0),
            "rating": best.get("rating", ""),
            "badge_svg": f"https://clarvia-api.onrender.com/v1/badge/{best.get('scan_id', '')}",
            "detail_url": f"https://clarvia.art/scan/{best.get('scan_id', '')}",
            "found": True,
        }

    return {
        "url": url,
        "score": None,
        "rating": None,
        "badge_svg": None,
        "detail_url": f"https://clarvia.art/?url={url}",
        "found": False,
        "message": "Service not yet scanned. Scan it at clarvia.art",
    }
