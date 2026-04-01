"""Extended E2E tests for the Clarvia AEO Scanner API.

Covers additional endpoints and error cases not in test_e2e.py:
- /v1/search, /v1/stats, /v1/leaderboard (marked slow: loads 15k+ tools)
- /v1/history/{tool_slug} and /v1/history (no data loading, fast)
- /v1/featured, /v1/methodology, /v1/compare
- Error cases: invalid params, nonexistent resources, boundary values
- MCP server tool grade logic (no network, fast)

Tests marked @pytest.mark.slow trigger loading prebuilt-scans.json (5MB,
15k items) with O(n^2) dedup. Run them with:
    pytest tests/test_e2e_extended.py -m slow

Fast tests (no data loading):
    pytest tests/test_e2e_extended.py -m "not slow"
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ===================================================================
# FAST TESTS — no data loading required
# ===================================================================


class TestMethodologyEndpoint:
    """Tests for /v1/methodology — static response, no data loading."""

    async def test_methodology_returns_docs(self, client):
        resp = await client.get("/v1/methodology")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "dimensions" in data
        assert "total_score" in data
        assert data["total_score"] == 100

    async def test_methodology_has_dimension_details(self, client):
        resp = await client.get("/v1/methodology")
        dims = resp.json()["dimensions"]
        assert len(dims) >= 4
        for name, info in dims.items():
            assert "max" in info
            assert "description" in info


class TestHistoryEndpoint:
    """Tests for /v1/history — uses JSONL file, no prebuilt-scans loading."""

    async def test_tool_history_nonexistent(self, client):
        resp = await client.get("/v1/history/this-tool-does-not-exist-xyz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool_slug"] == "this-tool-does-not-exist-xyz"
        assert data["scans"] == []
        assert data["total"] == 0

    async def test_tool_history_delta_nonexistent(self, client):
        resp = await client.get("/v1/history/nonexistent-tool-slug/delta")
        assert resp.status_code == 200
        data = resp.json()
        assert data["delta"] is None

    async def test_platform_history(self, client):
        resp = await client.get("/v1/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "snapshots" in data
        assert "total_days" in data
        assert isinstance(data["snapshots"], list)

    async def test_platform_history_days_param(self, client):
        resp = await client.get("/v1/history", params={"days": 7})
        assert resp.status_code == 200
        assert len(resp.json()["snapshots"]) <= 7

    async def test_platform_history_max_days(self, client):
        resp = await client.get("/v1/history", params={"days": 365})
        assert resp.status_code == 200

    async def test_platform_history_invalid_days(self, client):
        resp = await client.get("/v1/history", params={"days": 0})
        assert resp.status_code == 422

    async def test_tool_history_empty_slug(self, client):
        """Empty-ish slug returns 400."""
        resp = await client.get("/v1/history/   ")
        # Either 400 (explicit check) or 200 with empty results
        assert resp.status_code in (200, 400)


class TestScanErrorCases:
    """Error cases for /api/scan — validation only, no data loading."""

    async def test_scan_empty_body(self, client):
        resp = await client.post("/api/scan", json={})
        assert resp.status_code in (400, 422)

    async def test_scan_no_body(self, client):
        resp = await client.post("/api/scan")
        assert resp.status_code in (400, 422)

    async def test_scan_xss_in_url(self, client):
        xss = "<script>alert('xss')</script>"
        resp = await client.post("/api/scan", json={"url": xss})
        assert "<script>" not in resp.text

    async def test_wrong_method_on_scan(self, client):
        resp = await client.get("/api/scan")
        assert resp.status_code in (404, 405)

    async def test_scan_null_url(self, client):
        resp = await client.post("/api/scan", json={"url": None})
        assert resp.status_code in (400, 422)

    async def test_scan_numeric_url(self, client):
        resp = await client.post("/api/scan", json={"url": 12345})
        assert resp.status_code in (400, 422)


class TestValidationErrors:
    """FastAPI validation errors — triggered before route handler, no data loading."""

    async def test_services_invalid_limit(self, client):
        resp = await client.get("/v1/services", params={"limit": -1})
        assert resp.status_code == 422

    async def test_services_limit_too_high(self, client):
        resp = await client.get("/v1/services", params={"limit": 999})
        assert resp.status_code == 422

    async def test_services_invalid_sort(self, client):
        resp = await client.get("/v1/services", params={"sort": "invalid_sort_value"})
        assert resp.status_code == 422

    async def test_services_negative_offset(self, client):
        resp = await client.get("/v1/services", params={"offset": -5})
        assert resp.status_code == 422

    async def test_leaderboard_limit_zero(self, client):
        resp = await client.get("/v1/leaderboard", params={"limit": 0})
        assert resp.status_code == 422

    async def test_leaderboard_limit_too_high(self, client):
        resp = await client.get("/v1/leaderboard", params={"limit": 999})
        assert resp.status_code == 422

    async def test_search_min_score_too_high(self, client):
        resp = await client.get("/v1/search", params={"min_score": 200})
        assert resp.status_code == 422

    async def test_search_negative_min_score(self, client):
        resp = await client.get("/v1/search", params={"min_score": -10})
        assert resp.status_code == 422


class TestMiscEndpoints:
    """Misc endpoints that don't need data loading."""

    async def test_nonexistent_endpoint(self, client):
        resp = await client.get("/v1/this_endpoint_does_not_exist")
        assert resp.status_code == 404

    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_waitlist(self, client):
        resp = await client.post("/api/waitlist", json={"email": "extended-test@example.com"})
        assert resp.status_code == 200


class TestMCPServerTools:
    """MCP server tool grade logic — pure functions, no network or data loading."""

    def test_grade_from_score_native(self):
        from app.mcp_server import _grade_from_score
        assert _grade_from_score(95) == "AGENT_NATIVE"
        assert _grade_from_score(90) == "AGENT_NATIVE"
        assert _grade_from_score(100) == "AGENT_NATIVE"

    def test_grade_from_score_friendly(self):
        from app.mcp_server import _grade_from_score
        assert _grade_from_score(70) == "AGENT_FRIENDLY"
        assert _grade_from_score(85) == "AGENT_FRIENDLY"
        assert _grade_from_score(89) == "AGENT_FRIENDLY"

    def test_grade_from_score_possible(self):
        from app.mcp_server import _grade_from_score
        assert _grade_from_score(50) == "AGENT_POSSIBLE"
        assert _grade_from_score(65) == "AGENT_POSSIBLE"
        assert _grade_from_score(69) == "AGENT_POSSIBLE"

    def test_grade_from_score_hostile(self):
        from app.mcp_server import _grade_from_score
        assert _grade_from_score(0) == "AGENT_HOSTILE"
        assert _grade_from_score(49) == "AGENT_HOSTILE"
        assert _grade_from_score(25) == "AGENT_HOSTILE"

    def test_grade_order_defined(self):
        from app.mcp_server import _GRADE_ORDER
        assert _GRADE_ORDER == [
            "AGENT_HOSTILE", "AGENT_POSSIBLE", "AGENT_FRIENDLY", "AGENT_NATIVE"
        ]

    def test_grade_order_monotonic(self):
        """Higher scores always produce equal or higher grade index."""
        from app.mcp_server import _grade_from_score, _GRADE_ORDER
        prev_idx = 0
        for score in range(0, 101):
            grade = _grade_from_score(score)
            idx = _GRADE_ORDER.index(grade)
            assert idx >= prev_idx, f"Score {score} produced lower grade than score {score-1}"
            prev_idx = idx


class TestScanHistorySlugLogic:
    """Test the slug conversion logic from scan_history_routes — no data loading."""

    def test_url_to_slug(self):
        from app.routes.scan_history_routes import _url_to_slug
        assert _url_to_slug("https://github.com/modelcontextprotocol/servers") == "github-com-modelcontextprotocol-servers"
        assert _url_to_slug("https://docs.cursor.com") == "docs-cursor-com"
        assert _url_to_slug("https://example.com/") == "example-com"

    def test_url_to_slug_case_insensitive(self):
        from app.routes.scan_history_routes import _url_to_slug
        assert _url_to_slug("https://GitHub.COM/Foo/Bar") == "github-com-foo-bar"

    def test_url_to_slug_strips_scheme(self):
        from app.routes.scan_history_routes import _url_to_slug
        assert _url_to_slug("http://example.com") == _url_to_slug("https://example.com")

    def test_slug_matches(self):
        from app.routes.scan_history_routes import _slug_matches
        assert _slug_matches("https://github.com/foo/bar", "github-com-foo-bar")
        assert not _slug_matches("https://github.com/foo/bar", "github-com-baz-qux")


class TestDeduplicateLogic:
    """Test dedup functions — pure logic, pre-loaded data not needed."""

    def _dedup(self, services):
        from app.routes.index_routes import _deduplicate_services
        return _deduplicate_services(services)

    def _make(self, name, url, score=50):
        return {"scan_id": f"scan_{name}", "service_name": name, "url": url, "clarvia_score": score}

    def test_empty(self):
        assert self._dedup([]) == []

    def test_single_item(self):
        result = self._dedup([self._make("A", "https://example.com", 50)])
        assert len(result) == 1

    def test_exact_url_keeps_higher(self):
        result = self._dedup([
            self._make("A", "https://example.com", 30),
            self._make("B", "https://example.com", 70),
        ])
        assert len(result) == 1
        assert result[0]["clarvia_score"] == 70

    def test_different_urls_kept(self):
        result = self._dedup([
            self._make("A", "https://a.com", 50),
            self._make("B", "https://b.com", 50),
        ])
        assert len(result) == 2

    def test_trailing_slash_normalized(self):
        result = self._dedup([
            self._make("A", "https://example.com/tool/", 30),
            self._make("B", "https://example.com/tool", 50),
        ])
        assert len(result) == 1

    def test_case_insensitive_urls(self):
        result = self._dedup([
            self._make("A", "https://GitHub.COM/Foo", 30),
            self._make("B", "https://github.com/foo", 70),
        ])
        assert len(result) == 1
        assert result[0]["clarvia_score"] == 70

    def test_no_url_entries_preserved(self):
        result = self._dedup([
            self._make("A", "", 50),
            self._make("B", "", 60),
        ])
        assert len(result) == 2


# ===================================================================
# SLOW TESTS — require loading 15k+ tools from prebuilt-scans.json
# ===================================================================


@pytest.mark.slow
class TestSearchEndpointSlow:
    """Tests for /v1/search — triggers data loading."""

    async def test_search_basic(self, client):
        resp = await client.get("/v1/search", params={"source": "scanned", "limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert "services" in data
        assert "total" in data
        assert "pagination" in data

    async def test_search_with_q_param(self, client):
        resp = await client.get("/v1/search", params={"q": "github", "source": "scanned", "limit": 5})
        assert resp.status_code == 200
        assert isinstance(resp.json()["services"], list)

    async def test_search_with_query_alias(self, client):
        resp = await client.get("/v1/search", params={"query": "email", "source": "scanned", "limit": 5})
        assert resp.status_code == 200

    async def test_search_with_min_score(self, client):
        resp = await client.get("/v1/search", params={"min_score": 70, "source": "scanned", "limit": 10})
        assert resp.status_code == 200
        for svc in resp.json()["services"]:
            assert svc["clarvia_score"] >= 70

    async def test_search_with_category_filter(self, client):
        resp = await client.get("/v1/search", params={"category": "ai", "source": "scanned", "limit": 5})
        assert resp.status_code == 200
        for svc in resp.json()["services"]:
            assert svc["category"] == "ai"

    async def test_search_with_service_type_filter(self, client):
        resp = await client.get("/v1/search", params={"service_type": "mcp_server", "source": "scanned", "limit": 5})
        assert resp.status_code == 200
        for svc in resp.json()["services"]:
            assert svc["service_type"] == "mcp_server"

    async def test_search_nonexistent_keyword(self, client):
        resp = await client.get("/v1/search", params={"q": "zzz_absolutely_nothing_here_xyz", "source": "scanned"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_search_limit_respected(self, client):
        resp = await client.get("/v1/search", params={"limit": 3, "source": "scanned"})
        assert resp.status_code == 200
        assert len(resp.json()["services"]) <= 3

    async def test_search_sql_injection(self, client):
        resp = await client.get("/v1/search", params={"q": "'; DROP TABLE services; --", "source": "scanned"})
        assert resp.status_code == 200

    async def test_search_unicode_query(self, client):
        resp = await client.get("/v1/search", params={"q": "도구 검색 테스트", "source": "scanned"})
        assert resp.status_code == 200

    async def test_search_very_long_query(self, client):
        long_q = "a" * 500
        resp = await client.get("/v1/search", params={"q": long_q, "source": "scanned"})
        assert resp.status_code == 200


@pytest.mark.slow
class TestStatsEndpointSlow:
    """Tests for /v1/stats — triggers data loading."""

    async def test_stats_scanned(self, client):
        resp = await client.get("/v1/stats", params={"source": "scanned"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_services" in data
        assert "avg_score" in data
        assert "by_category" in data
        assert isinstance(data["total_services"], int)
        assert data["total_services"] >= 0
        assert "scanned_count" not in data

    async def test_stats_score_distribution(self, client):
        resp = await client.get("/v1/stats", params={"source": "scanned"})
        data = resp.json()
        if data["total_services"] > 0:
            dist = data["score_distribution"]
            for bucket in ("excellent", "strong", "moderate", "weak"):
                assert bucket in dist
                assert dist[bucket] >= 0
            assert sum(dist.values()) == data["total_services"]

    async def test_stats_by_category_structure(self, client):
        resp = await client.get("/v1/stats", params={"source": "scanned"})
        data = resp.json()
        for cat, info in data["by_category"].items():
            assert "count" in info
            assert "avg_score" in info
            assert info["count"] > 0
            assert 0 <= info["avg_score"] <= 100


@pytest.mark.slow
class TestLeaderboardEndpointSlow:
    """Tests for /v1/leaderboard — triggers data loading."""

    async def test_leaderboard_default(self, client):
        resp = await client.get("/v1/leaderboard", params={"limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert "leaderboard" in data
        assert "total" in data

    async def test_leaderboard_sorted_desc(self, client):
        resp = await client.get("/v1/leaderboard", params={"limit": 10})
        entries = resp.json()["leaderboard"]
        if len(entries) >= 2:
            for i in range(len(entries) - 1):
                assert entries[i]["score"] >= entries[i + 1]["score"]

    async def test_leaderboard_rank_sequential(self, client):
        resp = await client.get("/v1/leaderboard", params={"limit": 10})
        for i, entry in enumerate(resp.json()["leaderboard"]):
            assert entry["rank"] == i + 1

    async def test_leaderboard_entry_structure(self, client):
        resp = await client.get("/v1/leaderboard", params={"limit": 5})
        for entry in resp.json()["leaderboard"]:
            for key in ("rank", "name", "score", "clarvia_score", "rating", "category", "scan_id"):
                assert key in entry
            assert entry["score"] == entry["clarvia_score"]

    async def test_leaderboard_category_filter(self, client):
        resp = await client.get("/v1/leaderboard", params={"category": "ai", "limit": 5})
        assert resp.status_code == 200
        for entry in resp.json()["leaderboard"]:
            assert entry["category"] == "ai"


@pytest.mark.slow
class TestServiceDetailSlow:
    """Tests for service detail — triggers data loading."""

    async def test_service_detail_nonexistent(self, client):
        resp = await client.get("/v1/services/___nonexistent_scan_id___")
        assert resp.status_code == 404

    async def test_pagination_offset_beyond_total(self, client):
        resp = await client.get("/v1/services", params={"offset": 999999, "limit": 10, "source": "scanned"})
        assert resp.status_code == 200
        assert resp.json()["services"] == []

    async def test_pagination_first_page(self, client):
        resp = await client.get("/v1/services", params={"offset": 0, "limit": 5, "source": "scanned"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["limit"] == 5


@pytest.mark.slow
class TestCrossEndpointConsistency:
    """Cross-endpoint consistency checks — require data loading."""

    async def test_stats_total_matches_services(self, client):
        stats_resp = await client.get("/v1/stats", params={"source": "scanned"})
        # include_archived=true so the count matches stats (which counts all)
        services_resp = await client.get("/v1/services", params={"limit": 1, "source": "scanned", "include_archived": "true"})
        assert stats_resp.status_code == 200
        assert services_resp.status_code == 200
        assert stats_resp.json()["total_services"] == services_resp.json()["total"]

    async def test_search_and_services_same_structure(self, client):
        search_resp = await client.get("/v1/search", params={"limit": 3, "source": "scanned"})
        services_resp = await client.get("/v1/services", params={"limit": 3, "source": "scanned"})
        assert search_resp.status_code == 200
        assert services_resp.status_code == 200
        for key in ("services", "total", "pagination"):
            assert key in search_resp.json()
            assert key in services_resp.json()

    async def test_categories_consistent_with_stats(self, client):
        cat_resp = await client.get("/v1/categories")
        stats_resp = await client.get("/v1/stats", params={"source": "scanned"})
        assert cat_resp.status_code == 200
        assert stats_resp.status_code == 200
        cat_names = {c["name"] for c in cat_resp.json()["categories"]}
        for cat in stats_resp.json()["by_category"]:
            assert cat in cat_names


@pytest.mark.slow
class TestFeaturedEndpointSlow:
    """Tests for /v1/featured — triggers data loading."""

    async def test_featured_basic(self, client):
        resp = await client.get("/v1/featured")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_top_10" in data
        assert "category_picks" in data
        assert "total_categories" in data

    async def test_featured_top(self, client):
        resp = await client.get("/v1/featured/top", params={"limit": 10})
        assert resp.status_code == 200


@pytest.mark.slow
class TestCompareEndpointSlow:
    """Tests for /v1/compare — triggers data loading."""

    async def test_compare_no_params(self, client):
        resp = await client.get("/v1/compare")
        assert resp.status_code == 400

    async def test_compare_with_nonexistent_names(self, client):
        resp = await client.get("/v1/compare", params={"names": "nonexistent_a,nonexistent_b"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


@pytest.mark.slow
class TestScoreEndpointSlow:
    """Tests for /v1/score — triggers data loading."""

    async def test_score_unknown_url(self, client):
        resp = await client.get("/v1/score", params={"url": "https://totally-unknown-xyz.example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("found") is False or data.get("clarvia_score", 0) == 0
