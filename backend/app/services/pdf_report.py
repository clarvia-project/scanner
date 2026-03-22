"""PDF report generation for Clarvia AEO Scanner.

Uses reportlab to generate branded PDF reports with:
- Score gauge visualization
- Dimension breakdown charts
- Sub-factor details
- Recommendations
- Clarvia branding
"""

import io
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Color constants
COLOR_BG = (10 / 255, 14 / 255, 20 / 255)
COLOR_WHITE = (224 / 255, 230 / 255, 237 / 255)
COLOR_MUTED = (107 / 255, 114 / 255, 128 / 255)
COLOR_CARD = (17 / 255, 24 / 255, 33 / 255)
COLOR_ACCENT = (59 / 255, 130 / 255, 246 / 255)
COLOR_GREEN = (34 / 255, 197 / 255, 94 / 255)
COLOR_YELLOW = (234 / 255, 179 / 255, 8 / 255)
COLOR_RED = (239 / 255, 68 / 255, 68 / 255)

DIMENSION_LABELS = {
    "api_accessibility": "API Accessibility",
    "data_structuring": "Data Structuring",
    "agent_compatibility": "Agent Compatibility",
    "trust_signals": "Trust Signals",
}


def _score_color(score: int, max_score: int = 100):
    pct = score / max(max_score, 1)
    if pct >= 0.7:
        return COLOR_GREEN
    elif pct >= 0.4:
        return COLOR_YELLOW
    return COLOR_RED


def _score_color_rl(score: int, max_score: int = 100):
    """Return reportlab Color for a given score."""
    from reportlab.lib.colors import Color
    r, g, b = _score_color(score, max_score)
    return Color(r, g, b)


def generate_pdf_report(report_data: dict) -> bytes:
    """Generate a PDF report from full report data. Returns PDF bytes."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch, mm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.graphics.shapes import Drawing, Circle, String, Rect
        from reportlab.graphics import renderPDF
    except ImportError:
        logger.error("reportlab not installed — cannot generate PDF")
        raise RuntimeError("PDF generation requires reportlab: pip install reportlab")

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CTitle",
        parent=styles["Title"],
        fontSize=24,
        textColor=colors.Color(*COLOR_WHITE),
        spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "CHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.Color(*COLOR_WHITE),
        spaceBefore=16,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "CBody",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.Color(*COLOR_MUTED),
        leading=14,
    )
    score_style = ParagraphStyle(
        "CScore",
        parent=styles["Normal"],
        fontSize=48,
        alignment=TA_CENTER,
        textColor=colors.Color(*COLOR_WHITE),
        spaceAfter=4,
    )
    sub_heading_style = ParagraphStyle(
        "CSubHead",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.Color(*COLOR_WHITE),
        spaceBefore=8,
        spaceAfter=4,
    )
    evidence_style = ParagraphStyle(
        "CEvidence",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.Color(*COLOR_MUTED),
        leftIndent=12,
        leading=12,
    )
    rec_style = ParagraphStyle(
        "CRec",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.Color(*COLOR_WHITE),
        leftIndent=16,
        leading=14,
        spaceBefore=4,
        spaceAfter=4,
    )

    elements = []

    # --- Header ---
    elements.append(Paragraph("CLARVIA", ParagraphStyle(
        "CLogo", parent=styles["Normal"], fontSize=10,
        textColor=colors.Color(*COLOR_MUTED),
        spaceAfter=4,
    )))
    elements.append(Paragraph("AEO Scanner Report", title_style))
    elements.append(Paragraph(
        f'{report_data.get("service_name", "Unknown")} — {report_data.get("url", "")}',
        body_style,
    ))
    elements.append(Spacer(1, 8))

    scanned_at = report_data.get("scanned_at", "")
    if isinstance(scanned_at, str) and scanned_at:
        try:
            dt = datetime.fromisoformat(scanned_at.replace("Z", "+00:00"))
            scanned_at = dt.strftime("%B %d, %Y at %H:%M UTC")
        except Exception:
            pass
    elements.append(Paragraph(f"Scanned: {scanned_at}", evidence_style))
    elements.append(Spacer(1, 16))

    # --- Overall Score ---
    score = report_data.get("clarvia_score", 0)
    rating = report_data.get("rating", "Unknown")
    score_color = _score_color_rl(score)

    elements.append(Paragraph(
        f'<font color="{score_color.hexval()}">{score}</font> / 100',
        score_style,
    ))
    elements.append(Paragraph(
        f'Rating: <font color="{score_color.hexval()}">{rating}</font>',
        ParagraphStyle("CRating", parent=body_style, alignment=TA_CENTER, fontSize=12),
    ))
    elements.append(Spacer(1, 20))

    # --- Dimension Breakdown ---
    elements.append(Paragraph("Dimension Breakdown", heading_style))

    dimensions = report_data.get("dimensions", {})
    for dim_key, dim_data in dimensions.items():
        label = DIMENSION_LABELS.get(dim_key, dim_key.replace("_", " ").title())
        dim_score = dim_data.get("score", 0)
        dim_max = dim_data.get("max", 25)
        dim_color = _score_color_rl(dim_score, dim_max)

        elements.append(Paragraph(
            f'{label}: <font color="{dim_color.hexval()}">{dim_score}/{dim_max}</font>',
            sub_heading_style,
        ))

        # Sub-factors
        sub_factors = dim_data.get("sub_factors", {})
        for sf_key, sf_data in sub_factors.items():
            sf_label = sf_data.get("label", sf_key.replace("_", " ").title())
            sf_score = sf_data.get("score", 0)
            sf_max = sf_data.get("max", 0)
            sf_color = _score_color_rl(sf_score, sf_max)

            elements.append(Paragraph(
                f'  {sf_label}: <font color="{sf_color.hexval()}">{sf_score}/{sf_max}</font>',
                evidence_style,
            ))

            # Evidence
            evidence = sf_data.get("evidence", {})
            reason = evidence.get("reason", "")
            if reason:
                elements.append(Paragraph(f"    {reason}", evidence_style))

        elements.append(Spacer(1, 8))

    # --- Onchain Bonus ---
    onchain = report_data.get("onchain_bonus", {})
    if onchain.get("applicable"):
        elements.append(Paragraph("Onchain Bonus", heading_style))
        oc_score = onchain.get("score", 0)
        oc_max = onchain.get("max", 25)
        elements.append(Paragraph(f"Score: {oc_score}/{oc_max}", sub_heading_style))
    else:
        elements.append(Paragraph("Onchain Bonus", heading_style))
        elements.append(Paragraph("Not applicable for this service.", evidence_style))

    elements.append(Spacer(1, 16))

    # --- Recommendations ---
    recommendations = report_data.get("recommendations", [])
    if recommendations:
        elements.append(Paragraph("Recommendations", heading_style))
        for i, rec in enumerate(recommendations, 1):
            priority = "HIGH" if i <= 3 else ("MEDIUM" if i <= 8 else "LOW")
            priority_color = (
                _score_color_rl(0, 100) if i <= 3
                else _score_color_rl(50, 100) if i <= 8
                else colors.Color(*COLOR_MUTED)
            )
            elements.append(Paragraph(
                f'<font color="{priority_color.hexval()}">[{priority}]</font> {rec}',
                rec_style,
            ))

    elements.append(Spacer(1, 24))

    # --- Footer ---
    elements.append(Paragraph(
        "Generated by Clarvia AEO Scanner | clarvia.io",
        ParagraphStyle("CFooter", parent=body_style, alignment=TA_CENTER, fontSize=8),
    ))

    # Build PDF
    def _on_page(canvas, doc):
        canvas.setFillColorRGB(*COLOR_BG)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)

    doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()
