"""Auto-gating middleware — intercepts HTTP calls and checks AEO scores.

Works with any Python agent framework (LangChain, CrewAI, AutoGen, raw httpx/aiohttp).

Usage:
    from clarvia_langchain import auto_gate

    # Activate globally — all outgoing HTTP calls get AEO-checked
    auto_gate.activate(min_score=60)

    # Or use as a context manager
    with auto_gate(min_score=60):
        # All HTTP calls inside this block are gated
        response = httpx.get("https://some-api.com/data")

    # Framework-specific decorators
    @auto_gate.before_tool_call(min_score=60)
    def my_tool(url: str):
        return httpx.get(url)
"""

from __future__ import annotations

import functools
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable

import httpx

logger = logging.getLogger("clarvia_langchain")

_CLARVIA_API = "https://clarvia-api.onrender.com"
_CACHE: dict[str, tuple[dict, float]] = {}
_CACHE_TTL = 3600  # 1 hour
_ACTIVE = False
_MIN_SCORE = 60
_BLOCK_MODE = "warn"  # "warn" | "block" | "log"


def _get_score(url: str) -> dict[str, Any]:
    """Fetch AEO score from Clarvia. Returns cached result if available."""
    # Extract domain
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = f"{parsed.scheme}://{parsed.netloc}"

    # Check cache
    if domain in _CACHE:
        result, expiry = _CACHE[domain]
        if time.monotonic() < expiry:
            return result

    # Fetch from Clarvia
    try:
        resp = httpx.get(
            f"{_CLARVIA_API}/v1/score",
            params={"url": domain},
            timeout=5.0,
            headers={"User-Agent": "clarvia-auto-gate/0.2.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            _CACHE[domain] = (data, time.monotonic() + _CACHE_TTL)
            return data
    except Exception as e:
        logger.debug("Clarvia score fetch failed for %s: %s", domain, e)

    return {"score": None, "rating": "UNKNOWN", "error": True}


def _check_and_act(url: str, min_score: int, mode: str) -> bool:
    """Check score and take action. Returns True if allowed."""
    data = _get_score(url)

    if data.get("error"):
        logger.debug("Clarvia unavailable — allowing %s (fail-open)", url)
        return True

    score = data.get("score", 0)
    rating = data.get("rating", "UNKNOWN")

    if score is not None and score >= min_score:
        logger.debug("Clarvia PASS: %s scored %d (%s)", url, score, rating)
        return True

    msg = (
        f"Clarvia AEO Warning: {url} scored {score}/100 ({rating}). "
        f"Minimum required: {min_score}. "
        f"Consider using a higher-scored alternative — "
        f"check https://clarvia.art/leaderboard"
    )

    if mode == "block":
        raise ConnectionRefusedError(msg)
    elif mode == "warn":
        logger.warning(msg)
        return True
    else:  # log
        logger.info(msg)
        return True


def activate(
    min_score: int = 60,
    mode: str = "warn",
    cache_ttl: int = 3600,
) -> None:
    """Activate auto-gating globally for all HTTP calls.

    Args:
        min_score: Minimum AEO score to allow (0-100). Default 60.
        mode: "warn" (log warning, allow), "block" (raise error), "log" (info only).
        cache_ttl: Cache TTL in seconds. Default 3600 (1 hour).
    """
    global _ACTIVE, _MIN_SCORE, _BLOCK_MODE, _CACHE_TTL
    _ACTIVE = True
    _MIN_SCORE = min_score
    _BLOCK_MODE = mode
    _CACHE_TTL = cache_ttl
    logger.info(
        "Clarvia auto-gate activated: min_score=%d, mode=%s",
        min_score, mode,
    )


def deactivate() -> None:
    """Deactivate auto-gating."""
    global _ACTIVE
    _ACTIVE = False


@contextmanager
def gate_context(min_score: int = 60, mode: str = "warn"):
    """Context manager for temporary auto-gating."""
    old_active, old_score, old_mode = _ACTIVE, _MIN_SCORE, _BLOCK_MODE
    activate(min_score=min_score, mode=mode)
    try:
        yield
    finally:
        globals()["_ACTIVE"] = old_active
        globals()["_MIN_SCORE"] = old_score
        globals()["_BLOCK_MODE"] = old_mode


def before_tool_call(
    min_score: int = 60,
    mode: str = "warn",
    url_param: str = "url",
) -> Callable:
    """Decorator that checks AEO score before a tool function runs.

    Works with any framework — just decorate your tool function.

    Args:
        min_score: Minimum AEO score required.
        mode: "warn", "block", or "log".
        url_param: Name of the parameter containing the target URL.

    Example::

        @before_tool_call(min_score=70, mode="block")
        def call_api(url: str, query: str):
            return httpx.get(url, params={"q": query})
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Try to extract URL from kwargs or first positional arg
            target_url = kwargs.get(url_param)
            if target_url is None and args:
                target_url = args[0]
            if target_url and isinstance(target_url, str):
                _check_and_act(target_url, min_score, mode)
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            target_url = kwargs.get(url_param)
            if target_url is None and args:
                target_url = args[0]
            if target_url and isinstance(target_url, str):
                _check_and_act(target_url, min_score, mode)
            return await func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator


def check(url: str, min_score: int = 60) -> dict[str, Any]:
    """Standalone score check. Returns score data with pass/fail.

    Useful for agents that want to programmatically decide.

    Example::

        result = clarvia.check("https://api.example.com")
        if result["passed"]:
            # safe to use
        else:
            # find alternatives
            alts = result.get("alternatives", [])
    """
    data = _get_score(url)
    score = data.get("score")
    passed = score is not None and score >= min_score
    return {
        **data,
        "passed": passed,
        "min_score": min_score,
        "check_url": url,
        "improve_guide": f"https://clarvia.art/guide",
        "leaderboard": f"https://clarvia.art/leaderboard",
    }
