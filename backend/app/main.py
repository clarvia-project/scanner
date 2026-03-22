"""FastAPI application entry point."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models import ErrorResponse, ScanRequest, ScanResponse
from .scanner import cleanup_cache, get_cached_scan, run_scan

app = FastAPI(
    title="Clarvia AEO Scanner",
    description="Scan any URL for AI Engine Optimization readiness.",
    version="1.0.0",
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {type(e).__name__}: {str(e)[:200]}",
        )


@app.get("/api/scan/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str):
    """Retrieve a cached scan result by ID."""
    result = get_cached_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scan not found or expired")
    return result


@app.post("/api/cache/cleanup")
async def cache_cleanup():
    """Remove expired cache entries."""
    removed = cleanup_cache()
    return {"removed": removed}
