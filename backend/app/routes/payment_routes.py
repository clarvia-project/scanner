"""Lemon Squeezy payment routes for detailed reports.

Replaces Stripe — no server SDK needed.
Lemon Squeezy acts as Merchant of Record (handles taxes, payouts).

Flow:
1. Frontend calls /create-checkout with scan_id
2. Backend builds Lemon Squeezy checkout URL with custom data
3. User pays on Lemon Squeezy hosted page
4. Webhook confirms payment → unlock report
"""

import hashlib
import hmac
import io
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/create-checkout")
async def create_checkout(request: Request):
    """Create a Lemon Squeezy checkout URL for a detailed report.

    Body: { "scan_id": "scn_abc123", "email": "user@example.com" (optional) }
    Returns: { "checkout_url": "https://clarvia.lemonsqueezy.com/checkout/..." }
    """
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

    # Build Lemon Squeezy checkout URL
    # Format: https://{store}.lemonsqueezy.com/checkout/buy/{variant_id}
    store_id = settings.lemonsqueezy_store_id
    variant_id = settings.lemonsqueezy_variant_id

    if not store_id or not variant_id:
        raise HTTPException(
            status_code=503,
            detail="Payment not configured. Set SCANNER_LEMONSQUEEZY_STORE_ID and SCANNER_LEMONSQUEEZY_VARIANT_ID.",
        )

    # Lemon Squeezy checkout URL with custom data
    checkout_url = (
        f"https://{store_id}.lemonsqueezy.com/checkout/buy/{variant_id}"
        f"?checkout[custom][scan_id]={scan_id}"
        f"&checkout[custom][service_name]={scan.service_name}"
    )
    if email:
        checkout_url += f"&checkout[email]={email}"

    # Add success/cancel URLs
    checkout_url += f"&checkout[custom][success_url]={settings.frontend_url}/report/{scan_id}"

    # Save pending report
    try:
        from ..services.supabase_client import save_report
        await save_report({
            "scan_id": scan_id,
            "payment_status": "pending",
            "amount_cents": 2900,
            "currency": "usd",
            "email": email,
        })
    except Exception as e:
        logger.warning("Failed to save pending report: %s", e)

    return {"checkout_url": checkout_url}


@router.post("/webhook")
async def lemonsqueezy_webhook(request: Request):
    """Handle Lemon Squeezy webhook events.

    Lemon Squeezy sends order_created when payment succeeds.
    Signature verified with HMAC-SHA256.
    """
    payload = await request.body()
    signature = request.headers.get("x-signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing x-signature header")

    # Verify webhook signature
    webhook_secret = settings.lemonsqueezy_webhook_secret
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    expected = hmac.new(
        webhook_secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_name = event.get("meta", {}).get("event_name")

    if event_name == "order_created":
        data = event.get("data", {})
        attrs = data.get("attributes", {})
        custom_data = event.get("meta", {}).get("custom_data", {})
        scan_id = custom_data.get("scan_id")

        if scan_id:
            logger.info("Lemon Squeezy payment confirmed for scan %s", scan_id)

            customer_email = attrs.get("user_email", "")
            order_id = str(data.get("id", ""))

            # Generate full report
            from ..scanner import get_cached_scan
            scan = get_cached_scan(scan_id)
            full_report = None
            if scan:
                full_report = _generate_full_report(scan)

            # Update report record
            try:
                from ..services.supabase_client import get_supabase
                client = get_supabase()
                if client:
                    client.table("reports").update({
                        "payment_status": "paid",
                        "stripe_payment_id": f"ls_{order_id}",  # reuse field
                        "email": customer_email,
                        "full_report_data": full_report,
                        "paid_at": "now()",
                    }).eq("scan_id", scan_id).execute()
            except Exception as e:
                logger.error("Failed to update report after payment: %s", e)

    return JSONResponse(content={"status": "ok"})


@router.get("/{scan_id}")
async def get_report(scan_id: str):
    """Get full report data (only available after payment)."""
    try:
        from ..services.supabase_client import get_report as db_get_report
        report = await db_get_report(scan_id)
        if report and report.get("payment_status") == "paid":
            return report
    except Exception:
        pass

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
    """Download PDF version of the detailed report."""
    from fastapi.responses import StreamingResponse

    report_data = None
    try:
        from ..services.supabase_client import get_report as db_get_report
        report = await db_get_report(scan_id)
        if report and report.get("payment_status") == "paid":
            report_data = report.get("full_report_data")
    except Exception:
        pass

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


# ---------------------------------------------------------------------------
# Report generation helpers (kept from stripe_routes.py)
# ---------------------------------------------------------------------------

def _load_benchmark_data() -> list[dict]:
    import json
    from pathlib import Path
    candidates = [
        Path(__file__).parent.parent.parent.parent / "frontend" / "public" / "data" / "prebuilt-scans.json",
        Path(__file__).parent.parent / "data" / "prebuilt-scans.json",
    ]
    for p in candidates:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return []


def _generate_full_report(scan) -> dict:
    """Generate comprehensive report data from a scan result."""
    dims = {}
    if hasattr(scan, "dimensions"):
        for k, v in scan.dimensions.items():
            if hasattr(v, "score"):
                dims[k] = {"score": v.score, "max": v.max, "sub_factors": {
                    sk: {"score": sv.score, "max": sv.max, "label": sv.label, "evidence": sv.evidence}
                    for sk, sv in v.sub_factors.items()
                }}
            elif isinstance(v, dict):
                dims[k] = v

    benchmark_data = _load_benchmark_data()

    return {
        "scan_id": scan.scan_id,
        "url": scan.url,
        "service_name": scan.service_name,
        "clarvia_score": scan.clarvia_score,
        "rating": scan.rating,
        "dimensions": dims,
        "recommendations": scan.top_recommendations if hasattr(scan, "top_recommendations") else [],
        "scanned_at": scan.scanned_at.isoformat() if hasattr(scan.scanned_at, "isoformat") else str(scan.scanned_at),
        "benchmark": _build_competitive_benchmark(scan, benchmark_data) if benchmark_data else None,
    }


def _build_competitive_benchmark(scan, benchmark_data: list[dict]) -> dict:
    if not benchmark_data:
        return {"percentile_rank": None, "industry_average": None, "services_scanned": 0}
    scores = sorted([s.get("clarvia_score", 0) for s in benchmark_data])
    n = len(scores)
    avg = sum(scores) / n if n else 0
    rank = sum(1 for s in scores if s < scan.clarvia_score)
    percentile = round((rank / n) * 100) if n else 0
    return {
        "percentile_rank": percentile,
        "industry_average": round(avg, 1),
        "industry_median": scores[n // 2] if n else 0,
        "services_scanned": n,
    }
