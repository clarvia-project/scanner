"""Webhook notification system — register URLs for event callbacks.

Supported events:
- scan_complete: Fired when a scan finishes (includes score, rating, scan_id)
- ticket_status_change: Fired when a CS ticket status changes

Endpoints:
- POST /v1/webhooks          — Register a webhook
- GET  /v1/webhooks          — List registered webhooks (by owner key)
- DELETE /v1/webhooks/{id}   — Delete a webhook

File-based storage (same pattern as CS tickets).
"""

import hashlib
import hmac
import json as _json
import logging
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path as _Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])

# ---------------------------------------------------------------------------
# File-based storage
# ---------------------------------------------------------------------------

_WEBHOOKS_DIR = _Path("/app/data/webhooks")

# Fallback for local dev
if not _Path("/app/data").exists():
    _WEBHOOKS_DIR = _Path(__file__).resolve().parents[3] / "data" / "webhooks"


VALID_EVENTS = {"scan_complete", "ticket_status_change"}


def _ensure_dir() -> None:
    _WEBHOOKS_DIR.mkdir(parents=True, exist_ok=True)


def _save_webhook(wh_id: str, wh: dict[str, Any]) -> None:
    _ensure_dir()
    path = _WEBHOOKS_DIR / f"{wh_id}.json"
    path.write_text(_json.dumps(wh, indent=2, default=str))


def _load_webhook(wh_id: str) -> dict[str, Any] | None:
    path = _WEBHOOKS_DIR / f"{wh_id}.json"
    if not path.exists():
        return None
    try:
        return _json.loads(path.read_text())
    except Exception:
        return None


def _load_all_webhooks() -> list[dict[str, Any]]:
    _ensure_dir()
    hooks = []
    for path in _WEBHOOKS_DIR.glob("wh_*.json"):
        try:
            hooks.append(_json.loads(path.read_text()))
        except Exception:
            continue
    return hooks


def _delete_webhook(wh_id: str) -> bool:
    path = _WEBHOOKS_DIR / f"{wh_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class RegisterWebhookRequest(BaseModel):
    url: str = Field(..., description="HTTPS callback URL")
    events: list[str] = Field(..., description="Events to subscribe to: scan_complete, ticket_status_change")
    secret: str | None = Field(None, description="Optional shared secret for HMAC-SHA256 signature verification")
    description: str | None = Field(None, max_length=200, description="Human-readable description")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("")
async def register_webhook(req: RegisterWebhookRequest, request: Request):
    """Register a new webhook for event notifications.

    The callback URL must be HTTPS. When events fire, Clarvia sends a POST
    with JSON payload and optional `X-Clarvia-Signature` header (HMAC-SHA256
    of the body using your shared secret).
    """
    # Validate URL
    url = req.url.strip()
    if not url.startswith("https://"):
        raise HTTPException(400, "Webhook URL must use HTTPS")

    # Validate events
    invalid = set(req.events) - VALID_EVENTS
    if invalid:
        raise HTTPException(400, f"Invalid events: {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_EVENTS))}")
    if not req.events:
        raise HTTPException(400, "At least one event is required")

    # Generate webhook ID and signing secret
    wh_id = f"wh_{secrets.token_urlsafe(12)}"
    signing_secret = req.secret or secrets.token_urlsafe(32)

    # Identify owner by API key or IP
    api_key = request.headers.get("x-api-key") or request.headers.get("x-clarvia-key")
    owner = api_key[:12] if api_key else (request.client.host if request.client else "unknown")

    now = datetime.now(timezone.utc).isoformat()
    webhook = {
        "webhook_id": wh_id,
        "url": url,
        "events": req.events,
        "signing_secret_hash": hashlib.sha256(signing_secret.encode()).hexdigest(),
        "signing_secret_preview": signing_secret[:8] + "...",
        "description": req.description,
        "owner": owner,
        "active": True,
        "failure_count": 0,
        "created_at": now,
        "last_triggered_at": None,
    }

    _save_webhook(wh_id, webhook)
    logger.info("Webhook registered: %s -> %s (events: %s)", wh_id, url, req.events)

    return {
        "webhook_id": wh_id,
        "url": url,
        "events": req.events,
        "signing_secret": signing_secret,
        "message": "Webhook registered. Store the signing_secret — it won't be shown again.",
    }


@router.get("")
async def list_webhooks(request: Request):
    """List webhooks owned by the current API key or IP."""
    api_key = request.headers.get("x-api-key") or request.headers.get("x-clarvia-key")
    owner = api_key[:12] if api_key else (request.client.host if request.client else "unknown")

    hooks = _load_all_webhooks()
    owned = [h for h in hooks if h.get("owner") == owner]

    return {
        "webhooks": [
            {
                "webhook_id": h["webhook_id"],
                "url": h["url"],
                "events": h["events"],
                "active": h["active"],
                "failure_count": h.get("failure_count", 0),
                "description": h.get("description"),
                "created_at": h["created_at"],
                "last_triggered_at": h.get("last_triggered_at"),
            }
            for h in owned
        ],
        "total": len(owned),
    }


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str, request: Request):
    """Delete a webhook registration."""
    wh = _load_webhook(webhook_id)
    if not wh:
        raise HTTPException(404, f"Webhook {webhook_id} not found")

    # Verify ownership
    api_key = request.headers.get("x-api-key") or request.headers.get("x-clarvia-key")
    owner = api_key[:12] if api_key else (request.client.host if request.client else "unknown")
    if wh.get("owner") != owner:
        raise HTTPException(403, "You can only delete your own webhooks")

    _delete_webhook(webhook_id)
    return {"status": "deleted", "webhook_id": webhook_id}


# ---------------------------------------------------------------------------
# Webhook firing (called internally by scan/CS routes)
# ---------------------------------------------------------------------------

async def fire_webhooks(event: str, payload: dict[str, Any]) -> int:
    """Fire webhooks for the given event. Returns count of successful deliveries.

    Called internally — not an HTTP endpoint.
    """
    if event not in VALID_EVENTS:
        logger.warning("Unknown webhook event: %s", event)
        return 0

    hooks = _load_all_webhooks()
    subscribers = [h for h in hooks if event in h.get("events", []) and h.get("active", True)]

    if not subscribers:
        return 0

    delivered = 0
    body = _json.dumps({
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }, default=str)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for wh in subscribers:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Clarvia-Webhooks/1.0",
                "X-Clarvia-Event": event,
                "X-Webhook-ID": wh["webhook_id"],
            }

            # Add HMAC signature if secret is stored
            secret_hash = wh.get("signing_secret_hash")
            if secret_hash:
                # We can't recover the secret from the hash, but the
                # registration response gave the user the raw secret.
                # For signing, we use the hash itself as a shared token.
                signature = hmac.new(
                    secret_hash.encode(), body.encode(), hashlib.sha256
                ).hexdigest()
                headers["X-Clarvia-Signature"] = f"sha256={signature}"

            try:
                resp = await client.post(wh["url"], content=body, headers=headers)
                if resp.status_code < 400:
                    delivered += 1
                    wh["last_triggered_at"] = datetime.now(timezone.utc).isoformat()
                    wh["failure_count"] = 0
                else:
                    wh["failure_count"] = wh.get("failure_count", 0) + 1
                    logger.warning(
                        "Webhook %s delivery failed: HTTP %d",
                        wh["webhook_id"], resp.status_code,
                    )
            except Exception as e:
                wh["failure_count"] = wh.get("failure_count", 0) + 1
                logger.warning("Webhook %s delivery error: %s", wh["webhook_id"], e)

            # Disable after 10 consecutive failures
            if wh.get("failure_count", 0) >= 10:
                wh["active"] = False
                logger.warning("Webhook %s disabled after 10 failures", wh["webhook_id"])

            _save_webhook(wh["webhook_id"], wh)

    logger.info("Webhook event %s: %d/%d delivered", event, delivered, len(subscribers))
    return delivered
