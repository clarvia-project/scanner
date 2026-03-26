"""Rate limiting and analytics middleware for the scanner API."""

import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .services.analytics import analytics
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
# TODO: Replace with Redis-backed store for multi-instance deployments.
#       In-memory rate limiting is ineffective when running behind a load
#       balancer with multiple app instances, as each instance maintains
#       its own counter. Use redis-py or valkey with atomic INCR + EXPIRE.
_rate_store: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)


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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory rate limiter.

    - 10 scans/hour per IP (free tier)
    - 100 scans/hour per API key (X-API-Key header)
    - Only applies to POST /api/scan
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only rate-limit scan endpoints
        if request.method != "POST" or not request.url.path.startswith("/api/scan"):
            return await call_next(request)

        # Bypass rate limiting for localhost/internal requests
        client_ip = _get_client_ip(request)
        if client_ip in ("127.0.0.1", "::1", "localhost"):
            return await call_next(request)

        # Bypass rate limiting for admin API key
        api_key = request.headers.get("x-api-key")
        if api_key:
            from .config import settings
            if api_key == getattr(settings, "admin_api_key", None):
                return await call_next(request)
        if api_key:
            key = f"apikey:{api_key}"
            limit = API_KEY_LIMIT
        else:
            key = f"ip:{client_ip}"
            limit = FREE_LIMIT

        entry = _rate_store[key]
        current = entry.increment()

        if current > limit:
            retry_after = int(entry.remaining)
            logger.warning("Rate limit exceeded for %s (count=%d, limit=%d)", key, current, limit)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {limit} scans per hour. Try again in {retry_after}s.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)

        # Add rate limit headers
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
        # Prevent caching of API responses
        if request.url.path.startswith("/api/"):
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


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Track all requests for KPI dashboard. Lightweight, non-blocking."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000

        client_ip = _get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        path = request.url.path
        method = request.method

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
            # URL is in request body, but we track count only here
            analytics.record_scan("unknown")

        # Track MCP calls
        if path.startswith("/mcp"):
            analytics.record_mcp_call(path)

        return response


def cleanup_rate_store() -> int:
    """Remove expired rate limit entries. Returns count removed."""
    expired = [
        k for k, entry in _rate_store.items()
        if time.monotonic() - entry.window_start >= WINDOW_SECONDS * 2
    ]
    for k in expired:
        del _rate_store[k]
    return len(expired)
