"""Stripe payment routes for $29 detailed reports.

Gracefully degrades if stripe package is not installed.
"""

import io
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_stripe():
    """Import and configure stripe. Returns the stripe module or raises ImportError."""
    import stripe

    if not settings.stripe_secret_key:
        raise ValueError("SCANNER_STRIPE_SECRET_KEY not configured")
    stripe.api_key = settings.stripe_secret_key
    return stripe


@router.post("/create-checkout")
async def create_checkout_session(request: Request):
    """Create a Stripe Checkout session for a $29 detailed report.

    Body: { "scan_id": "scn_abc123", "email": "user@example.com" (optional) }
    Returns: { "checkout_url": "https://checkout.stripe.com/..." }
    """
    try:
        stripe = _get_stripe()
    except (ImportError, ValueError) as e:
        raise HTTPException(status_code=503, detail=f"Payment not configured: {e}")

    body = await request.json()
    scan_id = body.get("scan_id")
    email = body.get("email")

    if not scan_id:
        raise HTTPException(status_code=400, detail="scan_id is required")

    # Verify scan exists
    from ..scanner import get_cached_scan
    scan = get_cached_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found or expired")

    try:
        checkout_params = {
            "payment_method_types": ["card"],
            "line_items": [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Clarvia Detailed Report — {scan.service_name}",
                        "description": (
                            f"Full AEO analysis for {scan.url}: "
                            "13 sub-factor breakdown, 15 recommendations, "
                            "competitive benchmarks, PDF download"
                        ),
                    },
                    "unit_amount": 2900,  # $29.00
                },
                "quantity": 1,
            }],
            "mode": "payment",
            "success_url": f"{settings.frontend_url}/report/{scan_id}?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{settings.frontend_url}/scan/{scan_id}",
            "metadata": {
                "scan_id": scan_id,
            },
        }

        # Use price_id if configured (production Stripe product)
        if settings.stripe_price_id:
            checkout_params["line_items"] = [{
                "price": settings.stripe_price_id,
                "quantity": 1,
            }]

        if email:
            checkout_params["customer_email"] = email

        session = stripe.checkout.Session.create(**checkout_params)

        # Save report record (pending payment)
        try:
            from ..services.supabase_client import save_report
            await save_report({
                "scan_id": scan_id,
                "stripe_session_id": session.id,
                "payment_status": "pending",
                "amount_cents": 2900,
                "currency": "usd",
                "email": email,
            })
        except Exception as e:
            logger.warning("Failed to save pending report: %s", e)

        return {"checkout_url": session.url, "session_id": session.id}

    except Exception as e:
        logger.exception("Stripe checkout creation failed")
        raise HTTPException(status_code=500, detail=f"Payment error: {str(e)[:200]}")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (payment confirmation).

    Stripe sends checkout.session.completed when payment succeeds.
    """
    try:
        stripe = _get_stripe()
    except (ImportError, ValueError):
        raise HTTPException(status_code=503, detail="Stripe not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        if not settings.stripe_webhook_secret:
            raise HTTPException(
                status_code=503,
                detail="Webhook secret not configured — cannot verify signature"
            )
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {e}")

    if event.get("type") == "checkout.session.completed":
        session_data = event.get("data", {}).get("object", {})
        scan_id = session_data.get("metadata", {}).get("scan_id")
        payment_intent = session_data.get("payment_intent")
        customer_email = session_data.get("customer_email") or session_data.get("customer_details", {}).get("email")

        if scan_id:
            logger.info("Payment confirmed for scan %s", scan_id)

            # Generate full report data
            from ..scanner import get_cached_scan
            scan = get_cached_scan(scan_id)
            full_report = None
            if scan:
                full_report = _generate_full_report(scan)

            # Update report record
            try:
                from ..services.supabase_client import update_report_payment
                await update_report_payment(session_data.get("id"), {
                    "payment_status": "paid",
                    "stripe_payment_id": payment_intent,
                    "email": customer_email,
                    "full_report_data": full_report,
                    "paid_at": "now()",
                })
            except Exception as e:
                logger.error("Failed to update report after payment: %s", e)

    return JSONResponse(content={"status": "ok"})


@router.get("/{scan_id}")
async def get_report(scan_id: str):
    """Get full report data (only available after payment).

    Returns 402 if payment hasn't been completed.
    """
    # Check Supabase for paid report
    try:
        from ..services.supabase_client import get_report as db_get_report
        report = await db_get_report(scan_id)
        if report and report.get("payment_status") == "paid":
            return report
    except Exception:
        pass

    # Fallback: check if scan exists but payment not done
    from ..scanner import get_cached_scan
    scan = get_cached_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    raise HTTPException(
        status_code=402,
        detail="Payment required. Purchase the detailed report to access full analysis.",
    )


@router.get("/{scan_id}/pdf")
async def get_report_pdf(scan_id: str):
    """Download PDF version of the detailed report.

    Requires payment to have been completed.
    """
    from fastapi.responses import StreamingResponse

    # Check for paid report in Supabase
    report_data = None
    try:
        from ..services.supabase_client import get_report as db_get_report
        report = await db_get_report(scan_id)
        if report and report.get("payment_status") == "paid":
            report_data = report.get("full_report_data")
    except Exception:
        pass

    # Fallback: generate from cached scan (dev/testing)
    if not report_data:
        from ..scanner import get_cached_scan
        scan = get_cached_scan(scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="Scan not found")
        report_data = _generate_full_report(scan)

    try:
        from ..services.pdf_report import generate_pdf_report
        pdf_bytes = generate_pdf_report(report_data)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    filename = f"clarvia-report-{scan_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _load_benchmark_data() -> list[dict]:
    """Load prebuilt scan data for competitive benchmarking."""
    import json
    from pathlib import Path

    # Try multiple paths for the prebuilt scans data
    candidates = [
        Path(__file__).parent.parent.parent.parent / "frontend" / "public" / "data" / "prebuilt-scans.json",
        Path(__file__).parent.parent / "data" / "prebuilt-scans.json",
    ]
    for p in candidates:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return []


def _build_competitive_benchmark(scan, benchmark_data: list[dict]) -> dict:
    """Build competitive benchmark from prebuilt scan data."""
    if not benchmark_data:
        return {"percentile_rank": None, "industry_average": None, "services_scanned": 0}

    scores = sorted([s.get("clarvia_score", 0) for s in benchmark_data])
    n = len(scores)
    avg = sum(scores) / n if n else 0
    rank = sum(1 for s in scores if s < scan.clarvia_score)
    percentile = round((rank / n) * 100) if n else 0

    # Dimension-level benchmarks
    dim_benchmarks = {}
    for dim_key in ["api_accessibility", "data_structuring", "agent_compatibility", "trust_signals"]:
        dim_scores = [
            s.get("dimensions", {}).get(dim_key, {}).get("score", 0)
            for s in benchmark_data
            if dim_key in s.get("dimensions", {})
        ]
        if dim_scores:
            dim_benchmarks[dim_key] = {
                "average": round(sum(dim_scores) / len(dim_scores), 1),
                "max_seen": max(dim_scores),
                "min_seen": min(dim_scores),
                "your_score": getattr(scan.dimensions.get(dim_key), "score", 0) if hasattr(scan, "dimensions") else 0,
            }

    # Top 5 peers (closest scores)
    peers = sorted(benchmark_data, key=lambda s: abs(s.get("clarvia_score", 0) - scan.clarvia_score))
    top_peers = [{"name": p["service_name"], "score": p["clarvia_score"], "rating": p.get("rating", "")} for p in peers[:5]]

    return {
        "percentile_rank": percentile,
        "industry_average": round(avg, 1),
        "industry_median": scores[n // 2] if n else 0,
        "top_score": scores[-1] if n else 0,
        "services_scanned": n,
        "dimension_benchmarks": dim_benchmarks,
        "closest_peers": top_peers,
    }


def _build_implementation_roadmap(dimensions_raw: dict) -> list[dict]:
    """Generate a prioritized implementation roadmap sorted by potential point gain."""
    roadmap = []

    ROADMAP_ITEMS = {
        "api_accessibility": {
            "endpoint_existence": {
                "action": "Make your API endpoint publicly reachable with proper HTTP status codes",
                "effort": "low",
                "timeline": "1-2 days",
            },
            "response_speed": {
                "action": "Optimize API response time to under 200ms (add caching, CDN, connection pooling)",
                "effort": "medium",
                "timeline": "3-5 days",
            },
            "auth_documentation": {
                "action": "Document authentication with OpenAPI security schemes and examples",
                "effort": "low",
                "timeline": "1 day",
            },
            "rate_limit_info": {
                "action": "Add X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset headers",
                "effort": "low",
                "timeline": "1 day",
            },
        },
        "data_structuring": {
            "schema_definition": {
                "action": "Publish OpenAPI/JSON Schema definitions for all endpoints",
                "effort": "medium",
                "timeline": "3-5 days",
            },
            "pricing_transparency": {
                "action": "Add machine-readable pricing endpoint or structured pricing page",
                "effort": "low",
                "timeline": "1-2 days",
            },
            "error_structure": {
                "action": "Return structured JSON errors with error codes, messages, and docs links",
                "effort": "low",
                "timeline": "1-2 days",
            },
        },
        "agent_compatibility": {
            "mcp_support": {
                "action": "Implement MCP (Model Context Protocol) server or publish MCP tool definitions",
                "effort": "high",
                "timeline": "1-2 weeks",
            },
            "robot_policy": {
                "action": "Add agent-friendly robots.txt and .well-known/ai-plugin.json",
                "effort": "low",
                "timeline": "1 day",
            },
            "discovery_mechanism": {
                "action": "Register on API directories and add structured discovery metadata",
                "effort": "medium",
                "timeline": "2-3 days",
            },
        },
        "trust_signals": {
            "uptime_monitoring": {
                "action": "Set up public status page (e.g., Betteruptime, Instatus) with API-accessible status",
                "effort": "low",
                "timeline": "1 day",
            },
            "documentation_quality": {
                "action": "Add interactive examples, code snippets in 3+ languages, and quickstart guide",
                "effort": "medium",
                "timeline": "3-5 days",
            },
            "update_frequency": {
                "action": "Publish changelog, maintain active GitHub with recent commits",
                "effort": "low",
                "timeline": "ongoing",
            },
        },
    }

    for dim_key, dim_data in dimensions_raw.items():
        subs = dim_data.get("sub_factors", {})
        items = ROADMAP_ITEMS.get(dim_key, {})
        for sf_key, sf_data in subs.items():
            gap = sf_data.get("max", 0) - sf_data.get("score", 0)
            if gap > 0 and sf_key in items:
                item = items[sf_key]
                roadmap.append({
                    "dimension": dim_key,
                    "sub_factor": sf_key,
                    "label": sf_data.get("label", sf_key),
                    "current_score": sf_data.get("score", 0),
                    "max_score": sf_data.get("max", 0),
                    "potential_gain": gap,
                    "action": item["action"],
                    "effort": item["effort"],
                    "timeline": item["timeline"],
                })

    roadmap.sort(key=lambda x: (-x["potential_gain"], {"low": 0, "medium": 1, "high": 2}.get(x["effort"], 3)))
    return roadmap


def _build_code_examples(dimensions_raw: dict) -> list[dict]:
    """Generate code examples for the top 3 most impactful improvements."""
    examples = []

    subs = {}
    for dim_data in dimensions_raw.values():
        for sf_key, sf_data in dim_data.get("sub_factors", {}).items():
            gap = sf_data.get("max", 0) - sf_data.get("score", 0)
            if gap > 0:
                subs[sf_key] = gap

    CODE_SNIPPETS = {
        "rate_limit_info": {
            "title": "Add Rate Limit Headers (Express.js)",
            "language": "javascript",
            "code": """// middleware/rateLimit.js
const rateLimit = require('express-rate-limit');

const limiter = rateLimit({
  windowMs: 60 * 1000,  // 1 minute
  max: 100,
  standardHeaders: true,  // X-RateLimit-* headers
  legacyHeaders: false,
  handler: (req, res) => {
    res.status(429).json({
      error: { code: 'rate_limited', message: 'Too many requests', retry_after: 60 }
    });
  }
});

app.use('/api/', limiter);""",
        },
        "error_structure": {
            "title": "Structured Error Responses (Python/FastAPI)",
            "language": "python",
            "code": """from fastapi import HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def structured_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"err_{exc.status_code}",
                "message": exc.detail,
                "docs_url": f"https://docs.yourapi.com/errors/{exc.status_code}",
                "request_id": request.state.request_id
            }
        }
    )""",
        },
        "schema_definition": {
            "title": "OpenAPI Schema Definition (FastAPI)",
            "language": "python",
            "code": """from pydantic import BaseModel, Field

class UserResponse(BaseModel):
    id: str = Field(..., description="Unique user identifier")
    name: str = Field(..., description="Display name")
    email: str = Field(..., description="Primary email address")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")

    model_config = {"json_schema_extra": {"example": {
        "id": "usr_123", "name": "Alice", "email": "alice@example.com",
        "created_at": "2025-01-01T00:00:00Z"
    }}}

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    ...""",
        },
        "robot_policy": {
            "title": "Agent-Friendly Discovery (robots.txt + ai-plugin.json)",
            "language": "json",
            "code": """// .well-known/ai-plugin.json
{
  "schema_version": "v1",
  "name_for_human": "Your API",
  "name_for_model": "your_api",
  "description_for_human": "Access your service via API",
  "description_for_model": "Programmatic access to [service]",
  "auth": { "type": "service_http", "authorization_type": "bearer" },
  "api": { "type": "openapi", "url": "https://api.yourservice.com/openapi.json" }
}""",
        },
        "mcp_support": {
            "title": "MCP Server Implementation (TypeScript)",
            "language": "typescript",
            "code": """import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const server = new McpServer({ name: "your-service", version: "1.0.0" });

server.tool("get_data", { id: z.string().describe("Resource ID") },
  async ({ id }) => {
    const data = await yourApi.getData(id);
    return { content: [{ type: "text", text: JSON.stringify(data) }] };
  }
);

// Start with: npx @anthropic-ai/mcp-inspector""",
        },
        "response_speed": {
            "title": "Response Caching (Express.js + Redis)",
            "language": "javascript",
            "code": """const Redis = require('ioredis');
const redis = new Redis(process.env.REDIS_URL);

async function cacheMiddleware(req, res, next) {
  const key = `cache:${req.originalUrl}`;
  const cached = await redis.get(key);
  if (cached) {
    res.set('X-Cache', 'HIT');
    res.set('Cache-Control', 'public, max-age=60');
    return res.json(JSON.parse(cached));
  }
  res.originalJson = res.json;
  res.json = (body) => {
    redis.setex(key, 60, JSON.stringify(body));
    res.set('X-Cache', 'MISS');
    return res.originalJson(body);
  };
  next();
}""",
        },
        "uptime_monitoring": {
            "title": "Health Check Endpoint",
            "language": "python",
            "code": """@app.get("/health")
async def health_check():
    checks = {}
    checks["database"] = await check_db_connection()
    checks["cache"] = await check_redis_connection()
    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
        "version": os.getenv("APP_VERSION", "unknown"),
        "uptime_seconds": time.time() - APP_START_TIME
    }""",
        },
    }

    ranked = sorted(subs.items(), key=lambda x: -x[1])
    for sf_key, gap in ranked[:3]:
        if sf_key in CODE_SNIPPETS:
            snippet = CODE_SNIPPETS[sf_key]
            examples.append({
                "sub_factor": sf_key,
                "potential_gain": gap,
                **snippet,
            })

    # Fill remaining slots if needed
    if len(examples) < 3:
        for sf_key, gap in ranked:
            if sf_key in CODE_SNIPPETS and not any(e["sub_factor"] == sf_key for e in examples):
                snippet = CODE_SNIPPETS[sf_key]
                examples.append({"sub_factor": sf_key, "potential_gain": gap, **snippet})
                if len(examples) >= 3:
                    break

    return examples


def _generate_full_report(scan) -> dict:
    """Generate the full paid report from a scan result.

    Includes: all 13 sub-factors detailed, 15 recommendations,
    competitive benchmarks, implementation roadmap, code examples,
    radar chart data, and full evidence.
    """
    from ..scanner import _generate_recommendations

    # Extract all dimensions with full evidence
    dimensions_raw = {}
    for dim_key, dim_result in scan.dimensions.items():
        dimensions_raw[dim_key] = {
            "score": dim_result.score,
            "max": dim_result.max,
            "sub_factors": {
                k: {
                    "score": v.score,
                    "max": v.max,
                    "label": v.label,
                    "evidence": v.evidence,
                }
                for k, v in dim_result.sub_factors.items()
            },
        }

    onchain_raw = {
        "score": scan.onchain_bonus.score,
        "max": scan.onchain_bonus.max,
        "applicable": scan.onchain_bonus.applicable,
        "sub_factors": {
            k: {
                "score": v.score,
                "max": v.max,
                "label": v.label,
                "evidence": v.evidence,
            }
            for k, v in scan.onchain_bonus.sub_factors.items()
        },
    }

    # Generate extended recommendations (up to 15) — all evidence-based
    extended_recs = _generate_recommendations(
        dimensions_raw, onchain_raw, max_recs=15,
    )

    # If still under 15, add dimension-level strategic recs
    if len(extended_recs) < 15:
        dim_scores = []
        dim_labels = {
            "api_accessibility": "API Accessibility",
            "data_structuring": "Data Structuring",
            "agent_compatibility": "Agent Compatibility",
            "trust_signals": "Trust Signals",
        }
        for key, label in dim_labels.items():
            dim = dimensions_raw.get(key, {})
            score = dim.get("score", 0)
            max_score = dim.get("max", 25)
            pct = round((score / max(max_score, 1)) * 100)
            dim_scores.append((pct, score, max_score, label, key))
        dim_scores.sort(key=lambda x: x[0])

        for pct, score, max_score, label, key in dim_scores:
            if len(extended_recs) >= 15:
                break
            if pct < 80:
                extended_recs.append(
                    f"Your weakest dimension is {label} at {score}/{max_score} "
                    f"({pct}%). Focus here for maximum score impact."
                )
                break  # Only add the single weakest dimension note

    extended_recs = extended_recs[:15]

    # Competitive benchmark
    benchmark_data = _load_benchmark_data()
    competitive_benchmark = _build_competitive_benchmark(scan, benchmark_data)

    # Implementation roadmap
    roadmap = _build_implementation_roadmap(dimensions_raw)

    # Code examples for top 3
    code_examples = _build_code_examples(dimensions_raw)

    # Radar chart data (normalized 0-100 per dimension)
    radar_chart = {
        "labels": ["API Accessibility", "Data Structuring", "Agent Compatibility", "Trust Signals"],
        "your_scores": [
            round((dimensions_raw.get(k, {}).get("score", 0) / max(dimensions_raw.get(k, {}).get("max", 1), 1)) * 100)
            for k in ["api_accessibility", "data_structuring", "agent_compatibility", "trust_signals"]
        ],
        "industry_average": [
            round((competitive_benchmark.get("dimension_benchmarks", {}).get(k, {}).get("average", 0) / max(dimensions_raw.get(k, {}).get("max", 1), 1)) * 100)
            for k in ["api_accessibility", "data_structuring", "agent_compatibility", "trust_signals"]
        ],
    }

    return {
        "scan_id": scan.scan_id,
        "url": scan.url,
        "service_name": scan.service_name,
        "clarvia_score": scan.clarvia_score,
        "rating": scan.rating,
        "dimensions": dimensions_raw,
        "onchain_bonus": onchain_raw,
        "recommendations": extended_recs,
        "competitive_benchmark": competitive_benchmark,
        "implementation_roadmap": roadmap,
        "code_examples": code_examples,
        "radar_chart": radar_chart,
        "scan_duration_ms": scan.scan_duration_ms,
        "scanned_at": scan.scanned_at.isoformat(),
    }
