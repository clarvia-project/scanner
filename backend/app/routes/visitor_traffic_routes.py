"""Privacy-first visitor traffic tracking — middleware + API endpoints.

Collects visitor traffic data with GDPR/CCPA compliance:
- Raw IP is NEVER stored to disk. Only SHA-256 hashed (daily-rotated salt).
- GeoIP resolves to country code only (no city/coordinates).
- 90-day retention with automatic cleanup.

Endpoints:
    GET /v1/traffic/visitors — visitor statistics (country, agent type, internal/external)
"""

import hashlib
import hmac
import json
import logging
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

router = APIRouter(prefix="/v1/traffic", tags=["traffic"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IP Hashing — raw IP never touches disk
# ---------------------------------------------------------------------------

# Secret key for HMAC-based daily salt generation.
# Falls back to a random key if not configured (random key = hashes won't
# persist across restarts, but that's acceptable for privacy-first design).
_IP_HASH_SECRET: str = os.environ.get("IP_HASH_SECRET", "") or os.environ.get("SCANNER_IP_HASH_SECRET", "")
if not _IP_HASH_SECRET:
    _IP_HASH_SECRET = hashlib.sha256(os.urandom(32)).hexdigest()
    logger.info("IP_HASH_SECRET not set — using ephemeral random key")


def _daily_salt(date_str: str) -> bytes:
    """Generate a deterministic daily salt via HMAC(date, secret).

    Same day + same secret = same salt, enabling unique visitor counts.
    Different day = different salt, preventing cross-day tracking.
    """
    return hmac.new(
        _IP_HASH_SECRET.encode(),
        date_str.encode(),
        hashlib.sha256,
    ).digest()


def hash_ip(raw_ip: str, date_str: Optional[str] = None) -> str:
    """Hash an IP address with a daily-rotating salt.

    Returns a hex digest. The same IP on the same day produces the same hash
    (for unique visitor counting), but cannot be reversed to the original IP.
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    salt = _daily_salt(date_str)
    return hashlib.sha256(salt + raw_ip.encode()).hexdigest()[:16]  # 16 hex chars = 64 bits, enough for uniqueness


# ---------------------------------------------------------------------------
# GeoIP — country code only, cached
# ---------------------------------------------------------------------------

# In-memory cache for GeoIP lookups (TTL = 1 hour, max 2000 entries)
_geoip_cache: dict[str, tuple[str, float]] = {}
_GEOIP_CACHE_TTL = 3600  # 1 hour
_GEOIP_CACHE_MAX = 2000


async def _lookup_country(ip: str) -> str:
    """Resolve IP to 2-letter country code using ip-api.com (free, no key needed).

    Returns "XX" on failure. Results are cached in-memory.
    """
    # Check cache first
    now = time.time()
    if ip in _geoip_cache:
        country, cached_at = _geoip_cache[ip]
        if now - cached_at < _GEOIP_CACHE_TTL:
            return country

    # Skip lookup for private/loopback IPs
    if ip.startswith(("10.", "172.16.", "192.168.", "127.", "::")) or ip == "localhost":
        _geoip_cache[ip] = ("XX", now)
        return "XX"

    try:
        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            # ip-api.com free tier: 45 req/min, no key needed, country only
            url = f"http://ip-api.com/json/{ip}?fields=countryCode"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    country = data.get("countryCode", "XX")
                    # Evict oldest if cache too large
                    if len(_geoip_cache) >= _GEOIP_CACHE_MAX:
                        oldest_key = min(_geoip_cache, key=lambda k: _geoip_cache[k][1])
                        del _geoip_cache[oldest_key]
                    _geoip_cache[ip] = (country, now)
                    return country
    except Exception as e:
        logger.debug("GeoIP lookup failed for %s: %s", ip[:8], e)

    _geoip_cache[ip] = ("XX", now)
    return "XX"


# ---------------------------------------------------------------------------
# Agent classification (reuses patterns from agent_traffic_routes)
# ---------------------------------------------------------------------------

_AGENT_TYPE_PATTERNS: dict[str, str] = {
    "claude": "claude", "anthropic": "claude",
    "chatgpt": "gpt", "gptbot": "gpt", "openai": "gpt",
    "cursor": "cursor", "copilot": "copilot",
    "perplexity": "perplexity", "gemini": "gemini",
    "langchain": "bot", "crewai": "bot", "autogpt": "bot",
}

_GENERIC_BOT_INDICATORS = ("bot/", "bot ", "spider", "crawl", "scraper")


def classify_visitor_agent(user_agent: str) -> str:
    """Classify user agent: claude/gpt/bot/human/unknown."""
    if not user_agent:
        return "unknown"
    ua_lower = user_agent.lower()

    for pattern, agent_type in _AGENT_TYPE_PATTERNS.items():
        if pattern in ua_lower:
            return agent_type

    if any(ind in ua_lower for ind in _GENERIC_BOT_INDICATORS):
        return "bot"

    # Common browser indicators = human
    if any(b in ua_lower for b in ("mozilla", "chrome", "safari", "firefox", "edge")):
        return "human"

    return "unknown"


# ---------------------------------------------------------------------------
# Internal traffic detection
# ---------------------------------------------------------------------------

_INTERNAL_UA_MARKERS = ("clarvia-internal",)
_INTERNAL_PATHS = ("/health",)
_RENDER_HEALTHCHECK_UAS = ("render", "kube-probe", "googlehc")


def is_internal_traffic(user_agent: str, path: str) -> bool:
    """Determine if a request is internal automation / healthcheck."""
    ua_lower = user_agent.lower()

    # Explicit internal marker
    if any(marker in ua_lower for marker in _INTERNAL_UA_MARKERS):
        return True

    # Health endpoint
    if any(path.startswith(p) for p in _INTERNAL_PATHS):
        return True

    # Render / k8s healthcheck
    if any(hc in ua_lower for hc in _RENDER_HEALTHCHECK_UAS):
        return True

    return False


# ---------------------------------------------------------------------------
# JSONL persistence
# ---------------------------------------------------------------------------

def _traffic_file() -> Path:
    """Resolve the visitor-traffic JSONL file path."""
    # Render production
    render_path = Path("/app/data/visitor-traffic.jsonl")
    if render_path.parent.exists():
        return render_path

    # Local dev: backend/data/
    base = Path(__file__).resolve()
    try:
        backend_data = base.parents[2] / "data" / "visitor-traffic.jsonl"
        backend_data.parent.mkdir(parents=True, exist_ok=True)
        return backend_data
    except (IndexError, OSError):
        pass

    return render_path


def _write_entry(entry: dict) -> None:
    """Append a single entry to the JSONL file."""
    try:
        path = _traffic_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug("Failed to write visitor traffic: %s", e)


def _load_entries(days: int = 7) -> list[dict]:
    """Load visitor traffic entries within the last N days."""
    path = _traffic_file()
    if not path.exists():
        return []

    cutoff_ts = time.time() - (days * 86400)
    results = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("timestamp_unix", 0) >= cutoff_ts:
                        results.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.debug("Failed to read visitor traffic: %s", e)

    return results


# ---------------------------------------------------------------------------
# 90-day retention cleanup
# ---------------------------------------------------------------------------

def cleanup_old_visitor_traffic(max_age_days: int = 90) -> int:
    """Remove visitor traffic records older than max_age_days.

    Rewrites the JSONL file in-place, keeping only recent entries.
    Returns the number of removed records.

    Safe to call from orchestrator / background task.
    """
    path = _traffic_file()
    if not path.exists():
        return 0

    cutoff_ts = time.time() - (max_age_days * 86400)
    kept = []
    removed = 0

    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("timestamp_unix", 0) >= cutoff_ts:
                        kept.append(line)
                    else:
                        removed += 1
                except json.JSONDecodeError:
                    continue

        if removed > 0:
            tmp_path = path.with_suffix(".jsonl.tmp")
            with open(tmp_path, "w") as f:
                for line in kept:
                    f.write(line + "\n")
            tmp_path.replace(path)
            logger.info("Visitor traffic cleanup: removed %d records older than %d days", removed, max_age_days)

    except Exception as e:
        logger.warning("Visitor traffic cleanup error: %s", e)

    return removed


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# Render.com proxy IPs — reuse the same logic as middleware.py
_TRUSTED_PROXY_PREFIXES = ("10.", "172.16.", "192.168.", "127.")


def _get_client_ip(request: Request) -> str:
    """Extract client IP, trusting X-Forwarded-For only from known proxies."""
    real_ip = request.client.host if request.client else "unknown"
    if any(real_ip.startswith(p) for p in _TRUSTED_PROXY_PREFIXES) or real_ip == "::1":
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return real_ip


class VisitorTrafficMiddleware(BaseHTTPMiddleware):
    """Privacy-first visitor traffic logger.

    - Hashes IP with daily-rotating salt (never stores raw IP)
    - Resolves country code only (no city/coordinates)
    - Distinguishes internal vs external traffic
    - Non-blocking: GeoIP lookup + JSONL write happen after response
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        path = request.url.path

        # Skip static assets and non-API paths to reduce noise
        if not path.startswith(("/api/", "/v1/", "/mcp", "/health")):
            return response

        user_agent = request.headers.get("user-agent", "")
        raw_ip = _get_client_ip(request)
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")

        # Hash IP — raw_ip stays in memory only, never written to disk
        ip_hashed = hash_ip(raw_ip, date_str)

        # Classify
        agent_type = classify_visitor_agent(user_agent)
        internal = is_internal_traffic(user_agent, path)

        # GeoIP lookup (async, cached, 2s timeout)
        try:
            country = await _lookup_country(raw_ip)
        except Exception:
            country = "XX"

        entry = {
            "ip_hash": ip_hashed,
            "country": country,
            "agent_type": agent_type,
            "user_agent": user_agent[:300],
            "endpoint": path,
            "method": request.method,
            "timestamp": now.isoformat(),
            "timestamp_unix": time.time(),
            "is_internal": internal,
        }

        # Write asynchronously (fire-and-forget via sync write; JSONL append is fast)
        _write_entry(entry)

        return response


# ---------------------------------------------------------------------------
# API Endpoint
# ---------------------------------------------------------------------------

@router.get("/visitors")
async def visitor_traffic_stats(
    days: int = Query(7, ge=1, le=90),
):
    """Visitor traffic statistics — country, agent type, internal/external breakdown.

    Privacy-safe: only returns aggregated counts. No raw IPs or PII.
    """
    entries = _load_entries(days=days)

    if not entries:
        return {
            "period_days": days,
            "total_visitors": 0,
            "unique_visitors": 0,
            "external_visitors": 0,
            "internal_requests": 0,
            "by_country": {},
            "by_agent_type": {},
            "daily": [],
            "message": "No visitor traffic recorded yet.",
        }

    # Unique visitor hashes
    unique_hashes: set[str] = set()
    external_hashes: set[str] = set()

    # Aggregations
    by_country: Counter = Counter()
    by_agent_type: Counter = Counter()
    by_day: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "unique": set(), "external": 0, "internal": 0,
        "by_country": Counter(), "by_agent_type": Counter(),
    })
    internal_count = 0
    external_count = 0

    for e in entries:
        ip_hash = e.get("ip_hash", "")
        country = e.get("country", "XX")
        agent_type = e.get("agent_type", "unknown")
        is_internal = e.get("is_internal", False)
        ts = e.get("timestamp", "")
        day = ts[:10] if len(ts) >= 10 else "unknown"

        unique_hashes.add(ip_hash)

        if is_internal:
            internal_count += 1
            by_day[day]["internal"] += 1
        else:
            external_count += 1
            external_hashes.add(ip_hash)
            by_country[country] += 1
            by_agent_type[agent_type] += 1
            by_day[day]["external"] += 1
            by_day[day]["by_country"][country] += 1
            by_day[day]["by_agent_type"][agent_type] += 1

        by_day[day]["total"] += 1
        by_day[day]["unique"].add(ip_hash)

    # Format daily
    daily = []
    for day in sorted(by_day.keys()):
        d = by_day[day]
        daily.append({
            "date": day,
            "total": d["total"],
            "unique": len(d["unique"]),
            "external": d["external"],
            "internal": d["internal"],
            "top_countries": dict(d["by_country"].most_common(10)),
            "top_agents": dict(d["by_agent_type"].most_common(5)),
        })

    return {
        "period_days": days,
        "total_requests": len(entries),
        "unique_visitors": len(unique_hashes),
        "external_visitors": len(external_hashes),
        "internal_requests": internal_count,
        "external_requests": external_count,
        "by_country": dict(sorted(by_country.items(), key=lambda x: x[1], reverse=True)),
        "by_agent_type": dict(sorted(by_agent_type.items(), key=lambda x: x[1], reverse=True)),
        "daily": daily,
    }
