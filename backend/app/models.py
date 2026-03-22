"""Pydantic models for request/response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


# --- Request ---

class ScanRequest(BaseModel):
    url: str = Field(..., description="URL to scan (website, API base, or docs URL)")


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

class ScanResponse(BaseModel):
    scan_id: str
    url: str
    service_name: str
    clarvia_score: int
    rating: str
    dimensions: dict[str, DimensionResult]
    onchain_bonus: OnchainBonusResult
    top_recommendations: list[str]
    scanned_at: datetime
    scan_duration_ms: int


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class WaitlistRequest(BaseModel):
    email: str = Field(..., description="Email address for waitlist signup")
