"""Rate limiting middleware for the scanner API."""

import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

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


def cleanup_rate_store() -> int:
    """Remove expired rate limit entries. Returns count removed."""
    expired = [
        k for k, entry in _rate_store.items()
        if time.monotonic() - entry.window_start >= WINDOW_SECONDS * 2
    ]
    for k in expired:
        del _rate_store[k]
    return len(expired)
