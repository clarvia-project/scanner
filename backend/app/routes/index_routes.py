"""Index API — Agent-facing service discovery endpoints."""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["index"])

# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------
_CATEGORY_MAP: dict[str, list[str]] = {
    "ai": [
        "openai", "anthropic", "google ai", "mistral", "cohere",
        "replicate", "hugging face", "together", "groq", "perplexity",
    ],
    "developer_tools": [
        "github", "gitlab", "vercel", "netlify", "supabase",
        "firebase", "aws", "cloudflare", "railway", "render",
    ],
    "payments": [
        "stripe", "paypal", "squareup", "plaid", "coinbase", "circle",
    ],
    "communication": [
        "slack", "discord", "twilio", "sendgrid", "resend",
    ],
    "data": [
        "snowflake", "databricks", "mixpanel", "amplitude", "segment",
    ],
    "productivity": [
        "notion", "linear", "atlassian", "asana", "figma", "canva",
    ],
    "blockchain": [
        "solana", "ethereum", "helius", "alchemy", "moralis", "dune",
    ],
    "mcp": [
        "mcp", "smithery", "glama",
    ],
}

# Reverse lookup: lowercase service name -> category
_SERVICE_CATEGORY: dict[str, str] = {}
for cat, names in _CATEGORY_MAP.items():
    for name in names:
        _SERVICE_CATEGORY[name.lower()] = cat


def _classify(service_name: str) -> str:
    key = service_name.lower()
    if key in _SERVICE_CATEGORY:
        return _SERVICE_CATEGORY[key]
    # Partial match fallback
    for name, cat in _SERVICE_CATEGORY.items():
        if name in key or key in name:
            return cat
    return "other"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
_services: list[dict[str, Any]] = []
_by_scan_id: dict[str, dict[str, Any]] = {}


class SortOrder(str, Enum):
    score_desc = "score_desc"
    score_asc = "score_asc"
    name_asc = "name_asc"
    name_desc = "name_desc"
    recent = "recent"


# ---------------------------------------------------------------------------
# Collected tools (loaded on demand when source=all)
# ---------------------------------------------------------------------------
_collected_tools: list[dict[str, Any]] = []
_collected_loaded = False

_COLLECTED_FILES = [
    "mcp-registry-all.json",
    "skills-cli-collected.json",
    "all-agent-tools.json",
]


def _find_data_dir() -> Path | None:
    candidates = [Path("/app/data")]
    base = Path(__file__).resolve()
    for i in range(2, 6):
        try:
            candidates.append(base.parents[i] / "data")
        except IndexError:
            break
    for p in candidates:
        if p.is_dir():
            return p
    return None


def _find_collected_file(fname: str) -> Path | None:
    """Search multiple candidate directories for a collected data file."""
    candidates = [Path("/app/data")]
    base = Path(__file__).resolve()
    for i in range(2, 6):
        try:
            candidates.append(base.parents[i] / "data")
        except IndexError:
            break
    for d in candidates:
        p = d / fname
        if p.exists():
            return p
    return None


def _load_collected() -> None:
    global _collected_tools, _collected_loaded
    if _collected_loaded:
        return

    from ..tool_scorer import normalize_tool

    seen_ids: set[str] = set()
    # name-based dedup: keep the higher-scored tool when the same name appears from different sources
    seen_names: dict[str, int] = {}  # lowercase name -> index in tools list
    tools: list[dict[str, Any]] = []

    for fname in _COLLECTED_FILES:
        fpath = _find_collected_file(fname)
        if not fpath:
            logger.warning("Collected file not found: %s", fname)
            continue
        try:
            with open(fpath, "r") as f:
                raw = json.load(f)
            for item in raw:
                normalized = normalize_tool(item)
                sid = normalized["scan_id"]
                if sid in seen_ids:
                    continue
                seen_ids.add(sid)

                name_key = normalized["service_name"].lower().strip()
                if name_key in seen_names:
                    existing_idx = seen_names[name_key]
                    existing_score = tools[existing_idx].get("clarvia_score", 0)
                    new_score = normalized.get("clarvia_score", 0)
                    if new_score > existing_score:
                        tools[existing_idx] = normalized
                else:
                    seen_names[name_key] = len(tools)
                    tools.append(normalized)
        except Exception as e:
            logger.warning("Failed to load %s: %s", fname, e)

    _collected_tools = tools
    _collected_loaded = True
    logger.info("Loaded %d collected tools from %d files", len(tools), len(_COLLECTED_FILES))


def _load_data() -> None:
    global _services, _by_scan_id
    data_dir = _find_data_dir()
    data_path = data_dir / "prebuilt-scans.json" if data_dir else None

    if data_path is None or not data_path.exists():
        logger.error("prebuilt-scans.json not found in any candidate path")
        return
    with open(data_path, "r") as f:
        raw = json.load(f)

    for entry in raw:
        entry["category"] = _classify(entry.get("service_name", ""))
    _services = raw
    _by_scan_id = {s["scan_id"]: s for s in _services}
    logger.info("Loaded %d services for Index API", len(_services))

    # Merge scanned profiles into the services index
    _merge_profiles()


def _merge_profiles() -> None:
    """Load scanned profiles and add them to the services index."""
    global _services, _by_scan_id
    try:
        from .profile_routes import get_all_profiles

        for profile in get_all_profiles():
            if profile.get("status") != "scanned" or profile.get("scan_result") is None:
                continue

            scan_result = profile["scan_result"]
            scan_id = scan_result.get("scan_id")
            if not scan_id or scan_id in _by_scan_id:
                continue  # already present or no scan_id

            entry = {
                "scan_id": scan_id,
                "url": profile["url"],
                "service_name": profile["name"],
                "description": profile.get("description", ""),
                "clarvia_score": profile.get("clarvia_score", 0),
                "rating": scan_result.get("rating", "unknown"),
                "dimensions": scan_result.get("dimensions", {}),
                "category": profile.get("category", "other"),
                "service_type": profile.get("service_type", "general"),
                "type_config": profile.get("type_config"),
                "scanned_at": scan_result.get("scanned_at"),
                "source": "profile",
                "profile_id": profile["profile_id"],
                "tags": profile.get("tags", []),
                "agents_json_valid": profile.get("agents_json_valid"),
            }
            _services.append(entry)
            _by_scan_id[scan_id] = entry

        logger.info("Merged profiles, total services: %d", len(_services))
    except Exception as e:
        logger.warning("Failed to merge profiles: %s", e)


def _ensure_loaded() -> None:
    if not _services:
        _load_data()


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _compact_service(s: dict[str, Any]) -> dict[str, Any]:
    """Return a compact representation (no sub_factors)."""
    dims = s.get("dimensions", {})
    result = {
        "name": s["service_name"],
        "url": s["url"],
        "description": s.get("description", ""),
        "category": s.get("category", "other"),
        "service_type": s.get("service_type", "general"),
        "clarvia_score": s["clarvia_score"],
        "rating": s["rating"],
        "dimensions": {k: v["score"] for k, v in dims.items()},
        "scan_id": s["scan_id"],
        "last_scanned": s.get("scanned_at"),
    }
    # Include connection_info for typed services
    tc = s.get("type_config")
    if tc:
        result["connection_info"] = _build_connection_info(s.get("service_type", "general"), tc)
    if s.get("profile_id"):
        result["profile_id"] = s["profile_id"]
    return result


def _build_connection_info(service_type: str, type_config: dict) -> dict[str, Any]:
    """Build agent-friendly connection info from type_config."""
    if service_type == "mcp_server":
        info: dict[str, Any] = {}
        if type_config.get("npm_package"):
            info["install"] = f"npm install {type_config['npm_package']}"
        if type_config.get("endpoint_url"):
            info["endpoint"] = type_config["endpoint_url"]
        if type_config.get("transport"):
            info["transport"] = type_config["transport"]
        if type_config.get("tools"):
            info["tools"] = type_config["tools"]
        return info
    elif service_type == "cli_tool":
        info = {}
        if type_config.get("install_command"):
            info["install"] = type_config["install_command"]
        if type_config.get("binary_name"):
            info["binary"] = type_config["binary_name"]
        return info
    elif service_type == "api":
        info = {}
        if type_config.get("openapi_url"):
            info["openapi"] = type_config["openapi_url"]
        if type_config.get("base_url"):
            info["base_url"] = type_config["base_url"]
        if type_config.get("auth_method"):
            info["auth"] = type_config["auth_method"]
        return info
    elif service_type == "skill":
        info = {}
        if type_config.get("skill_file_url"):
            info["skill_url"] = type_config["skill_file_url"]
        if type_config.get("compatible_agents"):
            info["agents"] = type_config["compatible_agents"]
        return info
    return {}


def _full_service(s: dict[str, Any]) -> dict[str, Any]:
    """Return a full representation with sub_factors."""
    return {
        "name": s["service_name"],
        "url": s["url"],
        "category": s.get("category", "other"),
        "clarvia_score": s["clarvia_score"],
        "rating": s["rating"],
        "dimensions": s.get("dimensions", {}),
        "scan_id": s["scan_id"],
        "last_scanned": s.get("scanned_at"),
    }


def _add_headers(response: Response) -> None:
    _ensure_loaded()
    response.headers["X-Clarvia-Version"] = "1.0"
    response.headers["X-Clarvia-Total-Services"] = str(len(_services))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/services")
async def list_services(
    response: Response,
    category: str | None = Query(None, description="Filter by category"),
    service_type: str | None = Query(None, description="Filter by type: mcp_server|skill|cli_tool|api|general"),
    q: str | None = Query(None, description="Text search in name/description"),
    min_score: int = Query(0, ge=0, le=100, description="Minimum Clarvia Score"),
    max_score: int | None = Query(None, ge=0, le=100, description="Maximum Clarvia Score"),
    sort: SortOrder = Query(SortOrder.score_desc, description="Sort order"),
    source: str | None = Query(None, description="'all' to include 20k+ collected tools, 'collected' for collected only, default=scanned only"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Search and filter services for agent consumption.

    Supports compound filters: service_type + category + score + text search.
    Use source=all to search across 20,000+ agent tools (MCP servers, APIs, CLIs, Skills).
    Example: GET /v1/services?source=all&service_type=mcp_server&q=github
    """
    _ensure_loaded()
    _add_headers(response)

    if source in ("all", "collected"):
        _load_collected()

    if source == "collected":
        filtered = list(_collected_tools)
    elif source == "all":
        # Merge: scanned services first (higher quality), then collected
        scanned_ids = {s["scan_id"] for s in _services}
        filtered = list(_services) + [
            t for t in _collected_tools if t["scan_id"] not in scanned_ids
        ]
    else:
        filtered = _services

    if category:
        filtered = [s for s in filtered if s.get("category") == category]

    if service_type:
        filtered = [s for s in filtered if s.get("service_type", "general") == service_type]

    if q:
        q_lower = q.lower()
        filtered = [
            s for s in filtered
            if q_lower in s.get("service_name", "").lower()
            or q_lower in s.get("description", "").lower()
            or q_lower in s.get("url", "").lower()
            or any(q_lower in t.lower() for t in s.get("tags", []))
        ]

    filtered = [s for s in filtered if s["clarvia_score"] >= min_score]

    if max_score is not None:
        filtered = [s for s in filtered if s["clarvia_score"] <= max_score]

    if sort == SortOrder.score_desc:
        filtered.sort(key=lambda s: s["clarvia_score"], reverse=True)
    elif sort == SortOrder.score_asc:
        filtered.sort(key=lambda s: s["clarvia_score"])
    elif sort == SortOrder.name_asc:
        filtered.sort(key=lambda s: s["service_name"].lower())
    elif sort == SortOrder.name_desc:
        filtered.sort(key=lambda s: s["service_name"].lower(), reverse=True)
    elif sort == SortOrder.recent:
        filtered.sort(key=lambda s: s.get("scanned_at") or "", reverse=True)

    total = len(filtered)
    page = filtered[offset : offset + limit]

    return {
        "total": total,
        "services": [_compact_service(s) for s in page],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        },
    }


# Aliases for discoverability — agents try /search, /score, /leaderboard
@router.get("/search")
async def search_alias(
    response: Response,
    q: str | None = Query(None),
    category: str | None = Query(None),
    service_type: str | None = Query(None),
    min_score: int = Query(0, ge=0, le=100),
    sort: SortOrder = Query(SortOrder.score_desc),
    source: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Alias for /v1/services — agents naturally look for /search."""
    return await list_services(
        response=response, category=category, service_type=service_type,
        q=q, min_score=min_score, max_score=None, sort=sort,
        source=source, limit=limit, offset=offset,
    )


@router.get("/score")
async def score_quick(
    response: Response,
    url: str = Query(..., description="Service URL to get score for"),
):
    """Quick score lookup by URL — returns cached score or 'not_found'."""
    _ensure_loaded()
    _add_headers(response)
    url_lower = url.lower().rstrip("/")
    for s in _services:
        if s.get("url", "").lower().rstrip("/") == url_lower:
            return {
                "url": url,
                "score": s["clarvia_score"],
                "rating": s["rating"],
                "category": s.get("category", "other"),
                "scan_id": s["scan_id"],
                "found": True,
            }
    return {
        "url": url,
        "score": None,
        "rating": None,
        "found": False,
        "message": "Not yet scanned. Use POST /api/scan to get a score.",
    }


@router.get("/leaderboard")
async def leaderboard(
    response: Response,
    category: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Top-scoring services leaderboard."""
    _ensure_loaded()
    _add_headers(response)
    filtered = _services
    if category:
        filtered = [s for s in filtered if s.get("category") == category]
    filtered = sorted(filtered, key=lambda s: s["clarvia_score"], reverse=True)[:limit]
    return {
        "leaderboard": [
            {
                "rank": i + 1,
                "name": s["service_name"],
                "url": s["url"],
                "score": s["clarvia_score"],
                "rating": s["rating"],
                "category": s.get("category", "other"),
                "scan_id": s["scan_id"],
            }
            for i, s in enumerate(filtered)
        ],
        "total": len(_services),
    }


@router.get("/services/{scan_id}")
async def get_service(scan_id: str, response: Response):
    """Get full details for a specific service by scan_id."""
    _ensure_loaded()
    _add_headers(response)

    service = _by_scan_id.get(scan_id)
    if not service:
        # Try collected tools
        _load_collected()
        for t in _collected_tools:
            if t["scan_id"] == scan_id:
                service = t
                break
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # For collected tools, return enriched format
    if scan_id.startswith("tool_"):
        return {
            "name": service["service_name"],
            "url": service.get("url", ""),
            "description": service.get("description", ""),
            "category": service.get("category", "other"),
            "service_type": service.get("service_type", "general"),
            "clarvia_score": service["clarvia_score"],
            "rating": service["rating"],
            "dimensions": service.get("dimensions", {}),
            "scan_id": service["scan_id"],
            "source": service.get("source", ""),
            "tags": service.get("tags", []),
            "type_config": service.get("type_config"),
            "last_scanned": service.get("scanned_at"),
        }
    return _full_service(service)


@router.get("/categories")
async def list_categories(response: Response):
    """List available categories with service counts."""
    _ensure_loaded()
    _add_headers(response)

    counts: dict[str, int] = {}
    for s in _services:
        cat = s.get("category", "other")
        counts[cat] = counts.get(cat, 0) + 1

    return {
        "categories": [
            {"name": cat, "count": counts.get(cat, 0)}
            for cat in sorted(_CATEGORY_MAP.keys())
        ],
    }


@router.get("/compare")
async def compare_services(
    response: Response,
    ids: str = Query(..., description="Comma-separated scan_ids (max 4)"),
):
    """Compare up to 4 services side by side."""
    _ensure_loaded()
    _load_collected()
    _add_headers(response)

    scan_ids = [s.strip() for s in ids.split(",")][:4]
    results = []

    for sid in scan_ids:
        service = _by_scan_id.get(sid)
        if not service:
            for t in _collected_tools:
                if t["scan_id"] == sid:
                    service = t
                    break
        if service:
            results.append(_compact_service(service))

    return {"services": results, "count": len(results)}


@router.get("/stats")
async def get_stats(
    response: Response,
    source: str | None = Query(None, description="'all' to include collected tools"),
):
    """Overall statistics across all indexed services."""
    _ensure_loaded()
    _add_headers(response)

    if source == "all":
        _load_collected()
        scanned_ids = {s["scan_id"] for s in _services}
        pool = list(_services) + [
            t for t in _collected_tools if t["scan_id"] not in scanned_ids
        ]
    else:
        pool = _services

    total = len(pool)
    if total == 0:
        return {"total_services": 0, "avg_score": 0, "by_category": {}}

    avg = sum(s["clarvia_score"] for s in pool) / total

    by_cat: dict[str, list[int]] = {}
    for s in pool:
        cat = s.get("category", "other")
        by_cat.setdefault(cat, []).append(s["clarvia_score"])

    by_type: dict[str, int] = {}
    for s in pool:
        st = s.get("service_type", "general")
        by_type[st] = by_type.get(st, 0) + 1

    result: dict[str, Any] = {
        "total_services": total,
        "avg_score": round(avg, 1),
        "score_distribution": {
            "excellent": len([s for s in pool if s["clarvia_score"] >= 90]),
            "strong": len([s for s in pool if 75 <= s["clarvia_score"] < 90]),
            "moderate": len([s for s in pool if 50 <= s["clarvia_score"] < 75]),
            "weak": len([s for s in pool if s["clarvia_score"] < 50]),
        },
        "by_category": {
            cat: {
                "count": len(scores),
                "avg_score": round(sum(scores) / len(scores), 1),
            }
            for cat, scores in sorted(by_cat.items())
        },
        "by_type": by_type,
    }

    # Add source breakdown when showing all
    if source == "all":
        result["scanned_count"] = len(_services)
        result["collected_count"] = total - len(_services)

    return result
