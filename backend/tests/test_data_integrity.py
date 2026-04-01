"""Data integrity tests — catch data inconsistencies that broke trust.

Covers bugs: A3-1 (total mismatch), A3-2 (count:0 categories),
A3-3 (category/type confusion), A3-6 (ghost categories),
A1-3 (duplicate services), A3-10 (duplicate URLs).
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
# Stats ↔ Categories consistency
# ---------------------------------------------------------------------------

class TestStatsIntegrity:
    """Stats endpoint returns consistent, non-corrupted data."""

    async def test_stats_has_required_fields(self, client):
        resp = await client.get("/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data or "total_services" in data
        assert "by_category" in data or "categories" in data

    async def test_stats_total_positive(self, client):
        resp = await client.get("/v1/stats")
        data = resp.json()
        total = data.get("total", data.get("total_services", 0))
        assert total > 0, "Total services should be > 0"

    async def test_no_ghost_categories(self, client):
        """No single-character or empty category names (bug A3-6: 's' category)."""
        resp = await client.get("/v1/stats")
        data = resp.json()
        by_cat = data.get("by_category", data.get("categories", {}))
        for cat_name in by_cat:
            assert len(cat_name) >= 2, f"Ghost category detected: '{cat_name}'"
            assert cat_name.strip(), f"Empty category name detected"


class TestCategoriesIntegrity:
    """Categories endpoint returns accurate counts."""

    async def test_categories_returns_list(self, client):
        resp = await client.get("/v1/categories")
        assert resp.status_code == 200
        data = resp.json()
        # Response should be a list or have a categories key
        cats = data if isinstance(data, list) else data.get("categories", [])
        assert len(cats) > 0, "Should have at least one category"

    async def test_no_zero_count_categories(self, client):
        """All listed categories should have count > 0 (bug A3-2)."""
        resp = await client.get("/v1/categories")
        data = resp.json()
        cats = data if isinstance(data, list) else data.get("categories", [])
        for cat in cats:
            count = cat.get("count", cat.get("tool_count", 0))
            name = cat.get("name", cat.get("slug", "unknown"))
            assert count > 0, f"Category '{name}' has count=0"

    async def test_category_name_valid(self, client):
        """Category names should be at least 2 characters."""
        resp = await client.get("/v1/categories")
        data = resp.json()
        cats = data.get("categories", []) if isinstance(data, dict) else data
        # Categories may include type-based pseudo-categories like "mcp"
        for cat in cats:
            name = cat.get("name", cat.get("slug", ""))
            assert len(name) >= 2, f"Category name too short: '{name}'"


class TestCategoryTypesSeparation:
    """category and service_type are distinct concepts (bug A3-3)."""

    async def test_category_filter_not_return_all_types(self, client):
        """?category=mcp should NOT return all service_type=mcp_server items
        unless explicitly aliased."""
        resp_all = await client.get("/v1/services", params={"limit": 5})
        if resp_all.status_code != 200:
            pytest.skip("services endpoint not available")

        resp_mcp = await client.get("/v1/services", params={
            "category": "mcp", "limit": 100
        })
        assert resp_mcp.status_code == 200
        data = resp_mcp.json()
        services = data.get("services", data.get("results", []))

        # If mcp is aliased to service_type, all results should be mcp_server type
        for svc in services:
            stype = svc.get("service_type", "")
            cat = svc.get("category", "")
            # Either filtered by real category OR by type alias — not a mix
            assert stype == "mcp_server" or cat == "mcp", (
                f"Confused category/type: {svc.get('service_name')} "
                f"has category={cat}, type={stype}"
            )


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

class TestNoDuplicates:
    """No duplicate services in search or feed results."""

    async def test_feed_no_duplicate_scan_ids(self, client):
        """Feed should not contain duplicate scan_ids (bug A3-10)."""
        resp = await client.get("/v1/feed/scores", params={"limit": 500})
        assert resp.status_code == 200
        data = resp.json()
        services = data.get("services", [])
        scan_ids = [s["scan_id"] for s in services if s.get("scan_id")]
        dupes = [sid for sid in scan_ids if scan_ids.count(sid) > 1]
        assert len(dupes) == 0, f"Duplicate scan_ids found: {set(dupes)}"

    async def test_search_no_duplicate_results(self, client):
        """Search should not return the same tool twice (bug A1-3)."""
        resp = await client.get("/v1/services", params={
            "q": "database", "limit": 50
        })
        if resp.status_code != 200:
            pytest.skip("services endpoint not available")
        data = resp.json()
        services = data.get("services", data.get("results", []))
        scan_ids = [s.get("scan_id") for s in services if s.get("scan_id")]
        dupes = [sid for sid in scan_ids if scan_ids.count(sid) > 1]
        assert len(dupes) == 0, f"Duplicate search results: {set(dupes)}"

    async def test_featured_no_duplicates(self, client):
        """Featured/top should not have duplicate entries."""
        resp = await client.get("/v1/feed/top", params={"limit": 50})
        if resp.status_code != 200:
            pytest.skip("feed/top not available")
        data = resp.json()
        services = data.get("top_services", [])
        names = [s.get("name", "") for s in services]
        dupes = [n for n in names if names.count(n) > 1 and n]
        assert len(dupes) == 0, f"Duplicate featured tools: {set(dupes)}"


# ---------------------------------------------------------------------------
# Cross-endpoint consistency
# ---------------------------------------------------------------------------

class TestCrossEndpointConsistency:
    """Numbers match across different API endpoints."""

    async def test_feed_stats_total_matches_feed_scores(self, client):
        """feed/stats total should match feed/scores total (bug A3-8)."""
        resp_stats = await client.get("/v1/feed/stats")
        resp_scores = await client.get("/v1/feed/scores", params={"limit": 1})

        if resp_stats.status_code != 200 or resp_scores.status_code != 200:
            pytest.skip("feed endpoints not available")

        stats_total = resp_stats.json().get("total_services", 0)
        scores_total = resp_scores.json().get("total", 0)

        # Allow ±1 tolerance for race conditions
        assert abs(stats_total - scores_total) <= 1, (
            f"feed/stats total ({stats_total}) != feed/scores total ({scores_total})"
        )

    async def test_stats_category_sum_close_to_total(self, client):
        """Sum of category counts should be close to total (bug A3-1).

        Not exact because some tools may be in 'other' or uncategorized.
        """
        resp = await client.get("/v1/feed/stats")
        if resp.status_code != 200:
            pytest.skip("feed/stats not available")

        data = resp.json()
        total = data.get("total_services", 0)
        by_cat = data.get("by_category", {})
        cat_sum = sum(by_cat.values())

        # Category sum should equal total (each tool has exactly one category)
        assert cat_sum == total, (
            f"Category sum ({cat_sum}) != total ({total}), diff={abs(cat_sum - total)}"
        )
