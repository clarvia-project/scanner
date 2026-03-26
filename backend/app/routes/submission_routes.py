"""Submission API — Tool maker self-service submission and badge endpoints.

Endpoints:
  POST /v1/submit        — Submit a tool URL for scanning and indexing
  GET  /v1/badge/{id}    — Clarvia score badge (SVG, cached 24h)
  GET  /v1/submissions/{id} — Check submission status
"""

import json
import logging
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field, HttpUrl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["submissions"])

# ---------------------------------------------------------------------------
# Data persistence
# ---------------------------------------------------------------------------

_DATA_CANDIDATES = [
    Path("/app/data/submissions.jsonl"),
    Path(__file__).resolve().parents[3] / "data" / "submissions.jsonl",
]

_PREBUILT_CANDIDATES = [
    Path("/app/data/prebuilt-scans.json"),
    Path(__file__).resolve().parents[3] / "data" / "prebuilt-scans.json",
]


def _submissions_path() -> Path:
    for p in _DATA_CANDIDATES:
        if p.parent.exists():
            return p
    return _DATA_CANDIDATES[0]


def _prebuilt_path() -> Path | None:
    for p in _PREBUILT_CANDIDATES:
        if p.exists():
            return p
    return None


def _generate_submission_id() -> str:
    """Generate a unique submission ID."""
    chars = string.ascii_lowercase + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(12))
    return f"sub_{random_part}"


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class SubmitRequest(BaseModel):
    url: str = Field(..., description="URL of the tool to submit (GitHub repo, npm package, API docs, etc.)")
    name: Optional[str] = Field(None, description="Tool name (auto-detected if not provided)")
    description: Optional[str] = Field(None, description="Brief description")
    contact_email: Optional[str] = Field(None, description="Contact email for updates")


class SubmitResponse(BaseModel):
    submission_id: str
    status: str
    estimated_time: str
    message: str
    badge_preview: str


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

_BLOCKED_DOMAINS = {
    "localhost", "127.0.0.1", "0.0.0.0", "example.com", "example.org",
}


def _validate_url(url: str) -> tuple[bool, str]:
    """Validate submission URL. Returns (is_valid, error_message)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    if parsed.scheme not in ("http", "https"):
        return False, "URL must use http or https"

    if not parsed.netloc:
        return False, "URL must include a domain"

    hostname = (parsed.hostname or "").lower()
    if hostname in _BLOCKED_DOMAINS:
        return False, f"Domain {hostname} is not allowed"

    # Block private IP ranges (IPv4)
    private_prefixes = (
        "10.", "172.16.", "172.17.", "172.18.", "172.19.",
        "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
        "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
        "172.30.", "172.31.", "192.168.", "169.254.",
    )
    for prefix in private_prefixes:
        if hostname.startswith(prefix):
            return False, "Private IP addresses are not allowed"

    # Block IPv6 loopback
    if hostname in ("::1", "[::1]"):
        return False, "Loopback addresses are not allowed"

    return True, ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/submit")
async def submit_tool(req: SubmitRequest) -> SubmitResponse:
    """Submit a tool for Clarvia scanning and indexing.

    The tool URL will be validated and queued for scanning. Once scanned,
    it will be auto-indexed in the Clarvia catalog if it scores > 0.

    Returns a submission ID that can be used to check status.
    """
    # Validate URL
    is_valid, error = _validate_url(req.url)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Generate submission ID
    sub_id = _generate_submission_id()

    # Build submission record
    submission = {
        "submission_id": sub_id,
        "url": req.url.strip().rstrip("/"),
        "name": req.name,
        "description": req.description,
        "contact_email": req.contact_email,
        "status": "queued",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    # Persist to JSONL
    path = _submissions_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(submission, default=str) + "\n")

    logger.info("New submission: %s -> %s", sub_id, req.url)

    return SubmitResponse(
        submission_id=sub_id,
        status="queued",
        estimated_time="5-30 minutes",
        message="Tool submitted successfully. It will be scanned and indexed automatically.",
        badge_preview=f"https://clarvia-api.onrender.com/v1/badge/{sub_id}",
    )


@router.get("/submissions/{submission_id}")
async def get_submission_status(submission_id: str):
    """Check the status of a tool submission."""
    path = _submissions_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Submission not found")

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("submission_id") == submission_id:
                    result: dict[str, Any] = {
                        "submission_id": entry["submission_id"],
                        "url": entry["url"],
                        "status": entry.get("status", "unknown"),
                        "submitted_at": entry.get("submitted_at"),
                    }
                    if entry.get("scan_id"):
                        result["scan_id"] = entry["scan_id"]
                        result["clarvia_score"] = entry.get("clarvia_score")
                        result["badge"] = entry.get("badge")
                    if entry.get("error"):
                        result["error"] = entry["error"]
                    if entry.get("processed_at"):
                        result["processed_at"] = entry["processed_at"]
                    return result
            except json.JSONDecodeError:
                continue

    raise HTTPException(status_code=404, detail="Submission not found")


# ---------------------------------------------------------------------------
# Clarvia Badge endpoint (/v1/badge/{identifier})
# ---------------------------------------------------------------------------

_SVG_BADGE = """\
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" \
width="{total_w}" height="20" role="img" aria-label="{label}: {value}">
  <title>{label}: {value}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_w}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>
    <rect width="{total_w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" \
font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="11">
    <text aria-hidden="true" x="{label_x}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_x}" y="14">{label}</text>
    <text aria-hidden="true" x="{value_x}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{value_x}" y="14">{value}</text>
  </g>
</svg>"""


def _score_to_color(score: float | None) -> str:
    """Map score to badge color."""
    if score is None:
        return "#9f9f9f"  # gray
    if score >= 75:
        return "#4c1"  # bright green
    if score >= 50:
        return "#97ca00"  # green
    if score >= 30:
        return "#dfb317"  # yellow
    return "#e05d44"  # red


def _make_badge(label: str, value: str, color: str) -> str:
    """Generate shields.io-style SVG badge."""
    label_w = len(label) * 6.5 + 12
    value_w = len(value) * 6.5 + 12
    label_w = max(label_w, 40)
    value_w = max(value_w, 30)
    total_w = label_w + value_w

    return _SVG_BADGE.format(
        total_w=total_w,
        label_w=label_w,
        value_w=value_w,
        label_x=label_w / 2,
        value_x=label_w + value_w / 2,
        label=label,
        value=value,
        color=color,
    )


def _find_service_by_id(identifier: str) -> dict | None:
    """Look up a service by scan_id, submission_id, or name."""
    # Try prebuilt scans
    path = _prebuilt_path()
    if path:
        try:
            with open(path) as f:
                services = json.load(f)
            for svc in services:
                if svc.get("scan_id") == identifier:
                    return svc
            # Name match fallback
            for svc in services:
                if svc.get("service_name", "").lower() == identifier.lower():
                    return svc
        except Exception:
            pass

    # Try in-memory cache
    try:
        from ..scanner import get_cached_scan
        scan = get_cached_scan(identifier)
        if scan:
            return {
                "scan_id": scan.scan_id,
                "service_name": scan.service_name,
                "clarvia_score": scan.clarvia_score,
            }
    except Exception:
        pass

    return None


@router.get("/badge/{identifier:path}")
async def clarvia_badge(
    identifier: str,
    style: str = Query("flat", pattern="^(flat|flat-square)$"),
):
    """Generate a Clarvia score badge (SVG).

    The identifier can be a scan_id, service name, or submission ID.
    Badge is cached for 24 hours.

    Embed in README:
        ![Clarvia Score](https://clarvia-api.onrender.com/v1/badge/{scan_id})
    """
    service = _find_service_by_id(identifier)

    if service is None:
        svg = _make_badge("Clarvia", "?", _score_to_color(None))
    else:
        score = service.get("clarvia_score", 0)
        # Display as X.X/10 format for cleaner badges
        score_10 = round(score / 10, 1)
        svg = _make_badge("Clarvia", f"{score_10}/10", _score_to_color(score))

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=86400, s-maxage=86400",
            "Vary": "Accept",
        },
    )
