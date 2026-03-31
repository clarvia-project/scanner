"""FastAPI application entry point."""

import asyncio
import logging
import json as _json_mod
import sys
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# ---------------------------------------------------------------------------
# H3: Structured JSON logging
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return _json_mod.dumps(log_entry, ensure_ascii=False)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[_handler], force=True)


# ---------------------------------------------------------------------------
# H6: Request body size limiter middleware
# ---------------------------------------------------------------------------

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body exceeds max_bytes (default 1 MB)."""

    def __init__(self, app: ASGIApp, max_bytes: int = 1_048_576) -> None:  # 1 MB
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "type": "payload_too_large",
                        "message": f"Request body exceeds {self.max_bytes} bytes limit.",
                    }
                },
            )
        return await call_next(request)

from .config import settings  # noqa: E402
from .middleware import AnalyticsMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware, SecurityMiddleware  # noqa: E402
from .models import ScanRequest, ScanResponse, WaitlistRequest  # noqa: E402
from .routes.admin_routes import router as admin_router  # noqa: E402
from .routes.badge_routes import router as badge_router  # noqa: E402
from .routes.feedback_routes import router as feedback_router  # noqa: E402
from .routes.index_routes import router as index_router  # noqa: E402
from .routes.profile_routes import router as profile_router  # noqa: E402
from .routes.recommend_routes import router as recommend_router  # noqa: E402
from .routes.marketing_routes import router as marketing_router  # noqa: E402
from .routes.setup_routes import router as setup_router  # noqa: E402
from .routes.cs_routes import router as cs_router  # noqa: E402
from .routes.feed_routes import router as feed_router  # noqa: E402
from .routes.trending_routes import router as trending_router  # noqa: E402
from .routes.webhook_routes import router as webhook_router  # noqa: E402
from .routes.submission_routes import router as submission_router  # noqa: E402
from .routes.collection_routes import router as collection_router  # noqa: E402
from .routes.history_routes import router as history_router  # noqa: E402
from .routes.team_routes import router as team_router  # noqa: E402
from .routes.analytics_routes import router as analytics_router  # noqa: E402
from .routes.scan_history_routes import router as scan_history_router  # noqa: E402
from .routes.agent_traffic_routes import router as agent_traffic_router  # noqa: E402
from .routes.agent_traffic_routes import AgentTrafficMiddleware  # noqa: E402
from .routes.visitor_traffic_routes import router as visitor_traffic_router  # noqa: E402
from .routes.visitor_traffic_routes import VisitorTrafficMiddleware  # noqa: E402
from .keepalive import keepalive_loop  # noqa: E402
from .scanner import cleanup_cache, get_cached_scan, run_scan  # noqa: E402

import os  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

logger = logging.getLogger(__name__)

# Background task handle for periodic cache cleanup
_cache_cleanup_task: asyncio.Task | None = None


async def _periodic_cache_cleanup():
    """Background task: clean expired cache entries every 30 minutes."""
    import asyncio
    while True:
        await asyncio.sleep(1800)  # 30 minutes
        try:
            removed = cleanup_cache()
            from .middleware import cleanup_rate_store
            rate_removed = cleanup_rate_store()
            from .routes.visitor_traffic_routes import cleanup_old_visitor_traffic
            visitor_removed = cleanup_old_visitor_traffic(max_age_days=90)
            if removed or rate_removed or visitor_removed:
                logger.info("Background cleanup: %d cache + %d rate-limit + %d visitor-traffic entries removed", removed, rate_removed, visitor_removed)
        except Exception as e:
            logger.warning("Background cleanup error: %s", e)


async def _send_telegram_alert(text: str) -> None:
    """Send a Telegram alert (fire-and-forget)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    try:
        import aiohttp
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=aiohttp.ClientTimeout(total=10))
    except Exception as e:
        logger.warning("Telegram alert failed: %s", e)


async def _periodic_data_freshness_check():
    """Background task: alert via Telegram if catalog data is stale (> 36h)."""
    import asyncio
    await asyncio.sleep(3600)  # first check after 1h (allow startup to finish)
    while True:
        try:
            from .routes.index_routes import get_data_info
            info = get_data_info()
            if info["stale"]:
                msg = (
                    f"⚠️ *Clarvia API — Stale Data Alert*\n"
                    f"Tool count: {info['tool_count']:,}\n"
                    f"Last loaded: {info['loaded_at'] or 'never'}\n"
                    f"Age: {info['age_hours']}h (threshold: 36h)\n"
                    f"Action: check GitHub Actions auto\\_merge job or trigger Render redeploy."
                )
                logger.warning("Data stale: %s hours old", info["age_hours"])
                await _send_telegram_alert(msg)
        except Exception as e:
            logger.warning("Freshness check error: %s", e)
        await asyncio.sleep(3600)  # check every hour


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    import asyncio
    global _cache_cleanup_task

    # --- Startup ---
    # Load profiles (moved from module-level import to avoid side effects)
    from .routes.profile_routes import _load_profiles
    _load_profiles()
    logger.info("Profiles loaded during startup")

    # Load index data via subprocess to completely avoid GIL contention.
    # json.load of 21MB + classify + dedup holds the GIL for minutes on
    # 0.5 vCPU, starving Uvicorn. A subprocess does all CPU work in its
    # own process; main process only does a fast pickle.loads at the end.
    import subprocess, pickle, threading, tempfile, os
    from .routes.index_routes import _find_data_dir

    def _bg_load_subprocess():
        """Heavy JSON parse + classify + dedup in a child process."""
        from .routes import index_routes as ir

        data_dir = _find_data_dir()
        data_path = data_dir / "prebuilt-scans.json" if data_dir else None
        if data_path is None or not data_path.exists():
            logger.error("prebuilt-scans.json not found")
            return

        # Write a small Python script that does all the CPU work
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(f"""
import json, pickle, sys, re
with open({str(data_path)!r}) as fh:
    raw = json.load(fh)

_AI_KW = re.compile(r"\\b(llm|gpt|claude|openai|anthropic|genai|generative|diffusion|embedding|transformer|neural|machine.?learning|deep.?learning|natural.?language|computer.?vision|reinforcement.?learning|rag|vector.?db|fine.?tun|prompt|chatbot|copilot|ai.?agent|autonomous.?agent|model.?serving|inference|hugging.?face)\\b", re.I)
_DEV_KW = re.compile(r"\\b(api|sdk|cli|devtool|developer|github|gitlab|docker|kubernetes|terraform|cicd|ci/cd|testing|debug|lint|format|build|deploy|monitor|logging|database|sql|nosql|redis|queue|cache|auth|oauth|jwt|security|cloud|aws|azure|gcp|serverless|cdn|dns|ssl|tls|git|npm|pip|cargo|brew|vscode|ide|editor|terminal|shell|bash|zsh|webhook|graphql|rest|grpc|protobuf|microservice|container|orchestrat)\\b", re.I)

def classify(name, desc):
    text = (name + " " + desc).lower()
    if _AI_KW.search(text):
        return "ai"
    if _DEV_KW.search(text):
        return "developer_tools"
    return "other"

for entry in raw:
    entry["category"] = classify(entry.get("service_name",""), entry.get("description",""))

# Dedup pass 1: exact URL
url_best = {{}}
for i, s in enumerate(raw):
    url = (s.get("url") or "").rstrip("/").lower()
    if not url:
        continue
    if url in url_best:
        if s.get("clarvia_score",0) > raw[url_best[url]].get("clarvia_score",0):
            url_best[url] = i
    else:
        url_best[url] = i
kept = set(url_best.values())
for i, s in enumerate(raw):
    if not (s.get("url") or "").strip():
        kept.add(i)
raw = [raw[i] for i in sorted(kept)]

sys.stdout.buffer.write(pickle.dumps(raw))
""")
            script_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True, timeout=600,
            )
            if result.returncode != 0:
                logger.error("Subprocess load failed: %s", result.stderr.decode()[:500])
                return
            raw = pickle.loads(result.stdout)
        finally:
            os.unlink(script_path)

        ir._services = raw
        ir._by_scan_id = {s["scan_id"]: s for s in raw}
        from datetime import datetime
        ir._data_loaded_at = datetime.utcnow()
        logger.info("Index data loaded (subprocess): %d services", len(raw))
        ir._merge_profiles()

    import sys
    threading.Thread(target=_bg_load_subprocess, daemon=True).start()
    logger.info("Index data loading scheduled (subprocess)")

    # Start background cache cleanup
    _cache_cleanup_task = asyncio.create_task(_periodic_cache_cleanup())

    # Start data freshness monitor (alerts via Telegram if catalog > 36h old)
    asyncio.create_task(_periodic_data_freshness_check())

    # Start keep-alive ping to prevent Render cold starts
    asyncio.create_task(keepalive_loop())

    # Seed scan history from prebuilt-scans if empty
    from .routes.scan_history_routes import seed_history_from_prebuilt
    seeded = seed_history_from_prebuilt()
    if seeded:
        logger.info("Scan history seeded: %d entries", seeded)

    # Start persistent analytics JSONL writer
    from .services.analytics_writer import analytics_writer
    analytics_writer.start()

    # Start MCP session manager (required for Streamable HTTP transport)
    try:
        from .mcp_server import mcp_session_manager
        async with mcp_session_manager.run():
            logger.info("MCP session manager started")
            yield
    except Exception as exc:
        logger.warning("MCP session manager not available: %s", exc)
        yield

    # --- Shutdown ---
    logger.info("Shutting down gracefully...")
    # Flush remaining analytics to disk
    await analytics_writer.stop()
    if _cache_cleanup_task:
        _cache_cleanup_task.cancel()
        try:
            await _cache_cleanup_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutdown complete")


_is_production = os.environ.get("SCANNER_ENV", "production") == "production"

app = FastAPI(
    title="Clarvia AEO Scanner API",
    description=(
        "Scan any URL for AI Engine Optimization (AEO) readiness. "
        "Provides AEO scoring, actionable recommendations, competitive benchmarks, "
        "and machine-readable feeds for agent frameworks and MCP registries.\n\n"
        "**Base URL:** `https://clarvia-api.onrender.com`\n\n"
        "**Rate limits:** Free tier 10 scans/hr, Pro 100 scans/hr, Enterprise unlimited.\n\n"
        "**Authentication:** Most read endpoints are public. Write operations require "
        "an API key via `X-API-Key` header."
    ),
    version="1.2.3",
    docs_url="/docs",
    redoc_url="/redoc",
    # Always expose OpenAPI spec — required for AEO discoverability
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "scan", "description": "Core AEO scanning endpoints"},
        {"name": "index", "description": "Service index — browse, search, and filter scanned services"},
        {"name": "feed", "description": "Machine-readable data feeds for registries and agents"},
        {"name": "profiles", "description": "Service profile management"},
        {"name": "badge", "description": "Embeddable SVG badges for AEO scores"},
        {"name": "cs", "description": "Customer support ticket system for agents"},
        {"name": "recommend", "description": "Service recommendations and alternatives"},
        {"name": "trending", "description": "Trending services and score changes"},
        {"name": "feedback", "description": "User feedback and ratings"},
        {"name": "setup", "description": "Setup wizard for new service onboarding"},
        {"name": "marketing", "description": "Marketing assets and embeds"},
        {"name": "webhooks", "description": "Webhook registration for event notifications"},
        {"name": "keys", "description": "API key self-service management"},
        {"name": "submissions", "description": "Tool submission and Clarvia badge system"},
        {"name": "admin", "description": "Admin-only operations (requires API key)"},
        {"name": "admin-analytics", "description": "API traffic analytics and monitoring (requires API key)"},
    ],
)

# CORS — use settings.cors_origins as the base, add production domains
_cors_origins = list(settings.cors_origins)
# Ensure production domains are always included
for _origin in [
    "https://clarvia.art",
    "https://www.clarvia.art",
    "https://clarvia-aeo-scanner.vercel.app",
]:
    if _origin not in _cors_origins:
        _cors_origins.append(_origin)
if settings.frontend_url and settings.frontend_url not in _cors_origins:
    _cors_origins.append(settings.frontend_url)
# Allow localhost in development
if not _is_production:
    _cors_origins.extend(["http://localhost:3000", "http://localhost:8002"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Clarvia-Key", "Authorization"],
)

# Analytics (outermost — sees all requests)
app.add_middleware(AnalyticsMiddleware)

# Visitor traffic (privacy-first: hashed IP + country only, 90-day retention)
app.add_middleware(VisitorTrafficMiddleware)

# Agent traffic measurement (detects AI agent user-agents, logs to JSONL)
app.add_middleware(AgentTrafficMiddleware)

# Security (abuse detection, suspicious request blocking)
app.add_middleware(SecurityMiddleware)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Body size limit (1 MB)
app.add_middleware(BodySizeLimitMiddleware, max_bytes=1_048_576)


# ---------------------------------------------------------------------------
# Consistent error responses (RFC 7807 inspired)
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "api_error",
                "code": exc.status_code,
                "message": str(exc.detail),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    import html
    # Sanitize error details to prevent XSS via reflected input
    sanitized_errors = []
    for err in exc.errors():
        sanitized = {k: html.escape(str(v)) if isinstance(v, str) else v for k, v in err.items()}
        if "input" in sanitized:
            sanitized["input"] = "[redacted]"
        sanitized_errors.append(sanitized)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "validation_error",
                "code": 422,
                "message": "Invalid request parameters",
                "details": str(sanitized_errors)[:500],
            }
        },
    )


# ---------------------------------------------------------------------------
# Optional service imports (graceful degradation without Stripe/Supabase)
# ---------------------------------------------------------------------------
_supabase_client = None

try:
    from .services.supabase_client import get_supabase
    _supabase_client = get_supabase
except ImportError:
    logger.info("Supabase client not available (missing supabase package)")

# Mount routers
app.include_router(index_router)
app.include_router(recommend_router)
app.include_router(profile_router)
app.include_router(feedback_router)
app.include_router(admin_router)
app.include_router(badge_router)
app.include_router(trending_router)
app.include_router(marketing_router)
app.include_router(setup_router)
app.include_router(cs_router)
app.include_router(feed_router)
app.include_router(webhook_router)
app.include_router(submission_router)
app.include_router(collection_router)
app.include_router(history_router)
app.include_router(team_router)
app.include_router(analytics_router)
app.include_router(scan_history_router)
app.include_router(agent_traffic_router)
app.include_router(visitor_traffic_router)

# ---------------------------------------------------------------------------
# Compatibility: /api/v1/* → /v1/* (DESIGN.md specifies /api/v1/*)
# ---------------------------------------------------------------------------
from starlette.responses import RedirectResponse as _RedirectResponse
from fastapi import APIRouter as _APIRouter

_compat_router = _APIRouter(prefix="/api/v1", tags=["compatibility"])


@_compat_router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def _api_v1_compat(request: Request, path: str):
    """Proxy /api/v1/* to /v1/* for DESIGN.md contract compatibility."""
    target = f"/v1/{path}"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return _RedirectResponse(url=target, status_code=307)


# NOTE: _compat_router is registered at the bottom of this file (after all
# native /api/v1/* routes) so that FastAPI matches the direct routes first
# and the catch-all redirect only fires for paths not natively handled.

# MCP server (Streamable HTTP transport for Smithery / remote MCP clients)
try:
    from .mcp_server import mcp_app
    from starlette.routing import Mount
    app.router.routes.insert(0, Mount("/mcp", app=mcp_app))
    logger.info("MCP Streamable HTTP server mounted at /mcp")
except Exception as exc:
    logger.warning("MCP server not available: %s", exc)

# Payment: Lemon Squeezy (primary) with Stripe fallback
try:
    from .routes.payment_routes import router as payment_router
    app.include_router(payment_router, prefix="/api/report")
    logger.info("Lemon Squeezy payment routes loaded")
except ImportError:
    try:
        from .routes.stripe_routes import router as stripe_router
        app.include_router(stripe_router, prefix="/api/report")
        logger.info("Stripe payment routes loaded (fallback)")
    except ImportError:
        logger.info("No payment routes available")


# ---------------------------------------------------------------------------
# Custom OpenAPI schema — enhanced for agent discoverability
# ---------------------------------------------------------------------------

from fastapi.openapi.utils import get_openapi  # noqa: E402

def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    schema["info"]["x-logo"] = {
        "url": "https://clarvia.art/logo.png",
        "altText": "Clarvia",
    }
    schema["info"]["contact"] = {
        "name": "Clarvia API Support",
        "url": "https://clarvia.art",
        "email": "api@clarvia.art",
    }
    schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
    schema["info"]["x-agent-instructions"] = (
        "Use /v1/score to check AEO score for any URL. "
        "Use /v1/search to find tools by keyword. "
        "Use /v1/compare to compare two tools head-to-head. "
        "Use /v1/leaderboard to get top-rated tools by category. "
        "No authentication required for read endpoints."
    )
    schema["servers"] = [
        {
            "url": "https://clarvia-api.onrender.com",
            "description": "Production API",
        }
    ]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = _custom_openapi  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# Agent discovery endpoints (robots.txt, sitemap, llms.txt)
# ---------------------------------------------------------------------------

from fastapi.responses import PlainTextResponse  # noqa: E402

@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def api_robots_txt():
    """Robots.txt for the API domain — allow all AI agent crawlers."""
    return """User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Bytespider
Allow: /

User-agent: CCBot
Allow: /

Sitemap: https://clarvia-api.onrender.com/sitemap.xml
"""


@app.get("/sitemap.xml", response_class=Response, include_in_schema=False)
async def api_sitemap():
    """Minimal sitemap for the API domain pointing to key discovery endpoints."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://clarvia-api.onrender.com/openapi.json</loc><changefreq>daily</changefreq><priority>1.0</priority></url>
  <url><loc>https://clarvia-api.onrender.com/docs</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>
  <url><loc>https://clarvia-api.onrender.com/redoc</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>
  <url><loc>https://clarvia-api.onrender.com/v1/services</loc><changefreq>daily</changefreq><priority>0.9</priority></url>
  <url><loc>https://clarvia-api.onrender.com/v1/categories</loc><changefreq>daily</changefreq><priority>0.7</priority></url>
  <url><loc>https://clarvia-api.onrender.com/v1/stats</loc><changefreq>daily</changefreq><priority>0.6</priority></url>
  <url><loc>https://clarvia-api.onrender.com/v1/trending</loc><changefreq>daily</changefreq><priority>0.7</priority></url>
  <url><loc>https://clarvia-api.onrender.com/health</loc><changefreq>always</changefreq><priority>0.3</priority></url>
</urlset>"""
    return Response(content=xml, media_type="application/xml")


@app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
async def api_llms_txt():
    """LLMs.txt for the API domain — help LLMs understand Clarvia API."""
    return """# Clarvia API

> Clarvia is an AEO (Agent Engine Optimization) scanner and tool directory for AI agents.
> It indexes 15,400+ tools (MCP servers, APIs, CLIs, Skills) and scores each for agent readiness (0-100).

## API Base URL
https://clarvia-api.onrender.com

## OpenAPI Spec
https://clarvia-api.onrender.com/openapi.json

## MCP Server
npx -y clarvia-mcp-server

## Key Endpoints
- GET /v1/services?q=keyword — Search tools
- GET /v1/score?url=example.com — Quick score
- GET /v1/recommend — Intent-based recommendations
- GET /v1/categories — Browse categories
- GET /v1/trending — Trending tools
- GET /v1/leaderboard — Top-scored tools
- GET /v1/stats — Platform statistics
"""


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
async def health():
    """Enhanced health check with real system status."""
    checks: dict[str, Any] = {}
    overall = "healthy"

    # 1. Cache status
    from .scanner import _scan_cache
    checks["cache"] = {"status": "ok", "entries": len(_scan_cache)}

    # 2. Supabase / DB connectivity
    try:
        from .services.supabase_client import get_supabase
        client = get_supabase()
        if client:
            checks["database"] = {"status": "ok"}
        else:
            checks["database"] = {"status": "not_configured"}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}
        overall = "degraded"

    # 3. Memory usage (stdlib resource module — no extra dependency)
    try:
        import resource
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        # macOS: ru_maxrss in bytes; Linux: in KB
        import sys as _sys
        rss_bytes = rusage.ru_maxrss if _sys.platform == "darwin" else rusage.ru_maxrss * 1024
        checks["memory"] = {
            "status": "ok",
            "rss_mb": round(rss_bytes / 1_048_576, 1),
        }
        if rss_bytes > 536_870_912:  # > 512 MB
            checks["memory"]["status"] = "warning"
            overall = "degraded"
    except Exception:
        checks["memory"] = {"status": "unavailable"}

    # 4. Data freshness
    from .routes.index_routes import get_data_info
    data_info = get_data_info()
    checks["data"] = {
        "status": "stale" if data_info["stale"] else "ok",
        "tool_count": data_info["tool_count"],
        "loaded_at": data_info["loaded_at"],
        "age_hours": data_info["age_hours"],
    }
    if data_info["stale"]:
        overall = "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


@app.post("/api/scan", response_model=ScanResponse, tags=["scan"])
async def scan_url(req: ScanRequest, request: Request):
    """Run a full AEO scan on the provided URL.

    Returns detailed AEO scoring with dimension breakdowns, recommendations,
    and a unique scan_id for retrieval. Rate limited per IP or API key.

    Free tier: 10 scans/day, top 3 recommendations, evidence blurred.
    Starter+: higher limits, full evidence, more recommendations.
    """
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL is required")

    # Validate URL scheme before any processing
    from .services.security import is_url_safe
    url_clean = req.url.strip()
    if not url_clean.startswith(("http://", "https://")):
        if url_clean.startswith(("javascript:", "data:", "file:", "ftp:")):
            raise HTTPException(status_code=422, detail=f"Blocked URL scheme: {url_clean.split(':')[0]}")
        url_clean = "https://" + url_clean
    safe, reason = is_url_safe(url_clean)
    if not safe:
        raise HTTPException(status_code=422, detail=reason)
    req.url = url_clean

    # --- Tier-based daily scan limit ---
    from .services.tier_gate import (
        check_daily_scan_limit, increment_daily_scan, gate_response,
        RECOMMENDATION_LIMITS, has_feature, Feature,
    )

    # Determine user plan from Clarvia API key
    user_plan = "free"
    clarvia_key = request.headers.get("x-clarvia-key") or request.headers.get("x-api-key")
    rate_key = request.client.host if request.client else "unknown"

    if clarvia_key:
        try:
            from .services.auth_service import validate_api_key
            meta = await validate_api_key(clarvia_key)
            if meta:
                user_plan = meta.get("plan", "free")
                rate_key = f"apikey:{meta.get('key_id', clarvia_key[:12])}"
        except Exception:
            pass

    # Check daily scan limit
    allowed, current, limit = check_daily_scan_limit(rate_key, user_plan)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Daily scan limit reached",
                "current": current,
                "limit": limit,
                "plan": user_plan,
                "upgrade_url": "https://clarvia.art/pricing",
                "message": f"Free tier allows {limit} scans/day. Upgrade for more.",
            },
        )

    # Block auth_headers for free tier (authenticated scan is paid feature)
    if req.auth_headers and not has_feature(user_plan, Feature.AUTHENTICATED_SCAN):
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Authenticated scanning requires a starter or higher plan.",
                "upgrade_url": "https://clarvia.art/pricing",
                "current_plan": user_plan,
            },
        )

    try:
        result = await run_scan(req.url, auth_headers=req.auth_headers)

        # Increment daily scan counter on success
        increment_daily_scan(rate_key)

        # Add to in-memory index for immediate discoverability (compare, badge-data, score)
        try:
            from .routes.index_routes import _services, _by_scan_id, _classify
            entry = result.model_dump(mode="json") if hasattr(result, "model_dump") else {}
            if entry.get("scan_id") and entry["scan_id"] not in _by_scan_id:
                entry["category"] = _classify(entry.get("service_name", ""))
                _services.append(entry)
                _by_scan_id[entry["scan_id"]] = entry
        except Exception:
            pass  # Non-critical — index will catch up on next reload

        # Persist to Supabase if available
        if _supabase_client:
            try:
                from .services.supabase_client import save_scan
                await save_scan(result)
            except Exception as e:
                logger.warning("Failed to persist scan to Supabase: %s", e)

        # Save to scan history (Supabase + JSONL fallback)
        try:
            dim_scores = {}
            if result.dimensions:
                for k, v in result.dimensions.items():
                    dim_scores[k] = v.score if hasattr(v, "score") else (v.get("score", 0) if isinstance(v, dict) else 0)
            from .routes.scan_history_routes import persist_scan_result
            await persist_scan_result(
                url=result.url,
                scan_id=result.scan_id,
                score=result.clarvia_score,
                rating=result.rating,
                service_name=result.service_name,
                dimensions=dim_scores or None,
            )
        except Exception as e:
            logger.warning("Failed to save scan history: %s", e)

        # Fire scan_complete webhooks (non-blocking)
        try:
            from .routes.webhook_routes import fire_webhooks
            asyncio.create_task(fire_webhooks("scan_complete", {
                "url": result.url,
                "service_name": result.service_name,
                "scan_id": result.scan_id,
                "clarvia_score": result.clarvia_score,
                "rating": result.rating,
            }))
        except Exception:
            pass  # Webhook delivery is best-effort

        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Scan failed for URL: %s", req.url)
        raise HTTPException(
            status_code=500,
            detail="Scan failed due to an internal error. Please try again later.",
        )


@app.get("/api/scan/{scan_id}", response_model=ScanResponse, tags=["scan"])
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


@app.get("/api/scan/{scan_id}/sarif", tags=["scan"])
async def get_scan_sarif(scan_id: str):
    """Export scan results as SARIF 2.1.0 JSON for CI/CD integration."""
    result = get_cached_scan(scan_id)
    if result is None:
        if _supabase_client:
            try:
                from .services.supabase_client import get_scan_from_db
                result = await get_scan_from_db(scan_id)
            except Exception as e:
                logger.warning("Supabase lookup failed: %s", e)
        if result is None:
            raise HTTPException(status_code=404, detail="Scan not found or expired")

    from .sarif import scan_to_sarif
    sarif_doc = scan_to_sarif(result)
    return JSONResponse(
        content=sarif_doc,
        media_type="application/sarif+json",
        headers={"Content-Disposition": f'attachment; filename="{scan_id}.sarif.json"'},
    )


@app.post("/api/waitlist", tags=["marketing"])
async def join_waitlist(req: WaitlistRequest):
    """Add an email to the waitlist."""
    if _supabase_client:
        try:
            from .services.supabase_client import add_to_waitlist
            await add_to_waitlist(req.email)
        except Exception as e:
            logger.warning("Failed to save waitlist email: %s", e)

    return {"status": "ok", "message": "You've been added to the waitlist!"}


@app.post("/api/cache/cleanup", tags=["admin"])
async def cache_cleanup(request: Request):
    """Remove expired cache entries. Requires admin API key."""
    # Require admin API key for manual cache cleanup
    api_key = request.headers.get("x-api-key") or request.headers.get("x-clarvia-key")
    if not settings.admin_api_key or api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Admin API key required")

    removed = cleanup_cache()
    from .middleware import cleanup_rate_store
    rate_removed = cleanup_rate_store()
    return {"cache_removed": removed, "rate_limit_removed": rate_removed}


# ---------------------------------------------------------------------------
# Clarvia Public API v1 — programmatic access for agent builders
# ---------------------------------------------------------------------------

@app.get("/api/v1/score", tags=["scan"])
async def api_v1_score(url: str):
    """Get Clarvia Score for a URL. Checks cache/prebuilt first, runs live scan if needed.

    Usage: GET /api/v1/score?url=stripe.com
    Returns: { url, service_name, clarvia_score, rating, dimensions, scan_id }
    """
    import json
    from pathlib import Path

    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="url query parameter is required")

    # Normalize
    clean_url = url.strip().lower()
    if not clean_url.startswith("http"):
        clean_url = f"https://{clean_url}"

    def _domain_match(url_a: str, url_b: str) -> bool:
        """Compare URLs by domain (hostname) instead of substring."""
        from urllib.parse import urlparse as _up
        host_a = (_up(url_a).hostname or "").lower().removeprefix("www.")
        host_b = (_up(url_b).hostname or "").lower().removeprefix("www.")
        return host_a == host_b and host_a != ""

    # Check prebuilt scans first (fast path) — use shared in-memory data
    from .routes import index_routes as _idx
    _idx._ensure_loaded()
    scans = _idx._services
    if scans:
        for s in scans:
            if _domain_match(clean_url, s.get("url", "")):
                return {
                    "url": s["url"],
                    "service_name": s["service_name"],
                    "clarvia_score": s["clarvia_score"],
                    "rating": s.get("rating", ""),
                    "dimensions": {
                        k: {"score": v["score"], "max": v["max"]}
                        for k, v in s.get("dimensions", {}).items()
                    },
                    "scan_id": s["scan_id"],
                    "source": "prebuilt",
                    "scored_by": "Clarvia AEO",
                    "clarvia_profile_url": f"https://clarvia.art/tool/{s['scan_id']}",
                }

    # Run live scan
    try:
        result = await run_scan(clean_url)

        # Persist to scan history (Supabase + JSONL fallback)
        try:
            dim_scores = {}
            if result.dimensions:
                for k, v in result.dimensions.items():
                    dim_scores[k] = v.score if hasattr(v, "score") else (v.get("score", 0) if isinstance(v, dict) else 0)
            from .routes.scan_history_routes import persist_scan_result
            await persist_scan_result(
                url=result.url,
                scan_id=result.scan_id,
                score=result.clarvia_score,
                rating=result.rating,
                service_name=result.service_name,
                dimensions=dim_scores or None,
            )
        except Exception as e:
            logger.warning("Failed to save scan history from /v1/score: %s", e)

        return {
            "url": result.url,
            "service_name": result.service_name,
            "clarvia_score": result.clarvia_score,
            "rating": result.rating,
            "dimensions": {
                k: {"score": v.score, "max": v.max}
                for k, v in result.dimensions.items()
            },
            "scan_id": result.scan_id,
            "source": "live",
            "scored_by": "Clarvia AEO",
            "clarvia_profile_url": f"https://clarvia.art/tool/{result.scan_id}",
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("API v1 score scan failed for URL: %s", clean_url)
        raise HTTPException(status_code=500, detail="Scan failed due to an internal error. Please try again later.")


@app.get("/api/v1/leaderboard", tags=["index"])
async def api_v1_leaderboard(category: str | None = None, type: str | None = None, limit: int = 50, offset: int = 0):
    """Get the Clarvia leaderboard.

    Usage: GET /api/v1/leaderboard?category=ai_llm&limit=10
           GET /api/v1/leaderboard?type=mcp&limit=5
           GET /api/v1/leaderboard?type=api&limit=5
    """
    from .routes import index_routes as _idx
    _idx._ensure_loaded()
    scans = list(_idx._services)  # Copy to avoid mutating shared data
    if not scans:
        return {"services": [], "total": 0}

    # Filter by category
    if category:
        scans = [s for s in scans if s.get("category", "").lower() == category.lower()]

    # Filter by service_type (e.g. "mcp", "api")
    if type:
        scans = [s for s in scans if s.get("service_type", "").lower() == type.lower()]

    # Deduplicate by URL (keep highest-scoring entry per URL)
    seen_urls: dict[str, dict] = {}
    for s in scans:
        url_key = (s.get("url") or "").lower().rstrip("/")
        existing = seen_urls.get(url_key)
        if existing is None or s.get("clarvia_score", 0) > existing.get("clarvia_score", 0):
            seen_urls[url_key] = s
    scans = list(seen_urls.values())

    # Sort by score descending
    scans.sort(key=lambda s: s.get("clarvia_score", 0), reverse=True)

    # Apply pagination
    total = len(scans)
    page = scans[offset:offset + limit]

    return {
        "services": [
            {
                "service_name": s["service_name"],
                "url": s["url"],
                "clarvia_score": s["clarvia_score"],
                "rating": s.get("rating", ""),
                "scan_id": s["scan_id"],
            }
            for s in page
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@app.get("/api/v1/compare", tags=["index"])
async def api_v1_compare(urls: str):
    """Compare 2-5 services side by side with live scan fallback.

    Usage: GET /api/v1/compare?urls=stripe.com,plaid.com
    Returns detailed dimension-level comparison with winner analysis.
    """
    url_list = [u.strip() for u in urls.split(",") if u.strip()]
    if len(url_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 comma-separated URLs")
    if len(url_list) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 URLs for comparison")

    # Use shared in-memory data instead of re-reading 16MB JSON from disk
    from .routes import index_routes as _idx2
    _idx2._ensure_loaded()
    prebuilt = _idx2._services

    def _domain_match_compare(url_a: str, url_b: str) -> bool:
        """Compare URLs by domain (hostname) instead of substring."""
        from urllib.parse import urlparse as _up
        host_a = (_up(url_a).hostname or "").lower().removeprefix("www.")
        host_b = (_up(url_b).hostname or "").lower().removeprefix("www.")
        return host_a == host_b and host_a != ""

    def _normalize_compare_url(raw: str) -> str:
        clean = raw.lower().strip()
        if not clean.startswith("http"):
            clean = f"https://{clean}"
        return clean

    def _extract_name(url: str) -> str:
        return url.replace("https://", "").replace("http://", "").split("/")[0]

    services = []
    for url in url_list:
        clean = _normalize_compare_url(url)
        name = _extract_name(clean)

        # 1) Check prebuilt index first (fast path)
        match = next(
            (s for s in prebuilt if _domain_match_compare(clean, s.get("url", ""))),
            None
        )
        if match:
            services.append({
                "url": match["url"],
                "name": match.get("service_name", name),
                "score": match["clarvia_score"],
                "rating": match.get("rating", ""),
                "dimensions": {
                    k: {"score": v["score"], "max": v["max"]}
                    for k, v in match.get("dimensions", {}).items()
                },
                "source": "prebuilt",
            })
            continue

        # 2) Check live scan cache
        from .scanner import _scan_cache, _normalize_url as _norm_url
        try:
            normalized = _norm_url(clean)
        except Exception:
            normalized = clean
        cached_entry = next(
            (entry for sid, (entry, _ts) in _scan_cache.items()
             if _domain_match_compare(normalized, entry.url)),
            None
        )
        if cached_entry is not None:
            services.append({
                "url": cached_entry.url,
                "name": cached_entry.service_name,
                "score": cached_entry.clarvia_score,
                "rating": cached_entry.rating,
                "dimensions": {
                    k: {"score": v.score, "max": v.max}
                    for k, v in cached_entry.dimensions.items()
                },
                "source": "cache",
            })
            continue

        # 3) Run live scan
        try:
            result = await run_scan(clean)
            services.append({
                "url": result.url,
                "name": result.service_name,
                "score": result.clarvia_score,
                "rating": result.rating,
                "dimensions": {
                    k: {"score": v.score, "max": v.max}
                    for k, v in result.dimensions.items()
                },
                "source": "live",
            })
        except Exception as e:
            logger.warning("Compare scan failed for %s: %s", clean, e)
            services.append({
                "url": clean,
                "name": name,
                "score": None,
                "rating": None,
                "dimensions": {},
                "error": "scan_failed",
                "source": "error",
            })

    # --- Build comparison analysis ---
    scored = [s for s in services if s.get("score") is not None]

    winner = None
    winner_score_diff = None
    dimension_winners: dict[str, str] = {}
    summary = ""

    if len(scored) >= 2:
        # Overall winner
        top = max(scored, key=lambda s: s["score"])
        second = max((s for s in scored if s is not top), key=lambda s: s["score"])
        winner = top["name"]
        winner_score_diff = top["score"] - second["score"]

        # Dimension-level winners (only dimensions present in all scored services)
        all_dims: set[str] = set()
        for s in scored:
            all_dims.update(s["dimensions"].keys())

        for dim in all_dims:
            best = max(
                (s for s in scored if dim in s["dimensions"]),
                key=lambda s: s["dimensions"][dim]["score"],
                default=None,
            )
            if best:
                dimension_winners[dim] = best["name"]

        # Build summary string
        if winner_score_diff == 0:
            summary = f"{top['name']} and {second['name']} are tied with equal overall scores."
        else:
            # Find biggest advantage dimension
            advantage_dim = None
            advantage_gap = 0
            for dim, winner_name in dimension_winners.items():
                if winner_name == top["name"]:
                    top_dim_score = top["dimensions"].get(dim, {}).get("score", 0)
                    second_dim_score = second["dimensions"].get(dim, {}).get("score", 0)
                    gap = top_dim_score - second_dim_score
                    if gap > advantage_gap:
                        advantage_gap = gap
                        advantage_dim = dim

            # Find where top loses (if any)
            loser_dims = [
                dim for dim, winner_name in dimension_winners.items()
                if winner_name != top["name"] and len(scored) == 2
            ]

            dim_label = (advantage_dim or "").replace("_", " ").title() if advantage_dim else ""
            loser_label = loser_dims[0].replace("_", " ").title() if loser_dims else ""

            summary = f"{top['name']} scores {winner_score_diff} point{'s' if winner_score_diff != 1 else ''} higher overall."
            if advantage_dim and advantage_gap > 0:
                top_dim_score = top["dimensions"].get(advantage_dim, {}).get("score", 0)
                second_dim_score = second["dimensions"].get(advantage_dim, {}).get("score", 0)
                summary += f" Key advantage: better {dim_label} ({top_dim_score} vs {second_dim_score})."
            if loser_label:
                summary += f" {second['name']} leads in {loser_label}."

    # If no service could be scored at all, return 400
    if not scored:
        raise HTTPException(
            status_code=400,
            detail="Both services failed to scan. Please verify the URLs are accessible.",
        )

    # Strip internal "source" field from final output
    output_services = []
    for s in services:
        svc = {k: v for k, v in s.items() if k != "source"}
        output_services.append(svc)

    return {
        "services": output_services,
        "winner": winner,
        "winner_score_diff": winner_score_diff,
        "dimension_winners": dimension_winners,
        "summary": summary,
    }


@app.get("/api/v1/pricing", tags=["keys"])
async def api_v1_pricing():
    """Return pricing tiers and feature comparison.

    This is the canonical pricing endpoint — frontend and docs link here.
    """
    from .routes.payment_routes import get_pricing
    return await get_pricing()


@app.get("/api/v1/my-plan", tags=["keys"])
async def api_v1_my_plan(request: Request):
    """Get the authenticated user's plan and usage.

    Requires X-Clarvia-Key header.
    """
    from .routes.payment_routes import get_my_plan
    return await get_my_plan(request)


@app.get("/api/v1/methodology", tags=["scan"])
async def api_v1_methodology():
    """Return the scoring methodology as structured JSON."""
    return {
        "version": "1.1",
        "updated": "2026-03-25",
        "total_score": 100,
        "dimensions": {
            "api_accessibility": {
                "max": 25,
                "description": "How easily agents can reach and authenticate with your API",
                "sub_factors": {
                    "endpoint_existence": {"max": 7, "description": "Publicly reachable endpoint returning 2xx"},
                    "response_speed": {"max": 6, "description": "Median response time, target <200ms"},
                    "auth_documentation": {"max": 3, "description": "OpenAPI security schemes documented"},
                    "rate_limit_info": {"max": 6, "description": "X-RateLimit-* headers present. #1 cause of agent failures."},
                    "api_versioning": {"max": 1, "description": "API version in URL path or header"},
                    "sdk_availability": {"max": 1, "description": "Official SDKs on PyPI/npm"},
                    "free_tier": {"max": 1, "description": "Free tier or trial available"},
                },
            },
            "data_structuring": {
                "max": 25,
                "description": "Schema definition, pricing clarity, and error handling",
                "sub_factors": {
                    "schema_definition": {"max": 7, "description": "OpenAPI/JSON Schema published with typed models"},
                    "pricing_quantified": {"max": 5, "description": "Machine-readable pricing information"},
                    "error_structure": {"max": 5, "description": "Structured JSON errors (RFC 7807 or equivalent)"},
                    "webhook_support": {"max": 3, "description": "Webhook endpoints or documented webhook system"},
                    "batch_api": {"max": 3, "description": "Batch/bulk endpoints for efficient agent operations"},
                    "type_definitions": {"max": 2, "description": "JSON Schema or TypeScript type definitions published"},
                },
            },
            "agent_compatibility": {
                "max": 25,
                "description": "MCP support, robot policies, and discovery mechanisms",
                "sub_factors": {
                    "mcp_server_exists": {"max": 7, "description": "MCP server registered on mcp.so/smithery/glama"},
                    "robot_policy": {"max": 5, "description": "Agent-friendly robots.txt with AI agent rules"},
                    "discovery_mechanism": {"max": 5, "description": "Listed on API directories, discovery metadata"},
                    "idempotency_support": {"max": 3, "description": "Idempotency-Key header support for safe retries"},
                    "pagination_pattern": {"max": 2, "description": "Consistent cursor/offset pagination"},
                    "streaming_support": {"max": 3, "description": "SSE/streaming endpoints for real-time data"},
                },
            },
            "trust_signals": {
                "max": 25,
                "description": "Uptime, documentation quality, and update frequency",
                "sub_factors": {
                    "success_rate_uptime": {"max": 6, "description": "Public status page with uptime metrics and history"},
                    "documentation_quality": {"max": 5, "description": "API reference, guides, code examples, changelogs"},
                    "update_frequency": {"max": 4, "description": "Active changelog, recent updates within 30-90 days"},
                    "response_consistency": {"max": 4, "description": "Identical responses across repeated requests"},
                    "error_response_quality": {"max": 3, "description": "Error includes code, message, and documentation link"},
                    "deprecation_policy": {"max": 2, "description": "Explicit deprecation/versioning policy documented"},
                    "sla_guarantee": {"max": 1, "description": "Published SLA or uptime commitment"},
                },
            },
        },
        "onchain_bonus": {
            "max": 0,
            "status": "coming_soon",
            "description": "Blockchain-integrated services bonus (not yet active — planned for V2)",
            "sub_factors": {
                "transaction_success_rate": {"max": 10, "description": "On-chain transaction success rate"},
                "real_volume": {"max": 10, "description": "Verified real transaction volume"},
                "staking_commitment": {"max": 5, "description": "Staking or commitment signals"},
            },
        },
        "weight_rationale": {
            "rate_limit_info": "Raised from 3 to 6: #1 cause of agent failures in production (429 errors)",
            "mcp_server": "Lowered from 10 to 7: Important but APIs work fine without MCP via OpenAPI",
            "idempotency_support": "New (3pts): Critical for agent retry safety",
            "streaming_support": "New (3pts): Essential for LLM-based services",
            "pagination_pattern": "New (2pts): Agents need to handle large datasets",
            "trust_signals": "Restructured to 7 sub-factors: response consistency, error quality, deprecation, SLA now scored separately",
            "data_structuring": "Restructured to 6 sub-factors: added webhook support, batch API, type definitions; removed CORS",
        },
    }


# ---------------------------------------------------------------------------
# Authenticated Scan endpoint
# ---------------------------------------------------------------------------

@app.post("/api/scan/authenticated", tags=["scan"])
async def authenticated_scan(request: Request):
    """Run a deep authenticated scan against an API using user-supplied credentials.

    Body: {
        "url": "https://api.example.com",
        "api_key": "Bearer sk-xxx",
        "header_name": "Authorization",
        "run_full_scan": true  // optional: also run full AEO scan with auth
    }

    The API key is used only during the scan and is never logged or stored.
    This is a PAID feature — requires a valid Clarvia API key (starter+ plan).

    Deep scan includes:
    - Response structure analysis
    - Error response pattern analysis (404, 401, 403, 405, 422 responses)
    - Rate limit header detection and budget estimation
    - Protected endpoint discovery (common API patterns)
    - Pagination pattern detection
    - Optional full AEO scan with auth headers forwarded
    """
    import aiohttp
    import json as _json
    from .scanner import _validate_scan_url

    # --- Tier gate: authenticated scan requires starter+ plan ---
    clarvia_key = request.headers.get("x-clarvia-key")
    user_plan = "free"
    if clarvia_key:
        try:
            from .services.auth_service import validate_api_key
            meta = await validate_api_key(clarvia_key)
            if meta:
                user_plan = meta.get("plan", "free")
        except Exception:
            pass

    if user_plan == "free":
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Authenticated scan requires a starter or higher plan.",
                "upgrade_url": "https://clarvia.art/pricing",
                "current_plan": user_plan,
            },
        )

    body = await request.json()
    url: str = (body.get("url") or "").strip()
    api_key: str = (body.get("api_key") or "").strip()
    header_name: str = (body.get("header_name") or "Authorization").strip()
    run_full_scan: bool = body.get("run_full_scan", False)

    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")

    # Normalize
    if not url.startswith("http"):
        url = f"https://{url}"
    url = url.rstrip("/")

    try:
        _validate_scan_url(url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    auth_headers = {header_name: api_key}
    timeout = aiohttp.ClientTimeout(total=15)

    response_structure: dict = {}
    error_patterns: dict = {}
    rate_limit_analysis: dict = {}
    protected_endpoints: list[dict] = []
    pagination_analysis: dict = {}
    headers_found: list[str] = []
    auth_method: str = "unknown"

    # Detect auth method from the key value
    lower_key = api_key.lower()
    if lower_key.startswith("bearer "):
        auth_method = "bearer_token"
    elif lower_key.startswith("basic "):
        auth_method = "basic"
    elif lower_key.startswith("token "):
        auth_method = "token"
    else:
        auth_method = f"custom_header ({header_name})"

    USEFUL_HEADERS = {
        "content-type", "x-ratelimit-limit", "x-ratelimit-remaining",
        "x-ratelimit-reset", "x-request-id", "retry-after",
        "access-control-allow-origin", "access-control-allow-methods",
        "x-powered-by", "server", "strict-transport-security",
        "x-content-type-options", "x-frame-options",
        "x-total-count", "x-page", "x-per-page", "link",
    }

    # Common API endpoint patterns to probe
    _ENDPOINT_PATTERNS = [
        ("/users", "GET", "User management"),
        ("/me", "GET", "Current user profile"),
        ("/account", "GET", "Account info"),
        ("/v1", "GET", "API v1 root"),
        ("/v2", "GET", "API v2 root"),
        ("/api", "GET", "API root"),
        ("/graphql", "POST", "GraphQL endpoint"),
        ("/health", "GET", "Health check"),
        ("/status", "GET", "Status endpoint"),
        ("/docs", "GET", "API documentation"),
        ("/openapi.json", "GET", "OpenAPI spec"),
        ("/swagger.json", "GET", "Swagger spec"),
    ]

    try:
        # ssl=False is intentional for authenticated scan probing — targets may
        # use self-signed certs. This only applies to user-initiated scans.
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # --- Phase 1: Base response structure ---
            try:
                async with session.get(url, headers=auth_headers, ssl=False) as resp:
                    ct = resp.headers.get("Content-Type", "")
                    body_text = await resp.text()
                    is_json = False
                    has_typed_fields = False
                    response_keys: list[str] = []
                    try:
                        parsed = _json.loads(body_text)
                        is_json = True
                        if isinstance(parsed, dict):
                            has_typed_fields = any(
                                isinstance(v, (int, float, bool, list, dict))
                                for v in parsed.values()
                            )
                            response_keys = list(parsed.keys())[:20]
                    except (ValueError, _json.JSONDecodeError):
                        pass

                    response_structure = {
                        "status_code": resp.status,
                        "content_type": ct.split(";")[0].strip(),
                        "is_json": is_json,
                        "has_typed_fields": has_typed_fields,
                        "top_level_keys": response_keys,
                    }

                    for h in resp.headers:
                        if h.lower() in USEFUL_HEADERS:
                            headers_found.append(h)
            except asyncio.TimeoutError:
                response_structure = {"error": "Timeout on base URL request"}
            except Exception as e:
                response_structure = {"error": f"Request failed: {type(e).__name__}"}

            # --- Phase 2: Error pattern analysis (404, 401 without auth, 405) ---
            error_codes_tested: dict[str, dict] = {}

            async def _test_error(test_url: str, method: str, label: str, use_auth: bool = True) -> dict | None:
                hdrs = dict(auth_headers) if use_auth else {}
                try:
                    req_method = getattr(session, method.lower(), session.get)
                    async with req_method(test_url, headers=hdrs, ssl=False) as resp:
                        err_text = await resp.text()
                        structured = False
                        has_code = False
                        has_message = False
                        has_docs_link = False
                        try:
                            err_json = _json.loads(err_text)
                            structured = True
                            if isinstance(err_json, dict):
                                keys_lower = {k.lower() for k in err_json.keys()}
                                has_code = bool(keys_lower & {"code", "error_code", "status", "status_code"})
                                has_message = bool(keys_lower & {"message", "error", "detail", "description"})
                                # Check for documentation link in error
                                err_str = str(err_json).lower()
                                has_docs_link = any(w in err_str for w in ("docs.", "documentation", "help.", "support."))
                        except (ValueError, _json.JSONDecodeError):
                            pass
                        return {
                            "status_code": resp.status,
                            "is_structured_json": structured,
                            "has_error_code": has_code,
                            "has_error_message": has_message,
                            "has_docs_link": has_docs_link,
                        }
                except Exception:
                    return None

            # Test 404
            result_404 = await _test_error(f"{url}/clarvia-test-nonexistent-path-404", "GET", "not_found")
            if result_404:
                error_codes_tested["404_not_found"] = result_404

            # Test 405 (wrong method)
            result_405 = await _test_error(url, "DELETE", "method_not_allowed")
            if result_405:
                error_codes_tested["405_method_not_allowed"] = result_405

            # Test 401 (no auth)
            result_401 = await _test_error(url, "GET", "unauthorized", use_auth=False)
            if result_401:
                error_codes_tested["401_unauthorized"] = result_401

            # Test 422 (bad input)
            try:
                async with session.post(
                    url, headers=auth_headers,
                    json={"clarvia_test": True}, ssl=False,
                ) as resp:
                    err_text = await resp.text()
                    structured = False
                    try:
                        _json.loads(err_text)
                        structured = True
                    except (ValueError, _json.JSONDecodeError):
                        pass
                    error_codes_tested["422_validation"] = {
                        "status_code": resp.status,
                        "is_structured_json": structured,
                    }
            except Exception:
                pass

            # Summarize error quality
            structured_count = sum(1 for v in error_codes_tested.values() if v.get("is_structured_json"))
            total_tested = len(error_codes_tested)
            has_docs = any(v.get("has_docs_link") for v in error_codes_tested.values())
            error_patterns = {
                "error_codes_tested": error_codes_tested,
                "consistency_score": f"{structured_count}/{total_tested} structured",
                "quality": (
                    "excellent" if structured_count == total_tested and has_docs
                    else "good" if structured_count == total_tested
                    else "partial" if structured_count > 0
                    else "poor"
                ),
                "has_documentation_links": has_docs,
            }

            # --- Phase 3: Rate limit analysis ---
            rl_limit = None
            rl_remaining = None
            rl_reset = None
            has_retry_after = False

            for h_name in headers_found:
                h_lower = h_name.lower()
                if h_lower == "x-ratelimit-limit":
                    try:
                        async with session.head(url, headers=auth_headers, ssl=False) as resp:
                            rl_limit = resp.headers.get("X-RateLimit-Limit")
                            rl_remaining = resp.headers.get("X-RateLimit-Remaining")
                            rl_reset = resp.headers.get("X-RateLimit-Reset")
                            has_retry_after = "Retry-After" in resp.headers
                    except Exception:
                        pass
                    break

            # If no rate limit headers found from first pass, do a dedicated check
            if rl_limit is None:
                try:
                    async with session.head(url, headers=auth_headers, ssl=False) as resp:
                        rl_limit = resp.headers.get("X-RateLimit-Limit") or resp.headers.get("x-ratelimit-limit")
                        rl_remaining = resp.headers.get("X-RateLimit-Remaining") or resp.headers.get("x-ratelimit-remaining")
                        rl_reset = resp.headers.get("X-RateLimit-Reset") or resp.headers.get("x-ratelimit-reset")
                        has_retry_after = any(
                            h.lower() == "retry-after" for h in resp.headers
                        )
                        # Also collect any headers we missed
                        for h in resp.headers:
                            if h.lower() in USEFUL_HEADERS and h not in headers_found:
                                headers_found.append(h)
                except Exception:
                    pass

            rate_limit_analysis = {
                "limit": rl_limit,
                "remaining": rl_remaining,
                "reset": rl_reset,
                "has_retry_after": has_retry_after,
                "completeness": (
                    "full" if all([rl_limit, rl_remaining, rl_reset, has_retry_after])
                    else "good" if all([rl_limit, rl_remaining])
                    else "partial" if rl_limit
                    else "none"
                ),
                "agent_safety_note": (
                    "Agents can self-throttle safely" if rl_limit and rl_remaining
                    else "Agents cannot detect rate limits — high risk of 429 errors"
                ),
            }

            # --- Phase 4: Protected endpoint discovery ---
            async def _probe_endpoint(path: str, method: str, label: str) -> dict | None:
                probe_url = f"{url.rstrip('/')}{path}"
                try:
                    req_method = getattr(session, method.lower(), session.get)
                    kwargs = {"headers": auth_headers, "ssl": False}
                    if method.upper() == "POST":
                        kwargs["json"] = {}
                    async with req_method(probe_url, **kwargs) as resp:
                        if resp.status < 500:  # Any non-server-error means endpoint exists
                            ct = resp.headers.get("Content-Type", "")
                            return {
                                "path": path,
                                "method": method.upper(),
                                "label": label,
                                "status_code": resp.status,
                                "content_type": ct.split(";")[0].strip(),
                                "accessible": resp.status < 400,
                                "auth_required": resp.status in (401, 403),
                            }
                except Exception:
                    pass
                return None

            # Probe endpoints concurrently (with limit)
            probe_tasks = [
                _probe_endpoint(path, method, label)
                for path, method, label in _ENDPOINT_PATTERNS
            ]
            probe_results = await asyncio.gather(*probe_tasks, return_exceptions=True)
            protected_endpoints = [
                r for r in probe_results
                if isinstance(r, dict) and r is not None
            ]

            # --- Phase 5: Pagination detection ---
            try:
                async with session.get(url, headers=auth_headers, ssl=False) as resp:
                    body_text = await resp.text()
                    link_header = resp.headers.get("Link", "")
                    has_link_pagination = "rel=" in link_header

                    has_cursor = False
                    has_offset = False
                    has_total_count = False
                    try:
                        data = _json.loads(body_text)
                        if isinstance(data, dict):
                            keys_lower = {k.lower() for k in data.keys()}
                            has_cursor = bool(keys_lower & {"cursor", "next_cursor", "next_page_token", "page_token", "after"})
                            has_offset = bool(keys_lower & {"offset", "page", "per_page", "page_size", "limit"})
                            has_total_count = bool(keys_lower & {"total", "total_count", "count", "total_results"})
                    except (ValueError, _json.JSONDecodeError):
                        pass

                    # Check X-Total-Count style headers
                    has_total_header = any(
                        h.lower() in ("x-total-count", "x-total", "x-page")
                        for h in resp.headers
                    )

                    pagination_analysis = {
                        "has_link_header": has_link_pagination,
                        "has_cursor_pagination": has_cursor,
                        "has_offset_pagination": has_offset,
                        "has_total_count": has_total_count or has_total_header,
                        "pattern": (
                            "cursor" if has_cursor
                            else "link_header" if has_link_pagination
                            else "offset" if has_offset
                            else "none_detected"
                        ),
                    }
            except Exception:
                pagination_analysis = {"error": "Could not analyze pagination"}

            # --- Phase 6 (optional): Full AEO scan with auth ---
            full_scan_result = None
            if run_full_scan:
                try:
                    scan_result = await run_scan(url, auth_headers=auth_headers)
                    full_scan_result = {
                        "scan_id": scan_result.scan_id,
                        "clarvia_score": scan_result.clarvia_score,
                        "rating": scan_result.rating,
                        "agent_grade": scan_result.agent_grade,
                        "authenticated_scan": True,
                        "dimensions": {
                            k: {"score": v.score, "max": v.max}
                            for k, v in scan_result.dimensions.items()
                        },
                        "top_recommendations": scan_result.top_recommendations[:5],
                    }
                except Exception as e:
                    full_scan_result = {"error": f"Full scan failed: {type(e).__name__}"}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Authenticated scan failed for %s", url)
        raise HTTPException(status_code=500, detail="Authenticated scan failed due to an internal error. Please try again later.")

    report = {
        "url": url,
        "auth_method": auth_method,
        "scan_type": "authenticated_deep",
        "response_structure": response_structure,
        "error_patterns": error_patterns,
        "rate_limit_analysis": rate_limit_analysis,
        "protected_endpoints": protected_endpoints,
        "pagination_analysis": pagination_analysis,
        "headers_found": sorted(set(headers_found)),
    }
    if full_scan_result:
        report["full_aeo_scan"] = full_scan_result

    return {"auth_scan_report": report}


# ---------------------------------------------------------------------------
# MCP Scan endpoint
# ---------------------------------------------------------------------------

@app.get("/api/v1/mcp-scan", tags=["scan"])
async def mcp_scan(identifier: str):
    """Scan an MCP server by URL, npm package name, or GitHub repo.

    Query param `identifier` can be:
    - A mcp.run URL (e.g. "https://mcp.run/@jake/code-search")
    - An npm package name (e.g. "@anthropic/mcp-server-fetch")
    - A GitHub repo URL (e.g. "https://github.com/org/repo")
    """
    import re
    import json
    import aiohttp

    identifier = identifier.strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="identifier query parameter is required")

    timeout = aiohttp.ClientTimeout(total=15)
    tools: list[dict] = []
    mcp_found = False
    quality_score = 0
    recommendations: list[str] = []
    source_type = "unknown"

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:

            # --- Case 1: mcp.run URL ---
            if "mcp.run/" in identifier:
                source_type = "mcp_run"
                try:
                    async with session.get(identifier, ssl=False) as resp:
                        if resp.status == 200:
                            html = await resp.text()
                            mcp_found = True

                            # Extract tool names/descriptions from page content
                            # mcp.run pages typically have tool info in structured elements
                            tool_pattern = re.findall(
                                r'"name"\s*:\s*"([^"]+)".*?"description"\s*:\s*"([^"]*)"',
                                html,
                                re.DOTALL,
                            )
                            if tool_pattern:
                                for name, desc in tool_pattern:
                                    tools.append({
                                        "name": name,
                                        "description": desc[:200],
                                        "parameters_count": 0,  # Not reliably extractable from HTML
                                    })

                            # Fallback: look for tool headings or list items
                            if not tools:
                                heading_tools = re.findall(r'<h[23][^>]*>([^<]+)</h[23]>', html)
                                for t in heading_tools[:20]:
                                    clean = t.strip()
                                    if clean and len(clean) < 80:
                                        tools.append({"name": clean, "description": "", "parameters_count": 0})

                        else:
                            mcp_found = False
                except Exception:
                    mcp_found = False

            # --- Case 2: GitHub URL ---
            elif "github.com/" in identifier:
                source_type = "github"
                # Extract owner/repo
                gh_match = re.search(r'github\.com/([^/]+/[^/\s?#]+)', identifier)
                if not gh_match:
                    raise HTTPException(status_code=422, detail="Could not parse GitHub URL")

                repo_path = gh_match.group(1).rstrip("/")
                api_base = f"https://api.github.com/repos/{repo_path}"

                # Check package.json for MCP references
                pkg_url = f"https://raw.githubusercontent.com/{repo_path}/main/package.json"
                try:
                    async with session.get(pkg_url, ssl=False) as resp:
                        if resp.status == 200:
                            pkg_text = await resp.text()
                            pkg = json.loads(pkg_text)
                            deps = {
                                **pkg.get("dependencies", {}),
                                **pkg.get("devDependencies", {}),
                            }
                            mcp_deps = [k for k in deps if "modelcontextprotocol" in k.lower() or "mcp" in k.lower()]
                            if mcp_deps:
                                mcp_found = True

                            # Extract tool info from package.json keywords/description
                            desc = pkg.get("description", "")
                            keywords = pkg.get("keywords", [])
                            if any("mcp" in kw.lower() for kw in keywords):
                                mcp_found = True

                            # Check for tool definitions in bin or main entry
                            if mcp_found and desc:
                                tools.append({
                                    "name": pkg.get("name", repo_path.split("/")[-1]),
                                    "description": desc[:200],
                                    "parameters_count": 0,
                                })
                except Exception:
                    pass

                # Also check for mcp.json at repo root
                if not mcp_found:
                    mcp_json_url = f"https://raw.githubusercontent.com/{repo_path}/main/mcp.json"
                    try:
                        async with session.get(mcp_json_url, ssl=False) as resp:
                            if resp.status == 200:
                                mcp_found = True
                                mcp_data = json.loads(await resp.text())
                                if isinstance(mcp_data, dict):
                                    for tool_def in mcp_data.get("tools", []):
                                        tools.append({
                                            "name": tool_def.get("name", "unknown"),
                                            "description": tool_def.get("description", "")[:200],
                                            "parameters_count": len(tool_def.get("inputSchema", {}).get("properties", {})),
                                        })
                    except Exception:
                        pass

            # --- Case 3: npm package name ---
            else:
                source_type = "npm"
                # URL-encode scoped packages: @scope/name -> @scope%2fname
                pkg_name = identifier.strip()
                npm_url = f"https://registry.npmjs.org/{pkg_name.replace('/', '%2f')}"

                try:
                    async with session.get(npm_url, ssl=False) as resp:
                        if resp.status == 200:
                            data = json.loads(await resp.text())
                            desc = data.get("description", "")
                            keywords = data.get("keywords", [])
                            name = data.get("name", pkg_name)

                            if any("mcp" in kw.lower() for kw in keywords) or "mcp" in desc.lower() or "model context protocol" in desc.lower():
                                mcp_found = True

                            # Check latest version for MCP dependencies
                            dist_tags = data.get("dist-tags", {})
                            latest_ver = dist_tags.get("latest", "")
                            versions = data.get("versions", {})
                            if latest_ver and latest_ver in versions:
                                ver_data = versions[latest_ver]
                                deps = {
                                    **ver_data.get("dependencies", {}),
                                    **ver_data.get("devDependencies", {}),
                                }
                                mcp_deps = [k for k in deps if "modelcontextprotocol" in k.lower() or "mcp" in k.lower()]
                                if mcp_deps:
                                    mcp_found = True

                            tools.append({
                                "name": name,
                                "description": desc[:200],
                                "parameters_count": 0,
                            })
                        elif resp.status == 404:
                            mcp_found = False
                except Exception:
                    pass

    except Exception:
        raise HTTPException(status_code=500, detail="MCP scan failed due to an internal error. Please try again later.")

    # --- Quality scoring ---
    if mcp_found:
        quality_score += 30  # Base: MCP detected

        # Tool count scoring (up to 20 pts)
        tool_count = len(tools)
        if tool_count >= 5:
            quality_score += 20
        elif tool_count >= 1:
            quality_score += tool_count * 4

        # Description quality (up to 30 pts)
        described_tools = sum(1 for t in tools if t.get("description") and len(t["description"]) > 10)
        if tools:
            desc_ratio = described_tools / len(tools)
            quality_score += int(desc_ratio * 30)

        # Parameter typing (up to 20 pts)
        typed_tools = sum(1 for t in tools if t.get("parameters_count", 0) > 0)
        if tools:
            typed_ratio = typed_tools / len(tools)
            quality_score += int(typed_ratio * 20)

        quality_score = min(quality_score, 100)

    # --- Recommendations ---
    if not mcp_found:
        recommendations.append("No MCP integration detected. Consider adding @modelcontextprotocol/sdk.")
    else:
        if len(tools) == 0:
            recommendations.append("No tools detected. Expose tool definitions in your MCP server manifest.")
        undescribed = [t["name"] for t in tools if not t.get("description") or len(t.get("description", "")) < 10]
        if undescribed:
            recommendations.append(f"Add meaningful descriptions to: {', '.join(undescribed[:5])}")
        untyped = [t["name"] for t in tools if t.get("parameters_count", 0) == 0]
        if untyped:
            recommendations.append(f"Add parameter schemas (inputSchema) for: {', '.join(untyped[:5])}")
        if len(tools) < 3:
            recommendations.append("Consider exposing more tools to increase utility for AI agents.")

    return {
        "identifier": identifier,
        "source_type": source_type,
        "mcp_found": mcp_found,
        "tools": tools,
        "quality_score": quality_score,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Fix-This Code Generation — pre-written templates, no LLM calls
# ---------------------------------------------------------------------------

FIX_TEMPLATES: dict[str, dict[str, dict]] = {
    "rate_limit_info": {
        "python": {
            "title": "Add Rate Limit Headers (FastAPI)",
            "code": """from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/resource", tags=["scan"])
@limiter.limit("60/minute")
async def get_resource(request: Request):
    return {"data": "example"}

# Automatically adds X-RateLimit-Limit, X-RateLimit-Remaining,
# and X-RateLimit-Reset headers to every response.""",
            "install": "pip install slowapi",
            "estimated_time": "10 min",
            "potential_gain": 6,
        },
        "nodejs": {
            "title": "Add Rate Limit Headers (Express)",
            "code": """const rateLimit = require('express-rate-limit');

const limiter = rateLimit({
  windowMs: 60 * 1000,       // 1 minute window
  max: 100,                   // limit each IP to 100 req/window
  standardHeaders: true,      // Return X-RateLimit-* headers
  legacyHeaders: false,
  message: { error: { code: 'RATE_LIMITED', message: 'Too many requests' } },
});

// Apply to all API routes
app.use('/api/', limiter);

// Or apply to specific routes
app.get('/api/resource', limiter, (req, res) => {
  res.json({ data: 'example' });
});""",
            "install": "npm install express-rate-limit",
            "estimated_time": "10 min",
            "potential_gain": 6,
        },
        "go": {
            "title": "Add Rate Limit Headers (Go)",
            "code": """package main

import (
    "net/http"
    "strconv"
    "time"

    "golang.org/x/time/rate"
)

var limiter = rate.NewLimiter(rate.Every(time.Minute/100), 10) // 100/min, burst 10

func rateLimitMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        reservation := limiter.Reserve()
        if !reservation.OK() {
            w.Header().Set("Retry-After", "60")
            http.Error(w, `{"error":"rate_limited"}`, http.StatusTooManyRequests)
            return
        }
        w.Header().Set("X-RateLimit-Limit", "100")
        w.Header().Set("X-RateLimit-Remaining",
            strconv.Itoa(int(limiter.Tokens())))
        next.ServeHTTP(w, r)
    })
}""",
            "install": "go get golang.org/x/time/rate",
            "estimated_time": "15 min",
            "potential_gain": 6,
        },
    },
    "error_structure": {
        "python": {
            "title": "Structured JSON Error Responses (FastAPI)",
            "code": """from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

class APIError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, docs: str = ""):
        self.code = code
        self.message = message
        self.status = status
        self.docs = docs

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(status_code=exc.status, content={
        "error": {
            "code": exc.code,
            "message": exc.message,
            "docs_url": exc.docs or f"https://docs.example.com/errors/{exc.code}",
            "request_id": request.headers.get("x-request-id", ""),
        }
    })

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "docs_url": "https://docs.example.com/errors/INTERNAL_ERROR",
        }
    })""",
            "install": "",
            "estimated_time": "15 min",
            "potential_gain": 7,
        },
        "nodejs": {
            "title": "Structured JSON Error Responses (Express)",
            "code": """class APIError extends Error {
  constructor(code, message, status = 400, docsUrl = '') {
    super(message);
    this.code = code;
    this.status = status;
    this.docsUrl = docsUrl || `https://docs.example.com/errors/${code}`;
  }
}

// Error handling middleware — add AFTER all routes
app.use((err, req, res, next) => {
  if (err instanceof APIError) {
    return res.status(err.status).json({
      error: {
        code: err.code,
        message: err.message,
        docs_url: err.docsUrl,
        request_id: req.headers['x-request-id'] || '',
      },
    });
  }
  console.error('Unhandled error:', err);
  res.status(500).json({
    error: {
      code: 'INTERNAL_ERROR',
      message: 'An unexpected error occurred',
      docs_url: 'https://docs.example.com/errors/INTERNAL_ERROR',
    },
  });
});

// Usage: throw new APIError('INVALID_PARAM', 'Missing url field', 422);""",
            "install": "",
            "estimated_time": "15 min",
            "potential_gain": 7,
        },
        "go": {
            "title": "Structured JSON Error Responses (Go)",
            "code": """package main

import (
    "encoding/json"
    "fmt"
    "net/http"
)

type APIError struct {
    Code    string `json:"code"`
    Message string `json:"message"`
    DocsURL string `json:"docs_url"`
}

func writeError(w http.ResponseWriter, status int, code, message string) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(map[string]APIError{
        "error": {
            Code:    code,
            Message: message,
            DocsURL: fmt.Sprintf("https://docs.example.com/errors/%s", code),
        },
    })
}

// Usage in handler:
func handler(w http.ResponseWriter, r *http.Request) {
    id := r.URL.Query().Get("id")
    if id == "" {
        writeError(w, 400, "MISSING_PARAM", "Query parameter id is required")
        return
    }
}""",
            "install": "",
            "estimated_time": "15 min",
            "potential_gain": 7,
        },
    },
    "mcp_server": {
        "python": {
            "title": "MCP Server Scaffold (Python)",
            "code": """import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-service", description="My API as an MCP server")

@mcp.tool()
async def search(query: str, limit: int = 10) -> str:
    \"\"\"Search for items matching the query.

    Args:
        query: Search keywords
        limit: Max results to return (1-100)
    \"\"\"
    # Replace with your actual API logic
    results = await your_api.search(query=query, limit=limit)
    return json.dumps(results, indent=2)

@mcp.resource("schema://openapi")
async def get_schema() -> str:
    \"\"\"Return the OpenAPI schema for this service.\"\"\"
    return json.dumps(your_openapi_spec)

# Run: python server.py
if __name__ == "__main__":
    mcp.run(transport="stdio")""",
            "install": "pip install mcp[cli]",
            "estimated_time": "30 min",
            "potential_gain": 7,
        },
        "nodejs": {
            "title": "MCP Server Scaffold (Node.js)",
            "code": """import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "my-service",
  version: "1.0.0",
  description: "My API as an MCP server",
});

server.tool("search",
  { query: z.string(), limit: z.number().default(10) },
  async ({ query, limit }) => {
    // Replace with your actual API logic
    const results = await yourApi.search({ query, limit });
    return { content: [{ type: "text", text: JSON.stringify(results) }] };
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);""",
            "install": "npm install @modelcontextprotocol/sdk zod",
            "estimated_time": "30 min",
            "potential_gain": 7,
        },
        "go": {
            "title": "MCP Server Scaffold (Go)",
            "code": """package main

import (
    "context"
    "fmt"
    "os"

    "github.com/mark3labs/mcp-go/mcp"
    "github.com/mark3labs/mcp-go/server"
)

func main() {
    s := server.NewMCPServer("my-service", "1.0.0")
    searchTool := mcp.NewTool("search",
        mcp.WithDescription("Search for items"),
        mcp.WithString("query", mcp.Required(), mcp.Description("Search keywords")),
        mcp.WithNumber("limit", mcp.Description("Max results")),
    )
    s.AddTool(searchTool, func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
        query := req.Params.Arguments["query"].(string)
        // Replace with your actual search logic
        return mcp.NewToolResultText(fmt.Sprintf("Results for: %s", query)), nil
    })
    if err := server.ServeStdio(s); err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\\n", err)
        os.Exit(1)
    }
}""",
            "install": "go get github.com/mark3labs/mcp-go",
            "estimated_time": "30 min",
            "potential_gain": 7,
        },
    },
    "schema_definition": {
        "python": {
            "title": "OpenAPI Schema with Pydantic Models (FastAPI)",
            "code": """from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(
    title="My API",
    version="1.0.0",
    description="A well-documented API with full OpenAPI schema",
)

class Item(BaseModel):
    id: str = Field(..., description="Unique item identifier", example="item_abc123")
    name: str = Field(..., min_length=1, max_length=200, description="Item name")
    price: float = Field(..., gt=0, description="Price in USD")
    tags: list[str] = Field(default=[], description="Categorization tags")

class ItemList(BaseModel):
    items: list[Item]
    total: int = Field(..., description="Total number of items")
    cursor: Optional[str] = Field(None, description="Cursor for next page")

@app.get("/api/items", tags=["index"], response_model=ItemList, summary="List all items")
async def list_items(cursor: Optional[str] = None, limit: int = 20):
    \"\"\"Retrieve a paginated list of items.\"\"\"
    pass  # your implementation

# OpenAPI JSON auto-served at /openapi.json
# Interactive docs at /docs and /redoc""",
            "install": "",
            "estimated_time": "20 min",
            "potential_gain": 10,
        },
        "nodejs": {
            "title": "OpenAPI Schema with swagger-jsdoc (Express)",
            "code": """const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');

const swaggerSpec = swaggerJsdoc({
  definition: {
    openapi: '3.0.0',
    info: { title: 'My API', version: '1.0.0' },
    servers: [{ url: '/api' }],
  },
  apis: ['./routes/*.js'],
});

app.use('/docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));
app.get('/openapi.json', (req, res) => res.json(swaggerSpec));

/**
 * @openapi
 * /api/items:
 *   get:
 *     summary: List all items
 *     parameters:
 *       - in: query
 *         name: limit
 *         schema: { type: integer, default: 20 }
 *     responses:
 *       200:
 *         description: Paginated item list
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 items: { type: array, items: { $ref: '#/components/schemas/Item' } }
 *                 total: { type: integer }
 */
app.get('/api/items', (req, res) => { /* ... */ });""",
            "install": "npm install swagger-jsdoc swagger-ui-express",
            "estimated_time": "25 min",
            "potential_gain": 10,
        },
        "go": {
            "title": "OpenAPI Schema with swag (Go)",
            "code": """package main

import (
    "net/http"
    httpSwagger "github.com/swaggo/http-swagger"
    _ "myapp/docs" // generated by swag init
)

// @title My API
// @version 1.0
// @description A well-documented API
// @BasePath /api

type Item struct {
    ID    string   `json:"id" example:"item_abc123"`
    Name  string   `json:"name" example:"Widget"`
    Price float64  `json:"price" example:"29.99"`
    Tags  []string `json:"tags" example:"electronics,sale"`
}

type ItemList struct {
    Items  []Item `json:"items"`
    Total  int    `json:"total" example:"142"`
    Cursor string `json:"cursor,omitempty"`
}

// ListItems godoc
// @Summary List all items
// @Produce json
// @Param limit query int false "Page size" default(20)
// @Success 200 {object} ItemList
// @Router /items [get]
func ListItems(w http.ResponseWriter, r *http.Request) { /* ... */ }

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/api/items", ListItems)
    mux.Handle("/docs/", httpSwagger.WrapHandler)
    http.ListenAndServe(":8080", mux)
}""",
            "install": "go install github.com/swaggo/swag/cmd/swag@latest && go get github.com/swaggo/http-swagger",
            "estimated_time": "25 min",
            "potential_gain": 10,
        },
    },
    "robot_policy": {
        "python": {
            "title": "Agent-Friendly robots.txt and ai-plugin.json (FastAPI)",
            "code": """from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

ROBOTS_TXT = \"\"\"User-agent: *
Allow: /api/
Allow: /docs
Allow: /openapi.json

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: CCBot
Allow: /

Sitemap: https://api.example.com/sitemap.xml
\"\"\"

@app.get("/robots.txt", tags=["system"], response_class=PlainTextResponse)
async def robots():
    return ROBOTS_TXT

@app.get("/.well-known/ai-plugin.json", tags=["system"])
async def ai_plugin():
    return {
        "schema_version": "v1",
        "name_for_human": "My Service",
        "name_for_model": "my_service",
        "description_for_human": "Access My Service data and actions",
        "description_for_model": "Query and manage resources via REST API",
        "auth": {"type": "none"},
        "api": {"type": "openapi", "url": "https://api.example.com/openapi.json"},
    }""",
            "install": "",
            "estimated_time": "10 min",
            "potential_gain": 5,
        },
        "nodejs": {
            "title": "Agent-Friendly robots.txt and ai-plugin.json (Express)",
            "code": """const ROBOTS_TXT = `User-agent: *
Allow: /api/
Allow: /docs
Allow: /openapi.json

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: CCBot
Allow: /

Sitemap: https://api.example.com/sitemap.xml
`;

app.get('/robots.txt', (req, res) => {
  res.type('text/plain').send(ROBOTS_TXT);
});

app.get('/.well-known/ai-plugin.json', (req, res) => {
  res.json({
    schema_version: 'v1',
    name_for_human: 'My Service',
    name_for_model: 'my_service',
    description_for_human: 'Access My Service data and actions',
    description_for_model: 'Query and manage resources via REST API',
    auth: { type: 'none' },
    api: { type: 'openapi', url: 'https://api.example.com/openapi.json' },
  });
});""",
            "install": "",
            "estimated_time": "10 min",
            "potential_gain": 5,
        },
        "go": {
            "title": "Agent-Friendly robots.txt and ai-plugin.json (Go)",
            "code": """package main

import (
    "encoding/json"
    "net/http"
)

const robotsTxt = `User-agent: *
Allow: /api/
Allow: /docs
Allow: /openapi.json

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: CCBot
Allow: /
`

func robotsHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "text/plain")
    w.Write([]byte(robotsTxt))
}

func aiPluginHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "schema_version":        "v1",
        "name_for_human":        "My Service",
        "name_for_model":        "my_service",
        "description_for_model": "Query and manage resources via REST API",
        "auth":                  map[string]string{"type": "none"},
        "api": map[string]string{
            "type": "openapi",
            "url":  "https://api.example.com/openapi.json",
        },
    })
}

// Register: mux.HandleFunc("/robots.txt", robotsHandler)
//           mux.HandleFunc("/.well-known/ai-plugin.json", aiPluginHandler)""",
            "install": "",
            "estimated_time": "10 min",
            "potential_gain": 5,
        },
    },
    "uptime_monitoring": {
        "python": {
            "title": "Health Endpoint and Status Page (FastAPI)",
            "code": """import time
from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI()
_start_time = time.monotonic()

@app.get("/health")
async def health():
    \"\"\"Basic health check — returns 200 if service is running.\"\"\"
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.monotonic() - _start_time),
        "version": "1.0.0",
    }

@app.get("/health/ready")
async def readiness():
    \"\"\"Readiness probe — checks downstream dependencies.\"\"\"
    checks = {}
    # Add your dependency checks here:
    # checks["database"] = await check_db()
    # checks["cache"] = await check_redis()
    all_ok = all(v == "ok" for v in checks.values()) if checks else True
    return {
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# Tip: Point UptimeRobot or Better Stack at /health for free monitoring""",
            "install": "",
            "estimated_time": "10 min",
            "potential_gain": 8,
        },
        "nodejs": {
            "title": "Health Endpoint and Status Page (Express)",
            "code": """const startTime = Date.now();

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime_seconds: Math.round((Date.now() - startTime) / 1000),
    version: '1.0.0',
  });
});

app.get('/health/ready', async (req, res) => {
  const checks = {};
  // Add dependency checks:
  // checks.database = await checkDb();
  // checks.cache = await checkRedis();
  const allOk = Object.values(checks).every(v => v === 'ok');
  res.status(allOk || !Object.keys(checks).length ? 200 : 503).json({
    status: allOk || !Object.keys(checks).length ? 'ready' : 'degraded',
    checks,
    timestamp: new Date().toISOString(),
  });
});

// Tip: Point UptimeRobot or Better Stack at /health for free monitoring""",
            "install": "",
            "estimated_time": "10 min",
            "potential_gain": 8,
        },
        "go": {
            "title": "Health Endpoint and Status Page (Go)",
            "code": """package main

import (
    "encoding/json"
    "net/http"
    "time"
)

var startTime = time.Now()

func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "status":         "healthy",
        "timestamp":      time.Now().UTC().Format(time.RFC3339),
        "uptime_seconds": int(time.Since(startTime).Seconds()),
        "version":        "1.0.0",
    })
}

func readinessHandler(w http.ResponseWriter, r *http.Request) {
    checks := map[string]string{}
    // Add checks: checks["database"] = checkDB()
    allOk := true
    for _, v := range checks {
        if v != "ok" { allOk = false }
    }
    status := "ready"
    if !allOk { status = "degraded"; w.WriteHeader(503) }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "status": status, "checks": checks,
        "timestamp": time.Now().UTC().Format(time.RFC3339),
    })
}

// Register: mux.HandleFunc("/health", healthHandler)
//           mux.HandleFunc("/health/ready", readinessHandler)""",
            "install": "",
            "estimated_time": "10 min",
            "potential_gain": 8,
        },
    },
    "idempotency_support": {
        "python": {
            "title": "Idempotency-Key Support (FastAPI)",
            "code": """from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# In-memory store (use Redis in production)
_idempotency_cache: dict[str, dict] = {}

class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            return await call_next(request)

        # Return cached response if key already seen
        if idem_key in _idempotency_cache:
            cached = _idempotency_cache[idem_key]
            return Response(
                content=cached["body"],
                status_code=cached["status"],
                headers={**cached["headers"], "X-Idempotent-Replayed": "true"},
                media_type="application/json",
            )

        response = await call_next(request)
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        _idempotency_cache[idem_key] = {
            "body": body,
            "status": response.status_code,
            "headers": dict(response.headers),
        }
        return Response(content=body, status_code=response.status_code,
                        headers=dict(response.headers), media_type="application/json")

app = FastAPI()
app.add_middleware(IdempotencyMiddleware)""",
            "install": "",
            "estimated_time": "20 min",
            "potential_gain": 3,
        },
        "nodejs": {
            "title": "Idempotency-Key Support (Express)",
            "code": """// In-memory store (use Redis in production)
const idempotencyCache = new Map();

function idempotencyMiddleware(req, res, next) {
  if (!['POST', 'PUT', 'PATCH'].includes(req.method)) return next();

  const key = req.headers['idempotency-key'];
  if (!key) return next();

  if (idempotencyCache.has(key)) {
    const cached = idempotencyCache.get(key);
    res.set({ ...cached.headers, 'X-Idempotent-Replayed': 'true' });
    return res.status(cached.status).json(cached.body);
  }

  const originalJson = res.json.bind(res);
  res.json = (body) => {
    idempotencyCache.set(key, {
      body,
      status: res.statusCode,
      headers: res.getHeaders(),
    });
    // Auto-expire after 24h
    setTimeout(() => idempotencyCache.delete(key), 86400000);
    return originalJson(body);
  };
  next();
}

// Usage: app.use('/api/', idempotencyMiddleware);""",
            "install": "",
            "estimated_time": "20 min",
            "potential_gain": 3,
        },
        "go": {
            "title": "Idempotency-Key Support (Go)",
            "code": """package main

import (
    "bytes"
    "net/http"
    "sync"
)

type cachedResponse struct {
    StatusCode int
    Body       []byte
    Headers    http.Header
}

var (
    idemCache = map[string]*cachedResponse{}
    idemMu    sync.RWMutex
)

type responseRecorder struct {
    http.ResponseWriter
    statusCode int
    body       bytes.Buffer
}

func (rr *responseRecorder) WriteHeader(code int) {
    rr.statusCode = code
    rr.ResponseWriter.WriteHeader(code)
}
func (rr *responseRecorder) Write(b []byte) (int, error) {
    rr.body.Write(b)
    return rr.ResponseWriter.Write(b)
}

func idempotencyMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        key := r.Header.Get("Idempotency-Key")
        if key == "" || r.Method == "GET" {
            next.ServeHTTP(w, r); return
        }
        idemMu.RLock()
        if cached, ok := idemCache[key]; ok {
            idemMu.RUnlock()
            w.Header().Set("X-Idempotent-Replayed", "true")
            w.WriteHeader(cached.StatusCode)
            w.Write(cached.Body); return
        }
        idemMu.RUnlock()
        rec := &responseRecorder{ResponseWriter: w, statusCode: 200}
        next.ServeHTTP(rec, r)
        idemMu.Lock()
        idemCache[key] = &cachedResponse{rec.statusCode, rec.body.Bytes(), w.Header().Clone()}
        idemMu.Unlock()
    })
}""",
            "install": "",
            "estimated_time": "20 min",
            "potential_gain": 3,
        },
    },
}

_VALID_STACKS = {"python", "nodejs", "go"}


@app.post("/api/v1/fix", tags=["scan"])
async def generate_fix(request: Request):
    """Generate stack-specific code to fix a scan issue. No LLM calls — uses pre-written templates.

    Body: { "sub_factor": "rate_limit_info", "stack": "python", "context": { ... } }
    """
    body = await request.json()
    sub_factor = body.get("sub_factor", "").strip()
    stack = body.get("stack", "python").strip().lower()

    if not sub_factor:
        raise HTTPException(status_code=400, detail="sub_factor is required")
    if stack not in _VALID_STACKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported stack '{stack}'. Choose from: {', '.join(sorted(_VALID_STACKS))}",
        )
    if sub_factor not in FIX_TEMPLATES:
        raise HTTPException(
            status_code=404,
            detail=f"No fix template for '{sub_factor}'. Available: {', '.join(sorted(FIX_TEMPLATES.keys()))}",
        )

    tmpl = FIX_TEMPLATES[sub_factor].get(stack)
    if not tmpl:
        raise HTTPException(
            status_code=404,
            detail=f"No '{stack}' template for '{sub_factor}'",
        )

    return {
        "sub_factor": sub_factor,
        "stack": stack,
        "title": tmpl["title"],
        "code": tmpl["code"].strip(),
        "install": tmpl.get("install", ""),
        "estimated_time": tmpl.get("estimated_time", "15 min"),
        "potential_gain": tmpl.get("potential_gain", 0),
    }


# ---------------------------------------------------------------------------
# Improvement Playbook — batch fix suggestions for a scan
# ---------------------------------------------------------------------------

@app.get("/api/v1/playbook", tags=["scan"])
async def get_playbook(scan_id: str):
    """Return actionable fix suggestions for all low-scoring sub-factors in a scan.

    Aggregates FIX_TEMPLATES for every sub_factor that scored below its max.
    Sorted by potential_gain (highest impact first).
    """
    # Get scan result
    cached = get_cached_scan(scan_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Scan not found. Run a scan first.")

    # cached is a ScanResponse Pydantic model — convert to dict for uniform access
    scan_data = cached.model_dump() if hasattr(cached, "model_dump") else cached

    items = []
    dimensions = scan_data.get("dimensions", {}) if isinstance(scan_data, dict) else {}
    for dim_key, dim_data in dimensions.items():
        sub_factors = dim_data.get("sub_factors", {}) if isinstance(dim_data, dict) else {}
        for sf_key, sf_data in sub_factors.items():
            sf_dict = sf_data if isinstance(sf_data, dict) else {}
            score = sf_dict.get("score", 0)
            max_score = sf_dict.get("max", 0)
            if max_score <= 0 or score >= max_score:
                continue  # already at max

            gap = max_score - score
            if gap < 1:
                continue

            # Check if we have a fix template
            if sf_key not in FIX_TEMPLATES:
                continue

            fixes = {}
            for stack in ("python", "nodejs", "go"):
                tmpl = FIX_TEMPLATES[sf_key].get(stack)
                if tmpl:
                    fixes[stack] = {
                        "title": tmpl["title"],
                        "code": tmpl["code"].strip(),
                        "install": tmpl.get("install", ""),
                        "estimated_time": tmpl.get("estimated_time", "15 min"),
                    }

            if not fixes:
                continue

            items.append({
                "sub_factor": sf_key,
                "dimension": dim_key,
                "label": sf_dict.get("label", sf_key.replace("_", " ").title()),
                "current_score": score,
                "max_score": max_score,
                "potential_gain": gap,
                "fixes": fixes,
            })

    # Sort by potential gain (biggest improvements first)
    items.sort(key=lambda x: x["potential_gain"], reverse=True)

    service_name = scan_data.get("service_name", "") if isinstance(scan_data, dict) else getattr(cached, "service_name", "")
    clarvia_score = scan_data.get("clarvia_score", 0) if isinstance(scan_data, dict) else getattr(cached, "clarvia_score", 0)

    return {
        "scan_id": scan_id,
        "service_name": service_name,
        "items": items,
        "total_potential_gain": sum(i["potential_gain"] for i in items),
        "current_score": clarvia_score,
        "projected_score": min(100, clarvia_score + sum(i["potential_gain"] for i in items)),
    }


# ---------------------------------------------------------------------------
# Agent Traffic Monitoring
# ---------------------------------------------------------------------------

@app.post("/api/v1/traffic/register", tags=["trending"])
async def register_traffic_monitoring(request: Request):
    """Register a URL for agent traffic monitoring.

    Body: { "url": "https://api.example.com", "email": "user@example.com" }
    Returns: { tracking_id, url, email, created_at, middleware_snippets: {python, nodejs, go} }
    """
    from .services.traffic_monitor import register_url, get_middleware_snippets

    body = await request.json()
    url = (body.get("url") or "").strip()
    email = (body.get("email") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    if not email:
        raise HTTPException(status_code=400, detail="email is required")

    result = await register_url(url, email)
    tracking_id = result["tracking_id"]
    snippets = get_middleware_snippets(tracking_id)

    return {
        "tracking_id": tracking_id,
        "url": result["url"],
        "email": result["email"],
        "created_at": result["created_at"],
        "existing": result.get("existing", False),
        "middleware_snippets": snippets,
    }


@app.post("/api/v1/traffic/ingest", tags=["trending"])
async def ingest_traffic(request: Request):
    """Receive traffic events from user's installed middleware.

    Body: { "tracking_id": "trk_xxx", "user_agent": "...", "path": "/api/v1/data", "method": "GET" }
    Called by the middleware running on the user's server.
    """
    from .services.traffic_monitor import ingest_event

    body = await request.json()
    tracking_id = (body.get("tracking_id") or "").strip()
    user_agent = body.get("user_agent", "")
    path = body.get("path", "/")
    method = body.get("method", "GET")

    if not tracking_id:
        raise HTTPException(status_code=400, detail="tracking_id is required")

    recorded = await ingest_event(tracking_id, user_agent, path, method)
    if not recorded:
        return {"status": "skipped", "reason": "unknown tracking_id or non-agent user-agent"}

    return {"status": "ok"}


@app.get("/api/v1/traffic/stats", tags=["trending"])
async def get_traffic_stats(tracking_id: str, days: int = 7):
    """Get agent traffic analytics for a registered tracking ID.

    Usage: GET /api/v1/traffic/stats?tracking_id=trk_xxx&days=7
    """
    from .services.traffic_monitor import get_stats

    if not tracking_id:
        raise HTTPException(status_code=400, detail="tracking_id query parameter is required")
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="days must be between 1 and 90")

    stats = await get_stats(tracking_id, days)
    if stats is None:
        raise HTTPException(status_code=404, detail="tracking_id not found")

    return stats


# ---------------------------------------------------------------------------
# Scan history
# ---------------------------------------------------------------------------

@app.get("/api/v1/history", tags=["scan"])
async def scan_history(url: str, limit: int = 20):
    """Get scan history for a URL showing score changes over time."""
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="url query parameter is required")

    clean_url = url.strip().lower()
    if not clean_url.startswith("http"):
        clean_url = f"https://{clean_url}"
    clean_url = clean_url.rstrip("/")

    limit = max(1, min(limit, 100))

    try:
        from .services.supabase_client import get_scan_history
        scans = await get_scan_history(clean_url, limit=limit)
        return {"url": clean_url, "scans": scans, "total": len(scans)}
    except Exception:
        logger.exception("Failed to fetch scan history for %s", clean_url)
        raise HTTPException(status_code=500, detail="Failed to fetch history. Please try again later.")


# ---------------------------------------------------------------------------
# Data Moat: Trends & Tracked URLs
# ---------------------------------------------------------------------------

# In-memory tracker for auto-rescan (persisted to Supabase if available)
_tracked_urls: dict[str, dict] = {}  # url -> {service_name, category, added_at}


@app.post("/api/v1/track", tags=["scan"])
async def track_url(request: Request):
    """Register a URL for periodic tracking. Data moat: builds historical dataset."""
    body = await request.json()
    url = body.get("url", "").strip().lower()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    if not url.startswith("http"):
        url = f"https://{url}"
    url = url.rstrip("/")

    category = body.get("category", "general")
    service_name = body.get("service_name", url.split("//")[-1].split("/")[0])

    _tracked_urls[url] = {
        "service_name": service_name,
        "category": category,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }

    # Also persist to Supabase if available
    client = _supabase_client
    if client:
        try:
            client.table("tracked_urls").upsert(
                {"url": url, "service_name": service_name, "category": category},
                on_conflict="url",
            ).execute()
        except Exception:
            pass  # table may not exist yet, that's fine

    return {"tracked": True, "url": url, "total_tracked": len(_tracked_urls)}


@app.get("/api/v1/tracked", tags=["scan"])
async def list_tracked():
    """List all tracked URLs."""
    return {"urls": [{"url": k, **v} for k, v in _tracked_urls.items()], "total": len(_tracked_urls)}


@app.get("/api/v1/trends", tags=["trending"])
async def get_trends(url: str, days: int = 90):
    """Get score trend data for a URL — the core data moat feature.

    Returns time-series of scores with dimension breakdowns,
    plus delta vs first scan (shows improvement over time).
    """
    clean_url = url.strip().lower()
    if not clean_url.startswith("http"):
        clean_url = f"https://{clean_url}"
    clean_url = clean_url.rstrip("/")

    try:
        from .services.supabase_client import get_scan_history
        scans = await get_scan_history(clean_url, limit=500)
    except Exception:
        logger.exception("Failed to fetch trend data for %s", clean_url)
        raise HTTPException(status_code=500, detail="Failed to fetch trend data. Please try again later.")

    if not scans:
        return {"url": clean_url, "trend": [], "delta": None, "message": "No historical data yet"}

    # Sort chronologically (oldest first)
    scans.sort(key=lambda s: s.get("scanned_at", ""))

    first = scans[0]
    latest = scans[-1]

    delta = {
        "score": latest.get("score", 0) - first.get("score", 0),
        "period_days": 0,
        "first_scan": first.get("scanned_at"),
        "latest_scan": latest.get("scanned_at"),
        "scans_count": len(scans),
    }

    # Calculate dimension deltas if available
    if first.get("dimensions") and latest.get("dimensions"):
        delta["dimensions"] = {}
        for dim in latest["dimensions"]:
            delta["dimensions"][dim] = (
                latest["dimensions"].get(dim, 0) - first["dimensions"].get(dim, 0)
            )

    return {
        "url": clean_url,
        "service_name": latest.get("service_name", ""),
        "trend": scans,
        "delta": delta,
        "latest_score": latest.get("score", 0),
        "latest_rating": latest.get("rating", ""),
    }


@app.post("/api/v1/rescan-tracked", tags=["scan"])
async def rescan_all_tracked():
    """Trigger a rescan of all tracked URLs. Called by cron/scheduler.

    This is the engine that builds the data moat — each call adds a new
    data point to every tracked service's history.
    """
    if not _tracked_urls:
        return {"rescanned": 0, "message": "No tracked URLs"}

    from .scanner import scan_url
    results = []
    for url in list(_tracked_urls.keys()):
        try:
            result = await scan_url(url)
            dim_scores = {}
            if result.dimensions:
                for k, v in result.dimensions.items():
                    dim_scores[k] = v.score if hasattr(v, "score") else (v.get("score", 0) if isinstance(v, dict) else 0)

            from .services.supabase_client import save_scan, save_scan_history
            try:
                await save_scan(result)
            except Exception:
                pass
            await save_scan_history(
                url=result.url, scan_id=result.scan_id,
                score=result.clarvia_score, rating=result.rating,
                service_name=result.service_name, dimensions=dim_scores or None,
            )
            results.append({"url": url, "score": result.clarvia_score, "ok": True})
        except Exception as e:
            results.append({"url": url, "error": str(e)[:100], "ok": False})

    return {
        "rescanned": len(results),
        "success": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Data Moat B: Industry Benchmarks
# ---------------------------------------------------------------------------


@app.get("/api/v1/benchmark", tags=["index"])
async def get_benchmark(category: str = "all"):
    """Get industry benchmark data — network-effect moat.

    Returns average/median/percentile scores across all scanned services,
    optionally filtered by category. More users = better benchmarks.
    """
    from .services.supabase_client import get_supabase
    client = get_supabase()
    scans_data: list[dict] = []

    if client:
        try:
            query = client.table("scans").select(
                "url, service_name, clarvia_score, rating, dimensions, scanned_at"
            ).order("scanned_at", desc=True)
            result = query.limit(2000).execute()
            if result.data:
                scans_data = result.data
        except Exception as e:
            logger.error("Benchmark query failed: %s", e)

    # Also include tracked URLs' category info
    categorized: dict[str, list[dict]] = {"all": []}
    seen_urls: set[str] = set()

    for scan in scans_data:
        url = scan.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        cat = _tracked_urls.get(url, {}).get("category", "general")
        categorized.setdefault(cat, []).append(scan)
        categorized["all"].append(scan)

    target = categorized.get(category, categorized.get("all", []))
    if not target:
        return {
            "category": category,
            "total_services": 0,
            "message": "No benchmark data yet. Scan more services to unlock industry comparisons.",
        }

    scores = sorted([s["clarvia_score"] for s in target])
    n = len(scores)

    import statistics
    avg = round(statistics.mean(scores), 1)
    median = round(statistics.median(scores), 1)
    p25 = scores[max(0, n // 4 - 1)] if n >= 4 else scores[0]
    p75 = scores[max(0, (3 * n) // 4 - 1)] if n >= 4 else scores[-1]
    p90 = scores[max(0, int(n * 0.9) - 1)] if n >= 2 else scores[-1]

    # Dimension averages
    dim_avgs: dict[str, float] = {}
    dim_counts: dict[str, int] = {}
    for s in target:
        dims = s.get("dimensions")
        if not dims or not isinstance(dims, dict):
            continue
        for dk, dv in dims.items():
            sc = dv.get("score", dv) if isinstance(dv, dict) else dv
            if isinstance(sc, (int, float)):
                dim_avgs[dk] = dim_avgs.get(dk, 0) + sc
                dim_counts[dk] = dim_counts.get(dk, 0) + 1
    for dk in dim_avgs:
        dim_avgs[dk] = round(dim_avgs[dk] / dim_counts[dk], 1)

    # Rating distribution
    rating_dist: dict[str, int] = {}
    for s in target:
        r = s.get("rating", "Unknown")
        rating_dist[r] = rating_dist.get(r, 0) + 1

    # Top/bottom services
    top5 = sorted(target, key=lambda x: x.get("clarvia_score", 0), reverse=True)[:5]
    bottom5 = sorted(target, key=lambda x: x.get("clarvia_score", 0))[:5]

    return {
        "category": category,
        "total_services": n,
        "score_stats": {
            "average": avg,
            "median": median,
            "p25": p25,
            "p75": p75,
            "p90": p90,
            "min": scores[0],
            "max": scores[-1],
        },
        "dimension_averages": dim_avgs,
        "rating_distribution": rating_dist,
        "top_services": [
            {"service": s.get("service_name", ""), "score": s["clarvia_score"], "url": s.get("url", "")}
            for s in top5
        ],
        "bottom_services": [
            {"service": s.get("service_name", ""), "score": s["clarvia_score"], "url": s.get("url", "")}
            for s in bottom5
        ],
        "available_categories": list(set(categorized.keys()) - {"all"}),
    }


@app.get("/api/v1/benchmark/percentile", tags=["index"])
async def get_percentile(url: str):
    """Get a specific service's percentile rank among all scanned services."""
    clean_url = url.strip().lower()
    if not clean_url.startswith("http"):
        clean_url = f"https://{clean_url}"
    clean_url = clean_url.rstrip("/")

    from .services.supabase_client import get_supabase
    client = get_supabase()
    all_scores: list[int] = []
    target_score: int | None = None

    if client:
        try:
            result = client.table("scans").select("url, clarvia_score").execute()
            if result.data:
                seen: set[str] = set()
                for row in result.data:
                    u = row.get("url", "")
                    if u in seen:
                        continue
                    seen.add(u)
                    sc = row["clarvia_score"]
                    all_scores.append(sc)
                    if u == clean_url:
                        target_score = sc
        except Exception as e:
            logger.error("Percentile query failed: %s", e)

    if target_score is None:
        raise HTTPException(status_code=404, detail="Service not found. Scan it first.")

    if not all_scores:
        return {"url": clean_url, "score": target_score, "percentile": 50}

    below = sum(1 for s in all_scores if s < target_score)
    percentile = round((below / len(all_scores)) * 100, 1)

    return {
        "url": clean_url,
        "score": target_score,
        "percentile": percentile,
        "rank": sorted(all_scores, reverse=True).index(target_score) + 1,
        "total_services": len(all_scores),
        "message": f"Better than {percentile}% of scanned services",
    }


# ---------------------------------------------------------------------------
# Data Moat C: Agent Accessibility Probing
# ---------------------------------------------------------------------------


@app.post("/api/v1/accessibility-probe", tags=["scan"])
async def accessibility_probe(request: Request):
    """Probe a service as an AI agent would — unique proprietary data.

    Simulates real agent behavior: sends requests with agent-like headers,
    tests MCP endpoint discovery, checks robots.txt ai-agent policies,
    measures response times, and tests structured data extraction.

    This data is UNIQUE to Clarvia — no one else collects it.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    if not url.startswith("http"):
        url = f"https://{url}"

    import httpx
    import time

    results: dict[str, Any] = {
        "url": url,
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "agent_access": {},
    }

    agent_headers = {
        "User-Agent": "ClarviaAgent/1.0 (AI-Agent; +https://clarvia.com/bot)",
        "Accept": "application/json, text/html",
    }

    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=agent_headers) as client:
        # 1. Basic agent access test
        try:
            t0 = time.perf_counter()
            resp = await client.get(url)
            latency_ms = round((time.perf_counter() - t0) * 1000)
            results["agent_access"]["reachable"] = True
            results["agent_access"]["status_code"] = resp.status_code
            results["agent_access"]["latency_ms"] = latency_ms
            results["agent_access"]["content_type"] = resp.headers.get("content-type", "")
            results["agent_access"]["blocked"] = resp.status_code in (403, 429, 451)
        except Exception as e:
            results["agent_access"]["reachable"] = False
            results["agent_access"]["error"] = str(e)[:200]

        # 2. robots.txt AI agent policy
        try:
            base = url.rstrip("/")
            robots_resp = await client.get(f"{base}/robots.txt")
            robots_text = robots_resp.text[:2000] if robots_resp.status_code == 200 else ""
            ai_mentions = []
            for line in robots_text.lower().split("\n"):
                if any(kw in line for kw in ["gptbot", "chatgpt", "anthropic", "claude", "ai", "agent", "llm"]):
                    ai_mentions.append(line.strip())
            results["robots_policy"] = {
                "exists": robots_resp.status_code == 200,
                "ai_agent_mentions": ai_mentions,
                "allows_ai": not any("disallow: /" in m for m in ai_mentions) if ai_mentions else True,
            }
        except Exception:
            results["robots_policy"] = {"exists": False, "ai_agent_mentions": [], "allows_ai": True}

        # 3. MCP/agent discovery endpoints
        discovery_paths = [
            "/.well-known/mcp.json",
            "/.well-known/ai-plugin.json",
            "/.well-known/agent.json",
            "/api/mcp",
            "/mcp",
        ]
        results["discovery_endpoints"] = {}
        base = url.rstrip("/")
        for path in discovery_paths:
            try:
                dr = await client.get(f"{base}{path}")
                results["discovery_endpoints"][path] = {
                    "status": dr.status_code,
                    "found": dr.status_code == 200,
                    "content_type": dr.headers.get("content-type", ""),
                }
            except Exception:
                results["discovery_endpoints"][path] = {"status": 0, "found": False}

        # 4. JSON API test (can agent get structured data?)
        try:
            api_resp = await client.get(url, headers={"Accept": "application/json"})
            ct = api_resp.headers.get("content-type", "")
            is_json = "json" in ct
            results["structured_data"] = {
                "json_available": is_json,
                "content_type": ct,
            }
            if is_json:
                try:
                    parsed = api_resp.json()
                    results["structured_data"]["parseable"] = True
                    results["structured_data"]["top_keys"] = list(parsed.keys())[:10] if isinstance(parsed, dict) else "array"
                except Exception:
                    results["structured_data"]["parseable"] = False
        except Exception:
            results["structured_data"] = {"json_available": False}

    # 5. Calculate probe score (0-100)
    probe_score = 0
    aa = results.get("agent_access", {})
    if aa.get("reachable") and not aa.get("blocked"):
        probe_score += 30
    if aa.get("latency_ms", 9999) < 2000:
        probe_score += 10
    rp = results.get("robots_policy", {})
    if rp.get("allows_ai"):
        probe_score += 15
    if rp.get("ai_agent_mentions"):
        probe_score += 5  # Explicitly mentions AI = aware of agents
    de = results.get("discovery_endpoints", {})
    found_endpoints = sum(1 for v in de.values() if v.get("found"))
    probe_score += min(found_endpoints * 15, 30)
    sd = results.get("structured_data", {})
    if sd.get("json_available"):
        probe_score += 10

    results["probe_score"] = min(probe_score, 100)
    results["probe_rating"] = (
        "Excellent" if probe_score >= 80 else
        "Good" if probe_score >= 60 else
        "Fair" if probe_score >= 40 else
        "Poor"
    )

    # Save probe result to Supabase if available
    from .services.supabase_client import get_supabase
    sb = get_supabase()
    if sb:
        try:
            sb.table("accessibility_probes").insert({
                "url": url,
                "probe_score": results["probe_score"],
                "probe_rating": results["probe_rating"],
                "agent_reachable": aa.get("reachable", False),
                "agent_blocked": aa.get("blocked", False),
                "latency_ms": aa.get("latency_ms"),
                "allows_ai": rp.get("allows_ai", True),
                "discovery_count": found_endpoints,
                "json_available": sd.get("json_available", False),
                "full_result": results,
                "probed_at": results["probed_at"],
            }).execute()
        except Exception:
            pass  # table may not exist yet

    return results


# ---------------------------------------------------------------------------
# API Key Management
# ---------------------------------------------------------------------------


async def _optional_api_key(request: Request) -> dict | None:
    """Extract and validate an API key from X-Clarvia-Key header.

    Returns key metadata dict if valid, None if no key provided.
    Raises HTTPException(401) if key is present but invalid.
    Raises HTTPException(429) if rate limit exceeded.
    """
    key = request.headers.get("x-clarvia-key")
    if not key:
        return None

    from .services.auth_service import check_rate_limit, validate_api_key

    meta = await validate_api_key(key)
    if not meta:
        raise HTTPException(status_code=401, detail="Invalid API key")

    allowed = await check_rate_limit(meta["key_hash"], meta.get("rate_limit", 10))
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return meta


@app.post("/api/v1/keys", tags=["keys"])
async def create_key(request: Request):
    """Create a new API key.

    Body: { "email": "user@example.com", "plan": "free" }
    Returns: { "key": "clv_xxx...", "key_id": "clv_xxx", "plan": "free", "rate_limit": 10 }
    IMPORTANT: The full key is shown only once.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    email = body.get("email", "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")

    plan = body.get("plan", "free")

    from .services.auth_service import create_api_key

    result = await create_api_key(email, plan)
    return result


@app.get("/api/v1/keys/validate", tags=["keys"])
async def validate_key(request: Request):
    """Validate an API key passed in X-Clarvia-Key header.

    Returns: { "valid": true, "plan": "free", "rate_limit": 10 }
    """
    key = request.headers.get("x-clarvia-key")
    if not key:
        raise HTTPException(status_code=400, detail="X-Clarvia-Key header is required")

    from .services.auth_service import validate_api_key

    meta = await validate_api_key(key)
    if not meta:
        return {"valid": False}

    return {
        "valid": True,
        "key_id": meta.get("key_id"),
        "plan": meta.get("plan", "free"),
        "rate_limit": meta.get("rate_limit", 10),
    }


@app.get("/api/v1/keys/{key_id}/usage", tags=["keys"])
async def get_key_usage(key_id: str, request: Request):
    """Get usage statistics for an API key.

    Pass the key_id (e.g. clv_XXXXXXXX) in the URL path and the full key in
    X-Clarvia-Key header for authentication.

    Returns plan info, rate limits, and current usage within the billing window.
    """
    auth_key = request.headers.get("x-clarvia-key")
    if not auth_key:
        raise HTTPException(status_code=401, detail="X-Clarvia-Key header required")

    from .services.auth_service import validate_api_key, _hash_key, _rate_hits, PLAN_LIMITS
    import time as _t

    meta = await validate_api_key(auth_key)
    if not meta:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Verify the key_id matches the provided key
    if meta.get("key_id") != key_id:
        raise HTTPException(status_code=403, detail="Key ID does not match the provided API key")

    plan = meta.get("plan", "free")
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    # Calculate current usage from rate hits
    key_hash = _hash_key(auth_key)
    now = _t.monotonic()
    window = 3600
    hits = _rate_hits.get(key_hash, [])
    recent_hits = [t for t in hits if now - t < window]

    return {
        "key_id": key_id,
        "plan": plan,
        "rate_limit": limits["rate_limit"],
        "scans_per_month": limits["scans_per_month"],
        "current_window": {
            "requests_used": len(recent_hits),
            "requests_remaining": max(0, limits["rate_limit"] - len(recent_hits)),
            "window_seconds": window,
            "resets_in_seconds": int(window - (now - recent_hits[0]) if recent_hits else window),
        },
        "created_at": meta.get("created_at"),
        "last_used_at": meta.get("last_used_at"),
        "tiers": {
            "free": {"rate_limit": 10, "scans_per_hour": 10},
            "pro": {"rate_limit": 100, "scans_per_hour": 100},
            "enterprise": {"rate_limit": "unlimited", "scans_per_hour": "unlimited"},
        },
    }


# ---------------------------------------------------------------------------
# Batch scan endpoint
# ---------------------------------------------------------------------------

import asyncio  # noqa: E402
import time as _time  # noqa: E402
from collections import defaultdict  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

class BatchScanRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, max_length=5)

class BatchScanResultItem(BaseModel):
    url: str
    score: int | None = None
    dimensions: dict[str, Any] | None = None
    status: str  # "success" | "error"
    error: str | None = None

class BatchScanResponse(BaseModel):
    results: list[BatchScanResultItem]
    total: int
    completed: int
    failed: int

# Simple in-memory rate limiter for batch endpoint (5 req/min per IP)
_batch_rate_store: dict[str, list[float]] = defaultdict(list)
_BATCH_RATE_LIMIT = 5
_BATCH_RATE_WINDOW = 60  # seconds


def _check_batch_rate_limit(client_ip: str) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    now = _time.time()
    timestamps = _batch_rate_store[client_ip]
    # Prune old entries
    _batch_rate_store[client_ip] = [t for t in timestamps if now - t < _BATCH_RATE_WINDOW]
    if len(_batch_rate_store[client_ip]) >= _BATCH_RATE_LIMIT:
        return False
    _batch_rate_store[client_ip].append(now)
    return True


@app.post("/api/v1/batch-score", tags=["scan"], response_model=BatchScanResponse)
async def batch_score(req: BatchScanRequest, request: Request):
    """Run AEO scans on multiple URLs in parallel (max 5, 10s timeout each).

    Returns partial results — URLs that timeout get status="timeout".
    Batch scanning requires a paid plan (starter+).
    """
    # --- Tier gate: batch scan requires starter+ ---
    from .services.tier_gate import has_feature, Feature, BATCH_LIMITS

    user_plan = "free"
    clarvia_key = request.headers.get("x-clarvia-key") or request.headers.get("x-api-key")
    if clarvia_key:
        try:
            from .services.auth_service import validate_api_key
            meta = await validate_api_key(clarvia_key)
            if meta:
                user_plan = meta.get("plan", "free")
        except Exception:
            pass

    if not has_feature(user_plan, Feature.BATCH_SCAN):
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Batch scanning requires a pro or higher plan.",
                "upgrade_url": "https://clarvia.art/pricing",
                "current_plan": user_plan,
            },
        )

    batch_limit = BATCH_LIMITS.get(user_plan, 5)

    # Validate
    if not req.urls:
        raise HTTPException(status_code=400, detail="urls array must not be empty")
    if len(req.urls) > batch_limit:
        raise HTTPException(status_code=400, detail=f"Maximum {batch_limit} URLs per batch request for {user_plan} plan")

    # Rate limit check
    client_ip = request.client.host if request.client else "unknown"
    if not _check_batch_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Batch rate limit exceeded (5 requests per minute)",
        )

    _SCAN_TIMEOUT = 10  # seconds per URL

    async def _scan_one(url: str) -> BatchScanResultItem:
        try:
            result = await asyncio.wait_for(run_scan(url), timeout=_SCAN_TIMEOUT)

            # Persist to scan history
            try:
                dim_scores = {}
                if result.dimensions:
                    for k, v in result.dimensions.items():
                        dim_scores[k] = v.score if hasattr(v, "score") else (v.get("score", 0) if isinstance(v, dict) else 0)
                from .routes.scan_history_routes import persist_scan_result
                await persist_scan_result(
                    url=result.url,
                    scan_id=result.scan_id,
                    score=result.clarvia_score,
                    rating=result.rating,
                    service_name=result.service_name,
                    dimensions=dim_scores or None,
                )
            except Exception:
                pass  # Non-critical for batch scans

            return BatchScanResultItem(
                url=url,
                score=result.clarvia_score,
                dimensions={
                    k: v.model_dump() if hasattr(v, "model_dump") else v
                    for k, v in result.dimensions.items()
                },
                status="success",
            )
        except asyncio.TimeoutError:
            return BatchScanResultItem(
                url=url,
                status="error",
                error=f"Scan timed out after {_SCAN_TIMEOUT}s",
            )
        except Exception:
            return BatchScanResultItem(
                url=url,
                status="error",
                error="Scan failed due to an internal error.",
            )

    results = await asyncio.gather(*[_scan_one(url) for url in req.urls])
    results_list = list(results)
    completed = sum(1 for r in results_list if r.status == "success")
    failed = sum(1 for r in results_list if r.status == "error")

    return BatchScanResponse(
        results=results_list,
        total=len(results_list),
        completed=completed,
        failed=failed,
    )


# ---------------------------------------------------------------------------
# CI/CD Integration — gate PRs on AEO score
# ---------------------------------------------------------------------------

class CICheckRequest(BaseModel):
    url: str = Field(..., description="URL to scan")
    min_score: int = Field(default=60, ge=0, le=100, description="Minimum overall Clarvia Score to pass")
    required_dimensions: dict[str, int] | None = Field(
        default=None,
        description="Optional per-dimension minimum scores, e.g. {\"api_accessibility\": 15}",
    )

class CIDimensionCheck(BaseModel):
    score: int
    min: int
    passed: bool

class CICheckResponse(BaseModel):
    url: str
    score: int
    min_score: int
    passed: bool
    dimensions: dict[str, Any]
    dimension_checks: dict[str, CIDimensionCheck]
    badge_url: str
    details_url: str


@app.post("/api/v1/ci/check", tags=["scan"], response_model=CICheckResponse)
async def ci_check(req: CICheckRequest, request: Request):
    """CI/CD gate: scan a URL and check if it meets minimum AEO thresholds.

    Requires X-Clarvia-Key header with pro+ plan.
    Returns passed=true only when overall score >= min_score
    AND every required_dimension meets its minimum.
    """
    # --- Auth: require valid API key ---
    key = request.headers.get("x-clarvia-key")
    if not key:
        raise HTTPException(status_code=401, detail="X-Clarvia-Key header is required")

    from .services.auth_service import check_rate_limit, validate_api_key

    meta = await validate_api_key(key)
    if not meta:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # --- Tier gate: CI/CD requires pro+ ---
    from .services.tier_gate import has_feature, Feature
    user_plan = meta.get("plan", "free")
    if not has_feature(user_plan, Feature.CI_CD_CHECK):
        raise HTTPException(
            status_code=402,
            detail={
                "error": "CI/CD integration requires a pro or higher plan.",
                "upgrade_url": "https://clarvia.art/pricing",
                "current_plan": user_plan,
            },
        )

    allowed = await check_rate_limit(meta["key_hash"], meta.get("rate_limit", 10))
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # --- Run scan ---
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="url is required")

    try:
        result = await run_scan(req.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("CI check scan failed for URL: %s", req.url)
        raise HTTPException(status_code=500, detail="Scan failed due to an internal error. Please try again later.")

    # Persist to scan history
    try:
        dim_scores = {}
        if result.dimensions:
            for k, v in result.dimensions.items():
                dim_scores[k] = v.score if hasattr(v, "score") else (v.get("score", 0) if isinstance(v, dict) else 0)
        from .routes.scan_history_routes import persist_scan_result
        await persist_scan_result(
            url=result.url,
            scan_id=result.scan_id,
            score=result.clarvia_score,
            rating=result.rating,
            service_name=result.service_name,
            dimensions=dim_scores or None,
        )
    except Exception as e:
        logger.warning("Failed to save scan history from CI check: %s", e)

    # --- Evaluate thresholds ---
    overall_score = result.clarvia_score
    overall_passed = overall_score >= req.min_score

    dimensions_flat: dict[str, Any] = {}
    for k, v in result.dimensions.items():
        dimensions_flat[k] = {
            "score": v.score,
            "max": v.max,
        }

    dimension_checks: dict[str, CIDimensionCheck] = {}
    all_dims_passed = True
    if req.required_dimensions:
        for dim_name, dim_min in req.required_dimensions.items():
            dim_data = dimensions_flat.get(dim_name)
            if dim_data:
                dim_score = dim_data["score"]
                dim_passed = dim_score >= dim_min
                if not dim_passed:
                    all_dims_passed = False
                dimension_checks[dim_name] = CIDimensionCheck(
                    score=dim_score, min=dim_min, passed=dim_passed
                )
            else:
                # Unknown dimension — treat as failed
                all_dims_passed = False
                dimension_checks[dim_name] = CIDimensionCheck(
                    score=0, min=dim_min, passed=False
                )

    passed = overall_passed and all_dims_passed

    return CICheckResponse(
        url=result.url,
        score=overall_score,
        min_score=req.min_score,
        passed=passed,
        dimensions=dimensions_flat,
        dimension_checks=dimension_checks,
        badge_url=f"https://clarvia.art/api/badge/{result.scan_id}",
        details_url=f"https://clarvia.art/scan/{result.scan_id}",
    )


# ---------------------------------------------------------------------------
# PDF Export (white-label support)
# ---------------------------------------------------------------------------

@app.get("/api/v1/export/pdf", tags=["scan"])
async def export_pdf(
    request: Request,
    scan_id: str,
    brand_name: str = "Clarvia",
    brand_logo_url: str | None = None,
):
    """Export a scan result as a branded PDF report.

    Supports white-labeling: pass brand_name to replace default Clarvia branding.
    Requires starter+ plan.

    Args:
        scan_id: The scan identifier to export.
        brand_name: Brand name shown on the report (default: "Clarvia").
        brand_logo_url: Optional brand logo URL (reserved for future use).
    """
    # --- Tier gate: PDF export requires starter+ ---
    from .services.tier_gate import has_feature, Feature
    user_plan = "free"
    clarvia_key = request.headers.get("x-clarvia-key") or request.headers.get("x-api-key")
    if clarvia_key:
        try:
            from .services.auth_service import validate_api_key
            meta = await validate_api_key(clarvia_key)
            if meta:
                user_plan = meta.get("plan", "free")
        except Exception:
            pass
    if not has_feature(user_plan, Feature.PDF_EXPORT):
        raise HTTPException(
            status_code=402,
            detail={
                "error": "PDF export requires a starter or higher plan.",
                "upgrade_url": "https://clarvia.art/pricing",
                "current_plan": user_plan,
            },
        )
    import io
    from fastapi.responses import StreamingResponse

    # 1. Try to load from Supabase (paid reports)
    report_data = None
    try:
        from .services.supabase_client import get_report as db_get_report
        report = await db_get_report(scan_id)
        if report and report.get("full_report_data"):
            report_data = report["full_report_data"]
    except Exception:
        pass

    # 2. Fallback: build from cached scan
    if not report_data:
        scan = get_cached_scan(scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Scan not found or expired")

        # Build a lightweight report dict from the ScanResponse
        report_data = {
            "scan_id": scan.scan_id,
            "url": scan.url,
            "service_name": scan.service_name,
            "clarvia_score": scan.clarvia_score,
            "rating": scan.rating,
            "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else "",
            "dimensions": {
                k: {
                    "score": v.score,
                    "max": v.max,
                    "sub_factors": {
                        sk: {
                            "score": sv.score,
                            "max": sv.max,
                            "label": sv.label,
                            "evidence": sv.evidence,
                        }
                        for sk, sv in v.sub_factors.items()
                    },
                }
                for k, v in scan.dimensions.items()
            },
            "onchain_bonus": {
                "score": scan.onchain_bonus.score,
                "max": scan.onchain_bonus.max,
                "applicable": scan.onchain_bonus.applicable,
            },
            "recommendations": scan.top_recommendations[:5],
        }

    # 3. Generate PDF with white-label branding
    try:
        from .services.pdf_report import generate_pdf_report
        pdf_bytes = generate_pdf_report(report_data, brand_name=brand_name)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("PDF export failed for scan_id=%s", scan_id)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    filename = f"aeo-report-{scan_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# agents.json — opt-in agent discovery protocol
# ---------------------------------------------------------------------------

@app.get("/.well-known/agents.json", tags=["system"])
async def agents_json():
    """Serve /.well-known/agents.json — the agent discovery standard.

    Services that host this file declare themselves as agent-ready.
    Clarvia gives a score bonus to services that adopt this protocol.
    """
    return {
        "schema_version": "1.0",
        "service": {
            "name": "Clarvia AEO Scanner",
            "description": "AI Engine Optimization scoring and agent-readiness evaluation for any web service.",
            "url": "https://clarvia.art",
            "api_base": "https://clarvia-api.onrender.com",
        },
        "capabilities": {
            "scan": {
                "endpoint": "/api/scan",
                "method": "POST",
                "description": "Score any URL for agent-readiness (0-100)",
                "input": {"url": "string"},
                "output": {"clarvia_score": "number", "rating": "string", "dimensions": "object"},
            },
            "gate_check": {
                "endpoint": "/api/v1/batch-score",
                "method": "POST",
                "description": "Batch check multiple URLs with pass/fail for agent tool-use",
                "input": {"urls": "string[]"},
            },
            "probe": {
                "endpoint": "/api/v1/accessibility-probe",
                "method": "POST",
                "description": "Real-time accessibility probe (reachability, OpenAPI, MCP support)",
                "input": {"url": "string"},
            },
            "benchmark": {
                "endpoint": "/api/v1/benchmark",
                "method": "GET",
                "description": "Industry benchmark statistics",
            },
            "search": {
                "endpoint": "/v1/services",
                "method": "GET",
                "description": "Search indexed services by category and minimum score",
                "input": {"category": "string?", "min_score": "number?"},
            },
        },
        "mcp": {
            "package": "@clarvia/mcp-server",
            "tools": [
                "scan_service",
                "clarvia_gate_check",
                "clarvia_batch_check",
                "clarvia_find_alternatives",
                "clarvia_probe",
                "search_services",
            ],
        },
        "langchain": {
            "package": "clarvia-langchain",
            "install": "pip install clarvia-langchain",
        },
        "auth": {
            "type": "api_key",
            "header": "X-API-Key",
            "free_tier": True,
            "docs": "https://clarvia.art/docs",
        },
        "rate_limits": {
            "free": "15 scans/month",
            "pro": "500 scans/month",
            "business": "unlimited",
        },
    }


@app.post("/api/v1/validate-agents-json", tags=["scan"])
async def validate_agents_json(request: Request):
    """Validate a service's /.well-known/agents.json file.

    Returns whether the file exists and conforms to the schema.
    Services with valid agents.json get a score bonus.
    """
    import httpx

    body = await request.json()
    url = body.get("url", "").rstrip("/")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    agents_url = f"{url}/.well-known/agents.json"
    result = {
        "url": agents_url,
        "exists": False,
        "valid": False,
        "errors": [],
        "data": None,
    }

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(agents_url)
            if resp.status_code != 200:
                result["errors"].append(f"HTTP {resp.status_code}")
                return result

            result["exists"] = True
            data = resp.json()
            result["data"] = data

            # Basic schema validation
            errors = []
            if "schema_version" not in data:
                errors.append("Missing schema_version")
            if "service" not in data:
                errors.append("Missing service block")
            elif not isinstance(data["service"], dict):
                errors.append("service must be an object")
            else:
                for field in ("name", "url"):
                    if field not in data["service"]:
                        errors.append(f"Missing service.{field}")
            if "capabilities" not in data:
                errors.append("Missing capabilities block")

            result["errors"] = errors
            result["valid"] = len(errors) == 0

    except httpx.TimeoutException:
        result["errors"].append("Timeout fetching agents.json")
    except Exception as e:
        result["errors"].append(str(e)[:200])

    return result


# ---------------------------------------------------------------------------
# A2A Agent Card — Google Agent-to-Agent protocol discovery
# ---------------------------------------------------------------------------

@app.get("/.well-known/agent.json", tags=["system"])
async def a2a_agent_card():
    """Google A2A protocol agent card.

    Allows orchestrator agents to discover Clarvia as a specialist agent
    for tool quality assessment and AEO scoring via the Agent-to-Agent protocol.
    Spec: https://google.github.io/A2A/
    """
    return {
        "schema_version": "1.0",
        "name": "Clarvia AEO Scanner",
        "description": "AI Engine Optimization (AEO) specialist agent. Scores any web service, API, or MCP server for agent-readiness on a 0-100 scale. Use this agent when you need to evaluate tool quality, find agent-compatible APIs, or optimize a service for AI discoverability.",
        "url": "https://clarvia.art",
        "provider": {
            "name": "Clarvia",
            "url": "https://clarvia.art",
        },
        "version": "1.1.0",
        "capabilities": {
            "streaming": False,
            "push_notifications": False,
            "state_transition_history": False,
        },
        "authentication": {
            "schemes": ["api_key"],
            "credentials": {
                "type": "api_key",
                "in": "header",
                "name": "X-API-Key",
                "description": "Free tier available — no key required for basic scans",
            },
        },
        "skills": [
            {
                "id": "scan_service",
                "name": "Scan Service for AEO Score",
                "description": "Score any URL for AI/agent readiness. Returns 0-100 score with breakdown across 5 dimensions: API Accessibility, Data Structuring, Agent Compatibility, Trust Signals, Onchain/Verifiability.",
                "input_modes": ["text"],
                "output_modes": ["text", "data"],
                "examples": [
                    "Score https://api.stripe.com for agent readiness",
                    "Is OpenAI's API well-structured for autonomous agents?",
                    "What is the AEO score for github.com?",
                ],
            },
            {
                "id": "batch_check",
                "name": "Batch Quality Gate Check",
                "description": "Check multiple services at once with pass/fail gate. Use before selecting tools in an agentic workflow.",
                "input_modes": ["text", "data"],
                "output_modes": ["data"],
                "examples": [
                    "Which of these 5 APIs should my agent use?",
                    "Gate check: stripe.com, paypal.com, square.com",
                ],
            },
            {
                "id": "find_alternatives",
                "name": "Find Agent-Compatible Alternatives",
                "description": "Given a service that scored poorly, find better-scoring alternatives in the same category.",
                "input_modes": ["text"],
                "output_modes": ["text", "data"],
                "examples": [
                    "Find alternatives to Twilio that score above 70",
                    "What are the best agent-ready payment APIs?",
                ],
            },
            {
                "id": "search_indexed",
                "name": "Search 15,400+ Indexed Tools",
                "description": "Search Clarvia's index of pre-scored tools by category, score threshold, or keyword.",
                "input_modes": ["text"],
                "output_modes": ["data"],
                "examples": [
                    "Show me all MCP servers with AEO score > 80",
                    "Find database tools scored by Clarvia",
                ],
            },
        ],
        "mcp_server": {
            "package": "clarvia-mcp-server",
            "install": "npx clarvia-mcp-server",
            "npm": "https://www.npmjs.com/package/clarvia-mcp-server",
        },
        "contact": {
            "url": "https://clarvia.art",
            "documentation": "https://clarvia-api.onrender.com/docs",
            "openapi": "https://clarvia-api.onrender.com/openapi.json",
        },
    }


# ---------------------------------------------------------------------------
# Monitor lifecycle
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def _start_monitor():
    """Start the background monitoring service if enabled."""
    import os
    if os.environ.get("SCANNER_MONITOR_ENABLED", "").lower() in ("1", "true", "yes"):
        try:
            from .services.monitor import get_monitor
            interval = int(os.environ.get("SCANNER_MONITOR_INTERVAL", "86400"))
            webhook_url = os.environ.get("SCANNER_MONITOR_WEBHOOK_URL")
            monitor = get_monitor(
                interval_seconds=interval,
                webhook_url=webhook_url,
            )
            await monitor.start()
            logger.info("Background monitor started (interval=%ds)", interval)
        except Exception as e:
            logger.warning("Failed to start monitor: %s", e)


@app.on_event("shutdown")
async def _stop_monitor():
    """Stop the background monitoring service."""
    try:
        from .services.monitor import _monitor
        if _monitor:
            await _monitor.stop()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Native /api/v1/* aliases — must be registered BEFORE compat_router catch-all
# so these return 200 directly instead of 307 redirecting to /v1/*.
# ---------------------------------------------------------------------------

# Bug fix A: GET/POST /api/v1/recommend — was 307 → /v1/recommend
from .routes.recommend_routes import (
    recommend_tools as _recommend_post,
    recommend_tools_get as _recommend_get,
)

_alias_router = _APIRouter(prefix="/api/v1", tags=["alias"])
_alias_router.add_api_route(
    "/recommend",
    _recommend_get,
    methods=["GET"],
    include_in_schema=False,
)
_alias_router.add_api_route(
    "/recommend",
    _recommend_post,
    methods=["POST"],
    include_in_schema=False,
)

# Bug fix C: GET /api/v1/ci/check — POST only was causing 307→404 chain for GET requests.
# Return 405 Method Not Allowed with a clear message.
@_alias_router.get("/ci/check", include_in_schema=False)
async def _ci_check_get_alias():
    """CI check requires POST with a JSON body. GET is not supported."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=405,
        content={"error": {"type": "method_not_allowed", "code": 405, "message": "Use POST /api/v1/ci/check with a JSON body containing 'url'."}},
        headers={"Allow": "POST"},
    )

# Bug fix B: GET /api/v1/scan/{scan_id} — was 307 → /v1/scan/{scan_id} (404)
# Actual route lives at /api/scan/{scan_id}; add /api/v1/ alias here.
from .scanner import get_cached_scan as _get_cached_scan

@_alias_router.get("/scan/{scan_id}", include_in_schema=False)
async def _api_v1_get_scan(scan_id: str):
    """Alias: /api/v1/scan/{scan_id} → same logic as /api/scan/{scan_id}."""
    result = _get_cached_scan(scan_id)
    if result is None:
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

app.include_router(_alias_router)

# ---------------------------------------------------------------------------
# Register compat router LAST so native /api/v1/* routes (keys, ci/check, etc.)
# take precedence over the catch-all redirect to /v1/*.
# ---------------------------------------------------------------------------
app.include_router(_compat_router)

