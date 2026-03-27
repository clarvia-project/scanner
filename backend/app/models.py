"""Pydantic models for request/response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# --- Request ---

class ScanRequest(BaseModel):
    url: str = Field(..., description="URL to scan (website, API base, or docs URL)", max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty")
        # Reject obviously malicious input
        if any(c in v for c in ("<", ">", "{", "}", "|", "\\", "^", "`")):
            raise ValueError("URL contains invalid characters")
        return v
    auth_headers: dict[str, str] | None = Field(
        default=None,
        description="Optional auth headers to forward when scanning the target API "
        "(e.g. {'Authorization': 'Bearer sk-xxx', 'X-API-Key': 'my-key'}). "
        "These are forwarded to the target but never stored or logged.",
    )


# --- Sub-models ---

class SubFactorResult(BaseModel):
    score: int
    max: int
    label: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class DimensionResult(BaseModel):
    score: int
    max: int = 25
    sub_factors: dict[str, SubFactorResult] = Field(default_factory=dict)


class OnchainBonusResult(BaseModel):
    score: int = 0
    max: int = 25
    applicable: bool = False
    sub_factors: dict[str, SubFactorResult] = Field(default_factory=dict)


# --- Response ---

def _score_to_grade(score: int) -> str:
    """Convert numeric score to agent grade."""
    if score >= 80:
        return "AGENT_NATIVE"
    if score >= 60:
        return "AGENT_FRIENDLY"
    if score >= 40:
        return "AGENT_POSSIBLE"
    return "AGENT_HOSTILE"


class ScanResponse(BaseModel):
    scan_id: str
    url: str
    service_name: str
    clarvia_score: int
    rating: str
    agent_grade: str = Field(
        default="AGENT_POSSIBLE",
        description="Agent compatibility grade: AGENT_NATIVE (80+), AGENT_FRIENDLY (60-79), AGENT_POSSIBLE (40-59), AGENT_HOSTILE (<40)",
    )
    dimensions: dict[str, DimensionResult]
    onchain_bonus: OnchainBonusResult
    top_recommendations: list[str]
    scanned_at: datetime
    scan_duration_ms: int
    authenticated_scan: bool = Field(
        default=False,
        description="Whether this scan used authenticated headers to access the target API.",
    )

    def model_post_init(self, __context: Any) -> None:
        # Auto-set agent_grade from score
        if self.agent_grade == "AGENT_POSSIBLE":
            object.__setattr__(self, "agent_grade", _score_to_grade(self.clarvia_score))


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class WaitlistRequest(BaseModel):
    email: str = Field(
        ...,
        description="Email address for waitlist signup",
        max_length=320,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    )
