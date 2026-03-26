"""Team API — basic multi-user organization support."""
import secrets
import string
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1", tags=["teams"])
logger = logging.getLogger(__name__)

_teams: dict[str, dict] = {}

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=1000)

class TeamMember(BaseModel):
    email: str
    role: str = "member"  # "owner", "admin", "member"

def _gen_team_id():
    chars = string.ascii_lowercase + string.digits
    return "team_" + "".join(secrets.choice(chars) for _ in range(12))

def _gen_api_key():
    return "sk_team_" + secrets.token_hex(24)

@router.post("/teams")
async def create_team(req: TeamCreate):
    """Create a new team with an API key."""
    team_id = _gen_team_id()
    api_key = _gen_api_key()
    now = datetime.now(timezone.utc).isoformat()

    team = {
        "team_id": team_id,
        "name": req.name,
        "description": req.description,
        "api_key": api_key,
        "members": [],
        "watchlist": [],  # scan_ids to monitor
        "approved_tools": [],  # scan_ids of approved tools
        "blocked_tools": [],  # scan_ids of blocked tools
        "settings": {
            "min_score_threshold": 50,
            "auto_block_below": 30,
            "scan_visibility": "team",  # "team" or "private"
        },
        "created_at": now,
    }
    _teams[team_id] = team

    return {
        "team_id": team_id,
        "api_key": api_key,
        "name": req.name,
        "message": "Team created. Use the API key for authenticated requests."
    }

@router.get("/teams/{team_id}")
async def get_team(team_id: str, request: Request):
    """Get team details."""
    team = _teams.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Return without exposing full API key
    return {
        "team_id": team["team_id"],
        "name": team["name"],
        "description": team["description"],
        "members": team["members"],
        "watchlist_count": len(team["watchlist"]),
        "approved_count": len(team["approved_tools"]),
        "blocked_count": len(team["blocked_tools"]),
        "settings": team["settings"],
    }

@router.post("/teams/{team_id}/watchlist")
async def add_to_watchlist(team_id: str, request: Request):
    """Add tools to team watchlist for monitoring."""
    team = _teams.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    body = await request.json()
    scan_ids = body.get("scan_ids", [])

    for sid in scan_ids[:50]:
        if sid not in team["watchlist"]:
            team["watchlist"].append(sid)

    return {"watchlist_count": len(team["watchlist"]), "added": len(scan_ids)}

@router.post("/teams/{team_id}/approve")
async def approve_tool(team_id: str, request: Request):
    """Add tools to team's approved list."""
    team = _teams.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    body = await request.json()
    scan_ids = body.get("scan_ids", [])

    for sid in scan_ids[:50]:
        if sid not in team["approved_tools"]:
            team["approved_tools"].append(sid)
        # Remove from blocked if present
        if sid in team["blocked_tools"]:
            team["blocked_tools"].remove(sid)

    return {"approved_count": len(team["approved_tools"])}

@router.post("/teams/{team_id}/block")
async def block_tool(team_id: str, request: Request):
    """Add tools to team's blocked list (security/compliance deny-list)."""
    team = _teams.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    body = await request.json()
    scan_ids = body.get("scan_ids", [])
    reason = body.get("reason", "")

    for sid in scan_ids[:50]:
        if sid not in team["blocked_tools"]:
            team["blocked_tools"].append(sid)
        if sid in team["approved_tools"]:
            team["approved_tools"].remove(sid)

    return {"blocked_count": len(team["blocked_tools"])}

@router.get("/teams/{team_id}/check/{scan_id}")
async def check_tool_status(team_id: str, scan_id: str):
    """Check if a tool is approved, blocked, or unreviewed for this team."""
    team = _teams.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if scan_id in team["blocked_tools"]:
        return {"scan_id": scan_id, "status": "blocked", "allowed": False}
    elif scan_id in team["approved_tools"]:
        return {"scan_id": scan_id, "status": "approved", "allowed": True}
    else:
        # Check against auto-block threshold
        from .index_routes import _by_scan_id, _ensure_loaded
        _ensure_loaded()
        svc = _by_scan_id.get(scan_id)
        if svc and svc["clarvia_score"] < team["settings"]["auto_block_below"]:
            return {"scan_id": scan_id, "status": "auto_blocked", "allowed": False,
                    "reason": f"Score {svc['clarvia_score']} below team threshold {team['settings']['auto_block_below']}"}
        return {"scan_id": scan_id, "status": "unreviewed", "allowed": True}
