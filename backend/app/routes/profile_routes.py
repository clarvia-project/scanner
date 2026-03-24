"""Profile API — Layer 2: MCP service registration and discovery."""

import json
import logging
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

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
    path = _data_path()
    if path.exists():
        try:
            with open(path, "r") as f:
                data = json.load(f)
            _profiles = {p["profile_id"]: p for p in data}
            logger.info("Loaded %d profiles from %s", len(_profiles), path)
        except Exception as e:
            logger.error("Failed to load profiles: %s", e)
    else:
        logger.info("No profiles file found, starting empty")


def _save_profiles() -> None:
    path = _data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w") as f:
            json.dump(list(_profiles.values()), f, indent=2, default=str)
    except Exception as e:
        logger.error("Failed to save profiles: %s", e)


def _gen_id() -> str:
    chars = string.ascii_lowercase + string.digits
    return "prf_" + "".join(secrets.choice(chars) for _ in range(12))


def get_all_profiles() -> list[dict[str, Any]]:
    """Public accessor for index integration."""
    if not _profiles:
        _load_profiles()
    return list(_profiles.values())


# Load on module import
_load_profiles()


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
    url: str = Field(..., min_length=1)
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
    github_url: str | None = None
    mcp_config: MCPConfig | None = None
    contact_email: str | None = None
    tags: list[str] = Field(default_factory=list)


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    url: str | None = None
    description: str | None = None
    category: str | None = None
    service_type: str | None = None
    type_config: dict[str, Any] | None = None
    github_url: str | None = None
    mcp_config: MCPConfig | None = None
    contact_email: str | None = None
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
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/profiles")
async def create_profile(req: ProfileCreateRequest):
    """Register a new service. No API key required — open registration."""
    # Validate service_type
    stype = req.service_type or "general"
    if stype not in SERVICE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid service_type. Must be one of: {', '.join(SERVICE_TYPES)}")

    # Check for duplicate URL
    for p in _profiles.values():
        if p["url"] == req.url:
            raise HTTPException(
                status_code=409,
                detail=f"Profile already exists for URL: {req.url}",
            )

    profile_id = _gen_id()
    now = datetime.now(timezone.utc).isoformat()

    profile = {
        "profile_id": profile_id,
        "name": req.name,
        "url": req.url,
        "description": req.description,
        "category": req.category,
        "service_type": stype,
        "type_config": req.type_config,
        "github_url": req.github_url,
        "mcp_config": req.mcp_config.model_dump() if req.mcp_config else None,
        "contact_email": req.contact_email,
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
    _schedule_agents_json_check(profile_id, req.url)

    # Auto-trigger scan (non-blocking)
    _schedule_auto_scan(profile_id)

    return {
        "profile_id": profile_id,
        "name": req.name,
        "url": req.url,
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
    """List registered profiles with optional filters."""
    results = list(_profiles.values())

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
    """Get full profile details."""
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/profiles/{profile_id}")
async def update_profile(profile_id: str, req: ProfileUpdateRequest, _key: ApiKeyDep):
    """Update an existing profile. Requires API key."""
    profile = _profiles.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    updates = req.model_dump(exclude_unset=True)
    if "mcp_config" in updates and updates["mcp_config"] is not None:
        updates["mcp_config"] = updates["mcp_config"].model_dump() if hasattr(updates["mcp_config"], "model_dump") else updates["mcp_config"]

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

        return {
            "profile_id": profile_id,
            "clarvia_score": result.clarvia_score,
            "rating": result.rating,
            "status": "scanned",
            "scan_id": result.scan_id,
        }
    except Exception as e:
        logger.exception("Profile scan failed for %s", profile["url"])
        profile["status"] = "scan_failed"
        _save_profiles()
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {type(e).__name__}: {str(e)[:200]}",
        )


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
