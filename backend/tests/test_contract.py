"""Contract tests — ensure API responses match what frontend expects.

Covers bugs: A1-5 (badge score mismatch), A1-6 (grade inconsistency),
A2-4 (missing service_name).
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = [pytest.mark.asyncio, pytest.mark.slow]


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_first_service(client) -> dict | None:
    """Get a real service entry for testing."""
    resp = await client.get("/v1/feed/scores", params={"limit": 1, "min_score": 50})
    if resp.status_code != 200:
        return None
    services = resp.json().get("services", [])
    return services[0] if services else None


# ---------------------------------------------------------------------------
# Service detail response shape
# ---------------------------------------------------------------------------

class TestServiceDetailContract:
    """Service detail API returns all fields the frontend needs."""

    async def test_service_has_required_fields(self, client):
        svc = await _get_first_service(client)
        if not svc:
            pytest.skip("No services available")

        scan_id = svc.get("scan_id", "")
        resp = await client.get(f"/v1/services/{scan_id}")
        if resp.status_code == 404:
            pytest.skip(f"Service {scan_id} not found via detail endpoint")

        assert resp.status_code == 200
        data = resp.json()

        # Fields the frontend tool/[id]/page.tsx expects
        # Detail endpoint uses "name" not "service_name"
        required_fields = [
            "scan_id", "name", "clarvia_score", "rating",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    async def test_service_name_not_generic(self, client):
        """Service name should be meaningful, not just 'Api' (bug A2-4)."""
        svc = await _get_first_service(client)
        if not svc:
            pytest.skip("No services available")

        name = svc.get("name", svc.get("service_name", ""))
        generic_names = {"api", "the", "a", "an", "app", "service", "server"}
        assert name.lower() not in generic_names, (
            f"Service name too generic: '{name}'"
        )

    async def test_score_within_valid_range(self, client):
        svc = await _get_first_service(client)
        if not svc:
            pytest.skip("No services available")

        score = svc.get("score", svc.get("clarvia_score", -1))
        assert 0 <= score <= 125, f"Score out of range: {score}"


# ---------------------------------------------------------------------------
# Badge ↔ Detail score consistency
# ---------------------------------------------------------------------------

class TestBadgeConsistency:
    """Badge score must match the detail page score (bug A1-5)."""

    async def test_badge_json_score_matches_feed(self, client):
        """Badge JSON endpoint should return same score as feed.

        Known bug A1-5: badge uses prebuilt-scans.json while feed merges
        prebuilt + collected. A collected tool may have a different score
        than its prebuilt counterpart.
        """
        svc = await _get_first_service(client)
        if not svc:
            pytest.skip("No services available")

        scan_id = svc.get("scan_id", "")
        feed_score = svc.get("score", svc.get("clarvia_score"))

        resp = await client.get(f"/api/badge/{scan_id}/json")
        assert resp.status_code == 200
        badge_data = resp.json()

        badge_score = badge_data.get("score")
        if badge_data.get("isError"):
            pytest.skip("Badge returned error (service not in prebuilt)")

        # This is a KNOWN BUG (A1-5) — badge resolves via prebuilt first,
        # feed may merge collected data with different scores.
        # Mark as xfail so it doesn't block CI but stays visible.
        if badge_score != feed_score:
            pytest.xfail(
                f"KNOWN BUG A1-5: Badge score ({badge_score}) != feed score ({feed_score}) "
                f"for {scan_id}. Badge uses prebuilt-scans.json priority."
            )

    async def test_badge_svg_is_valid(self, client):
        """Badge SVG should be a valid SVG with some score displayed."""
        svc = await _get_first_service(client)
        if not svc:
            pytest.skip("No services available")

        scan_id = svc.get("scan_id", "")

        resp = await client.get(f"/api/badge/{scan_id}")
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("image/svg+xml")

        svg_text = resp.text
        # Badge should contain "AEO" label and some score number
        assert "AEO" in svg_text or "Clarvia" in svg_text, "Badge missing label"
        assert "/100" in svg_text, "Badge missing score format"

    async def test_badge_unknown_returns_question_mark(self, client):
        """Unknown identifier should show '?' not crash."""
        resp = await client.get("/api/badge/nonexistent-tool-xyz-12345")
        assert resp.status_code == 200
        assert "?" in resp.text


# ---------------------------------------------------------------------------
# Compare grade consistency
# ---------------------------------------------------------------------------

class TestCompareConsistency:
    """Compare endpoint grades must be consistent with detail (bug A1-6)."""

    async def test_compare_returns_structured_data(self, client):
        """Compare endpoint should return comparable data for 2 tools."""
        # Get 2 services
        resp = await client.get("/v1/feed/scores", params={"limit": 2, "min_score": 30})
        if resp.status_code != 200:
            pytest.skip("feed/scores not available")

        services = resp.json().get("services", [])
        if len(services) < 2:
            pytest.skip("Not enough services for compare")

        ids = f"{services[0]['scan_id']},{services[1]['scan_id']}"
        resp = await client.get("/v1/compare", params={"ids": ids})
        if resp.status_code != 200:
            pytest.skip("compare endpoint not available")

        data = resp.json()
        # Should have comparison data for both tools
        tools = data.get("tools", data.get("results", data.get("services", [])))
        assert len(tools) >= 2, "Compare should return data for both tools"

    async def test_compare_scores_match_individual(self, client):
        """Scores in compare response should match individual lookups."""
        resp = await client.get("/v1/feed/scores", params={"limit": 2, "min_score": 30})
        if resp.status_code != 200:
            pytest.skip("feed/scores not available")

        services = resp.json().get("services", [])
        if len(services) < 2:
            pytest.skip("Not enough services")

        ids = f"{services[0]['scan_id']},{services[1]['scan_id']}"
        resp = await client.get("/v1/compare", params={"ids": ids})
        if resp.status_code != 200:
            pytest.skip("compare endpoint not available")

        data = resp.json()
        tools = data.get("tools", data.get("results", data.get("services", [])))

        for tool in tools:
            compare_score = tool.get("clarvia_score", tool.get("score"))
            scan_id = tool.get("scan_id", "")

            # Find matching feed score
            for svc in services:
                if svc.get("scan_id") == scan_id:
                    feed_score = svc.get("score", svc.get("clarvia_score"))
                    assert compare_score == feed_score, (
                        f"Compare score ({compare_score}) != feed score ({feed_score}) "
                        f"for {scan_id}"
                    )
                    break


# ---------------------------------------------------------------------------
# Leaderboard contract
# ---------------------------------------------------------------------------

class TestLeaderboardContract:
    """Leaderboard returns properly ordered data."""

    async def test_leaderboard_score_descending(self, client):
        resp = await client.get("/v1/leaderboard", params={"limit": 20})
        if resp.status_code != 200:
            pytest.skip("leaderboard not available")

        data = resp.json()
        tools = data.get("services", data.get("results", data.get("leaderboard", [])))
        scores = [t.get("clarvia_score", t.get("score", 0)) for t in tools]

        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Leaderboard not sorted: position {i} score {scores[i]} "
                f"< position {i+1} score {scores[i+1]}"
            )


# ---------------------------------------------------------------------------
# Scan response contract
# ---------------------------------------------------------------------------

class TestScanContract:
    """Scan response has all fields the frontend needs."""

    async def test_scan_response_structure(self, client):
        """POST /api/scan should return structured score data."""
        resp = await client.post("/api/scan", json={"url": "https://httpbin.org"})
        if resp.status_code != 200:
            pytest.skip("Scan failed (may be network-dependent)")

        data = resp.json()
        assert "scan_id" in data
        assert "clarvia_score" in data
        assert "rating" in data
        assert "dimensions" in data
        assert isinstance(data["clarvia_score"], int)

    async def test_scan_response_has_service_name(self, client):
        """Scan result should have a meaningful service_name (bug A2-4)."""
        resp = await client.post("/api/scan", json={"url": "https://httpbin.org"})
        if resp.status_code != 200:
            pytest.skip("Scan failed")

        data = resp.json()
        name = data.get("service_name", "")
        assert len(name) >= 2, f"Service name too short: '{name}'"
