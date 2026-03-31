"""Profile API — Layer 2: MCP service registration and discovery."""

import json
import logging
import secrets
import string
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, EmailStr, Field, HttpUrl

from ..auth import ApiKeyDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["profiles"])

# ---------------------------------------------------------------------------
# Data persistence (in-memory + JSON file)
# ---------------------------------------------------------------------------
_DATA_CANDIDATES = [
    Path("/app/data/profiles.json"),
    Path(__file__).resolve().parents[3] / "data" / "profiles.json",
]

_profiles: dict[str, dict[str, Any]] = {}  # profile_id -> profile


def _data_path() -> Path:
    for p in _DATA_CANDIDATES:
        if p.parent.exists():
            return p
    return _DATA_CANDIDATES[0]


def _load_profiles() -> None:
    global _profiles

    # 1. 로컬 JSON 파일에서 로드
    path = _data_path()
    if path.exists():
        try:
            with open(path, "r") as f:
                data = json.load(f)
            _profiles = {p["profile_id"]: p for p in data}
            logger.info("Loaded %d profiles from %s", len(_profiles), path)
        except Exception as e:
            logger.error("Failed to load profiles from file: %s", e)

    # 2. Supabase에서 병합 (파일에 없는 프로필 추가)
    try:
        from ..services.supabase_client import get_supabase
        client = get_supabase()
        if client:
            result = client.table("profiles").select("*").execute()
            if result.data:
                for row in result.data:
                    pid = row["profile_id"]
                    if pid not in _profiles:
                        _profiles[pid] = row
                logger.info("Merged Supabase profiles, total: %d", len(_profiles))
    except Exception as e:
        logger.debug("Supabase profile load skipped: %s", e)

    if not _profiles:
        logger.info("No profiles found, starting empty")


def _save_profiles() -> None:
    # 1. JSON 파일 (로컬 백업)
    path = _data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w") as f:
            json.dump(list(_profiles.values()), f, indent=2, default=str)
    except Exception as e:
        logger.error("Failed to save profiles to file: %s", e)

    # 2. Supabase (프로덕션 영속성)
    try:
        from ..services.supabase_client import get_supabase
        client = get_supabase()
        if client and _profiles:
            for p in _profiles.values():
                row = {
                    "profile_id": p["profile_id"],
                    "name": p["name"],
                    "url": p["url"],
                    "description": p.get("description", ""),
                    "category": p.get("category", "other"),
                    "service_type": p.get("service_type", "general"),
                    "github_url": p.get("github_url"),
                    "type_config": p.get("type_config"),
                    "tags": p.get("tags", []),
                    "status": p.get("status", "pending"),
                    "clarvia_score": p.get("clarvia_score", 0) or 0,
                    "scan_result": p.get("scan_result"),
                }
                try:
                    client.table("profiles").upsert(row, on_conflict="profile_id").execute()
                except Exception:
                    pass  # 테이블 미존재 시 무시, 파일 백업은 이미 완료
    except Exception as e:
        logger.debug("Supabase profile sync skipped: %s", e)


def _gen_id() -> str:
    chars = string.ascii_lowercase + string.digits
    return "prf_" + "".join(secrets.choice(chars) for _ in range(12))


def get_all_profiles() -> list[dict[str, Any]]:
    """Public accessor for index integration."""
    if not _profiles:
        _load_profiles()
    return list(_profiles.values())


# NOTE: _load_profiles() is called during app lifespan startup (see main.py),
# not at module import time, to avoid side effects during import.


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class MCPConfig(BaseModel):
    transport: str = "stdio"
    tools_count: int = 0
    resources_count: int = 0


SERVICE_TYPES = {"mcp_server", "skill", "cli_tool", "api", "general"}


class ProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    url: HttpUrl = Field(..., description="Service URL (must be a valid HTTP/HTTPS URL)")
    description: str = Field("", max_length=2000)
    category: str = Field("other", max_length=50)
    service_type: str = Field("general", description="mcp_server|skill|cli_tool|api|general")
    type_config: dict[str, Any] | None = Field(
        None,
        description="Type-specific config. "
        "mcp_server: {npm_package, endpoint_url, transport, tools, resources}. "
        "skill: {skill_file_url, compatible_agents, execution_env}. "
        "cli_tool: {install_command, binary_name, usage_example}. "
        "api: {openapi_url, auth_method, base_url}.",
    )
    github_url: HttpUrl | None = None
    mcp_config: MCPConfig | None = None
    contact_email: EmailStr | None = None
    tags: list[str] = Field(default_factory=list)


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    url: HttpUrl | None = None
    description: str | None = None
    category: str | None = None
    service_type: str | None = None
    type_config: dict[str, Any] | None = None
    github_url: HttpUrl | None = None
    mcp_config: MCPConfig | None = None
    contact_email: EmailStr | None = None
    tags: list[str] | None = None


# ---------------------------------------------------------------------------
# Badge helpers
# ---------------------------------------------------------------------------

def _badge_color(score: int | None) -> str:
    if score is None:
        return "#9f9f9f"  # gray for unscored
    if score >= 80:
        return "#4c1"  # bright green
    if score >= 60:
        return "#97ca00"  # green
    if score >= 40:
        return "#dfb317"  # yellow
    return "#e05d44"  # red


def _make_badge_svg(score: int | None) -> str:
    score_text = str(score) if score is not None else "?"
    color = _badge_color(score)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="150" height="20">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="150" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="90" height="20" fill="#555"/>
    <rect x="90" width="60" height="20" fill="{color}"/>
    <rect width="150" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="45" y="15" fill="#010101" fill-opacity=".3">Clarvia Score</text>
    <text x="45" y="14" fill="#fff">Clarvia Score</text>
    <text x="120" y="15" fill="#010101" fill-opacity=".3">{score_text}</text>
    <text x="120" y="14" fill="#fff">{score_text}</text>
  </g>
</svg>"""


# ---------------------------------------------------------------------------
# Simple IP-based rate limiter for POST /profiles (5 req/min per IP)
# ---------------------------------------------------------------------------
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW = 60  # seconds


def _check_rate_limit(ip: str) -> None:
    """Raise 429 if IP exceeds 5 requests per minute."""
    now = time.time()
    timestamps = _rate_limit_store[ip]
    # Prune old entries
    _rate_limit_store[ip] = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[ip]) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {_RATE_LIMIT_MAX} profile registrations per minute.",
        )
    _rate_limit_store[ip].append(now)
    # Evict stale IPs to prevent unbounded growth
    if len(_rate_limit_store) > 10_000:
        cutoff = now - _RATE_LIMIT_WINDOW
        stale = [k for k, v in _rate_limit_store.items() if not v or v[-1] < cutoff]
        for k in stale:
            del _rate_limit_store[k]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/profiles")
async def create_profile(req: ProfileCreateRequest, request: Request):
    """Register a new service. No API key required — open registration."""
    # Rate limit: 5 per minute per IP
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
    # Validate service_type
    stype = req.service_type or "general"
    if stype not in SERVICE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid service_type. Must be one of: {', '.join(SERVICE_TYPES)}")

    # Check for duplicate URL
    req_url_str = str(req.url)
    for p in _profiles.values():
        if p["url"] == req_url_str:
            raise HTTPException(
                status_code=409,
                detail=f"Profile already exists for URL: {req_url_str}",
            )

    profile_id = _gen_id()
    now = datetime.now(timezone.utc).isoformat()

    # Convert Pydantic Url/EmailStr objects to plain strings for JSON serialization
    url_str = str(req.url)
    github_url_str = str(req.github_url) if req.github_url else None
    contact_email_str = str(req.contact_email) if req.contact_email else None

    profile = {
        "profile_id": profile_id,
        "name": req.name,
        "url": url_str,
        "description": req.description,
        "category": req.category,
        "service_type": stype,
        "type_config": req.type_config,
        "github_url": github_url_str,
        "mcp_config": req.mcp_config.model_dump() if req.mcp_config else None,
        "contact_email": contact_email_str,
        "tags": req.tags,
        "clarvia_score": None,
        "status": "pending_scan",
        "created_at": now,
        "updated_at": now,
        "last_scanned_at": None,
        "scan_result": None,
        "agents_json_valid": None,
        "email_verified": False,
    }

    _profiles[profile_id] = profile
    _save_profiles()

    # Auto-validate agents.json in background (non-blocking)
    _schedule_agents_json_check(profile_id, url_str)

    # Auto-trigger scan (non-blocking)
    _schedule_auto_scan(profile_id)

    return {
        "profile_id": profile_id,
        "name": req.name,
        "url": url_str,
        "service_type": stype,
        "clarvia_score": None,
        "status": "pending_scan",
        "created_at": now,
        "service_url": f"https://clarvia.art/service/{profile_id}",
    }


def _schedule_agents_json_check(profile_id: str, url: str) -> None:
    """Non-blocking agents.json validation after registration."""
    import asyncio
    import httpx

    async def _check():
        try:
            agents_url = f"{url.rstrip('/')}/.well-known/agents.json"
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(agents_url)
                valid = resp.status_code == 200
                if profile_id in _profiles:
                    _profiles[profile_id]["agents_json_valid"] = valid
                    _save_profiles()
        except Exception:
            if profile_id in _profiles:
                _profiles[profile_id]["agents_json_valid"] = False
                _save_profiles()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_check())
    except Exception:
        pass


def _schedule_auto_scan(profile_id: str) -> None:
    """Auto-trigger scan after registration (non-blocking)."""
    import asyncio

    async def _scan():
        try:
            profile = _profiles.get(profile_id)
            if not profile:
                return
            profile["status"] = "scanning"
            _save_profiles()

            from ..scanner import run_scan
            result = await run_scan(profile["url"])

            profile["clarvia_score"] = result.clarvia_score
            profile["status"] = "scanned"
            profile["last_scanned_at"] = datetime.now(timezone.utc).isoformat()
            profile["scan_result"] = {
                "scan_id": result.scan_id,
                "rating": result.rating,
                "clarvia_score": result.clarvia_score,
                "dimensions": {
                    k: {"score": v.score, "max": v.max}
                    for k, v in result.dimensions.items()
                },
                "top_recommendations": result.top_recommendations,
                "scanned_at": result.scanned_at.isoformat(),
            }
            _save_profiles()

            try:
                from ..services.supabase_client import save_scan
                await save_scan(result)
            except Exception:
                pass

            # Persist to scan history
            try:
                dim_scores = {k: v.score for k, v in result.dimensions.items()}
                from .scan_history_routes import persist_scan_result
                await persist_scan_result(
                    url=result.url, scan_id=result.scan_id,
                    score=result.clarvia_score, rating=result.rating,
                    service_name=result.service_name, dimensions=dim_scores or None,
                )
            except Exception:
                pass
        except Exception as e:
            logger.warning("Auto-scan failed for %s: %s", profile_id, e)
            if profile_id in _profiles:
                _profiles[profile_id]["status"] = "scan_failed"
                _save_profiles()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_scan())
    except Exception:
        pass


@router.get("/profiles")
async def list_profiles(
    category: str | None = Query(None, description="Filter by category"),
    service_type: str | None = Query(None, description="Filter by service type"),
    status: str | None = Query(None, description="Filter by status"),
    min_score: int | None = Query(None, ge=0, le=100),
    q: str | None = Query(None, description="Text search in name/description"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List registered profiles with optional filters.

    Merges directly registered profiles with the prebuilt services index so
    that category/search filters work across all known tools (not just the
    small set registered via POST /profiles).
    """
    # Start with directly registered profiles
    registered = list(_profiles.values())

    # Merge index services (leaderboard data) — deduplicate by URL
    seen_urls: set[str] = {p.get("url", "") for p in registered}
    try:
        from .index_routes import _services, _ensure_loaded
        _ensure_loaded()
        for svc in _services:
            url = svc.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                registered.append({
                    "profile_id": svc.get("scan_id", ""),
                    "name": svc.get("service_name", ""),
                    "url": url,
                    "description": svc.get("description", ""),
                    "category": svc.get("category", "other"),
                    "service_type": svc.get("service_type", "general"),
                    "type_config": None,
                    "clarvia_score": svc.get("clarvia_score"),
                    "status": "scanned",
                    "tags": svc.get("tags", []),
                    "agents_json_valid": None,
                    "created_at": svc.get("scanned_at"),
                })
    except Exception as e:
        logger.debug("Index merge skipped in list_profiles: %s", e)

    results = registered

    if category:
        results = [p for p in results if p.get("category") == category]
    if service_type:
        results = [p for p in results if p.get("service_type", "general") == service_type]
    if status:
        results = [p for p in results if p.get("status") == status]
    if q:
        q_lower = q.lower()
        results = [p for p in results if q_lower in p.get("name", "").lower() or q_lower in p.get("description", "").lower()]
    if min_score is not None:
        results = [
            p for p in results
            if p.get("clarvia_score") is not None
            and p["clarvia_score"] >= min_score
        ]

    # Sort: scored first (desc), then pending
    results.sort(
        key=lambda p: (p.get("clarvia_score") is not None, p.get("clarvia_score") or 0),
        reverse=True,
    )

    total = len(results)
    page = results[offset : offset + limit]

    return {
        "total": total,
        "profiles": [
            {
                "profile_id": p["profile_id"],
                "name": p["name"],
                "url": p["url"],
                "category": p.get("category", "other"),
                "service_type": p.get("service_type", "general"),
                "type_config": p.get("type_config"),
                "clarvia_score": p.get("clarvia_score"),
                "status": p.get("status"),
                "tags": p.get("tags", []),
                "agents_json_valid": p.get("agents_json_valid"),
                "created_at": p.get("created_at"),
            }
            for p in page
        ],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        },
    }


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str):
    """Get full profile details.

    Accepts:
      - profile_id (prf_xxx)  — registered profile
      - scan_id (scn_xxx)     — prebuilt scan from index
      - slug (e.g. github-com-org-repo) — matched by URL slug
    """
    # 1. Direct profile lookup
    profile = _profiles.get(profile_id)
    if profile:
        return profile

    # 2. Fallback: look up from main services index (prebuilt-scans + collected)
    try:
        from .index_routes import _by_scan_id, _services, _ensure_loaded, _load_collected, _collected_tools
        _ensure_loaded()

        # Try scan_id match
        service = _by_scan_id.get(profile_id)

        # Try collected tools
        if not service:
            _load_collected()
            for t in _collected_tools:
                if t.get("scan_id") == profile_id:
                    service = t
                    break

        # Try slug match (url-derived slug)
        if not service:
            import re
            slug = profile_id.strip().lower()
            for s in _services:
                url = (s.get("url") or "").lower()
                url_slug = re.sub(r"^https?://", "", url).rstrip("/")
                url_slug = re.sub(r"[^a-z0-9]+", "-", url_slug).strip("-")
                if url_slug == slug:
                    service = s
                    break

        # Try name match (case-insensitive, hyphenated)
        if not service:
            normalized = profile_id.replace("-", " ").replace("_", " ").lower()
            for s in _services:
                if s.get("service_name", "").lower() == normalized:
                    service = s
                    break

        if service:
            return {
                "profile_id": service.get("scan_id", profile_id),
                "name": service.get("service_name", ""),
                "url": service.get("url", ""),
                "description": service.get("description", ""),
                "category": service.get("category", "other"),
                "service_type": service.get("service_type", "general"),
                "clarvia_score": service.get("clarvia_score"),
                "rating": service.get("rating", ""),
                "dimensions": service.get("dimensions", {}),
                "scan_id": service.get("scan_id", ""),
                "tags": service.get("tags", []),
                "status": "scanned",
                "source": "index",
                "last_scanned_at": service.get("scanned_at"),
            }
    except Exception as e:
        logger.warning("Fallback profile lookup failed: %s", e)

    raise HTTPException(status_code=404, detail="Profile not found")


@router.put("/profiles/{profile_id}")
async def update_profile(profile_id: str, req: ProfileUpdateRequest, _key: ApiKeyDep):
    """Update an existing profile. Requires API key."""
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    updates = req.model_dump(exclude_unset=True)
    if "mcp_config" in updates and updates["mcp_config"] is not None:
        updates["mcp_config"] = updates["mcp_config"].model_dump() if hasattr(updates["mcp_config"], "model_dump") else updates["mcp_config"]

    # Convert Pydantic Url/EmailStr objects to plain strings
    for url_field in ("url", "github_url"):
        if url_field in updates and updates[url_field] is not None:
            updates[url_field] = str(updates[url_field])
    if "contact_email" in updates and updates["contact_email"] is not None:
        updates["contact_email"] = str(updates["contact_email"])

    for key, value in updates.items():
        profile[key] = value

    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_profiles()

    return profile


@router.post("/profiles/{profile_id}/scan")
async def scan_profile(profile_id: str, _key: ApiKeyDep):
    """Trigger a scan for the profile's URL and update its Clarvia Score. Requires API key."""
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile["status"] = "scanning"
    _save_profiles()

    try:
        from ..scanner import run_scan
        result = await run_scan(profile["url"])

        profile["clarvia_score"] = result.clarvia_score
        profile["status"] = "scanned"
        profile["last_scanned_at"] = datetime.now(timezone.utc).isoformat()
        profile["scan_result"] = {
            "scan_id": result.scan_id,
            "rating": result.rating,
            "clarvia_score": result.clarvia_score,
            "dimensions": {
                k: {"score": v.score, "max": v.max}
                for k, v in result.dimensions.items()
            },
            "top_recommendations": result.top_recommendations,
            "scanned_at": result.scanned_at.isoformat(),
        }
        _save_profiles()

        # Persist to Supabase
        try:
            from ..services.supabase_client import save_scan
            await save_scan(result)
        except Exception as e:
            logger.warning("Failed to persist scan to Supabase: %s", e)

        # Persist to scan history
        try:
            dim_scores = {k: v.score for k, v in result.dimensions.items()}
            from .scan_history_routes import persist_scan_result
            await persist_scan_result(
                url=result.url, scan_id=result.scan_id,
                score=result.clarvia_score, rating=result.rating,
                service_name=result.service_name, dimensions=dim_scores or None,
            )
        except Exception:
            pass

        return {
            "profile_id": profile_id,
            "clarvia_score": result.clarvia_score,
            "rating": result.rating,
            "status": "scanned",
            "scan_id": result.scan_id,
        }
    except Exception:
        logger.exception("Profile scan failed for %s", profile["url"])
        profile["status"] = "scan_failed"
        _save_profiles()
        raise HTTPException(
            status_code=500,
            detail="Scan failed due to an internal error. Please try again later.",
        )


# ---------------------------------------------------------------------------
# Rescan rate limiter: 1 rescan per profile per hour
# ---------------------------------------------------------------------------
_rescan_timestamps: dict[str, float] = {}
_RESCAN_COOLDOWN = 3600  # seconds


@router.post("/profiles/{profile_id}/rescan")
async def rescan_profile(profile_id: str):
    """Trigger a rescan. No API key needed — open to tool authors."""
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Rate limit: 1 rescan per profile per hour
    now = time.time()
    last_rescan = _rescan_timestamps.get(profile_id, 0)
    if now - last_rescan < _RESCAN_COOLDOWN:
        remaining = int(_RESCAN_COOLDOWN - (now - last_rescan))
        raise HTTPException(
            status_code=429,
            detail=f"Rescan rate limit: 1 per hour. Try again in {remaining}s.",
        )

    _rescan_timestamps[profile_id] = now
    profile["status"] = "scanning"
    _save_profiles()

    try:
        from ..scanner import run_scan
        result = await run_scan(profile["url"])

        profile["clarvia_score"] = result.clarvia_score
        profile["status"] = "scanned"
        profile["last_scanned_at"] = datetime.now(timezone.utc).isoformat()
        profile["scan_result"] = {
            "scan_id": result.scan_id,
            "rating": result.rating,
            "clarvia_score": result.clarvia_score,
            "dimensions": {
                k: {"score": v.score, "max": v.max}
                for k, v in result.dimensions.items()
            },
            "top_recommendations": result.top_recommendations,
            "scanned_at": result.scanned_at.isoformat(),
        }
        _save_profiles()

        try:
            from ..services.supabase_client import save_scan
            await save_scan(result)
        except Exception as e:
            logger.warning("Failed to persist rescan to Supabase: %s", e)

        # Persist to scan history
        try:
            dim_scores = {k: v.score for k, v in result.dimensions.items()}
            from .scan_history_routes import persist_scan_result
            await persist_scan_result(
                url=result.url, scan_id=result.scan_id,
                score=result.clarvia_score, rating=result.rating,
                service_name=result.service_name, dimensions=dim_scores or None,
            )
        except Exception:
            pass

        return {
            "profile_id": profile_id,
            "clarvia_score": result.clarvia_score,
            "rating": result.rating,
            "status": "scanned",
            "scan_id": result.scan_id,
        }
    except Exception:
        logger.exception("Rescan failed for %s", profile["url"])
        profile["status"] = "scan_failed"
        _save_profiles()
        raise HTTPException(
            status_code=500,
            detail="Rescan failed due to an internal error. Please try again later.",
        )


@router.get("/profiles/{profile_id}/rank")
async def get_profile_rank(profile_id: str):
    """Get this tool's rank within its category and overall."""
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    score = profile.get("clarvia_score")
    if score is None:
        return {
            "overall_rank": None,
            "category_rank": None,
            "category_total": 0,
            "percentile": None,
            "message": "Profile has not been scanned yet.",
        }

    # Get all scored services from index
    from .index_routes import _services, _ensure_loaded
    _ensure_loaded()

    cat = profile.get("category", "other")
    all_scores = sorted(
        [s["clarvia_score"] for s in _services if s.get("clarvia_score") is not None],
        reverse=True,
    )
    cat_scores = sorted(
        [s["clarvia_score"] for s in _services
         if s.get("clarvia_score") is not None and s.get("category") == cat],
        reverse=True,
    )

    overall_rank = sum(1 for sc in all_scores if sc > score) + 1
    category_rank = sum(1 for sc in cat_scores if sc > score) + 1
    category_total = len(cat_scores)
    percentile = round((1 - (overall_rank - 1) / max(len(all_scores), 1)) * 100, 1) if all_scores else None

    return {
        "overall_rank": overall_rank,
        "category_rank": category_rank,
        "category": cat,
        "category_total": category_total,
        "percentile": percentile,
    }


@router.get("/profiles/{profile_id}/feedback")
async def get_profile_feedback(profile_id: str):
    """Get aggregated feedback from agents who used this tool."""
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Mock structure — to be populated by real feedback later
    return {
        "profile_id": profile_id,
        "total_feedback": 0,
        "success_rate": None,
        "avg_latency_ms": None,
        "recent": [],
    }


@router.post("/profiles/{profile_id}/claim")
async def claim_profile(profile_id: str, request: Request):
    """Claim ownership of a tool by verifying you control its GitHub repo.

    Send {"github_username": "your-username"} and we'll check if the profile's
    github_url belongs to that user/org. If matched, you get owner access.
    """
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    body = await request.json()
    github_username = body.get("github_username", "").strip().lower()

    if not github_username:
        raise HTTPException(status_code=400, detail="github_username required")

    # Check if profile has a GitHub URL
    github_url = (profile.get("github_url") or "").lower()
    if not github_url:
        raise HTTPException(status_code=400, detail="This profile has no GitHub URL to verify against")

    # Simple verification: check if the username appears in the GitHub URL
    # e.g., github.com/username/repo or github.com/org/repo
    if f"github.com/{github_username}/" in github_url or f"github.com/{github_username}" == github_url.rstrip("/"):
        profile["claimed_by"] = github_username
        profile["claimed_at"] = datetime.now(timezone.utc).isoformat()
        profile["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_profiles()
        return {
            "claimed": True,
            "profile_id": profile_id,
            "claimed_by": github_username,
            "message": "Ownership verified. You can now rescan and manage this profile."
        }

    raise HTTPException(
        status_code=403,
        detail=f"GitHub username '{github_username}' does not match the profile's GitHub URL. "
               f"The URL must contain github.com/{github_username}/..."
    )


@router.get("/profiles/{profile_id}/claim")
async def get_claim_status(profile_id: str):
    """Check if a profile has been claimed."""
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "profile_id": profile_id,
        "claimed": bool(profile.get("claimed_by")),
        "claimed_by": profile.get("claimed_by"),
        "claimed_at": profile.get("claimed_at"),
    }


@router.post("/profiles/{profile_id}/rate")
async def rate_tool(profile_id: str, request: Request):
    """Submit a community rating (1-5 stars) for a tool."""
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    body = await request.json()
    rating = body.get("rating", 0)
    review = body.get("review", "")

    if not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    # Store rating
    if "community_ratings" not in profile:
        profile["community_ratings"] = []

    profile["community_ratings"].append({
        "rating": rating,
        "review": review[:500],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Compute average
    ratings = [r["rating"] for r in profile["community_ratings"]]
    avg = sum(ratings) / len(ratings)
    profile["community_avg_rating"] = round(avg, 1)
    profile["community_rating_count"] = len(ratings)
    _save_profiles()

    return {
        "submitted": True,
        "avg_rating": profile["community_avg_rating"],
        "total_ratings": profile["community_rating_count"],
    }


@router.get("/profiles/{profile_id}/ratings")
async def get_ratings(profile_id: str):
    """Get community ratings for a tool."""
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    ratings = profile.get("community_ratings", [])
    avg = profile.get("community_avg_rating", 0)

    return {
        "profile_id": profile_id,
        "avg_rating": avg,
        "total_ratings": len(ratings),
        "ratings": ratings[-20:],  # Last 20
    }


@router.get("/profiles/{profile_id}/badge")
async def get_badge(profile_id: str):
    """Return an SVG badge showing the Clarvia Score."""
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    svg = _make_badge_svg(profile.get("clarvia_score"))
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Content-Type": "image/svg+xml",
        },
    )
