"""Simple API key authentication for Clarvia.

Keys are sha256-hashed before storage. Each key has:
- key_id: public identifier (first 12 chars, e.g. clv_xxxx)
- key_hash: sha256 of the full key
- user_email: owner email
- plan: "free" | "starter" | "pro" | "team"
- rate_limit: requests per hour
- created_at, last_used_at
"""

import hashlib
import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

from .supabase_client import get_supabase

logger = logging.getLogger(__name__)

# In-memory fallback when Supabase is unavailable
_keys_store: dict[str, dict] = {}

# Sliding-window rate limit tracker: key_hash -> list of timestamps
_rate_hits: dict[str, list[float]] = {}

PLAN_LIMITS = {
    "free": {"rate_limit": 10, "scans_per_month": 3},
    "starter": {"rate_limit": 30, "scans_per_month": 10},
    "pro": {"rate_limit": 100, "scans_per_month": -1},  # unlimited
    "enterprise": {"rate_limit": 999999, "scans_per_month": -1},  # unlimited
    "team": {"rate_limit": 500, "scans_per_month": -1},
}


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns (full_key, key_hash)."""
    raw = secrets.token_urlsafe(32)
    key = f"clv_{raw}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, key_hash


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def create_api_key(email: str, plan: str = "free") -> dict:
    """Create and store a new API key.

    Returns dict with key (shown once), key_id, plan, rate_limit.
    """
    if plan not in PLAN_LIMITS:
        plan = "free"

    full_key, key_hash = generate_api_key()
    key_id = full_key[:12]  # clv_XXXXXXXX
    now = datetime.now(timezone.utc).isoformat()
    limits = PLAN_LIMITS[plan]

    record = {
        "key_id": key_id,
        "key_hash": key_hash,
        "user_email": email,
        "plan": plan,
        "rate_limit": limits["rate_limit"],
        "scans_per_month": limits["scans_per_month"],
        "created_at": now,
        "last_used_at": None,
    }

    # Try Supabase first
    client = get_supabase()
    if client:
        try:
            client.table("api_keys").insert(record).execute()
            logger.info("API key created in Supabase for %s (plan=%s)", email, plan)
        except Exception as e:
            logger.error("Failed to save API key to Supabase: %s", e)
            _keys_store[key_hash] = record
    else:
        _keys_store[key_hash] = record

    return {
        "key": full_key,
        "key_id": key_id,
        "plan": plan,
        "rate_limit": limits["rate_limit"],
    }


async def validate_api_key(key: str) -> Optional[dict]:
    """Validate an API key. Returns key metadata or None."""
    key_hash = _hash_key(key)

    # Try Supabase first
    client = get_supabase()
    if client:
        try:
            result = (
                client.table("api_keys")
                .select("*")
                .eq("key_hash", key_hash)
                .single()
                .execute()
            )
            if result.data:
                # Update last_used_at
                try:
                    client.table("api_keys").update(
                        {"last_used_at": datetime.now(timezone.utc).isoformat()}
                    ).eq("key_hash", key_hash).execute()
                except Exception:
                    pass
                return result.data
        except Exception as e:
            logger.debug("Supabase key lookup failed: %s", e)

    # Fallback to in-memory
    record = _keys_store.get(key_hash)
    if record:
        record["last_used_at"] = datetime.now(timezone.utc).isoformat()
        return record

    return None


async def check_rate_limit(key_hash: str, limit: int) -> bool:
    """Check if the key is within rate limits. Returns True if allowed.

    Uses a sliding window of 1 hour.
    """
    now = time.monotonic()
    window = 3600  # 1 hour

    hits = _rate_hits.get(key_hash, [])
    # Prune old entries
    hits = [t for t in hits if now - t < window]
    hits.append(now)
    _rate_hits[key_hash] = hits

    return len(hits) <= limit
