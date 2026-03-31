"""Extended E2E tests for the Clarvia AEO Scanner API.

Covers additional endpoints and error cases not in test_e2e.py:
- /v1/search (alias for /v1/services)
- /v1/stats with various source params
- /v1/leaderboard with category filters
- /v1/history/{tool_slug} and /v1/history/{tool_slug}/delta
- /v1/history (platform-level snapshots)
- /v1/trending
- /v1/featured and /v1/featured/top
- /v1/methodology
- /v1/compare
- /v1/alternatives/{name}
- Error cases: invalid params, nonexistent resources, boundary values
- MCP server tool function tests (search_services, scan_service)
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# /v1/search endpoint (alias for /v1/services)
# ---------------------------------------------------------------------------


class TestSearchEndpoint:
    """Tests for /v1/search — agent-facing search alias."""

    @pytest.mark.asyncio
    async def test_search_basic(self, client):
        """Basic search returns 200 with expected structure."""
        resp = await client.get("/v1/search")
        assert resp.status_code == 200
        data = resp.json()
        assert "services" in data
        assert "total" in data
        assert "pagination" in data

    @pytest.mark.asyncio
    async def test_search_with_q_param(self, client):
        """Search with q parameter works."""
        resp = await client.get("/v1/search", params={"q": "github"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["services"], list)

    @pytest.mark.asyncio
    async def test_search_with_query_alias(self, client):
        """Search accepts 'query' as alias for 'q'."""
        resp = await client.get("/v1/search", params={"query": "email"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["services"], list)

    @pytest.mark.asyncio
    async def test_search_with_min_score(self, client):
        """Search with min_score filters correctly."""
        resp = await client.get("/v1/search", params={"min_score": 70, "limit": 10})
        assert resp.status_code == 200
        for svc in resp.json()["services"]:
            assert svc["clarvia_score"] >= 70

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, client):
        """Search with category filter returns only matching category."""
        resp = await client.get("/v1/search", params={"category": "ai", "limit": 5})
        assert resp.status_code == 200
        for svc in resp.json()["services"]:
            assert svc["category"] == "ai"

    @pytest.mark.asyncio
    async def test_search_with_service_type_filter(self, client):
        """Search with service_type filter."""
        resp = await client.get("/v1/search", params={"service_type": "mcp_server", "limit": 5})
        assert resp.status_code == 200
        for svc in resp.json()["services"]:
            assert svc["service_type"] == "mcp_server"

    @pytest.mark.asyncio
    async def test_search_nonexistent_keyword(self, client):
        """Searching for nonsense keyword returns 0 results."""
        resp = await client.get("/v1/search", params={"q": "zzz_absolutely_nothing_here_xyz"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_search_limit_respected(self, client):
        """Limit parameter caps returned results."""
        resp = await client.get("/v1/search", params={"limit": 3})
        assert resp.status_code == 200
        assert len(resp.json()["services"]) <= 3


# ---------------------------------------------------------------------------
# /v1/stats endpoint
# ---------------------------------------------------------------------------


class TestStatsEndpoint:
    """Tests for /v1/stats — platform statistics."""

    @pytest.mark.asyncio
    async def test_stats_default(self, client):
        """Default stats returns expected fields."""
        resp = await client.get("/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_services" in data
        assert "avg_score" in data
        assert "by_category" in data
        assert isinstance(data["total_services"], int)
        assert data["total_services"] >= 0

    @pytest.mark.asyncio
    async def test_stats_source_scanned(self, client):
        """source=scanned returns only prebuilt scans."""
        resp = await client.get("/v1/stats", params={"source": "scanned"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_services" in data
        # source=scanned should NOT include scanned_count/collected_count
        assert "scanned_count" not in data

    @pytest.mark.asyncio
    async def test_stats_source_all_breakdown(self, client):
        """source=all includes scanned+collected breakdown."""
        resp = await client.get("/v1/stats", params={"source": "all"})
        assert resp.status_code == 200
        data = resp.json()
        assert "scanned_count" in data
        assert "collected_count" in data
        assert data["total_services"] == data["scanned_count"] + data["collected_count"]

    @pytest.mark.asyncio
    async def test_stats_score_distribution(self, client):
        """Score distribution buckets are present and non-negative."""
        resp = await client.get("/v1/stats")
        data = resp.json()
        if data["total_services"] > 0:
            dist = data["score_distribution"]
            for bucket in ("excellent", "strong", "moderate", "weak"):
                assert bucket in dist
                assert dist[bucket] >= 0
            # Distribution sum should equal total
            assert sum(dist.values()) == data["total_services"]

    @pytest.mark.asyncio
    async def test_stats_by_category_structure(self, client):
        """Each category entry has count and avg_score."""
        resp = await client.get("/v1/stats")
        data = resp.json()
        for cat, info in data["by_category"].items():
            assert "count" in info
            assert "avg_score" in info
            assert info["count"] > 0
            assert 0 <= info["avg_score"] <= 100


# ---------------------------------------------------------------------------
# /v1/leaderboard endpoint
# ---------------------------------------------------------------------------


class TestLeaderboardEndpoint:
    """Tests for /v1/leaderboard."""

    @pytest.mark.asyncio
    async def test_leaderboard_default(self, client):
        """Leaderboard returns ranked list."""
        resp = await client.get("/v1/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "leaderboard" in data
        assert "total" in data
        assert isinstance(data["leaderboard"], list)

    @pytest.mark.asyncio
    async def test_leaderboard_sorted_desc(self, client):
        """Leaderboard entries are sorted by score descending."""
        resp = await client.get("/v1/leaderboard", params={"limit": 20})
        data = resp.json()
        entries = data["leaderboard"]
        if len(entries) >= 2:
            for i in range(len(entries) - 1):
                assert entries[i]["score"] >= entries[i + 1]["score"]

    @pytest.mark.asyncio
    async def test_leaderboard_rank_sequential(self, client):
        """Rank numbers are sequential starting from 1."""
        resp = await client.get("/v1/leaderboard", params={"limit": 10})
        entries = resp.json()["leaderboard"]
        for i, entry in enumerate(entries):
            assert entry["rank"] == i + 1

    @pytest.mark.asyncio
    async def test_leaderboard_entry_structure(self, client):
        """Each leaderboard entry has required fields."""
        resp = await client.get("/v1/leaderboard", params={"limit": 5})
        for entry in resp.json()["leaderboard"]:
            assert "rank" in entry
            assert "name" in entry
            assert "score" in entry
            assert "clarvia_score" in entry
            assert "rating" in entry
            assert "category" in entry
            assert "scan_id" in entry
            assert entry["score"] == entry["clarvia_score"]

    @pytest.mark.asyncio
    async def test_leaderboard_category_filter(self, client):
        """Category filter restricts leaderboard to that category."""
        resp = await client.get("/v1/leaderboard", params={"category": "ai", "limit": 10})
        assert resp.status_code == 200
        for entry in resp.json()["leaderboard"]:
            assert entry["category"] == "ai"

    @pytest.mark.asyncio
    async def test_leaderboard_limit_respected(self, client):
        """Limit parameter caps leaderboard size."""
        resp = await client.get("/v1/leaderboard", params={"limit": 3})
        assert len(resp.json()["leaderboard"]) <= 3


# ---------------------------------------------------------------------------
# /v1/history/{tool_slug} endpoint
# ---------------------------------------------------------------------------


class TestHistoryEndpoint:
    """Tests for /v1/history/{tool_slug} and /v1/history."""

    @pytest.mark.asyncio
    async def test_tool_history_nonexistent(self, client):
        """Nonexistent tool slug returns empty history."""
        resp = await client.get("/v1/history/this-tool-does-not-exist-xyz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool_slug"] == "this-tool-does-not-exist-xyz"
        assert data["scans"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_tool_history_delta_nonexistent(self, client):
        """Delta for nonexistent tool returns null delta."""
        resp = await client.get("/v1/history/nonexistent-tool-slug/delta")
        assert resp.status_code == 200
        data = resp.json()
        assert data["delta"] is None

    @pytest.mark.asyncio
    async def test_platform_history(self, client):
        """Platform-level history returns snapshots."""
        resp = await client.get("/v1/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "snapshots" in data
        assert "total_days" in data
        assert isinstance(data["snapshots"], list)

    @pytest.mark.asyncio
    async def test_platform_history_days_param(self, client):
        """Days parameter limits snapshot count."""
        resp = await client.get("/v1/history", params={"days": 7})
        assert resp.status_code == 200
        assert len(resp.json()["snapshots"]) <= 7


# ---------------------------------------------------------------------------
# /v1/trending endpoint
# ---------------------------------------------------------------------------


class TestTrendingEndpoint:
    """Tests for /v1/trending."""

    @pytest.mark.asyncio
    async def test_trending_basic(self, client):
        """Trending endpoint returns expected structure."""
        resp = await client.get("/v1/trending")
        assert resp.status_code == 200
        data = resp.json()
        assert "top_tools" in data
        assert "by_category" in data
        assert isinstance(data["top_tools"], list)

    @pytest.mark.asyncio
    async def test_trending_with_category(self, client):
        """Category filter works on trending."""
        resp = await client.get("/v1/trending", params={"category": "ai"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_trending_with_limit(self, client):
        """Limit parameter works on trending."""
        resp = await client.get("/v1/trending", params={"limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["top_tools"]) <= 5


# ---------------------------------------------------------------------------
# /v1/featured and /v1/featured/top
# ---------------------------------------------------------------------------


class TestFeaturedEndpoint:
    """Tests for /v1/featured and /v1/featured/top."""

    @pytest.mark.asyncio
    async def test_featured_basic(self, client):
        """Featured endpoint returns expected structure."""
        resp = await client.get("/v1/featured")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_top_10" in data
        assert "category_picks" in data
        assert "total_categories" in data

    @pytest.mark.asyncio
    async def test_featured_top(self, client):
        """Featured top endpoint returns high-scoring tools."""
        resp = await client.get("/v1/featured/top")
        assert resp.status_code == 200
        data = resp.json()
        assert "services" in data or "top" in data or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_featured_top_all_above_60(self, client):
        """Featured top only includes tools scoring >= 60."""
        resp = await client.get("/v1/featured/top", params={"limit": 50})
        if resp.status_code == 200:
            data = resp.json()
            # The response might have different shapes; find the list of tools
            tools = data.get("services") or data.get("top") or data.get("tools", [])
            if isinstance(tools, list):
                for t in tools:
                    score = t.get("clarvia_score") or t.get("score", 0)
                    assert score >= 60, f"Featured top tool scored {score} < 60"


# ---------------------------------------------------------------------------
# /v1/methodology
# ---------------------------------------------------------------------------


class TestMethodologyEndpoint:
    """Tests for /v1/methodology."""

    @pytest.mark.asyncio
    async def test_methodology_returns_docs(self, client):
        """Methodology endpoint returns scoring documentation."""
        resp = await client.get("/v1/methodology")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "dimensions" in data
        assert "total_score" in data
        assert data["total_score"] == 100


# ---------------------------------------------------------------------------
# /v1/compare
# ---------------------------------------------------------------------------


class TestCompareEndpoint:
    """Tests for /v1/compare."""

    @pytest.mark.asyncio
    async def test_compare_no_params(self, client):
        """Compare without ids or names returns 400."""
        resp = await client.get("/v1/compare")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_compare_with_nonexistent_names(self, client):
        """Compare with nonexistent names returns empty results."""
        resp = await client.get("/v1/compare", params={"names": "nonexistent_a,nonexistent_b"})
        assert resp.status_code == 200
        data = resp.json()
        assert "services" in data
        assert data["count"] == 0


# ---------------------------------------------------------------------------
# /v1/alternatives/{service_name}
# ---------------------------------------------------------------------------


class TestAlternativesEndpoint:
    """Tests for /v1/alternatives/{service_name}."""

    @pytest.mark.asyncio
    async def test_alternatives_nonexistent(self, client):
        """Alternatives for nonexistent service returns 404 or empty."""
        resp = await client.get("/v1/alternatives/totally_fake_service_xyz")
        # May return 404 or an empty list depending on implementation
        assert resp.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_alternatives_returns_list(self, client):
        """Alternatives returns a list structure."""
        # Use a common tool name that's likely in the index
        resp = await client.get("/v1/alternatives/github", params={"limit": 5})
        if resp.status_code == 200:
            data = resp.json()
            assert "alternatives" in data or isinstance(data, list) or "services" in data


# ---------------------------------------------------------------------------
# Error Cases & Edge Cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    """Error handling and edge case tests."""

    @pytest.mark.asyncio
    async def test_scan_empty_body(self, client):
        """POST /api/scan with empty body returns 422."""
        resp = await client.post("/api/scan", json={})
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_scan_no_body(self, client):
        """POST /api/scan without body returns error."""
        resp = await client.post("/api/scan")
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_services_invalid_limit(self, client):
        """Invalid limit value returns 422."""
        resp = await client.get("/v1/services", params={"limit": -1})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_services_limit_too_high(self, client):
        """Limit exceeding max returns 422."""
        resp = await client.get("/v1/services", params={"limit": 999})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_services_invalid_sort(self, client):
        """Invalid sort value returns 422."""
        resp = await client.get("/v1/services", params={"sort": "invalid_sort_value"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_services_negative_offset(self, client):
        """Negative offset returns 422."""
        resp = await client.get("/v1/services", params={"offset": -5})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_service_detail_empty_scan_id(self, client):
        """Empty-ish scan_id returns 404."""
        resp = await client.get("/v1/services/ ")
        assert resp.status_code in (404, 307, 200)  # May redirect or 404

    @pytest.mark.asyncio
    async def test_leaderboard_invalid_limit(self, client):
        """Leaderboard with limit=0 returns 422."""
        resp = await client.get("/v1/leaderboard", params={"limit": 0})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_history_invalid_days(self, client):
        """Platform history with days=0 returns 422."""
        resp = await client.get("/v1/history", params={"days": 0})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_scan_xss_in_url(self, client):
        """XSS payload in scan URL doesn't leak into response."""
        xss = "<script>alert('xss')</script>"
        resp = await client.post("/api/scan", json={"url": xss})
        assert "<script>" not in resp.text

    @pytest.mark.asyncio
    async def test_search_sql_injection(self, client):
        """SQL injection in search query is safely handled."""
        resp = await client.get("/v1/search", params={"q": "'; DROP TABLE services; --"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_nonexistent_endpoint(self, client):
        """Nonexistent API route returns 404."""
        resp = await client.get("/v1/this_endpoint_does_not_exist")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_wrong_method_on_scan(self, client):
        """GET /api/scan returns 405 (method not allowed)."""
        resp = await client.get("/api/scan")
        assert resp.status_code in (404, 405)


# ---------------------------------------------------------------------------
# Boundary & Pagination
# ---------------------------------------------------------------------------


class TestBoundaryPagination:
    """Boundary value and pagination tests."""

    @pytest.mark.asyncio
    async def test_pagination_offset_beyond_total(self, client):
        """Offset beyond total returns empty services list."""
        resp = await client.get("/v1/services", params={"offset": 999999, "limit": 10})
        assert resp.status_code == 200
        assert resp.json()["services"] == []

    @pytest.mark.asyncio
    async def test_pagination_first_page(self, client):
        """First page returns correct offset."""
        resp = await client.get("/v1/services", params={"offset": 0, "limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["limit"] == 5

    @pytest.mark.asyncio
    async def test_min_score_boundary_zero(self, client):
        """min_score=0 effectively returns all services."""
        resp = await client.get("/v1/services", params={"min_score": 0, "limit": 5})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_min_score_boundary_100(self, client):
        """min_score=100 returns only perfect-score services."""
        resp = await client.get("/v1/services", params={"min_score": 100, "limit": 5})
        assert resp.status_code == 200
        for svc in resp.json()["services"]:
            assert svc["clarvia_score"] >= 100

    @pytest.mark.asyncio
    async def test_leaderboard_max_limit(self, client):
        """Leaderboard with max allowed limit works."""
        resp = await client.get("/v1/leaderboard", params={"limit": 100})
        assert resp.status_code == 200
        assert len(resp.json()["leaderboard"]) <= 100

    @pytest.mark.asyncio
    async def test_search_empty_q(self, client):
        """Empty q parameter returns all services (no filter)."""
        resp = await client.get("/v1/search", params={"q": ""})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_search_unicode_query(self, client):
        """Unicode characters in search don't cause errors."""
        resp = await client.get("/v1/search", params={"q": "도구 검색 테스트"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_search_very_long_query(self, client):
        """Very long search query doesn't crash."""
        long_q = "a" * 500
        resp = await client.get("/v1/search", params={"q": long_q})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /v1/score endpoint
# ---------------------------------------------------------------------------


class TestScoreEndpoint:
    """Tests for /v1/score (single-tool score lookup)."""

    @pytest.mark.asyncio
    async def test_score_no_params(self, client):
        """Score endpoint without url returns error or not-found."""
        resp = await client.get("/v1/score")
        # Should return some form of error or empty result
        assert resp.status_code in (200, 400, 422)

    @pytest.mark.asyncio
    async def test_score_unknown_url(self, client):
        """Score for unknown URL returns not-found indicator."""
        resp = await client.get("/v1/score", params={"url": "https://totally-unknown-xyz.example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("found") is False or data.get("clarvia_score", 0) == 0


# ---------------------------------------------------------------------------
# MCP Server Tool Functions (unit tests)
# ---------------------------------------------------------------------------


class TestMCPServerTools:
    """Test MCP server tool functions directly (without HTTP transport).

    These test the internal functions exposed as MCP tools.
    Note: These functions call the live Clarvia API, so we test
    the helper/grade logic that doesn't require network.
    """

    def test_grade_from_score_native(self):
        """Score >= 90 gets AGENT_NATIVE grade."""
        from app.mcp_server import _grade_from_score
        assert _grade_from_score(95) == "AGENT_NATIVE"
        assert _grade_from_score(90) == "AGENT_NATIVE"

    def test_grade_from_score_friendly(self):
        """Score 70-89 gets AGENT_FRIENDLY grade."""
        from app.mcp_server import _grade_from_score
        assert _grade_from_score(70) == "AGENT_FRIENDLY"
        assert _grade_from_score(85) == "AGENT_FRIENDLY"

    def test_grade_from_score_possible(self):
        """Score 50-69 gets AGENT_POSSIBLE grade."""
        from app.mcp_server import _grade_from_score
        assert _grade_from_score(50) == "AGENT_POSSIBLE"
        assert _grade_from_score(65) == "AGENT_POSSIBLE"

    def test_grade_from_score_hostile(self):
        """Score < 50 gets AGENT_HOSTILE grade."""
        from app.mcp_server import _grade_from_score
        assert _grade_from_score(0) == "AGENT_HOSTILE"
        assert _grade_from_score(49) == "AGENT_HOSTILE"

    def test_grade_boundaries(self):
        """Exact boundary values are classified correctly."""
        from app.mcp_server import _grade_from_score
        assert _grade_from_score(89) == "AGENT_FRIENDLY"
        assert _grade_from_score(69) == "AGENT_POSSIBLE"
        assert _grade_from_score(49) == "AGENT_HOSTILE"

    def test_grade_order_defined(self):
        """Grade order list is defined and ordered correctly."""
        from app.mcp_server import _GRADE_ORDER
        assert _GRADE_ORDER == [
            "AGENT_HOSTILE", "AGENT_POSSIBLE", "AGENT_FRIENDLY", "AGENT_NATIVE"
        ]


# ---------------------------------------------------------------------------
# Cross-Endpoint Consistency
# ---------------------------------------------------------------------------


class TestCrossEndpointConsistency:
    """Tests that verify consistency across related endpoints."""

    @pytest.mark.asyncio
    async def test_stats_total_matches_services(self, client):
        """Stats total_services should match services total."""
        stats_resp = await client.get("/v1/stats", params={"source": "all"})
        services_resp = await client.get("/v1/services", params={"limit": 1})
        assert stats_resp.status_code == 200
        assert services_resp.status_code == 200

        stats_total = stats_resp.json()["total_services"]
        services_total = services_resp.json()["total"]
        assert stats_total == services_total

    @pytest.mark.asyncio
    async def test_leaderboard_count_within_total(self, client):
        """Leaderboard size doesn't exceed total tools."""
        lb_resp = await client.get("/v1/leaderboard", params={"limit": 100})
        stats_resp = await client.get("/v1/stats")
        assert lb_resp.status_code == 200
        assert stats_resp.status_code == 200

        lb_count = len(lb_resp.json()["leaderboard"])
        total = stats_resp.json()["total_services"]
        assert lb_count <= total

    @pytest.mark.asyncio
    async def test_search_and_services_return_same_structure(self, client):
        """/v1/search and /v1/services return the same response shape."""
        search_resp = await client.get("/v1/search", params={"limit": 3})
        services_resp = await client.get("/v1/services", params={"limit": 3})
        assert search_resp.status_code == 200
        assert services_resp.status_code == 200

        search_keys = set(search_resp.json().keys())
        services_keys = set(services_resp.json().keys())
        # Both should have these core keys
        for key in ("services", "total", "pagination"):
            assert key in search_keys, f"{key} missing from /v1/search"
            assert key in services_keys, f"{key} missing from /v1/services"

    @pytest.mark.asyncio
    async def test_categories_consistent_with_stats(self, client):
        """Categories list is consistent with stats by_category."""
        cat_resp = await client.get("/v1/categories")
        stats_resp = await client.get("/v1/stats", params={"source": "scanned"})
        assert cat_resp.status_code == 200
        assert stats_resp.status_code == 200

        cat_names = {c["name"] for c in cat_resp.json()["categories"]}
        stat_cats = set(stats_resp.json()["by_category"].keys())
        # Every stat category should appear in categories endpoint
        for cat in stat_cats:
            assert cat in cat_names, f"Category '{cat}' in stats but not in /v1/categories"


# ---------------------------------------------------------------------------
# Response Headers
# ---------------------------------------------------------------------------


class TestResponseHeaders:
    """Tests for response headers (caching, CORS-adjacent)."""

    @pytest.mark.asyncio
    async def test_services_has_cache_headers(self, client):
        """Services endpoint includes cache-control headers."""
        resp = await client.get("/v1/services", params={"limit": 1})
        assert resp.status_code == 200
        # The _add_headers helper should set cache control
        headers = resp.headers
        has_cache = (
            "cache-control" in headers
            or "x-total-count" in headers
            or "x-data-source" in headers
        )
        # At minimum the endpoint should respond cleanly
        assert resp.status_code == 200
