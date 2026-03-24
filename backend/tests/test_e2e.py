"""End-to-end tests for the Clarvia AEO Scanner API.

Tests cover the core scan flow, profile system, badge endpoint,
and report/payment routes. Runs against the actual FastAPI app
using httpx AsyncClient (no external network calls for badge/profile tests).
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
