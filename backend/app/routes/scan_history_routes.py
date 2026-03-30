"""Scan history API — per-tool score history and delta comparisons.

Endpoints:
    GET /v1/history/{tool_slug}       — scan history for a tool (by slug)
    GET /v1/history/{tool_slug}/delta  — before/after comparison
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/v1/history", tags=["history"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSONL persistence (fallback when Supabase is unavailable)
# ---------------------------------------------------------------------------

def _history_file() -> Path:
    """Find or create the scan-history JSONL file."""
    candidates = [
        Path("/app/data/scan-history.jsonl"),
    ]
    base = Path(__file__).resolve()
    for i in range(2, 6):
        try:
            candidates.append(base.parents[i] / "data" / "scan-history.jsonl")
        except IndexError:
            break
    for p in candidates:
        if p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
    return candidates[0]


def _url_to_slug(url: str) -> str:
    """Convert a URL to a stable slug for keying.

    Examples:
        https://github.com/modelcontextprotocol/servers -> github-com-modelcontextprotocol-servers
        https://docs.cursor.com -> docs-cursor-com
    """
    # Strip scheme
    cleaned = re.sub(r"^https?://", "", url.lower())
    # Strip trailing slash and common prefixes
    cleaned = cleaned.rstrip("/")
    # Replace non-alphanumeric chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", cleaned)
    # Collapse multiple hyphens, strip leading/trailing
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _slug_matches(url: str, target_slug: str) -> bool:
    """Check if a URL matches the given slug."""
    return _url_to_slug(url) == target_slug


def _save_to_jsonl(entry: dict) -> None:
    """Append a scan result to the JSONL history file."""
    try:
        path = _history_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Failed to write scan history to JSONL: %s", e)


def _load_from_jsonl(slug: str, limit: int = 50) -> list[dict]:
    """Load scan history entries for a slug from the JSONL file."""
    path = _history_file()
    if not path.exists():
        return []

    results = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if _slug_matches(entry.get("url", ""), slug):
                        results.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning("Failed to read scan history JSONL: %s", e)

    # Sort by timestamp descending (most recent first)
    results.sort(key=lambda x: x.get("scanned_at", ""), reverse=True)
    return results[:limit]


# ---------------------------------------------------------------------------
# Seed from prebuilt-scans.json (called once at startup if history is empty)
# ---------------------------------------------------------------------------

def seed_history_from_prebuilt() -> int:
    """Populate scan-history.jsonl with baseline entries from prebuilt-scans.json.

    Only runs if the history file is empty or missing. Each prebuilt scan gets
    one entry so that /v1/history/{slug}/delta has data immediately.
    Returns the number of entries seeded.
    """
    path = _history_file()
    # Skip if already has data
    if path.exists() and path.stat().st_size > 100:
        return 0

    # Find prebuilt-scans.json
    from pathlib import Path as _P
    candidates = [
        _P("/app/data/prebuilt-scans.json"),
    ]
    base = _P(__file__).resolve()
    for i in range(2, 6):
        try:
            candidates.append(base.parents[i] / "data" / "prebuilt-scans.json")
        except IndexError:
            break

    prebuilt_path = None
    for p in candidates:
        if p.exists():
            prebuilt_path = p
            break

    if not prebuilt_path:
        logger.warning("prebuilt-scans.json not found for history seeding")
        return 0

    try:
        with open(prebuilt_path) as f:
            scans = json.load(f)
    except Exception as e:
        logger.error("Failed to read prebuilt-scans.json for seeding: %s", e)
        return 0

    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        for s in scans:
            url = s.get("url", "")
            if not url:
                continue
            entry = {
                "url": url,
                "slug": _url_to_slug(url),
                "scan_id": s.get("scan_id", ""),
                "score": s.get("clarvia_score", 0),
                "rating": s.get("rating", ""),
                "service_name": s.get("service_name", ""),
                "scanned_at": s.get("scanned_at", datetime.now(timezone.utc).isoformat()),
                "source": "prebuilt_seed",
            }
            # Include dimensions if present
            dims = s.get("dimensions")
            if dims:
                # Flatten dimension scores for history
                entry["dimensions"] = {
                    k: v.get("score", 0) if isinstance(v, dict) else v
                    for k, v in dims.items()
                }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            count += 1

    logger.info("Seeded scan-history.jsonl with %d entries from prebuilt-scans.json", count)
    return count


# ---------------------------------------------------------------------------
# Public function: called from main.py after each scan
# ---------------------------------------------------------------------------

async def persist_scan_result(
    url: str,
    scan_id: str,
    score: int,
    rating: str,
    service_name: str,
    dimensions: Optional[dict] = None,
) -> None:
    """Save a scan result to both Supabase and local JSONL."""
    entry = {
        "url": url,
        "slug": _url_to_slug(url),
        "scan_id": scan_id,
        "score": score,
        "rating": rating,
        "service_name": service_name,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }
    if dimensions:
        entry["dimensions"] = dimensions

    # Always write to JSONL (lightweight, no dependencies)
    _save_to_jsonl(entry)

    # Also try Supabase
    try:
        from ..services.supabase_client import save_scan_history
        await save_scan_history(
            url=url,
            scan_id=scan_id,
            score=score,
            rating=rating,
            service_name=service_name,
            dimensions=dimensions,
        )
    except Exception as e:
        logger.debug("Supabase save skipped: %s", e)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{tool_slug}")
async def get_tool_scan_history(
    tool_slug: str,
    limit: int = Query(20, ge=1, le=100),
):
    """Get scan history for a tool by its slug.

    The slug is derived from the tool URL:
    - github.com/org/repo -> github-com-org-repo
    - docs.cursor.com -> docs-cursor-com

    Returns chronological scan results with scores and dimensions.
    """
    tool_slug = tool_slug.strip().lower()
    if not tool_slug:
        raise HTTPException(status_code=400, detail="tool_slug is required")

    # Try Supabase first
    scans = []
    try:
        from ..services.supabase_client import get_supabase
        client = get_supabase()
        if client:
            result = (
                client.table("scan_history")
                .select("scan_id, url, score, rating, scanned_at, dimensions, service_name")
                .order("scanned_at", desc=True)
                .limit(500)
                .execute()
            )
            if result.data:
                scans = [
                    r for r in result.data
                    if _slug_matches(r.get("url", ""), tool_slug)
                ][:limit]
    except Exception as e:
        logger.debug("Supabase history fetch failed, using JSONL: %s", e)

    # Fallback to JSONL
    if not scans:
        scans = _load_from_jsonl(tool_slug, limit=limit)

    return {
        "tool_slug": tool_slug,
        "scans": scans,
        "total": len(scans),
    }


@router.get("/{tool_slug}/delta")
async def get_tool_delta(
    tool_slug: str,
):
    """Get before/after comparison for a tool.

    Returns the first and latest scan with score delta and dimension changes.
    Useful for showing improvement over time.
    """
    tool_slug = tool_slug.strip().lower()
    if not tool_slug:
        raise HTTPException(status_code=400, detail="tool_slug is required")

    # Reuse the history endpoint logic
    scans = []
    try:
        from ..services.supabase_client import get_supabase
        client = get_supabase()
        if client:
            result = (
                client.table("scan_history")
                .select("scan_id, url, score, rating, scanned_at, dimensions, service_name")
                .order("scanned_at", desc=True)
                .limit(500)
                .execute()
            )
            if result.data:
                scans = [
                    r for r in result.data
                    if _slug_matches(r.get("url", ""), tool_slug)
                ]
    except Exception:
        pass

    if not scans:
        scans = _load_from_jsonl(tool_slug, limit=500)

    if not scans:
        return {
            "tool_slug": tool_slug,
            "delta": None,
            "message": "No scan history found for this tool.",
        }

    # Sort chronologically (oldest first)
    scans.sort(key=lambda s: s.get("scanned_at", ""))

    first = scans[0]
    latest = scans[-1]

    if len(scans) == 1:
        return {
            "tool_slug": tool_slug,
            "first_scan": first,
            "latest_scan": latest,
            "delta": {
                "score_change": 0,
                "scans_count": 1,
                "message": "Only one scan recorded. Rescan to see changes.",
            },
        }

    delta = {
        "score_change": latest.get("score", 0) - first.get("score", 0),
        "first_score": first.get("score", 0),
        "latest_score": latest.get("score", 0),
        "first_rating": first.get("rating"),
        "latest_rating": latest.get("rating"),
        "first_scanned_at": first.get("scanned_at"),
        "latest_scanned_at": latest.get("scanned_at"),
        "scans_count": len(scans),
    }

    # Dimension-level deltas
    first_dims = first.get("dimensions") or {}
    latest_dims = latest.get("dimensions") or {}
    if first_dims or latest_dims:
        all_keys = set(list(first_dims.keys()) + list(latest_dims.keys()))
        delta["dimensions"] = {}
        for k in sorted(all_keys):
            before = first_dims.get(k, 0)
            after = latest_dims.get(k, 0)
            delta["dimensions"][k] = {
                "before": before,
                "after": after,
                "change": after - before,
            }

    return {
        "tool_slug": tool_slug,
        "first_scan": first,
        "latest_scan": latest,
        "delta": delta,
    }
