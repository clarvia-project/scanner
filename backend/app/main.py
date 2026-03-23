"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .middleware import RateLimitMiddleware
from .models import ErrorResponse, ScanRequest, ScanResponse, WaitlistRequest
from .routes.index_routes import router as index_router
from .scanner import cleanup_cache, get_cached_scan, run_scan

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Clarvia AEO Scanner",
    description="Scan any URL for AI Engine Optimization readiness.",
    version="1.0.0",
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.add_middleware(RateLimitMiddleware)


# ---------------------------------------------------------------------------
# Optional service imports (graceful degradation without Stripe/Supabase)
# ---------------------------------------------------------------------------
_stripe_router = None
_supabase_client = None

try:
    from .routes.stripe_routes import router as stripe_router
    _stripe_router = stripe_router
except ImportError:
    logger.info("Stripe routes not available (missing stripe package)")

try:
    from .services.supabase_client import get_supabase
    _supabase_client = get_supabase
except ImportError:
    logger.info("Supabase client not available (missing supabase package)")

# Mount optional routers
app.include_router(index_router)

if _stripe_router:
    app.include_router(_stripe_router, prefix="/api/report")


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/scan", response_model=ScanResponse)
async def scan_url(req: ScanRequest):
    """Run a full AEO scan on the provided URL."""
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        result = await run_scan(req.url)

        # Persist to Supabase if available
        if _supabase_client:
            try:
                from .services.supabase_client import save_scan
                await save_scan(result)
            except Exception as e:
                logger.warning("Failed to persist scan to Supabase: %s", e)

        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Scan failed for URL: %s", req.url)
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {type(e).__name__}: {str(e)[:200]}",
        )


@app.get("/api/scan/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str):
    """Retrieve a cached scan result by ID."""
    result = get_cached_scan(scan_id)
    if result is None:
        # Try Supabase fallback
        if _supabase_client:
            try:
                from .services.supabase_client import get_scan_from_db
                result = await get_scan_from_db(scan_id)
                if result:
                    return result
            except Exception as e:
                logger.warning("Supabase lookup failed: %s", e)
        raise HTTPException(status_code=404, detail="Scan not found or expired")
    return result


@app.post("/api/waitlist")
async def join_waitlist(req: WaitlistRequest):
    """Add an email to the waitlist."""
    if _supabase_client:
        try:
            from .services.supabase_client import add_to_waitlist
            await add_to_waitlist(req.email)
        except Exception as e:
            logger.warning("Failed to save waitlist email: %s", e)

    return {"status": "ok", "message": "You've been added to the waitlist!"}


@app.post("/api/cache/cleanup")
async def cache_cleanup():
    """Remove expired cache entries."""
    removed = cleanup_cache()
    return {"removed": removed}
