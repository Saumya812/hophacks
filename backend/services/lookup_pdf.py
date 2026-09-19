"""
Smart Person Search — PDF export for lookup reports.

Uses ReportLab to produce a clean intelligence-brief style PDF.
"""

from __future__ import annotations

import base64
import io
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.Color(26 / 255, 43 / 255, 74 / 255)


def _safe(text: Any, limit: int = 500) -> str:
    s = str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s[:limit]


def _photo_flowable(photo_data_url: Optional[str], max_w=1.4 * inch, max_h=1.6 * inch):
    if not photo_data_url or "," not in photo_data_url:
        return None
    try:
        header, b64 = photo_data_url.split(",", 1)
        raw = base64.b64decode(b64)
        img = Image(io.BytesIO(raw), width=max_w, height=max_h, kind="proportional")
        return img
    except Exception:  # noqa: BLE001
        return None


def build_lookup_pdf(report: Dict[str, Any]) -> bytes:
    """Render a lookup report dict to PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="FindMyPal Smart Person Search Report",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FMPTitle",
        parent=styles["Heading1"],
        textColor=NAVY,
        fontSize=18,
        spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "FMPH2",
        parent=styles["Heading2"],
        textColor=NAVY,
        fontSize=13,
        spaceBefore=14,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "FMPBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1a2b4a"),
    )
    small = ParagraphStyle(
        "FMPSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#3c526d"),
    )

    summary = report.get("summary") or {}
    sightings: List[Dict] = report.get("sightings") or []
    locations: List[Dict] = report.get("locations") or []
    raw_mentions: List[Dict] = report.get("raw_mentions") or []

    story = []
    story.append(Paragraph("FindMyPal — Smart Person Search Report", title_style))
    story.append(
        Paragraph(
            "Community intelligence brief compiled from public web &amp; social index sources. "
            "Not affiliated with law enforcement. Do not misuse.",
            small,
        )
    )
    story.append(Spacer(1, 10))

    # Summary header with optional photo
    photo = _photo_flowable(summary.get("photo_data_url"))
    date_range = summary.get("date_range") or {}
    summary_html = (
        f"<b>Name:</b> {_safe(summary.get('name'))}<br/>"
        f"<b>Total mentions:</b> {_safe(summary.get('total_mentions'))}<br/>"
        f"<b>Date range:</b> {_safe(date_range.get('start') or '—')} → {_safe(date_range.get('end') or '—')}<br/>"
        f"<b>Most frequent location:</b> {_safe(summary.get('most_frequent_location') or '—')}<br/>"
        f"<b>Generated:</b> {_safe(summary.get('generated_at'))}"
    )
    if photo:
        tbl = Table([[photo, Paragraph(summary_html, body)]], colWidths=[1.6 * inch, 5.2 * inch])
        tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(tbl)
    else:
        story.append(Paragraph(summary_html, body))

    # Sighting claims (chronological social/web claims)
    claims: List[Dict] = report.get("claims") or [
        s for s in sightings if (s.get("kind") or "").lower() == "sighting"
    ]
    story.append(Paragraph("Sighting Claims", h2))
    if not claims:
        story.append(
            Paragraph(
                "No witness sighting claims extracted. News “last seen” reports are listed under All Extracted Mentions.",
                body,
            )
        )
    else:
        for i, c in enumerate(claims, start=1):
            summary_line = c.get("claim_summary") or (
                f"{c.get('username') or 'Someone'} on {c.get('source') or 'web'} "
                f"claims to have seen the person"
                + (f" on {c.get('date')}" if c.get("date") else "")
                + (f" at around {c.get('time')}" if c.get("time") else "")
                + (f" near {c.get('location')}" if c.get("location") else "")
            )
            line = (
                f"<b>{i}.</b> {_safe(summary_line, 400)}<br/>"
                f"<i>\"{_safe(c.get('quote'), 220)}\"</i><br/>"
                f"<font color='#4d6786'>{_safe(c.get('url'), 200)}</font>"
            )
            story.append(Paragraph(line, body))
            story.append(Spacer(1, 6))

    # All extracted mentions
    story.append(Paragraph("All Extracted Mentions", h2))
    if not sightings:
        story.append(Paragraph("No structured sightings extracted.", body))
    else:
        for s in sightings:
            conf = (s.get("confidence") or "low").upper()
            line = (
                f"<b>[{conf}]</b> {_safe(s.get('source'))}"
                f"{(' · @' + _safe(s.get('username'))) if s.get('username') else ''} · "
                f"{_safe(s.get('date') or 'undated')} · "
                f"{_safe(s.get('location') or 'no location')}<br/>"
                f"\"{_safe(s.get('quote'), 280)}\"<br/>"
                f"<font color='#4d6786'>{_safe(s.get('url'), 200)}</font>"
            )
            story.append(Paragraph(line, body))
            story.append(Spacer(1, 6))

    # Locations
    story.append(Paragraph("Mentioned Locations", h2))
    if not locations:
        story.append(Paragraph("No geocoded locations.", body))
    else:
        for loc in locations:
            story.append(
                Paragraph(
                    f"• {_safe(loc.get('label'))} "
                    f"(count={_safe(loc.get('count'))}, "
                    f"lat={_safe(loc.get('lat'))}, lng={_safe(loc.get('lng'))})",
                    body,
                )
            )

    # Raw mentions (abbreviated)
    story.append(Paragraph("Raw Mentions (sample)", h2))
    for item in raw_mentions[:30]:
        user = item.get("username")
        user_bit = f" · @{_safe(user)}" if user else ""
        story.append(
            Paragraph(
                f"<b>{_safe(item.get('source'))}</b>{user_bit} · {_safe(item.get('date'))}<br/>"
                f"{_safe(item.get('snippet') or item.get('text') or item.get('title'), 220)}<br/>"
                f"<font color='#4d6786'>{_safe(item.get('url'), 180)}</font>",
                small,
            )
        )
        story.append(Spacer(1, 4))

    if len(raw_mentions) > 30:
        story.append(Paragraph(f"…and {len(raw_mentions) - 30} more raw mentions.", small))

    doc.build(story)
    return buffer.getvalue()
