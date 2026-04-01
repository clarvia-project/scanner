"""AEO Score Badge SVG generator.

Endpoints:
  GET /api/badge/{identifier}         -> SVG badge image (default) or JSON
  GET /api/badge/{identifier}.svg     -> SVG badge image (alias)
  GET /api/badge/{identifier}/markdown -> Markdown embed snippet
  GET /api/badge/{identifier}/json    -> JSON score data (shields.io endpoint schema)

The identifier can be:
  - A scan_id (e.g. scn_bd5feadb71b9)
  - A service name (e.g. openai, stripe -- case-insensitive)
  - A URL-encoded service URL (e.g. https%3A%2F%2Fapi.openai.com)

Query params:
  - style: flat (default) | flat-square | for-the-badge
  - label: custom left-side label (default: "Clarvia")
  - compact: if true, show just the score number (default: false -> "AEO 85/100")
  - format: svg (default) | json
"""

import json
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, quote

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["badge"])

# Base URL for badge embedding
_BADGE_BASE_URL = "https://clarvia.art"
_SITE_URL = "https://clarvia.art"

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_prebuilt() -> list[dict]:
    """Return prebuilt scans via index_routes (shared, no duplicate load)."""
    from . import index_routes
    index_routes._ensure_loaded()
    return index_routes._services


def _find_service(identifier: str) -> Optional[dict]:
    """Resolve identifier to a scan entry.

    Priority:
      1. Exact scan_id match
      2. Case-insensitive service_name match
      3. URL match (decoded)
      4. In-memory cache from scanner
    """
    from ..scanner import get_cached_scan

    # Strip .svg suffix if present (handles /api/badge/openai.svg)
    clean_id = identifier
    if clean_id.endswith(".svg"):
        clean_id = clean_id[:-4]

    # 1. Try prebuilt scans first (authoritative scores)
    prebuilt = _load_prebuilt()
    decoded_id = unquote(clean_id)
    lower_id = decoded_id.lower()

    for entry in prebuilt:
        if entry.get("scan_id") == clean_id:
            return entry

    # 2. Fall back to in-memory scan cache (live scans)
    scan = get_cached_scan(clean_id)
    if scan:
        return {
            "scan_id": scan.scan_id,
            "service_name": scan.service_name,
            "clarvia_score": scan.clarvia_score,
            "rating": scan.rating,
        }

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
        if decoded_id.lower() in entry_url:
            return entry

    return None


# ---------------------------------------------------------------------------
# Clarvia owl icon (inline SVG path, 14x14)
# ---------------------------------------------------------------------------

# Minimal owl silhouette icon for the badge label area
_OWL_ICON = (
    '<g transform="translate(4,3) scale(0.028)">'
    '<path fill="#fff" d="M256 48C141.1 48 48 141.1 48 256s93.1 208 208 208 '
    "208-93.1 208-208S370.9 48 256 48zm-50 280c-22.1 0-40-17.9-40-40s17.9-40 "
    "40-40 40 17.9 40 40-17.9 40-40 40zm100 0c-22.1 0-40-17.9-40-40s17.9-40 "
    '40-40 40 17.9 40 40-17.9 40-40 40z"/>'
    "</g>"
)

# Width offset added for the icon
_ICON_WIDTH = 18

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
  {icon}
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
  {icon}
  <g fill="#fff" text-anchor="middle" \
font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="11">
    <text x="{label_x}" y="14">{label}</text>
    <text x="{value_x}" y="14">{value}</text>
  </g>
</svg>"""

_SVG_FOR_THE_BADGE = """\
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" \
width="{total_w}" height="28" role="img" aria-label="{label}: {value}">
  <title>{label}: {value}</title>
  <clipPath id="r">
    <rect width="{total_w}" height="28" rx="4" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="28" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="28" fill="{color}"/>
  </g>
  {icon_ftb}
  <g fill="#fff" text-anchor="middle" \
font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" \
font-size="10" letter-spacing="1.1">
    <text x="{label_x}" y="18" textLength="{label_text_w}" \
font-weight="bold" text-transform="uppercase">{label_upper}</text>
    <text x="{value_x}" y="18" textLength="{value_text_w}" \
font-weight="bold">{value}</text>
  </g>
</svg>"""


def _score_color(score: int | None) -> str:
    """Return badge color based on score thresholds."""
    if score is None:
        return "#9f9f9f"  # gray for unknown
    if score >= 80:
        return "#4c1"  # green
    if score >= 40:
        return "#dfb317"  # yellow
    return "#e05d44"  # red


def _score_grade(score: int | None) -> str:
    """Return letter grade for JSON endpoint."""
    if score is None:
        return "N/A"
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "F"


def _generate_badge(
    label: str,
    value: str,
    color: str,
    style: str = "flat",
) -> str:
    """Generate shields.io-style SVG badge with Clarvia owl icon."""
    if style == "for-the-badge":
        return _generate_badge_ftb(label, value, color)

    # Character width estimation (Verdana 11px)
    label_text_w = len(label) * 6.5 + 10
    label_w = label_text_w + _ICON_WIDTH  # extra space for owl icon
    value_w = len(value) * 6.5 + 10

    # Minimum widths
    label_w = max(label_w, 48)
    value_w = max(value_w, 24)

    total_w = label_w + value_w
    # Shift label text right to accommodate the owl icon
    label_x = _ICON_WIDTH + (label_w - _ICON_WIDTH) / 2
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
        icon=_OWL_ICON,
    )


def _generate_badge_ftb(label: str, value: str, color: str) -> str:
    """Generate 'for-the-badge' style SVG (taller, uppercase, bolder)."""
    label_upper = label.upper()
    # Wider character estimation for uppercase + letter-spacing
    label_text_w = len(label_upper) * 7.2
    value_text_w = len(value) * 7.2

    label_w = label_text_w + 20 + _ICON_WIDTH
    value_w = value_text_w + 20

    label_w = max(label_w, 50)
    value_w = max(value_w, 30)

    total_w = label_w + value_w
    label_x = _ICON_WIDTH + (label_w - _ICON_WIDTH) / 2
    value_x = label_w + value_w / 2

    # Slightly larger icon for the taller badge
    icon_ftb = (
        '<g transform="translate(6,4) scale(0.04)">'
        '<path fill="#fff" d="M256 48C141.1 48 48 141.1 48 256s93.1 208 208 208 '
        "208-93.1 208-208S370.9 48 256 48zm-50 280c-22.1 0-40-17.9-40-40s17.9-40 "
        "40-40 40 17.9 40 40-17.9 40-40 40zm100 0c-22.1 0-40-17.9-40-40s17.9-40 "
        '40-40 40 17.9 40 40-17.9 40-40 40z"/>'
        "</g>"
    )

    return _SVG_FOR_THE_BADGE.format(
        total_w=total_w,
        label_w=label_w,
        value_w=value_w,
        label_x=label_x,
        value_x=value_x,
        label=label,
        label_upper=label_upper,
        label_text_w=label_text_w,
        value=value,
        value_text_w=value_text_w,
        color=color,
        icon_ftb=icon_ftb,
    )


# ---------------------------------------------------------------------------
# Shared response builder
# ---------------------------------------------------------------------------

def _build_badge_response(
    identifier: str,
    style: str,
    label: str,
    compact: bool,
) -> Response:
    """Resolve identifier and return SVG badge Response."""
    service = _find_service(identifier)

    if service is None:
        value = "?"
        color = _score_color(None)
    else:
        score = service.get("clarvia_score", 0)
        value = str(score) if compact else f"AEO {score}/100"
        color = _score_color(score)

    svg = _generate_badge(label, value, color, style)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=3600, s-maxage=3600",
            "Vary": "Accept",
        },
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/badge/{identifier:path}.svg")
async def badge_svg_ext(
    identifier: str,
    style: str = Query("flat", pattern="^(flat|flat-square|for-the-badge)$"),
    label: str = Query("Clarvia", max_length=30),
    compact: bool = Query(False),
):
    """SVG badge with explicit .svg extension.

    Alias for /api/badge/{identifier} -- useful for image hotlinking
    that requires a file extension.
    """
    return _build_badge_response(identifier, style, label, compact)


@router.get("/api/badge/{identifier}/json")
async def badge_json(identifier: str):
    """Return JSON score data (shields.io endpoint schema compatible).

    Response follows the shields.io endpoint badge schema so it can be
    used with shields.io's dynamic badge feature as well.
    """
    service = _find_service(identifier)

    if service is None:
        return JSONResponse(
            content={
                "schemaVersion": 1,
                "label": "Clarvia AEO",
                "message": "not found",
                "color": "lightgrey",
                "isError": True,
            },
            headers={"Cache-Control": "public, max-age=3600, s-maxage=3600"},
        )

    score = service.get("clarvia_score", 0)
    rating = service.get("rating", "Unknown")
    service_name = service.get("service_name", identifier)

    return JSONResponse(
        content={
            "schemaVersion": 1,
            "label": "Clarvia AEO",
            "message": f"{score}/100",
            "color": _score_color(score).lstrip("#"),
            "score": score,
            "grade": _score_grade(score),
            "rating": rating,
            "service_name": service_name,
            "badge_url": f"{_BADGE_BASE_URL}/api/badge/{quote(identifier, safe='')}",
            "report_url": f"{_SITE_URL}/tool/{quote(identifier, safe='')}",
        },
        headers={"Cache-Control": "public, max-age=3600, s-maxage=3600"},
    )


@router.get("/api/badge/{identifier}/markdown")
async def badge_markdown(
    identifier: str,
    style: str = Query("flat", pattern="^(flat|flat-square|for-the-badge)$"),
    label: str = Query("Clarvia", max_length=30),
    compact: bool = Query(False),
):
    """Return markdown embed snippet for the AEO score badge.

    Response includes multiple formats:
      - markdown: standard markdown image syntax
      - markdown_with_link: badge linked to the Clarvia report page
      - html: img tag for HTML embedding
    """
    service = _find_service(identifier)
    service_name = identifier
    if service:
        service_name = service.get("service_name", identifier)

    # Build query params
    params = []
    if style != "flat":
        params.append(f"style={style}")
    if label != "Clarvia":
        params.append(f"label={quote(label)}")
    if compact:
        params.append("compact=true")
    qs = f"?{'&'.join(params)}" if params else ""

    badge_url = f"{_BADGE_BASE_URL}/api/badge/{quote(identifier, safe='')}{qs}"
    report_url = f"{_SITE_URL}/tool/{quote(identifier, safe='')}"

    return JSONResponse(
        content={
            "service_name": service_name,
            "badge_url": badge_url,
            "report_url": report_url,
            "snippets": {
                "markdown": f"![Clarvia AEO Score]({badge_url})",
                "markdown_with_link": f"[![Clarvia AEO Score]({badge_url})]({report_url})",
                "html": (
                    f'<a href="{report_url}">'
                    f'<img src="{badge_url}" alt="Clarvia AEO Score" />'
                    f"</a>"
                ),
                "rst": f".. image:: {badge_url}\n   :target: {report_url}\n   :alt: Clarvia AEO Score",
            },
        },
        headers={
            "Cache-Control": "public, max-age=3600, s-maxage=3600",
        },
    )


@router.get("/api/badge/{identifier:path}")
async def badge_svg(
    identifier: str,
    style: str = Query("flat", pattern="^(flat|flat-square|for-the-badge)$"),
    label: str = Query("Clarvia", max_length=30),
    compact: bool = Query(False),
    format: str = Query("svg", pattern="^(svg|json)$"),
):
    """Generate a shields.io-style SVG badge for a service's AEO score.

    The identifier can be a scan_id, service name, or URL.

    Query params:
      - style: flat | flat-square | for-the-badge
      - label: left-side text (default: "Clarvia")
      - compact: true -> show "85", false -> show "AEO 85/100" (default)
      - format: svg (default) | json
    """
    if format == "json":
        return await badge_json(identifier)
    return _build_badge_response(identifier, style, label, compact)
