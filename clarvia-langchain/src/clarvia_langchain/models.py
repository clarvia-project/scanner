"""Data models for Clarvia LangChain integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ServiceRating(str, Enum):
    """AEO rating tiers for service agent-friendliness.

    Score ranges:
        AGENT_NATIVE:   90-100 — Fully optimized for AI agents
        AGENT_FRIENDLY: 70-89  — Usable by agents with minor friction
        AGENT_POSSIBLE: 50-69  — Partially usable, may have issues
        AGENT_HOSTILE:  0-49   — Actively hostile or unusable by agents
    """

    AGENT_NATIVE = "AGENT_NATIVE"
    AGENT_FRIENDLY = "AGENT_FRIENDLY"
    AGENT_POSSIBLE = "AGENT_POSSIBLE"
    AGENT_HOSTILE = "AGENT_HOSTILE"

    @classmethod
    def from_score(cls, score: int) -> ServiceRating:
        """Derive rating tier from a numeric AEO score (0-100)."""
        if score >= 90:
            return cls.AGENT_NATIVE
        if score >= 70:
            return cls.AGENT_FRIENDLY
        if score >= 50:
            return cls.AGENT_POSSIBLE
        return cls.AGENT_HOSTILE

    @property
    def min_score(self) -> int:
        """Return the minimum score for this rating tier."""
        return {
            ServiceRating.AGENT_NATIVE: 90,
            ServiceRating.AGENT_FRIENDLY: 70,
            ServiceRating.AGENT_POSSIBLE: 50,
            ServiceRating.AGENT_HOSTILE: 0,
        }[self]


# Ordered from most restrictive to least restrictive
_RATING_ORDER: dict[ServiceRating, int] = {
    ServiceRating.AGENT_NATIVE: 3,
    ServiceRating.AGENT_FRIENDLY: 2,
    ServiceRating.AGENT_POSSIBLE: 1,
    ServiceRating.AGENT_HOSTILE: 0,
}


def rating_meets_minimum(actual: ServiceRating, minimum: ServiceRating) -> bool:
    """Check if an actual rating meets or exceeds the minimum required rating."""
    return _RATING_ORDER[actual] >= _RATING_ORDER[minimum]


@dataclass(frozen=True)
class GateResult:
    """Result of a CriteriaGate check.

    Attributes:
        allowed: Whether the call is permitted.
        score: The numeric AEO score (0-100), or None if the API call failed.
        rating: The derived ServiceRating tier.
        service_url: The URL that was checked.
        reason: Human-readable explanation of the decision.
        alternatives: Suggested alternative services (when blocked).
        cached: Whether this result came from the local cache.
    """

    allowed: bool
    score: int | None
    rating: ServiceRating
    service_url: str
    reason: str
    alternatives: list[str] = field(default_factory=list)
    cached: bool = False
