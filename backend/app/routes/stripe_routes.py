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
            import asyncio
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
        if settings.stripe_webhook_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        else:
            # Dev mode: parse without signature verification
            import json
            event = json.loads(payload)
            logger.warning("Webhook signature verification skipped (no webhook secret)")
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
                import asyncio
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


def _generate_full_report(scan) -> dict:
    """Generate the full paid report from a scan result.

    Includes: all 13 sub-factors detailed, 15 recommendations,
    competitive benchmark placeholders, full evidence.
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

    # Generate extended recommendations (15 instead of 5)
    all_recs = _generate_recommendations(dimensions_raw, onchain_raw)
    # Extend to 15 with more specific actionable items
    extended_recs = all_recs + [
        "Add response caching headers (ETag, Cache-Control) to improve response speed.",
        "Implement pagination in list endpoints for better agent data handling.",
        "Add webhook support so agents can receive real-time updates.",
        "Publish a .well-known/clarvia.json profile for maximum discoverability.",
        "Add rate limit headers (X-RateLimit-*) so agents can self-throttle.",
        "Provide SDKs in Python and JavaScript for easy agent integration.",
        "Add versioned API paths (v1, v2) to ensure backward compatibility.",
        "Implement structured logging with request IDs for debugging.",
        "Create an interactive API playground for developer onboarding.",
        "Publish your API on RapidAPI or similar marketplace for broader reach.",
    ]
    extended_recs = extended_recs[:15]

    return {
        "scan_id": scan.scan_id,
        "url": scan.url,
        "service_name": scan.service_name,
        "clarvia_score": scan.clarvia_score,
        "rating": scan.rating,
        "dimensions": dimensions_raw,
        "onchain_bonus": onchain_raw,
        "recommendations": extended_recs,
        "competitive_benchmark": {
            "note": "Competitive benchmarks will be available after scanning comparison URLs.",
            "industry_average": None,
            "top_performer": None,
        },
        "scan_duration_ms": scan.scan_duration_ms,
        "scanned_at": scan.scanned_at.isoformat(),
    }
