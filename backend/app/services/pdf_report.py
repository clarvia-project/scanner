"""PDF report generation for Clarvia AEO Scanner.

Uses reportlab to generate branded PDF reports with:
- Score gauge visualization
- Radar chart (your score vs industry avg)
- Dimension benchmark bars
- Implementation roadmap table
- Code examples
- Recommendations
- Clarvia branding
"""

import io
import logging
import math
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


def _draw_gauge(canvas_obj, x, y, score, size=120):
    """Draw a score gauge arc on the canvas."""
    from reportlab.lib.colors import Color

    center_x = x + size / 2
    center_y = y + size / 2
    radius = size * 0.42

    # Background arc
    canvas_obj.setStrokeColorRGB(30 / 255, 42 / 255, 58 / 255)
    canvas_obj.setLineWidth(8)
    canvas_obj.arc(
        center_x - radius, center_y - radius,
        center_x + radius, center_y + radius,
        startAng=135, extent=270,
    )

    # Score arc
    r, g, b = _score_color(score)
    canvas_obj.setStrokeColorRGB(r, g, b)
    canvas_obj.setLineWidth(8)
    extent = (score / 100) * 270
    canvas_obj.arc(
        center_x - radius, center_y - radius,
        center_x + radius, center_y + radius,
        startAng=135, extent=extent,
    )

    # Score text
    canvas_obj.setFillColorRGB(r, g, b)
    canvas_obj.setFont("Helvetica-Bold", 36)
    canvas_obj.drawCentredString(center_x, center_y - 8, str(score))
    canvas_obj.setFillColorRGB(*COLOR_MUTED)
    canvas_obj.setFont("Helvetica", 10)
    canvas_obj.drawCentredString(center_x, center_y - 24, "/ 100")


def _draw_radar_chart(canvas_obj, x, y, radar_data, size=200):
    """Draw a radar chart comparing your scores vs industry average."""
    from reportlab.lib.colors import Color

    labels = radar_data.get("labels", [])
    your_scores = radar_data.get("your_scores", [])
    industry_avg = radar_data.get("industry_average", [])
    n = len(labels)
    if n < 3:
        return

    cx = x + size / 2
    cy = y + size / 2
    max_r = size * 0.38

    # Draw grid rings
    canvas_obj.setStrokeColorRGB(30 / 255, 42 / 255, 58 / 255)
    canvas_obj.setLineWidth(0.5)
    for ring in [0.25, 0.5, 0.75, 1.0]:
        r = max_r * ring
        points = []
        for i in range(n):
            angle = math.radians(90 - (360 / n) * i)
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            points.append((px, py))
        path = canvas_obj.beginPath()
        path.moveTo(*points[0])
        for pt in points[1:]:
            path.lineTo(*pt)
        path.close()
        canvas_obj.drawPath(path, fill=0, stroke=1)

    # Draw axis lines
    for i in range(n):
        angle = math.radians(90 - (360 / n) * i)
        ex = cx + max_r * math.cos(angle)
        ey = cy + max_r * math.sin(angle)
        canvas_obj.line(cx, cy, ex, ey)

    # Draw industry average polygon
    canvas_obj.setStrokeColorRGB(*COLOR_MUTED)
    canvas_obj.setFillColorRGB(COLOR_MUTED[0], COLOR_MUTED[1], COLOR_MUTED[2])
    canvas_obj.setLineWidth(1)
    if industry_avg:
        pts = []
        for i in range(n):
            angle = math.radians(90 - (360 / n) * i)
            val = min(industry_avg[i] if i < len(industry_avg) else 0, 100) / 100
            px = cx + max_r * val * math.cos(angle)
            py = cy + max_r * val * math.sin(angle)
            pts.append((px, py))
        path = canvas_obj.beginPath()
        path.moveTo(*pts[0])
        for pt in pts[1:]:
            path.lineTo(*pt)
        path.close()
        canvas_obj.saveState()
        canvas_obj.setFillAlpha(0.15)
        canvas_obj.drawPath(path, fill=1, stroke=1)
        canvas_obj.restoreState()

    # Draw your score polygon
    canvas_obj.setStrokeColorRGB(*COLOR_ACCENT)
    canvas_obj.setLineWidth(2)
    pts = []
    for i in range(n):
        angle = math.radians(90 - (360 / n) * i)
        val = min(your_scores[i] if i < len(your_scores) else 0, 100) / 100
        px = cx + max_r * val * math.cos(angle)
        py = cy + max_r * val * math.sin(angle)
        pts.append((px, py))
    path = canvas_obj.beginPath()
    path.moveTo(*pts[0])
    for pt in pts[1:]:
        path.lineTo(*pt)
    path.close()
    canvas_obj.saveState()
    canvas_obj.setFillColorRGB(*COLOR_ACCENT)
    canvas_obj.setFillAlpha(0.2)
    canvas_obj.drawPath(path, fill=1, stroke=1)
    canvas_obj.restoreState()

    # Draw dots on your score
    for pt in pts:
        canvas_obj.setFillColorRGB(*COLOR_ACCENT)
        canvas_obj.circle(pt[0], pt[1], 3, fill=1, stroke=0)

    # Labels
    canvas_obj.setFillColorRGB(*COLOR_WHITE)
    canvas_obj.setFont("Helvetica", 8)
    for i in range(n):
        angle = math.radians(90 - (360 / n) * i)
        lx = cx + (max_r + 18) * math.cos(angle)
        ly = cy + (max_r + 18) * math.sin(angle)
        label = labels[i] if i < len(labels) else ""
        canvas_obj.drawCentredString(lx, ly - 3, label)


def _draw_benchmark_bar(canvas_obj, x, y, label, score, max_score, avg_score, width=350):
    """Draw a single benchmark comparison bar."""
    bar_h = 10
    bar_y = y

    # Label
    canvas_obj.setFillColorRGB(*COLOR_WHITE)
    canvas_obj.setFont("Helvetica", 9)
    canvas_obj.drawString(x, y + 14, label)

    # Score text
    r, g, b = _score_color(score, max_score)
    canvas_obj.setFillColorRGB(r, g, b)
    canvas_obj.setFont("Helvetica-Bold", 9)
    canvas_obj.drawRightString(x + width, y + 14, f"{score}/{max_score}")

    # Background bar
    canvas_obj.setFillColorRGB(30 / 255, 42 / 255, 58 / 255)
    canvas_obj.roundRect(x, bar_y, width, bar_h, 3, fill=1, stroke=0)

    # Score bar
    pct = min(score / max(max_score, 1), 1.0)
    canvas_obj.setFillColorRGB(r, g, b)
    canvas_obj.roundRect(x, bar_y, width * pct, bar_h, 3, fill=1, stroke=0)

    # Industry avg marker
    if avg_score is not None and max_score > 0:
        avg_pct = min(avg_score / max_score, 1.0)
        marker_x = x + width * avg_pct
        canvas_obj.setStrokeColorRGB(*COLOR_MUTED)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.setDash(2, 2)
        canvas_obj.line(marker_x, bar_y - 2, marker_x, bar_y + bar_h + 2)
        canvas_obj.setDash()  # Reset dash


def generate_pdf_report(report_data: dict, brand_name: str = "Clarvia") -> bytes:
    """Generate a PDF report from full report data. Returns PDF bytes.

    Args:
        report_data: Full report data dict.
        brand_name: Brand name for white-label support. Defaults to "Clarvia".
    """
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
            PageBreak,
            Preformatted,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        logger.error("reportlab not installed — cannot generate PDF")
        raise RuntimeError("PDF generation requires reportlab: pip install reportlab")

    buffer = io.BytesIO()
    page_w, page_h = A4

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    usable_w = page_w - 1.5 * inch
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CTitle", parent=styles["Title"], fontSize=24,
        textColor=colors.Color(*COLOR_WHITE), spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "CHeading", parent=styles["Heading2"], fontSize=14,
        textColor=colors.Color(*COLOR_WHITE), spaceBefore=16, spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "CBody", parent=styles["Normal"], fontSize=10,
        textColor=colors.Color(*COLOR_MUTED), leading=14,
    )
    score_style = ParagraphStyle(
        "CScore", parent=styles["Normal"], fontSize=48,
        alignment=TA_CENTER, textColor=colors.Color(*COLOR_WHITE), spaceAfter=4,
    )
    sub_heading_style = ParagraphStyle(
        "CSubHead", parent=styles["Normal"], fontSize=11,
        textColor=colors.Color(*COLOR_WHITE), spaceBefore=8, spaceAfter=4,
    )
    evidence_style = ParagraphStyle(
        "CEvidence", parent=styles["Normal"], fontSize=9,
        textColor=colors.Color(*COLOR_MUTED), leftIndent=12, leading=12,
    )
    rec_style = ParagraphStyle(
        "CRec", parent=styles["Normal"], fontSize=10,
        textColor=colors.Color(*COLOR_WHITE), leftIndent=16,
        leading=14, spaceBefore=4, spaceAfter=4,
    )
    code_style = ParagraphStyle(
        "CCode", parent=styles["Code"], fontSize=8,
        textColor=colors.Color(180 / 255, 200 / 255, 220 / 255),
        backColor=colors.Color(20 / 255, 28 / 255, 38 / 255),
        leading=11, leftIndent=8, rightIndent=8,
        spaceBefore=4, spaceAfter=8,
        fontName="Courier",
    )

    elements = []

    # --- Header ---
    elements.append(Paragraph(brand_name.upper(), ParagraphStyle(
        "CLogo", parent=styles["Normal"], fontSize=10,
        textColor=colors.Color(*COLOR_MUTED), spaceAfter=4,
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

    # Benchmark context
    benchmark = report_data.get("competitive_benchmark", {})
    if benchmark.get("percentile_rank") is not None:
        pctile = benchmark["percentile_rank"]
        avg = benchmark.get("industry_average", "N/A")
        n = benchmark.get("services_scanned", 0)
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(
            f'Ranked in the <font color="{score_color.hexval()}">{pctile}th percentile</font> '
            f'across {n} services (industry avg: {avg})',
            ParagraphStyle("CBenchNote", parent=body_style, alignment=TA_CENTER, fontSize=10),
        ))
    elements.append(Spacer(1, 20))

    # --- Dimension Breakdown with benchmark bars ---
    elements.append(Paragraph("Dimension Breakdown", heading_style))

    dimensions = report_data.get("dimensions", {})
    dim_benchmarks = benchmark.get("dimension_benchmarks", {})

    for dim_key, dim_data in dimensions.items():
        label = DIMENSION_LABELS.get(dim_key, dim_key.replace("_", " ").title())
        dim_score = dim_data.get("score", 0)
        dim_max = dim_data.get("max", 25)
        dim_color = _score_color_rl(dim_score, dim_max)
        dim_avg = dim_benchmarks.get(dim_key, {}).get("average")

        dim_text = f'{label}: <font color="{dim_color.hexval()}">{dim_score}/{dim_max}</font>'
        if dim_avg is not None:
            dim_text += f'  <font color="{colors.Color(*COLOR_MUTED).hexval()}">(avg: {dim_avg})</font>'
        elements.append(Paragraph(dim_text, sub_heading_style))

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

    elements.append(Spacer(1, 8))

    # --- Competitive Benchmark Peers ---
    peers = benchmark.get("closest_peers", [])
    if peers:
        elements.append(Paragraph("Competitive Landscape", heading_style))
        elements.append(Paragraph(
            "Services with similar Clarvia Scores:",
            evidence_style,
        ))

        peer_data = [["Service", "Score", "Rating"]]
        for p in peers:
            peer_data.append([p["name"], str(p["score"]), p.get("rating", "")])

        peer_table = Table(peer_data, colWidths=[usable_w * 0.5, usable_w * 0.2, usable_w * 0.3])
        peer_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(20 / 255, 28 / 255, 38 / 255)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.Color(*COLOR_ACCENT)),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.Color(*COLOR_WHITE)),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(30 / 255, 42 / 255, 58 / 255)),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ]))
        elements.append(peer_table)
        elements.append(Spacer(1, 12))

    # --- Implementation Roadmap ---
    roadmap = report_data.get("implementation_roadmap", [])
    if roadmap:
        elements.append(PageBreak())
        elements.append(Paragraph("Implementation Roadmap", heading_style))
        elements.append(Paragraph(
            "Prioritized by potential score improvement. Focus on high-gain, low-effort items first.",
            evidence_style,
        ))
        elements.append(Spacer(1, 8))

        road_data = [["Priority", "Action", "Gain", "Effort", "Timeline"]]
        for i, item in enumerate(roadmap[:10], 1):
            road_data.append([
                f"#{i}",
                item.get("action", "")[:80],
                f"+{item.get('potential_gain', 0)}",
                item.get("effort", "").upper(),
                item.get("timeline", ""),
            ])

        road_table = Table(road_data, colWidths=[
            usable_w * 0.08, usable_w * 0.5, usable_w * 0.08,
            usable_w * 0.14, usable_w * 0.2,
        ])
        road_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(20 / 255, 28 / 255, 38 / 255)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.Color(*COLOR_ACCENT)),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.Color(*COLOR_WHITE)),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(30 / 255, 42 / 255, 58 / 255)),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("ALIGN", (3, 0), (3, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(road_table)
        elements.append(Spacer(1, 16))

    # --- Code Examples ---
    code_examples = report_data.get("code_examples", [])
    if code_examples:
        elements.append(Paragraph("Code Examples", heading_style))
        elements.append(Paragraph(
            "Ready-to-use snippets for the highest-impact improvements:",
            evidence_style,
        ))
        elements.append(Spacer(1, 8))

        for ex in code_examples:
            elements.append(Paragraph(
                f'<b>{ex.get("title", "")}</b> <font color="{colors.Color(*COLOR_MUTED).hexval()}">(+{ex.get("potential_gain", 0)} pts)</font>',
                sub_heading_style,
            ))
            code_text = ex.get("code", "")
            # Use Preformatted for code blocks
            elements.append(Preformatted(code_text, code_style))
            elements.append(Spacer(1, 8))

    # --- Recommendations ---
    recommendations = report_data.get("recommendations", [])
    if recommendations:
        elements.append(PageBreak())
        elements.append(Paragraph("All Recommendations", heading_style))
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
    footer_text = (
        f"Generated by {brand_name} AEO Scanner | clarvia.art"
        if brand_name == "Clarvia"
        else f"Generated by {brand_name} | Powered by Clarvia AEO Scanner"
    )
    elements.append(Paragraph(
        footer_text,
        ParagraphStyle("CFooter", parent=body_style, alignment=TA_CENTER, fontSize=8),
    ))

    # Build PDF with dark background and gauge/radar on first page
    radar_data = report_data.get("radar_chart", {})

    def _on_first_page(canvas_obj, doc):
        canvas_obj.setFillColorRGB(*COLOR_BG)
        canvas_obj.rect(0, 0, page_w, page_h, fill=1, stroke=0)

        # Draw gauge in the top area (will overlap with platypus content area)
        # Position gauge at top-right of the usable area
        gauge_x = page_w - 0.75 * inch - 130
        gauge_y = page_h - 0.5 * inch - 160
        _draw_gauge(canvas_obj, gauge_x, gauge_y, report_data.get("clarvia_score", 0), size=120)

    def _on_later_pages(canvas_obj, doc):
        canvas_obj.setFillColorRGB(*COLOR_BG)
        canvas_obj.rect(0, 0, page_w, page_h, fill=1, stroke=0)

        # Page number
        canvas_obj.setFillColorRGB(*COLOR_MUTED)
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawCentredString(page_w / 2, 0.3 * inch, f"Page {doc.page}")

    doc.build(elements, onFirstPage=_on_first_page, onLaterPages=_on_later_pages)
    return buffer.getvalue()
