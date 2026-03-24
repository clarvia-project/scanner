"""End-to-end tests for the Clarvia AEO Scanner API.

Tests cover the core scan flow, profile system, badge endpoint,
report/payment routes, rate limiting, index API, and security.
Runs against the actual FastAPI app using httpx AsyncClient
(no external network calls for badge/profile tests).
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def fresh_rate_limit_client():
    """Client with a clean rate-limit store for isolated rate-limit tests."""
    from app.middleware import _rate_store
    _rate_store.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Forwarded-For": "203.0.113.99"},
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scan_missing_url(client):
    resp = await client.post("/api/scan", json={"url": ""})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_scan_invalid_url(client):
    resp = await client.post("/api/scan", json={"url": "not-a-url"})
    # Should return 422 (validation) or 500 (scan failure)
    assert resp.status_code in (422, 500)


@pytest.mark.asyncio
async def test_scan_valid_url(client):
    """Scan a real, lightweight URL and verify response structure."""
    resp = await client.post("/api/scan", json={"url": "https://httpbin.org"})
    # May timeout in CI, so accept 200 or 500
    if resp.status_code == 200:
        data = resp.json()
        assert "scan_id" in data
        assert "clarvia_score" in data
        assert "rating" in data
        assert "dimensions" in data
        assert isinstance(data["clarvia_score"], int)
        assert 0 <= data["clarvia_score"] <= 125
        assert data["rating"] in ("A+", "A", "B", "C", "D", "F")


@pytest.mark.asyncio
async def test_scan_not_found(client):
    resp = await client.get("/api/scan/nonexistent_scan_id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_profile_lifecycle(client):
    """Create, read, update, scan, badge — full profile lifecycle."""
    # Create
    create_resp = await client.post("/v1/profiles", json={
        "name": "Test Service",
        "url": "https://example.com",
        "description": "A test service for E2E testing",
        "category": "testing",
        "tags": ["test", "e2e"],
    })
    assert create_resp.status_code == 200
    profile = create_resp.json()
    profile_id = profile["profile_id"]
    assert profile_id.startswith("prf_")
    assert profile["name"] == "Test Service"
    assert profile["status"] == "pending_scan"

    # Read
    get_resp = await client.get(f"/v1/profiles/{profile_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Test Service"

    # Update
    update_resp = await client.put(f"/v1/profiles/{profile_id}", json={
        "description": "Updated description",
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Updated description"

    # List
    list_resp = await client.get("/v1/profiles")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1

    # List with category filter
    filtered_resp = await client.get("/v1/profiles?category=testing")
    assert filtered_resp.status_code == 200
    for p in filtered_resp.json()["profiles"]:
        assert p["category"] == "testing"


@pytest.mark.asyncio
async def test_profile_not_found(client):
    resp = await client.get("/v1/profiles/prf_nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_profile_duplicate_url(client):
    """Creating two profiles with the same URL should fail."""
    url = "https://duplicate-test.example.com"
    await client.post("/v1/profiles", json={
        "name": "First",
        "url": url,
    })
    resp = await client.post("/v1/profiles", json={
        "name": "Second",
        "url": url,
    })
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Badge
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_badge_svg(client):
    """Badge endpoint returns valid SVG."""
    # Create a profile first
    create_resp = await client.post("/v1/profiles", json={
        "name": "Badge Test",
        "url": "https://badge-test.example.com",
    })
    profile_id = create_resp.json()["profile_id"]

    resp = await client.get(f"/v1/profiles/{profile_id}/badge")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/svg+xml"
    body = resp.text
    assert "<svg" in body
    assert "Clarvia Score" in body


@pytest.mark.asyncio
async def test_badge_not_found(client):
    resp = await client.get("/v1/profiles/prf_nonexistent/badge")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_badge_color_unscored(client):
    """Unscored profile badge should show '?' with gray color."""
    create_resp = await client.post("/v1/profiles", json={
        "name": "Unscored Badge",
        "url": "https://unscored-badge.example.com",
    })
    profile_id = create_resp.json()["profile_id"]

    resp = await client.get(f"/v1/profiles/{profile_id}/badge")
    body = resp.text
    # Unscored shows "?" and gray color
    assert "?" in body
    assert "#9f9f9f" in body


# ---------------------------------------------------------------------------
# Report / Stripe (stub checks)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_report_requires_payment(client):
    """GET /api/report/{scan_id} without payment returns 402 or 404."""
    resp = await client.get("/api/report/nonexistent_scan_id")
    assert resp.status_code in (402, 404)


@pytest.mark.asyncio
async def test_checkout_missing_scan_id(client):
    """POST create-checkout without scan_id returns 400."""
    resp = await client.post("/api/report/create-checkout", json={})
    # 400 (missing scan_id) or 503 (stripe not configured)
    assert resp.status_code in (400, 503)


# ---------------------------------------------------------------------------
# Waitlist
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_waitlist(client):
    resp = await client.post("/api/waitlist", json={"email": "test@example.com"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Cache cleanup
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_cleanup(client):
    resp = await client.post("/api/cache/cleanup")
    assert resp.status_code == 200
    assert "removed" in resp.json()


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_enforcement(fresh_rate_limit_client):
    """Rate limit이 FREE_LIMIT(10) 초과 시 429를 반환하는지 확인."""
    client = fresh_rate_limit_client
    from app.middleware import FREE_LIMIT

    # FREE_LIMIT번까지는 허용 (빈 URL이라 400이지만 rate limit은 아님)
    for i in range(FREE_LIMIT):
        resp = await client.post("/api/scan", json={"url": ""})
        assert resp.status_code != 429, f"Blocked too early at request {i + 1}"

    # FREE_LIMIT+1번째 요청은 429
    resp = await client.post("/api/scan", json={"url": ""})
    assert resp.status_code == 429
    body = resp.json()
    assert "Rate limit exceeded" in body.get("error", "")
    assert "retry_after" in body
    assert "Retry-After" in resp.headers


@pytest.mark.asyncio
async def test_rate_limit_headers(fresh_rate_limit_client):
    """Rate limit 관련 헤더가 응답에 포함되는지 확인."""
    client = fresh_rate_limit_client
    # 빈 URL로 보내면 400이지만 미들웨어가 먼저 헤더를 붙인다.
    # 다만 400은 scan 함수에서 먼저 응답하므로,
    # 유효한 URL을 사용해야 미들웨어가 헤더를 추가할 수 있음.
    # POST /api/scan에 빈 URL을 보내면 핸들러가 400을 던져도
    # 미들웨어가 response에 헤더를 추가한 뒤 반환한다.
    resp = await client.post("/api/scan", json={"url": "https://example.com"})
    # 스캔이 성공/실패와 무관하게 rate limit 헤더 존재 확인
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers
    assert "X-RateLimit-Reset" in resp.headers
    assert int(resp.headers["X-RateLimit-Limit"]) > 0
    assert int(resp.headers["X-RateLimit-Remaining"]) >= 0


# ---------------------------------------------------------------------------
# Index API — Services
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_services_pagination(client):
    """페이지네이션이 올바르게 동작하는지."""
    # 첫 페이지
    resp = await client.get("/v1/services", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "services" in data
    assert "pagination" in data
    assert data["pagination"]["limit"] == 2
    assert data["pagination"]["offset"] == 0
    assert len(data["services"]) <= 2

    # offset이 total 이상이면 빈 리스트
    total = data["total"]
    if total > 0:
        resp2 = await client.get("/v1/services", params={"limit": 2, "offset": total + 100})
        assert resp2.status_code == 200
        assert resp2.json()["services"] == []


@pytest.mark.asyncio
async def test_services_filter_by_category(client):
    """카테고리 필터가 올바르게 동작하는지."""
    resp = await client.get("/v1/services", params={"category": "ai"})
    assert resp.status_code == 200
    data = resp.json()
    for svc in data["services"]:
        assert svc["category"] == "ai"


@pytest.mark.asyncio
async def test_services_filter_by_type(client):
    """service_type 필터가 올바르게 동작하는지."""
    resp = await client.get("/v1/services", params={"service_type": "mcp_server"})
    assert resp.status_code == 200
    data = resp.json()
    for svc in data["services"]:
        assert svc["service_type"] == "mcp_server"


@pytest.mark.asyncio
async def test_services_text_search(client):
    """q 파라미터 텍스트 검색이 동작하는지."""
    # 존재하지 않는 키워드로 검색하면 결과 0
    resp = await client.get("/v1/services", params={"q": "zzz_nonexistent_service_xyz"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    # 빈 문자열 쿼리는 필터 없이 전체 반환
    resp2 = await client.get("/v1/services", params={"q": ""})
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_services_sort_orders(client):
    """모든 정렬 옵션이 동작하는지."""
    for sort in ("score_desc", "score_asc", "name_asc", "name_desc", "recent"):
        resp = await client.get("/v1/services", params={"sort": sort, "limit": 5})
        assert resp.status_code == 200, f"Sort '{sort}' failed"
        data = resp.json()
        services = data["services"]

        if len(services) >= 2:
            if sort == "score_desc":
                assert services[0]["clarvia_score"] >= services[-1]["clarvia_score"]
            elif sort == "score_asc":
                assert services[0]["clarvia_score"] <= services[-1]["clarvia_score"]
            elif sort == "name_asc":
                assert services[0]["name"].lower() <= services[-1]["name"].lower()
            elif sort == "name_desc":
                assert services[0]["name"].lower() >= services[-1]["name"].lower()


@pytest.mark.asyncio
async def test_service_detail_404(client):
    """존재하지 않는 scan_id에 404 반환."""
    resp = await client.get("/v1/services/nonexistent_scan_id_xyz")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Index API — Categories & Stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_categories_endpoint(client):
    """카테고리 목록 엔드포인트 테스트."""
    resp = await client.get("/v1/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)
    # 각 카테고리는 name과 count 필드를 가져야 함
    for cat in data["categories"]:
        assert "name" in cat
        assert "count" in cat
        assert isinstance(cat["count"], int)
        assert cat["count"] >= 0


@pytest.mark.asyncio
async def test_stats_endpoint(client):
    """통계 엔드포인트 테스트."""
    resp = await client.get("/v1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_services" in data
    assert "avg_score" in data
    assert "by_category" in data
    assert isinstance(data["total_services"], int)
    assert isinstance(data["avg_score"], (int, float))

    if data["total_services"] > 0:
        assert "score_distribution" in data
        dist = data["score_distribution"]
        assert all(k in dist for k in ("excellent", "strong", "moderate", "weak"))


@pytest.mark.asyncio
async def test_stats_source_all(client):
    """source=all 통계 테스트."""
    resp = await client.get("/v1/stats", params={"source": "all"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_services" in data
    # source=all일 때 추가 필드
    assert "scanned_count" in data
    assert "collected_count" in data
    assert data["total_services"] == data["scanned_count"] + data["collected_count"]


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_xss_in_search_query(client):
    """검색 쿼리에 XSS 페이로드가 이스케이프되는지."""
    xss_payload = '<script>alert(1)</script>'
    resp = await client.get("/v1/services", params={"q": xss_payload})
    assert resp.status_code == 200
    body = resp.text
    # 응답 본문에 이스케이프되지 않은 <script> 태그가 없어야 함
    assert "<script>" not in body


@pytest.mark.asyncio
async def test_ssrf_scan_localhost(client):
    """localhost URL 스캔 차단 확인."""
    for url in (
        "http://localhost",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:3000/admin",
        "http://[::1]",
    ):
        resp = await client.post("/api/scan", json={"url": url})
        # 스캔이 성공해서는 안 됨: 400/422/403/500 중 하나
        assert resp.status_code != 200, f"Localhost URL '{url}' was not blocked"


@pytest.mark.asyncio
async def test_ssrf_scan_private_ip(client):
    """Private IP 스캔 차단 확인."""
    for url in (
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://192.168.1.1",
        "http://169.254.169.254",           # AWS metadata
        "http://169.254.169.254/latest/meta-data/",
    ):
        resp = await client.post("/api/scan", json={"url": url})
        # 프라이빗 IP 스캔이 성공해서는 안 됨
        assert resp.status_code != 200, f"Private IP URL '{url}' was not blocked"
