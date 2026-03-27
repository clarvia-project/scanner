"""API key authentication for write operations.

Read endpoints remain public. Write endpoints (POST/PUT/DELETE on profiles,
admin dashboard) require a valid API key via X-API-Key header.

Set SCANNER_ADMIN_API_KEY environment variable to enable.
If not set, all write operations are allowed (dev mode).
"""

import logging
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from .config import settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _constant_time_compare(a: str, b: str) -> bool:
    """Timing-safe string comparison."""
    return secrets.compare_digest(a.encode(), b.encode())


async def require_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """FastAPI dependency that enforces API key auth on write endpoints.

    If SCANNER_ADMIN_API_KEY is not configured, allows all requests (dev mode).
    Returns the validated API key string.
    """
    if not settings.admin_api_key:
        # Dev mode: no key required
        return "dev-mode"

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header. API key required for write operations.",
        )

    if not _constant_time_compare(api_key, settings.admin_api_key):
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )

    return api_key


# Type alias for use in route function signatures
ApiKeyDep = Annotated[str, Depends(require_api_key)]
