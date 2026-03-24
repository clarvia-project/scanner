"""Tests for CriteriaGate and GatedTool."""

from __future__ import annotations

import time
from typing import Any, Optional, Type
from unittest.mock import patch, MagicMock

import pytest

from clarvia_langchain import (
    CriteriaGate,
    GatedTool,
    GateBlockedError,
    GateResult,
    ServiceRating,
)
from clarvia_langchain.models import rating_meets_minimum


# ---------------------------------------------------------------------------
# ServiceRating tests
# ---------------------------------------------------------------------------


class TestServiceRating:
    def test_from_score_native(self):
        assert ServiceRating.from_score(95) == ServiceRating.AGENT_NATIVE
        assert ServiceRating.from_score(90) == ServiceRating.AGENT_NATIVE

    def test_from_score_friendly(self):
        assert ServiceRating.from_score(85) == ServiceRating.AGENT_FRIENDLY
        assert ServiceRating.from_score(70) == ServiceRating.AGENT_FRIENDLY

    def test_from_score_possible(self):
        assert ServiceRating.from_score(65) == ServiceRating.AGENT_POSSIBLE
        assert ServiceRating.from_score(50) == ServiceRating.AGENT_POSSIBLE

    def test_from_score_hostile(self):
        assert ServiceRating.from_score(49) == ServiceRating.AGENT_HOSTILE
        assert ServiceRating.from_score(0) == ServiceRating.AGENT_HOSTILE

    def test_min_score(self):
        assert ServiceRating.AGENT_NATIVE.min_score == 90
        assert ServiceRating.AGENT_HOSTILE.min_score == 0


class TestRatingMeetsMinimum:
    def test_native_meets_all(self):
        for rating in ServiceRating:
            assert rating_meets_minimum(ServiceRating.AGENT_NATIVE, rating)

    def test_hostile_meets_only_hostile(self):
        assert rating_meets_minimum(ServiceRating.AGENT_HOSTILE, ServiceRating.AGENT_HOSTILE)
        assert not rating_meets_minimum(ServiceRating.AGENT_HOSTILE, ServiceRating.AGENT_POSSIBLE)

    def test_friendly_meets_friendly_and_below(self):
        assert rating_meets_minimum(ServiceRating.AGENT_FRIENDLY, ServiceRating.AGENT_FRIENDLY)
        assert rating_meets_minimum(ServiceRating.AGENT_FRIENDLY, ServiceRating.AGENT_POSSIBLE)
        assert not rating_meets_minimum(ServiceRating.AGENT_FRIENDLY, ServiceRating.AGENT_NATIVE)


# ---------------------------------------------------------------------------
# CriteriaGate tests
# ---------------------------------------------------------------------------


def _mock_response(score: int, alternatives: list[str] | None = None):
    """Create a mock httpx response."""
    data = {"score": score}
    if alternatives:
        data["alternatives"] = alternatives
    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.raise_for_status.return_value = None
    return mock_resp


class TestCriteriaGate:
    def test_check_allowed(self):
        gate = CriteriaGate(api_key="clv_test", min_rating="AGENT_FRIENDLY")

        with patch.object(gate, "_fetch_score", return_value={"score": 85}):
            result = gate.check("https://api.example.com")

        assert result.allowed is True
        assert result.score == 85
        assert result.rating == ServiceRating.AGENT_FRIENDLY
        assert "permitted" in result.reason

    def test_check_blocked(self):
        gate = CriteriaGate(api_key="clv_test", min_rating="AGENT_FRIENDLY")

        with patch.object(
            gate,
            "_fetch_score",
            return_value={"score": 30, "alternatives": ["https://alt.example.com"]},
        ):
            result = gate.check("https://hostile.example.com")

        assert result.allowed is False
        assert result.score == 30
        assert result.rating == ServiceRating.AGENT_HOSTILE
        assert "BLOCKED" in result.reason
        assert "https://alt.example.com" in result.alternatives

    def test_check_fallback_on_api_error(self):
        gate = CriteriaGate(api_key="clv_test")

        with patch.object(gate, "_fetch_score", side_effect=Exception("timeout")):
            result = gate.check("https://api.example.com")

        assert result.allowed is True
        assert result.score is None
        assert "fallback" in result.reason.lower()

    def test_cache_hit(self):
        gate = CriteriaGate(api_key="clv_test", cache_ttl=3600)

        with patch.object(gate, "_fetch_score", return_value={"score": 92}) as mock_fetch:
            r1 = gate.check("https://api.example.com")
            r2 = gate.check("https://api.example.com")

        # Only one API call should have been made
        mock_fetch.assert_called_once()
        assert r1.cached is False
        assert r2.cached is True
        assert r2.score == 92

    def test_cache_expiry(self):
        gate = CriteriaGate(api_key="clv_test", cache_ttl=1)

        with patch.object(gate, "_fetch_score", return_value={"score": 75}) as mock_fetch:
            gate.check("https://api.example.com")

            # Manually expire the cache entry
            for key in gate._cache:
                result, _ = gate._cache[key]
                gate._cache[key] = (result, time.monotonic() - 1)

            gate.check("https://api.example.com")

        assert mock_fetch.call_count == 2

    def test_cache_disabled(self):
        gate = CriteriaGate(api_key="clv_test", cache_ttl=0)

        with patch.object(gate, "_fetch_score", return_value={"score": 80}) as mock_fetch:
            gate.check("https://api.example.com")
            gate.check("https://api.example.com")

        assert mock_fetch.call_count == 2

    def test_clear_cache(self):
        gate = CriteriaGate(api_key="clv_test", cache_ttl=3600)

        with patch.object(gate, "_fetch_score", return_value={"score": 80}) as mock_fetch:
            gate.check("https://api.example.com")
            gate.clear_cache()
            gate.check("https://api.example.com")

        assert mock_fetch.call_count == 2

    def test_min_rating_as_string(self):
        gate = CriteriaGate(api_key="clv_test", min_rating="AGENT_NATIVE")
        assert gate.min_rating == ServiceRating.AGENT_NATIVE

    def test_min_rating_as_enum(self):
        gate = CriteriaGate(api_key="clv_test", min_rating=ServiceRating.AGENT_POSSIBLE)
        assert gate.min_rating == ServiceRating.AGENT_POSSIBLE


# ---------------------------------------------------------------------------
# GatedTool tests
# ---------------------------------------------------------------------------


class _DummyTool:
    """Minimal stand-in for a LangChain BaseTool."""

    name = "dummy_search"
    description = "A dummy search tool"
    args_schema = None
    metadata: dict[str, Any] = {}

    def _run(self, *args, **kwargs):
        return "search result: ok"

    async def _arun(self, *args, **kwargs):
        return "async search result: ok"


class TestGatedTool:
    def _make_gate(self, score: int, alternatives: list[str] | None = None):
        gate = CriteriaGate(api_key="clv_test", min_rating="AGENT_FRIENDLY")
        data: dict[str, Any] = {"score": score}
        if alternatives:
            data["alternatives"] = alternatives
        patch_obj = patch.object(gate, "_fetch_score", return_value=data)
        return gate, patch_obj

    def test_allowed_invocation(self):
        gate, mock_ctx = self._make_gate(score=85)
        dummy = _DummyTool()

        gated = GatedTool(
            tool=dummy,  # type: ignore[arg-type]
            gate=gate,
            service_url="https://api.example.com",
        )

        with mock_ctx:
            result = gated._run(query="test")

        assert result == "search result: ok"

    def test_blocked_invocation_raises(self):
        gate, mock_ctx = self._make_gate(
            score=30, alternatives=["https://better.example.com"]
        )
        dummy = _DummyTool()

        gated = GatedTool(
            tool=dummy,  # type: ignore[arg-type]
            gate=gate,
            service_url="https://hostile.example.com",
        )

        with mock_ctx, pytest.raises(GateBlockedError) as exc_info:
            gated._run(query="test")

        assert exc_info.value.gate_result.score == 30
        assert "better.example.com" in str(exc_info.value)

    def test_blocked_invocation_returns_string(self):
        gate, mock_ctx = self._make_gate(score=30)
        dummy = _DummyTool()

        gated = GatedTool(
            tool=dummy,  # type: ignore[arg-type]
            gate=gate,
            service_url="https://hostile.example.com",
            raise_on_block=False,
        )

        with mock_ctx:
            result = gated._run(query="test")

        assert "BLOCKED" in result

    def test_missing_service_url_raises(self):
        gate = CriteriaGate(api_key="clv_test")
        dummy = _DummyTool()

        gated = GatedTool(tool=dummy, gate=gate)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="No service_url"):
            gated._run(query="test")

    def test_service_url_from_metadata(self):
        gate, mock_ctx = self._make_gate(score=80)
        dummy = _DummyTool()
        dummy.metadata = {"service_url": "https://meta.example.com"}

        gated = GatedTool(tool=dummy, gate=gate)  # type: ignore[arg-type]

        with mock_ctx:
            result = gated._run(query="test")

        assert result == "search result: ok"

    def test_delegates_name_and_description(self):
        gate = CriteriaGate(api_key="clv_test")
        dummy = _DummyTool()

        gated = GatedTool(
            tool=dummy,  # type: ignore[arg-type]
            gate=gate,
            service_url="https://example.com",
        )

        assert gated.name == "dummy_search"
        assert gated.description == "A dummy search tool"


# ---------------------------------------------------------------------------
# GateResult tests
# ---------------------------------------------------------------------------


class TestGateResult:
    def test_immutable(self):
        r = GateResult(
            allowed=True,
            score=90,
            rating=ServiceRating.AGENT_NATIVE,
            service_url="https://example.com",
            reason="test",
        )
        with pytest.raises(AttributeError):
            r.allowed = False  # type: ignore[misc]

    def test_defaults(self):
        r = GateResult(
            allowed=True,
            score=80,
            rating=ServiceRating.AGENT_FRIENDLY,
            service_url="https://example.com",
            reason="ok",
        )
        assert r.alternatives == []
        assert r.cached is False
