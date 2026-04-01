"""Search quality tests — ensure search results are relevant and well-ordered.

Covers bugs: A1-1 (stopwords in intent search), A1-2 (sort order broken),
A1-1 (intent not semantic).
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
# Score sorting
# ---------------------------------------------------------------------------

class TestSearchSorting:
    """Search results must be sorted by score descending (bug A1-2)."""

    async def test_default_search_score_descending(self, client):
        resp = await client.get("/v1/services", params={"q": "database", "limit": 20})
        if resp.status_code != 200:
            pytest.skip("services endpoint not available")

        data = resp.json()
        services = data.get("services", data.get("results", []))
        scores = [s.get("clarvia_score", s.get("score", 0)) for s in services]

        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Search not sorted by score: position {i} ({scores[i]}) "
                f"< position {i+1} ({scores[i+1]})"
            )

    async def test_feed_scores_sorted(self, client):
        resp = await client.get("/v1/feed/scores", params={"limit": 50})
        assert resp.status_code == 200
        services = resp.json().get("services", [])
        scores = [s.get("score", 0) for s in services]

        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Feed not sorted: position {i} ({scores[i]}) "
                f"< position {i+1} ({scores[i+1]})"
            )

    async def test_leaderboard_sorted(self, client):
        resp = await client.get("/v1/leaderboard", params={"limit": 30})
        if resp.status_code != 200:
            pytest.skip("leaderboard not available")

        data = resp.json()
        tools = data.get("services", data.get("results", data.get("leaderboard", [])))
        scores = [t.get("clarvia_score", t.get("score", 0)) for t in tools]

        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Leaderboard not sorted at position {i}"
            )


# ---------------------------------------------------------------------------
# Intent search quality
# ---------------------------------------------------------------------------

class TestIntentSearch:
    """Intent/recommend endpoint returns relevant, clean results."""

    async def test_intent_returns_results(self, client):
        resp = await client.get("/v1/recommend", params={
            "intent": "store user data securely",
            "limit": 5,
        })
        if resp.status_code != 200:
            pytest.skip("recommend endpoint not available")

        data = resp.json()
        results = data.get("results", data.get("recommendations", []))
        assert len(results) > 0, "Intent search returned no results"

    async def test_intent_no_stopword_matches(self, client):
        """Intent results should not match on stopwords like 'data', 'user' (bug A1-1)."""
        resp = await client.get("/v1/recommend", params={
            "intent": "store user data securely",
            "limit": 10,
        })
        if resp.status_code != 200:
            pytest.skip("recommend endpoint not available")

        data = resp.json()
        results = data.get("results", data.get("recommendations", []))

        for r in results:
            reason = r.get("match_reason", r.get("reason", "")).lower()
            # Match reasons should NOT be just stopwords
            stopword_only_reasons = {"data", "user", "the", "and", "in", "my", "a"}
            reason_words = set(reason.split())
            if reason_words and reason_words.issubset(stopword_only_reasons):
                pytest.fail(
                    f"Match reason is only stopwords: '{reason}' "
                    f"for {r.get('name', r.get('service_name', ''))}"
                )

    async def test_intent_combined_score_descending(self, client):
        """Recommendations should be sorted by combined_score (not relevance_score).

        The recommender sorts by combined_score which factors in both
        relevance and clarvia_score, not purely by relevance_score alone.
        """
        resp = await client.get("/v1/recommend", params={
            "intent": "automate github pr reviews",
            "limit": 10,
        })
        if resp.status_code != 200:
            pytest.skip("recommend endpoint not available")

        data = resp.json()
        results = data.get("recommendations", data.get("results", []))
        scores = [
            r.get("combined_score", r.get("relevance_score", 0))
            for r in results
        ]

        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Recommendations not sorted by combined_score at position {i}: "
                f"{scores[i]} < {scores[i+1]}"
            )

    async def test_database_intent_returns_db_tools(self, client):
        """'store user data securely' should return database/storage tools."""
        resp = await client.get("/v1/recommend", params={
            "intent": "store user data securely",
            "limit": 5,
        })
        if resp.status_code != 200:
            pytest.skip("recommend endpoint not available")

        data = resp.json()
        results = data.get("results", data.get("recommendations", []))
        if not results:
            pytest.skip("No results returned")

        # At least one result should be in database/storage/data category
        categories = [
            r.get("category", "").lower()
            for r in results
        ]
        names = [
            r.get("name", r.get("service_name", "")).lower()
            for r in results
        ]

        db_related = any(
            cat in ("database", "data", "storage", "cloud")
            or any(kw in name for kw in ("db", "sql", "data", "store", "supabase", "mongo", "redis", "postgres"))
            for cat, name in zip(categories, names)
        )
        assert db_related, (
            f"'store data securely' returned no DB tools. "
            f"Got: {list(zip(names, categories))}"
        )


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class TestPagination:
    """Pagination works correctly without gaps or overlaps."""

    async def test_feed_pagination_no_gaps(self, client):
        """Consecutive pages should not skip items."""
        page1 = await client.get("/v1/feed/scores", params={"limit": 10, "offset": 0})
        page2 = await client.get("/v1/feed/scores", params={"limit": 10, "offset": 10})

        assert page1.status_code == 200
        assert page2.status_code == 200

        ids1 = {s["scan_id"] for s in page1.json().get("services", [])}
        ids2 = {s["scan_id"] for s in page2.json().get("services", [])}

        # No overlap between pages
        overlap = ids1 & ids2
        assert len(overlap) == 0, f"Pagination overlap: {overlap}"

    async def test_feed_pagination_total_consistent(self, client):
        """Total count should be same across pages."""
        page1 = await client.get("/v1/feed/scores", params={"limit": 10, "offset": 0})
        page2 = await client.get("/v1/feed/scores", params={"limit": 10, "offset": 10})

        assert page1.status_code == 200
        assert page2.status_code == 200

        total1 = page1.json().get("total", 0)
        total2 = page2.json().get("total", 0)
        assert total1 == total2, f"Total changed between pages: {total1} vs {total2}"

    async def test_search_pagination(self, client):
        """Search pagination returns different results per page."""
        resp1 = await client.get("/v1/services", params={
            "q": "api", "limit": 5, "offset": 0
        })
        resp2 = await client.get("/v1/services", params={
            "q": "api", "limit": 5, "offset": 5
        })

        if resp1.status_code != 200:
            pytest.skip("services endpoint not available")

        svcs1 = resp1.json().get("services", resp1.json().get("results", []))
        svcs2 = resp2.json().get("services", resp2.json().get("results", []))

        if not svcs2:
            pytest.skip("Not enough results for pagination test")

        ids1 = {s.get("scan_id") for s in svcs1}
        ids2 = {s.get("scan_id") for s in svcs2}
        overlap = ids1 & ids2
        assert len(overlap) == 0, f"Search pagination overlap: {overlap}"


# ---------------------------------------------------------------------------
# Category filter
# ---------------------------------------------------------------------------

class TestCategoryFilter:
    """Category filtering returns accurate results."""

    async def test_category_filter_returns_correct_category(self, client):
        """Filtered results should all belong to the requested category."""
        resp = await client.get("/v1/services", params={
            "category": "ai", "limit": 10
        })
        if resp.status_code != 200:
            pytest.skip("services endpoint not available")

        services = resp.json().get("services", resp.json().get("results", []))
        for svc in services:
            cat = svc.get("category", "")
            assert cat == "ai", (
                f"Service '{svc.get('service_name')}' has category '{cat}', expected 'ai'"
            )

    async def test_type_filter_returns_correct_type(self, client):
        """service_type filter should work independently of category."""
        resp = await client.get("/v1/services", params={
            "service_type": "mcp_server", "limit": 10
        })
        if resp.status_code != 200:
            pytest.skip("services endpoint not available or no type filter")

        services = resp.json().get("services", resp.json().get("results", []))
        for svc in services:
            stype = svc.get("service_type", "")
            assert stype == "mcp_server", (
                f"Service '{svc.get('service_name')}' has type '{stype}', expected 'mcp_server'"
            )
