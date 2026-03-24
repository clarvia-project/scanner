"""CriteriaGate — checks Clarvia AEO scores before allowing API calls."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .models import GateResult, ServiceRating, rating_meets_minimum

logger = logging.getLogger("clarvia_langchain")

_DEFAULT_API_BASE = "https://clarvia-api.onrender.com/api/v1"
_DEFAULT_CACHE_TTL = 3600  # 1 hour in seconds


class CriteriaGate:
    """Gate that checks a service's AEO score before permitting tool invocation.

    Args:
        api_key: Clarvia API key (``clv_xxx``).
        min_rating: Minimum acceptable rating tier. Calls to services rated
            below this threshold are blocked. Defaults to ``AGENT_FRIENDLY``.
        api_base: Override the Clarvia API base URL.
        cache_ttl: Cache TTL in seconds. Set to 0 to disable caching.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        min_rating: str | ServiceRating = ServiceRating.AGENT_FRIENDLY,
        *,
        api_base: str = _DEFAULT_API_BASE,
        cache_ttl: int = _DEFAULT_CACHE_TTL,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key
        self.min_rating = (
            ServiceRating(min_rating) if isinstance(min_rating, str) else min_rating
        )
        self.api_base = api_base.rstrip("/")
        self.cache_ttl = cache_ttl
        self.timeout = timeout

        # In-memory cache: url -> (GateResult, expiry_timestamp)
        self._cache: dict[str, tuple[GateResult, float]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, service_url: str) -> GateResult:
        """Evaluate whether *service_url* meets the minimum rating.

        Returns a ``GateResult`` with the decision, score, and reasoning.
        On API failure the call is allowed through with a warning log.
        """
        # Cache lookup
        cached = self._cache_get(service_url)
        if cached is not None:
            return cached

        # Fetch score from Clarvia API
        try:
            data = self._fetch_score(service_url)
        except Exception as exc:
            logger.warning(
                "Clarvia API request failed for %s: %s — allowing call through",
                service_url,
                exc,
            )
            return self._make_fallback_result(service_url)

        score: int = data.get("score", 0)
        rating = ServiceRating.from_score(score)
        alternatives: list[str] = data.get("alternatives", [])

        allowed = rating_meets_minimum(rating, self.min_rating)
        reason = self._build_reason(service_url, score, rating, allowed)

        result = GateResult(
            allowed=allowed,
            score=score,
            rating=rating,
            service_url=service_url,
            reason=reason,
            alternatives=alternatives,
            cached=False,
        )

        self._cache_put(service_url, result)
        return result

    async def acheck(self, service_url: str) -> GateResult:
        """Async version of :meth:`check`."""
        cached = self._cache_get(service_url)
        if cached is not None:
            return cached

        try:
            data = await self._afetch_score(service_url)
        except Exception as exc:
            logger.warning(
                "Clarvia API request failed for %s: %s — allowing call through",
                service_url,
                exc,
            )
            return self._make_fallback_result(service_url)

        score: int = data.get("score", 0)
        rating = ServiceRating.from_score(score)
        alternatives: list[str] = data.get("alternatives", [])

        allowed = rating_meets_minimum(rating, self.min_rating)
        reason = self._build_reason(service_url, score, rating, allowed)

        result = GateResult(
            allowed=allowed,
            score=score,
            rating=rating,
            service_url=service_url,
            reason=reason,
            alternatives=alternatives,
            cached=False,
        )

        self._cache_put(service_url, result)
        return result

    def clear_cache(self) -> None:
        """Clear the entire score cache."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_score(self, service_url: str) -> dict[str, Any]:
        """Synchronous HTTP call to the Clarvia scoring API."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(
                f"{self.api_base}/score",
                params={"url": service_url},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def _afetch_score(self, service_url: str) -> dict[str, Any]:
        """Asynchronous HTTP call to the Clarvia scoring API."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.api_base}/score",
                params={"url": service_url},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "clarvia-langchain/0.1.0",
        }

    # -- Cache ---------------------------------------------------------

    def _cache_get(self, service_url: str) -> GateResult | None:
        if self.cache_ttl <= 0:
            return None
        entry = self._cache.get(service_url)
        if entry is None:
            return None
        result, expiry = entry
        if time.monotonic() > expiry:
            del self._cache[service_url]
            return None
        # Return a copy flagged as cached
        return GateResult(
            allowed=result.allowed,
            score=result.score,
            rating=result.rating,
            service_url=result.service_url,
            reason=result.reason,
            alternatives=result.alternatives,
            cached=True,
        )

    def _cache_put(self, service_url: str, result: GateResult) -> None:
        if self.cache_ttl <= 0:
            return
        self._cache[service_url] = (result, time.monotonic() + self.cache_ttl)

    # -- Result builders -----------------------------------------------

    def _make_fallback_result(self, service_url: str) -> GateResult:
        """Graceful fallback when the API is unreachable."""
        return GateResult(
            allowed=True,
            score=None,
            rating=ServiceRating.AGENT_POSSIBLE,
            service_url=service_url,
            reason=(
                f"Clarvia API unavailable — allowing call to {service_url} "
                f"(fallback mode)"
            ),
        )

    @staticmethod
    def _build_reason(
        service_url: str,
        score: int,
        rating: ServiceRating,
        allowed: bool,
    ) -> str:
        if allowed:
            return (
                f"{service_url} scored {score}/100 ({rating.value}) — call permitted"
            )
        return (
            f"{service_url} scored {score}/100 ({rating.value}) — "
            f"call BLOCKED (below minimum threshold)"
        )
