"""Agent CS (Customer Support) system — ticket API for agents to report issues.

Endpoints:
- POST /v1/cs/tickets          — Create a ticket (bug, feature, question, security)
- GET  /v1/cs/tickets          — List tickets (with filters)
- GET  /v1/cs/tickets/{id}     — Get ticket details
- POST /v1/cs/tickets/{id}/reply — Add a reply to a ticket
- PATCH /v1/cs/tickets/{id}    — Update ticket status (admin)
- GET  /admin/cs/overview      — Admin CS dashboard

No auth required for creating tickets (agents need easy access).
Admin endpoints require API key.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import ApiKeyDep

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cs"])

# ---------------------------------------------------------------------------
# In-memory storage (Supabase upgrade later)
# ---------------------------------------------------------------------------
_tickets: dict[str, dict[str, Any]] = {}
_ticket_counter = 0


def _gen_ticket_id() -> str:
    global _ticket_counter
    _ticket_counter += 1
    return f"CS-{_ticket_counter:04d}"


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class CreateTicketRequest(BaseModel):
    type: str = Field(..., description="Ticket type: bug, feature, question, security")
    title: str = Field(..., max_length=200, description="Short summary")
    description: str = Field(..., max_length=5000, description="Detailed description")
    agent_id: str | None = Field(None, description="Reporting agent identifier")
    service_url: str | None = Field(None, description="Related service URL (if applicable)")
    severity: str = Field("medium", description="low, medium, high, critical")
    metadata: dict[str, Any] | None = Field(None, description="Extra context (error logs, stack traces, etc.)")


class ReplyRequest(BaseModel):
    message: str = Field(..., max_length=5000)
    author: str = Field("system", description="Reply author (agent_id or 'admin')")


class UpdateTicketRequest(BaseModel):
    status: str | None = Field(None, description="open, in_progress, resolved, closed, wont_fix")
    priority: str | None = Field(None, description="low, medium, high, critical")
    assignee: str | None = Field(None, description="Assigned team member")
    tags: list[str] | None = Field(None)


# ---------------------------------------------------------------------------
# Public endpoints (no auth — agents need easy access)
# ---------------------------------------------------------------------------

@router.post("/v1/cs/tickets")
async def create_ticket(req: CreateTicketRequest):
    """Create a new CS ticket. Agents can report bugs, request features, ask questions, or flag security issues."""
    if req.type not in ("bug", "feature", "question", "security"):
        raise HTTPException(400, "type must be: bug, feature, question, or security")
    if req.severity not in ("low", "medium", "high", "critical"):
        raise HTTPException(400, "severity must be: low, medium, high, or critical")

    ticket_id = _gen_ticket_id()
    now = datetime.now(timezone.utc).isoformat()

    ticket = {
        "ticket_id": ticket_id,
        "type": req.type,
        "title": req.title,
        "description": req.description,
        "agent_id": req.agent_id,
        "service_url": req.service_url,
        "severity": req.severity,
        "status": "open",
        "priority": "high" if req.severity == "critical" or req.type == "security" else req.severity,
        "metadata": req.metadata or {},
        "tags": [req.type],
        "assignee": None,
        "replies": [],
        "created_at": now,
        "updated_at": now,
    }

    _tickets[ticket_id] = ticket

    # Auto-escalate security issues
    if req.type == "security":
        ticket["tags"].append("auto-escalated")
        ticket["priority"] = "critical"
        logger.warning("Security ticket created: %s — %s", ticket_id, req.title)

    logger.info("CS ticket created: %s [%s] %s", ticket_id, req.type, req.title)

    return {
        "ticket_id": ticket_id,
        "status": "open",
        "message": f"Ticket {ticket_id} created. We'll address this as soon as possible.",
        "track_url": f"https://clarvia.art/cs/{ticket_id}",
    }


@router.get("/v1/cs/tickets")
async def list_tickets(
    type: str | None = Query(None),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    agent_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List CS tickets with optional filters."""
    tickets = list(_tickets.values())

    if type:
        tickets = [t for t in tickets if t["type"] == type]
    if status:
        tickets = [t for t in tickets if t["status"] == status]
    if severity:
        tickets = [t for t in tickets if t["severity"] == severity]
    if agent_id:
        tickets = [t for t in tickets if t.get("agent_id") == agent_id]

    tickets = sorted(tickets, key=lambda t: t["created_at"], reverse=True)
    total = len(tickets)
    page = tickets[offset:offset + limit]

    # Strip long descriptions for list view
    summary = [
        {
            "ticket_id": t["ticket_id"],
            "type": t["type"],
            "title": t["title"],
            "status": t["status"],
            "severity": t["severity"],
            "priority": t["priority"],
            "agent_id": t.get("agent_id"),
            "replies_count": len(t["replies"]),
            "created_at": t["created_at"],
            "updated_at": t["updated_at"],
        }
        for t in page
    ]

    return {"total": total, "offset": offset, "limit": limit, "tickets": summary}


@router.get("/v1/cs/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Get full ticket details including replies."""
    ticket = _tickets.get(ticket_id)
    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} not found")
    return ticket


@router.post("/v1/cs/tickets/{ticket_id}/reply")
async def reply_to_ticket(ticket_id: str, req: ReplyRequest):
    """Add a reply to a ticket. Both agents and admins can reply."""
    ticket = _tickets.get(ticket_id)
    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} not found")

    reply = {
        "author": req.author,
        "message": req.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    ticket["replies"].append(reply)
    ticket["updated_at"] = reply["created_at"]

    # Auto-reopen if agent replies to resolved ticket
    if ticket["status"] in ("resolved", "closed") and req.author != "admin":
        ticket["status"] = "open"
        ticket["tags"].append("reopened")

    return {"status": "reply_added", "replies_count": len(ticket["replies"])}


# ---------------------------------------------------------------------------
# Admin endpoints (API key required)
# ---------------------------------------------------------------------------

@router.patch("/admin/cs/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, req: UpdateTicketRequest, _key: ApiKeyDep):
    """Update ticket status, priority, assignee, or tags (admin only)."""
    ticket = _tickets.get(ticket_id)
    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} not found")

    if req.status:
        if req.status not in ("open", "in_progress", "resolved", "closed", "wont_fix"):
            raise HTTPException(400, "Invalid status")
        ticket["status"] = req.status
    if req.priority:
        ticket["priority"] = req.priority
    if req.assignee is not None:
        ticket["assignee"] = req.assignee
    if req.tags is not None:
        ticket["tags"] = req.tags

    ticket["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {"status": "updated", "ticket": ticket}


@router.get("/admin/cs/overview")
async def admin_cs_overview(_key: ApiKeyDep):
    """CS dashboard overview for admin."""
    tickets = list(_tickets.values())

    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}

    for t in tickets:
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1
        by_type[t["type"]] = by_type.get(t["type"], 0) + 1
        by_severity[t["severity"]] = by_severity.get(t["severity"], 0) + 1

    open_tickets = [t for t in tickets if t["status"] in ("open", "in_progress")]
    open_tickets.sort(key=lambda t: (
        {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(t["priority"], 4),
        t["created_at"],
    ))

    return {
        "total": len(tickets),
        "by_status": by_status,
        "by_type": by_type,
        "by_severity": by_severity,
        "open_count": len(open_tickets),
        "open_tickets": [
            {
                "ticket_id": t["ticket_id"],
                "type": t["type"],
                "title": t["title"],
                "severity": t["severity"],
                "priority": t["priority"],
                "agent_id": t.get("agent_id"),
                "created_at": t["created_at"],
            }
            for t in open_tickets[:20]
        ],
    }
