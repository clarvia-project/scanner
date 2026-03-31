"""Rate limiting and analytics middleware for the scanner API."""

import asyncio
import logging
import time
from collections import defaultdict

from cachetools import TTLCache
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .services.analytics import analytics
from .services.analytics_writer import analytics_writer, build_analytics_entry
from .services.security import abuse_detector, is_suspicious_request

logger = logging.getLogger(__name__)

# Default limits
FREE_LIMIT = 10  # scans per hour per IP
API_KEY_LIMIT = 100  # scans per hour per API key
WINDOW_SECONDS = 3600  # 1 hour


class RateLimitEntry:
    __slots__ = ("count", "window_start")

    def __init__(self) -> None:
        self.count = 0
        self.window_start = time.monotonic()

    def reset_if_expired(self) -> None:
        now = time.monotonic()
        if now - self.window_start >= WINDOW_SECONDS:
            self.count = 0
            self.window_start = now

    def increment(self) -> int:
        self.reset_if_expired()
        self.count += 1
        return self.count

    @property
    def remaining(self) -> float:
        elapsed = time.monotonic() - self.window_start
        return max(0, WINDOW_SECONDS - elapsed)


# In-memory store: keyed by IP or API key
# TTLCache bounds memory usage: max 5,000 entries, auto-evicted after 2h.
# 50k was excessive for a single-worker 512MB instance — each entry holds a
# RateLimitEntry object.  5k covers ~5k unique IPs/keys per 2h window, which is
# far more than realistic traffic on Render Starter.
_rate_store: TTLCache = TTLCache(maxsize=5_000, ttl=WINDOW_SECONDS * 2)


# Render.com proxy IPs — only trust X-Forwarded-For from known proxies
_TRUSTED_PROXY_PREFIXES = ("10.", "172.16.", "192.168.", "127.")


def _get_client_ip(request: Request) -> str:
    """Extract client IP. Only trust X-Forwarded-For from known proxy IPs."""
    real_ip = request.client.host if request.client else "unknown"

    # Only trust forwarded header if request comes from a known proxy
    if any(real_ip.startswith(p) for p in _TRUSTED_PROXY_PREFIXES) or real_ip == "::1":
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

    return real_ip


ENTERPRISE_LIMIT = 999999  # effectively unlimited


def _resolve_limit(api_key: str | None) -> tuple[str, int]:
    """Determine the rate limit key and limit for a request.

    Returns (store_key, limit).
    """
    if api_key:
        # Check if it's a registered Clarvia key with a tier
        try:
            from .services.auth_service import _hash_key, _keys_store, PLAN_LIMITS
            key_hash = _hash_key(api_key)
            record = _keys_store.get(key_hash)
            if record:
                plan = record.get("plan", "free")
                tier_limit = PLAN_LIMITS.get(plan, {}).get("rate_limit", API_KEY_LIMIT)
                return f"apikey:{api_key}", tier_limit
        except Exception:
            pass
        return f"apikey:{api_key}", API_KEY_LIMIT
    return "", FREE_LIMIT


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory rate limiter.

    - 10 scans/hour per IP (free tier)
    - 100 scans/hour per API key (X-API-Key header)
    - Enforces on POST /api/scan; headers on ALL /api/ and /v1/ responses
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = _get_client_ip(request)
        path = request.url.path
        is_api = path.startswith(("/api/", "/v1/"))
        is_scan = request.method == "POST" and path.startswith("/api/scan")

        # Non-API paths pass through without rate limit headers
        if not is_api:
            return await call_next(request)

        # Bypass rate limiting for localhost/internal requests
        if client_ip in ("127.0.0.1", "::1", "localhost"):
            response = await call_next(request)
            # Still add headers for observability
            response.headers["X-RateLimit-Limit"] = str(FREE_LIMIT)
            response.headers["X-RateLimit-Remaining"] = str(FREE_LIMIT)
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + WINDOW_SECONDS))
            return response

        # Bypass rate limiting for admin API key
        api_key = request.headers.get("x-api-key") or request.headers.get("x-clarvia-key")
        if api_key:
            from .config import settings
            if api_key == getattr(settings, "admin_api_key", None):
                response = await call_next(request)
                response.headers["X-RateLimit-Limit"] = "unlimited"
                response.headers["X-RateLimit-Remaining"] = "unlimited"
                response.headers["X-RateLimit-Reset"] = str(int(time.time() + WINDOW_SECONDS))
                return response

        store_key, limit = _resolve_limit(api_key)
        if not store_key:
            store_key = f"ip:{client_ip}"

        # TTLCache doesn't support default factory; get-or-create manually.
        if store_key not in _rate_store:
            _rate_store[store_key] = RateLimitEntry()
        entry = _rate_store[store_key]

        # Only count scan requests against the limit
        if is_scan:
            current = entry.increment()
        else:
            # For non-scan requests, peek at current count without incrementing
            entry.reset_if_expired()
            current = entry.count

        if is_scan and current > limit:
            retry_after = int(entry.remaining)
            logger.warning("Rate limit exceeded for %s (count=%d, limit=%d)", store_key, current, limit)
            # Include CORS header manually: RateLimitMiddleware returns early (no call_next),
            # so CORSMiddleware (inner middleware) never runs → browser gets "Failed to fetch".
            origin = request.headers.get("origin", "")
            cors_headers: dict[str, str] = {}
            if origin:
                cors_headers["Access-Control-Allow-Origin"] = origin
                cors_headers["Vary"] = "Origin"
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {limit} scans per hour. Try again in {retry_after}s.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + entry.remaining)),
                    **cors_headers,
                },
            )

        response = await call_next(request)

        # Add rate limit headers to ALL API responses
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current))
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + entry.remaining))

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "0"
        # Prevent caching of API responses (except badge SVGs which are cacheable)
        if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/badge/"):
            response.headers["Cache-Control"] = "no-store"
        return response


_SAFE_PATHS = ("/health", "/v1/feed/", "/v1/categories", "/v1/search", "/v1/leaderboard", "/v1/score", "/v1/services", "/v1/cs/tickets")


class SecurityMiddleware(BaseHTTPMiddleware):
    """Block banned IPs, detect suspicious requests, enforce URL safety."""

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = _get_client_ip(request)
        path = request.url.path
        user_agent = request.headers.get("user-agent", "")

        # Never block health checks and read-only endpoints
        is_safe = any(path.startswith(p) for p in _SAFE_PATHS)

        # Check IP ban (skip for safe paths)
        if not is_safe and abuse_detector.is_banned(client_ip):
            abuse_detector.total_blocked += 1
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Access temporarily blocked due to abuse detection.",
                    "retry_after": 600,
                },
                headers={"Retry-After": "600"},
            )

        # Check suspicious patterns
        suspicious, reason = is_suspicious_request(user_agent, path)
        if suspicious:
            abuse_detector.record_error(client_ip)
            logger.warning("Suspicious request from %s: %s (path=%s)", client_ip, reason, path)

        response = await call_next(request)

        # Track errors for abuse detection (only for non-safe, non-404 paths)
        if response.status_code >= 400 and response.status_code != 404 and not is_safe:
            abuse_detector.record_error(client_ip)

        # Track scan bursts
        if path == "/api/scan" and request.method == "POST":
            abuse_detector.record_scan(client_ip)

        return response


# ---------------------------------------------------------------------------
# Agent traffic identification — MOAT DATA COLLECTION
# Every agent request is a data point. Over time this becomes the moat:
# which agents use which tools, at what frequency, with what success rate.
# No competitor can replicate 6+ months of accumulated agent usage data.
# ---------------------------------------------------------------------------

# Known agent/LLM user agent patterns (partial matches, case-insensitive)
_AGENT_UA_PATTERNS = (
    "claude",
    "gpt",
    "openai",
    "cursor",
    "continue",
    "copilot",
    "codeium",
    "anthropic",
    "langchain",
    "langgraph",
    "autogen",
    "crewai",
    "llamaindex",
    "llama_index",
    "smolagents",
    "agentops",
    "dify",
    "flowise",
    "n8n",
    "make.com",
    "zapier",
    "python-httpx",
    "python-requests",
    # MCP clients
    "mcp-client",
    "mcpclient",
    "clarvia-mcp",
    "smithery",
    # Generic agent indicators
    "bot/",
    "agent/",
    "-agent",
)


def _identify_agent_traffic(user_agent: str) -> str | None:
    """Classify user agent as a known agent type.

    Returns agent class string or None if human/unknown.
    This data accumulates into Clarvia's moat: tool usage patterns by agent type.
    """
    ua_lower = user_agent.lower()
    for pattern in _AGENT_UA_PATTERNS:
        if pattern in ua_lower:
            # Classify into broad categories
            if any(p in ua_lower for p in ("claude", "anthropic")):
                return "claude"
            if any(p in ua_lower for p in ("gpt", "openai")):
                return "openai"
            if "cursor" in ua_lower:
                return "cursor"
            if "continue" in ua_lower:
                return "continue"
            if any(p in ua_lower for p in ("langchain", "langgraph", "llamaindex", "llama_index")):
                return "langchain_ecosystem"
            if any(p in ua_lower for p in ("autogen", "crewai", "smolagents")):
                return "agent_framework"
            if any(p in ua_lower for p in ("n8n", "zapier", "make.com", "flowise", "dify")):
                return "automation_platform"
            if "mcp" in ua_lower or "smithery" in ua_lower:
                return "mcp_client"
            return "agent_other"
    return None


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Track all requests for KPI dashboard. Lightweight, non-blocking.

    Records to both in-memory analytics (real-time) and persistent JSONL
    files (historical queries). JSONL writes are buffered and async so
    they never block the request path.

    Also identifies agent traffic — this is moat data. Every agent request
    logged here is part of the dataset that competitors cannot replicate.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000

        client_ip = _get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        path = request.url.path
        method = request.method

        # Identify agent vs human traffic (moat data collection)
        agent_type = _identify_agent_traffic(user_agent)
        if agent_type:
            response.headers["X-Clarvia-Agent-Detected"] = agent_type

        # In-memory analytics (existing, real-time KPI)
        analytics.record_request(
            path=path,
            method=method,
            status_code=response.status_code,
            client_ip=client_ip,
            user_agent=user_agent,
            response_time_ms=elapsed_ms,
        )

        # Track scans specifically
        if path == "/api/scan" and method == "POST" and response.status_code == 200:
            analytics.record_scan("unknown")

        # Track MCP calls
        if path.startswith("/mcp"):
            analytics.record_mcp_call(path)

        # Persistent JSONL analytics (skip health checks and static assets)
        if path.startswith(("/api/", "/v1/", "/mcp")):
            entry = build_analytics_entry(
                path=path,
                method=method,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                client_ip=client_ip,
                user_agent=user_agent,
            )
            # Attach agent type to analytics entry for moat data accumulation
            if agent_type:
                entry["agent_type"] = agent_type
            # Fire-and-forget: buffer the entry without awaiting disk I/O
            asyncio.ensure_future(analytics_writer.record(entry))

        return response


def cleanup_rate_store() -> int:
    """Expire stale rate limit entries. TTLCache handles eviction automatically.

    This function is kept for API compatibility with the background cleanup task.
    TTLCache auto-evicts entries after 2h TTL, so manual cleanup is rarely needed.
    Returns the number of manually expired entries (typically 0 with TTLCache).
    """
    now = time.monotonic()
    expired = [
        k for k, entry in list(_rate_store.items())
        if now - entry.window_start >= WINDOW_SECONDS * 2
    ]
    for k in expired:
        try:
            del _rate_store[k]
        except KeyError:
            pass  # Already evicted by TTLCache
    return len(expired)
