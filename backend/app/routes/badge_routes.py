"""AEO Badge SVG generator.

Endpoint: GET /api/badge/{identifier}
Returns: SVG image (Content-Type: image/svg+xml)

The identifier can be:
  - A scan_id (e.g. scn_bd5feadb71b9)
  - A service name (e.g. openai, stripe — case-insensitive)
  - A URL-encoded service URL (e.g. https%3A%2F%2Fapi.openai.com)

Query params:
  - style: flat (default) | flat-square
  - label: custom left-side label (default: "AEO")
"""

import json
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Query
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["badge"])

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

_prebuilt_cache: list[dict] | None = None


def _load_prebuilt() -> list[dict]:
    """Load prebuilt scans from disk (cached after first call)."""
    global _prebuilt_cache
    if _prebuilt_cache is not None:
        return _prebuilt_cache

    candidates = [
        Path("/app/data/prebuilt-scans.json"),
        Path(__file__).resolve().parents[3] / "data" / "prebuilt-scans.json",
        Path(__file__).resolve().parents[2] / "data" / "prebuilt-scans.json",
    ]
    for p in candidates:
        if p.exists():
            with open(p) as f:
                _prebuilt_cache = json.load(f)
            logger.info("Badge: loaded %d prebuilt scans from %s", len(_prebuilt_cache), p)
            return _prebuilt_cache

    logger.warning("Badge: prebuilt-scans.json not found")
    _prebuilt_cache = []
    return _prebuilt_cache


def _find_service(identifier: str) -> Optional[dict]:
    """Resolve identifier to a scan entry.

    Priority:
      1. Exact scan_id match
      2. Case-insensitive service_name match
      3. URL match (decoded)
      4. In-memory cache from scanner
    """
    from ..scanner import get_cached_scan

    # 1. Try in-memory cache by scan_id
    scan = get_cached_scan(identifier)
    if scan:
        return {
            "scan_id": scan.scan_id,
            "service_name": scan.service_name,
            "clarvia_score": scan.clarvia_score,
            "rating": scan.rating,
        }

    # 2-3. Try prebuilt scans
    prebuilt = _load_prebuilt()
    decoded_id = unquote(identifier)
    lower_id = decoded_id.lower()

    for entry in prebuilt:
        if entry.get("scan_id") == identifier:
            return entry

    for entry in prebuilt:
        if entry.get("service_name", "").lower() == lower_id:
            return entry

    # Partial service name match (e.g. "openai" matches "OpenAI")
    for entry in prebuilt:
        name = entry.get("service_name", "").lower()
        if lower_id in name or name in lower_id:
            return entry

    # URL match
    for entry in prebuilt:
        entry_url = entry.get("url", "").lower().rstrip("/")
        if decoded_id.lower().rstrip("/") == entry_url:
            return entry
        # Match domain portion
        if decoded_id.lower() in entry_url:
            return entry

    return None


# ---------------------------------------------------------------------------
# SVG templates
# ---------------------------------------------------------------------------

_SVG_FLAT = """\
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

_SVG_FLAT_SQUARE = """\
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" \
width="{total_w}" height="20" role="img" aria-label="{label}: {value}">
  <title>{label}: {value}</title>
  <g shape-rendering="crispEdges">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>
  </g>
  <g fill="#fff" text-anchor="middle" \
font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="11">
    <text x="{label_x}" y="14">{label}</text>
    <text x="{value_x}" y="14">{value}</text>
  </g>
</svg>"""


def _score_color(score: int | None) -> str:
    """Return badge color based on score thresholds."""
    if score is None:
        return "#9f9f9f"  # gray for unknown
    if score >= 70:
        return "#4c1"  # green — shields.io standard
    if score >= 40:
        return "#dfb317"  # yellow
    return "#e05d44"  # red


def _generate_badge(
    label: str,
    value: str,
    color: str,
    style: str = "flat",
) -> str:
    """Generate shields.io-style SVG badge."""
    # Character width estimation (Verdana 11px)
    label_w = len(label) * 6.5 + 10
    value_w = len(value) * 6.5 + 10

    # Minimum widths
    label_w = max(label_w, 30)
    value_w = max(value_w, 24)

    total_w = label_w + value_w
    label_x = label_w / 2
    value_x = label_w + value_w / 2

    template = _SVG_FLAT_SQUARE if style == "flat-square" else _SVG_FLAT

    return template.format(
        total_w=total_w,
        label_w=label_w,
        value_w=value_w,
        label_x=label_x,
        value_x=value_x,
        label=label,
        value=value,
        color=color,
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/api/badge/{identifier:path}")
async def badge_svg(
    identifier: str,
    style: str = Query("flat", pattern="^(flat|flat-square)$"),
    label: str = Query("AEO", max_length=30),
):
    """Generate a shields.io-style SVG badge for a service's AEO score.

    The identifier can be a scan_id, service name, or URL.
    """
    service = _find_service(identifier)

    if service is None:
        svg = _generate_badge(label, "?", _score_color(None), style)
    else:
        score = service.get("clarvia_score", 0)
        svg = _generate_badge(label, str(score), _score_color(score), style)

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=3600, s-maxage=3600",
            "Vary": "Accept",
        },
    )
