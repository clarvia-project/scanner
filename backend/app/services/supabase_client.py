"""Supabase client for persisting scan data.

Gracefully degrades if Supabase is not configured — the scanner
still works using in-memory cache.
"""

import logging
from datetime import datetime, timezone

from ..config import settings

logger = logging.getLogger(__name__)

_client = None
_initialized = False


def get_supabase():
    """Return a Supabase client instance (lazy singleton).

    Returns None if Supabase is not configured or the package is missing.
    """
    global _client, _initialized

    if _initialized:
        return _client

    _initialized = True

    if not settings.supabase_url or not settings.supabase_anon_key:
        logger.info("Supabase not configured — using in-memory storage only")
        return None

    try:
        from supabase import create_client
        _client = create_client(settings.supabase_url, settings.supabase_anon_key)
        logger.info("Supabase client initialized successfully")
        return _client
    except ImportError:
        logger.warning("supabase package not installed — using in-memory storage only")
        return None
    except Exception as e:
        logger.error("Failed to initialize Supabase client: %s", e)
        return None


async def save_scan(scan_response) -> bool:
    """Persist a scan result to Supabase. Returns True on success."""
    client = get_supabase()
    if not client:
        return False

    try:
        data = {
            "scan_id": scan_response.scan_id,
            "url": scan_response.url,
            "service_name": scan_response.service_name,
            "clarvia_score": scan_response.clarvia_score,
            "rating": scan_response.rating,
            "dimensions": {
                k: {
                    "score": v.score,
                    "max": v.max,
                    "sub_factors": {
                        sk: {
                            "score": sv.score,
                            "max": sv.max,
                            "label": sv.label,
                            "evidence": sv.evidence,
                        }
                        for sk, sv in v.sub_factors.items()
                    },
                }
                for k, v in scan_response.dimensions.items()
            },
            "onchain_bonus": {
                "score": scan_response.onchain_bonus.score,
                "max": scan_response.onchain_bonus.max,
                "applicable": scan_response.onchain_bonus.applicable,
                "sub_factors": {
                    sk: {
                        "score": sv.score,
                        "max": sv.max,
                        "label": sv.label,
                        "evidence": sv.evidence,
                    }
                    for sk, sv in scan_response.onchain_bonus.sub_factors.items()
                },
            },
            "recommendations": scan_response.top_recommendations,
            "scan_duration_ms": scan_response.scan_duration_ms,
            "scanned_at": scan_response.scanned_at.isoformat(),
        }

        client.table("scans").upsert(data, on_conflict="scan_id").execute()
        return True
    except Exception as e:
        logger.error("Failed to save scan to Supabase: %s", e)
        return False


async def get_scan_from_db(scan_id: str) -> dict | None:
    """Retrieve a scan result from Supabase by scan_id."""
    client = get_supabase()
    if not client:
        return None

    try:
        result = (
            client.table("scans")
            .select("*")
            .eq("scan_id", scan_id)
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            # Reconstruct ScanResponse-compatible dict
            return {
                "scan_id": row["scan_id"],
                "url": row["url"],
                "service_name": row["service_name"],
                "clarvia_score": row["clarvia_score"],
                "rating": row["rating"],
                "dimensions": row["dimensions"],
                "onchain_bonus": row["onchain_bonus"],
                "top_recommendations": row.get("recommendations", []),
                "scanned_at": row["scanned_at"],
                "scan_duration_ms": row["scan_duration_ms"],
            }
    except Exception as e:
        logger.error("Failed to fetch scan from Supabase: %s", e)

    return None


async def save_report(report_data: dict) -> bool:
    """Save a paid report record to Supabase."""
    client = get_supabase()
    if not client:
        return False

    try:
        client.table("reports").insert(report_data).execute()
        return True
    except Exception as e:
        logger.error("Failed to save report to Supabase: %s", e)
        return False


async def update_report_payment(stripe_session_id: str, updates: dict) -> bool:
    """Update a report record after payment confirmation."""
    client = get_supabase()
    if not client:
        return False

    try:
        client.table("reports").update(updates).eq(
            "stripe_session_id", stripe_session_id
        ).execute()
        return True
    except Exception as e:
        logger.error("Failed to update report payment: %s", e)
        return False


async def get_report(scan_id: str) -> dict | None:
    """Get a paid report by scan_id."""
    client = get_supabase()
    if not client:
        return None

    try:
        result = (
            client.table("reports")
            .select("*")
            .eq("scan_id", scan_id)
            .eq("payment_status", "paid")
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Scan history
# ---------------------------------------------------------------------------

_history_fallback: dict[str, list[dict]] = {}


async def save_scan_history(
    url: str, scan_id: str, score: int, rating: str, service_name: str,
    dimensions: dict[str, int] | None = None,
) -> bool:
    """Append a scan result to the history table (with optional dimension scores)."""
    entry = {
        "scan_id": scan_id,
        "score": score,
        "rating": rating,
        "service_name": service_name,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }
    if dimensions:
        entry["dimensions"] = dimensions

    client = get_supabase()
    if client:
        try:
            client.table("scan_history").insert(
                {"url": url, **entry}
            ).execute()
            return True
        except Exception as e:
            logger.error("Failed to save scan history to Supabase: %s", e)

    # Fallback to in-memory
    _history_fallback.setdefault(url, []).insert(0, entry)
    # Keep only last 100 per URL in memory
    _history_fallback[url] = _history_fallback[url][:100]
    return True


async def get_scan_history(url: str, limit: int = 20) -> list[dict]:
    """Get scan history for a URL, ordered by most recent first."""
    client = get_supabase()
    if client:
        try:
            result = (
                client.table("scan_history")
                .select("scan_id, score, rating, scanned_at, dimensions, service_name")
                .eq("url", url)
                .order("scanned_at", desc=True)
                .limit(limit)
                .execute()
            )
            if result.data:
                return result.data
        except Exception as e:
            logger.error("Failed to fetch scan history from Supabase: %s", e)

    # Fallback to in-memory
    return _history_fallback.get(url, [])[:limit]


async def add_to_waitlist(email: str) -> bool:
    """Add email to the waitlist table."""
    client = get_supabase()
    if not client:
        logger.info("Waitlist signup (no DB): %s", email)
        return False

    try:
        client.table("waitlist").upsert(
            {"email": email}, on_conflict="email"
        ).execute()
        return True
    except Exception as e:
        logger.error("Failed to add to waitlist: %s", e)
        return False
