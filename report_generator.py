"""ZeroTax AI — Branded PDF Report Generator

Produces a professional multi-page PDF report from an AI analysis result.
Sections:
  1. Cover page (logo, headline, executive summary)
  2. Tax savings waterfall chart
  3. Strategy breakdown (one section per strategy)
  4. Implementation roadmap
  5. State filing portal links
  6. Attorney referral template
  7. Three-page legal disclaimer
"""

from __future__ import annotations

import io
import os
from datetime import date
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether, HRFlowable,
    ListFlowable, ListItem,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import utils

from state_portals import STATE_PORTALS, ATTORNEY_REFERRAL_TEMPLATE, get_state_info

# ─── Color Palette ────────────────────────────────────────────────────────────

C_BG         = HexColor("#080a0f")
C_CARD       = HexColor("#13161e")
C_BORDER     = HexColor("#1e2534")
C_BLUE       = HexColor("#3b82f6")
C_BLUE_DARK  = HexColor("#1d4ed8")
C_EMERALD    = HexColor("#10b981")
C_AMBER      = HexColor("#f59e0b")
C_RED        = HexColor("#ef4444")
C_TEXT       = HexColor("#f1f5f9")
C_MUTED      = HexColor("#64748b")
C_WHITE      = white
C_BLACK      = black
C_DARK_NAVY  = HexColor("#0f172a")
C_LIGHT_GRAY = HexColor("#e2e8f0")
C_MID_GRAY   = HexColor("#94a3b8")


# ─── Styles ───────────────────────────────────────────────────────────────────

def _build_styles() -> dict:
    base = getSampleStyleSheet()
    styles = {}

    def add(name, **kw):
        parent = kw.pop("parent", "Normal")
        styles[name] = ParagraphStyle(name=name, parent=base[parent], **kw)

    add("Cover_Title",    fontSize=42, leading=50, textColor=C_WHITE, spaceAfter=12, fontName="Helvetica-Bold", alignment=TA_CENTER)
    add("Cover_Sub",      fontSize=18, leading=24, textColor=C_BLUE,  spaceAfter=8,  fontName="Helvetica",      alignment=TA_CENTER)
    add("Cover_Tagline",  fontSize=12, leading=18, textColor=C_MUTED, spaceAfter=6,  fontName="Helvetica",      alignment=TA_CENTER)
    add("Headline",       fontSize=22, leading=28, textColor=C_WHITE, spaceAfter=8,  fontName="Helvetica-Bold", alignment=TA_LEFT)
    add("Section_Title",  fontSize=16, leading=22, textColor=C_BLUE,  spaceAfter=4,  fontName="Helvetica-Bold", spaceBefore=14)
    add("Strategy_Title", fontSize=13, leading=18, textColor=C_WHITE, spaceAfter=3,  fontName="Helvetica-Bold")
    add("Body",           fontSize=10, leading=16, textColor=C_LIGHT_GRAY, spaceAfter=6, fontName="Helvetica")
    add("Body_Small",     fontSize=9,  leading=14, textColor=C_MID_GRAY,   spaceAfter=4, fontName="Helvetica")
    add("Savings_Big",    fontSize=32, leading=40, textColor=C_EMERALD,    spaceAfter=4, fontName="Helvetica-Bold", alignment=TA_CENTER)
    add("Savings_Label",  fontSize=10, leading=14, textColor=C_MUTED,      spaceAfter=2, fontName="Helvetica",      alignment=TA_CENTER)
    add("Callout",        fontSize=13, leading=20, textColor=C_AMBER,      spaceAfter=6, fontName="Helvetica-Bold")
    add("Disclaimer",     fontSize=8,  leading=12, textColor=C_MID_GRAY,   spaceAfter=4, fontName="Helvetica", alignment=TA_JUSTIFY)
    add("Footer",         fontSize=7,  leading=10, textColor=C_MUTED,      fontName="Helvetica", alignment=TA_CENTER)
    add("Bullet",         fontSize=10, leading=15, textColor=C_LIGHT_GRAY, spaceAfter=3, fontName="Helvetica", leftIndent=12, firstLineIndent=-10)
    add("IRC_Citation",   fontSize=9,  leading=13, textColor=C_BLUE,       spaceAfter=3, fontName="Helvetica", leftIndent=8)
    add("Tag_Critical",   fontSize=8,  leading=10, textColor=white,        fontName="Helvetica-Bold", alignment=TA_CENTER)
    add("Action_Step",    fontSize=10, leading=15, textColor=C_LIGHT_GRAY, spaceAfter=2, fontName="Helvetica", leftIndent=16, firstLineIndent=-14)
    add("Roadmap_Phase",  fontSize=11, leading=16, textColor=C_AMBER,      spaceAfter=2, fontName="Helvetica-Bold")
    return styles


# ─── Matplotlib Charts ────────────────────────────────────────────────────────

def _mpl_waterfall(result: dict, width_in: float = 6.5, height_in: float = 3.5) -> io.BytesIO:
    breakdown = result.get("savings_breakdown", {})
    current   = float(result.get("current_estimated_tax", 0))
    optimized = float(result.get("optimized_estimated_tax", 0))

    labels  = ["Current Tax"]
    amounts = [current]
    is_pos  = [False]

    labels_map = {
        "entity_restructuring": "Entity Restructuring",
        "retirement_plans":     "Retirement Plans",
        "qbi_deduction":        "QBI §199A",
        "depreciation":         "Depreciation §168",
        "family_employment":    "Family Employment",
        "state_tax":            "State Tax",
        "other_deductions":     "Other Deductions",
    }
    for key, label in labels_map.items():
        v = float(breakdown.get(key, 0))
        if v > 0:
            labels.append(label)
            amounts.append(-v)
            is_pos.append(True)

    labels.append("Optimized Tax")
    amounts.append(optimized)
    is_pos.append(False)

    # Compute bar bases
    running = current
    bases   = [0]
    for a in amounts[1:-1]:
        bases.append(running + min(a, 0))
        running += a
    bases.append(0)

    colors = []
    for i, p in enumerate(is_pos):
        if i == 0:              colors.append("#475569")
        elif i == len(is_pos)-1:colors.append("#3b82f6")
        else:                   colors.append("#10b981")

    fig, ax = plt.subplots(figsize=(width_in, height_in))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    bars = ax.bar(range(len(labels)), [abs(a) for a in amounts], bottom=bases, color=colors, width=0.6, edgecolor="#1e2534", linewidth=0.8)

    # Connector lines
    for i in range(len(labels) - 1):
        top_i = bases[i] + abs(amounts[i]) if not is_pos[i] else bases[i] + abs(amounts[i])
        start = running = current
        r = current
        for j, a in enumerate(amounts):
            if j == i: break
            r += a
        x_start = i + 0.3
        x_end   = i + 0.7
        y_val   = r if i > 0 else current
        ax.plot([x_start, x_end], [y_val, y_val], color="#334155", linewidth=0.8, linestyle="--")

    for i, (bar, amount) in enumerate(zip(bars, amounts)):
        y = bar.get_y() + bar.get_height() + (current * 0.015)
        sign = "-$" if amount < 0 else "$"
        ax.text(bar.get_x() + bar.get_width()/2, y, f"{sign}{abs(amount):,.0f}",
                ha="center", va="bottom", fontsize=7.5, color="#f1f5f9", fontweight="bold")

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=7.5, color="#94a3b8")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.tick_params(colors="#64748b", which="both")
    ax.spines[:].set_color("#1e2534")
    ax.yaxis.label.set_color("#94a3b8")
    ax.set_ylabel("Annual Tax ($)", color="#94a3b8", fontsize=8)
    ax.grid(axis="y", color="#1e2534", linewidth=0.5, linestyle="--")
    fig.tight_layout(pad=1.2)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
    buf.seek(0)
    plt.close(fig)
    return buf


def _mpl_bar_chart(strategies: list, width_in: float = 6.5, height_in: float = 3.0) -> io.BytesIO:
    approved = [s for s in strategies if s.get("approved_for_report", True)]
    top = sorted(approved, key=lambda x: x.get("estimated_annual_savings", 0), reverse=True)[:10]
    names  = [s["name"][:30] + ("…" if len(s["name"]) > 30 else "") for s in top]
    savings = [float(s.get("estimated_annual_savings", 0)) for s in top]
    risks   = [int(s.get("risk_score", 5)) for s in top]
    colors = ["#10b981" if r <= 3 else "#3b82f6" if r <= 6 else "#f59e0b" for r in risks]

    fig, ax = plt.subplots(figsize=(width_in, height_in))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    y_pos = range(len(names))
    bars = ax.barh([n[::-1] for n in names[::-1]], savings[::-1], color=colors[::-1], height=0.6, edgecolor="#1e2534")
    for bar, v in zip(bars, savings[::-1]):
        ax.text(bar.get_width() + max(savings) * 0.01, bar.get_y() + bar.get_height()/2,
                f"${v:,.0f}", va="center", ha="left", fontsize=7.5, color="#f1f5f9")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.tick_params(colors="#64748b")
    ax.spines[:].set_color("#1e2534")
    ax.set_xlabel("Annual Tax Savings ($)", color="#94a3b8", fontsize=8)
    ax.tick_params(axis="y", labelsize=7.5, labelcolor="#94a3b8")
    ax.grid(axis="x", color="#1e2534", linewidth=0.5, linestyle="--")

    legend = [
        mpatches.Patch(color="#10b981", label="Low Risk (1-3)"),
        mpatches.Patch(color="#3b82f6", label="Med Risk (4-6)"),
        mpatches.Patch(color="#f59e0b", label="High Risk (7+)"),
    ]
    ax.legend(handles=legend, fontsize=7, loc="lower right", facecolor="#13161e", edgecolor="#1e2534", labelcolor="#94a3b8")
    fig.tight_layout(pad=1.2)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
    buf.seek(0)
    plt.close(fig)
    return buf


# ─── Page Templates ───────────────────────────────────────────────────────────

PAGE_W, PAGE_H = letter

def _header_footer(canvas, doc):
    canvas.saveState()
    # Header bar
    canvas.setFillColor(C_DARK_NAVY)
    canvas.rect(0, PAGE_H - 0.55 * inch, PAGE_W, 0.55 * inch, fill=1, stroke=0)
    canvas.setFillColor(C_BLUE)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(0.5 * inch, PAGE_H - 0.35 * inch, "ZeroTax AI")
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - 0.5 * inch, PAGE_H - 0.35 * inch, f"CONFIDENTIAL — Generated {date.today().isoformat()}")

    # Footer bar
    canvas.setFillColor(C_DARK_NAVY)
    canvas.rect(0, 0, PAGE_W, 0.45 * inch, fill=1, stroke=0)
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(PAGE_W / 2, 0.18 * inch,
        "This report is generated by AI and does not constitute legal, tax, or financial advice. Consult a licensed CPA or tax attorney.")
    canvas.drawRightString(PAGE_W - 0.5 * inch, 0.18 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _cover_page_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(C_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Gradient accent bar on left
    canvas.setFillColor(C_BLUE_DARK)
    canvas.rect(0, 0, 0.18 * inch, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, 0, 0.06 * inch, PAGE_H, fill=1, stroke=0)
    # Bottom strip
    canvas.setFillColor(C_DARK_NAVY)
    canvas.rect(0, 0, PAGE_W, 0.6 * inch, fill=1, stroke=0)
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(PAGE_W / 2, 0.22 * inch,
        "AI-GENERATED ANALYSIS • NOT LEGAL OR TAX ADVICE • CONFIDENTIAL")
    canvas.restoreState()


# ─── Helper Flowables ─────────────────────────────────────────────────────────

def _hr(color=C_BORDER, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=8, spaceBefore=8)


def _stat_table(data: list[tuple[str, str, str]]) -> Table:
    """3-column stat row: (label, value, sublabel)"""
    cells = [[
        [Paragraph(v, ParagraphStyle("sv", fontName="Helvetica-Bold", fontSize=20, textColor=HexColor(c if c else "#10b981"), alignment=TA_CENTER)),
         Paragraph(lbl, ParagraphStyle("sl", fontName="Helvetica", fontSize=8, textColor=HexColor("#64748b"), alignment=TA_CENTER))]
        for lbl, v, c in data
    ]]
    col_w = (PAGE_W - inch) / len(data)
    t = Table(cells, colWidths=[col_w] * len(data))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_CARD]),
        ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return t


def _priority_badge(priority: str) -> str:
    colors = {"critical": "#ef4444", "high": "#f59e0b", "medium": "#3b82f6", "low": "#64748b"}
    c = colors.get(priority, "#64748b")
    return f'<font color="{c}"><b>[{priority.upper()}]</b></font>'


def _complexity_badge(complexity: str) -> str:
    labels = {"simple": "✓ Simple", "medium": "◆ Medium", "complex": "⚠ Complex", "attorney_required": "⚖ Attorney Required"}
    colors = {"simple": "#10b981", "medium": "#3b82f6", "complex": "#f59e0b", "attorney_required": "#ef4444"}
    c = colors.get(complexity, "#64748b")
    lbl = labels.get(complexity, complexity)
    return f'<font color="{c}"><b>{lbl}</b></font>'


# ─── Section Builders ─────────────────────────────────────────────────────────

def _build_cover(result: dict, wizard_data: dict, styles: dict) -> list:
    story = []
    story.append(Spacer(1, 1.6 * inch))

    # Logo placeholder
    logo_d = Drawing(200, 50)
    logo_d.add(Rect(0, 10, 180, 35, fillColor=C_BLUE, strokeColor=None))
    logo_d.add(String(90, 22, "ZeroTax AI", fontName="Helvetica-Bold", fontSize=20, fillColor=white, textAnchor="middle"))
    story.append(logo_d)
    story.append(Spacer(1, 0.3 * inch))

    business_name = wizard_data.get("business_name", "Your Business")
    story.append(Paragraph(f"Tax Optimization Report", styles["Cover_Title"]))
    story.append(Paragraph(business_name, styles["Cover_Sub"]))
    story.append(Paragraph(f"Prepared by ZeroTax AI  •  {date.today().strftime('%B %d, %Y')}", styles["Cover_Tagline"]))
    story.append(Spacer(1, 0.4 * inch))

    # Headline savings box
    savings = result.get("projected_annual_savings", 0)
    savings_10yr = result.get("projected_10yr_savings", savings * 10)
    headline = [
        [Paragraph(f"${savings:,.0f}", ParagraphStyle("hs", fontName="Helvetica-Bold", fontSize=44, textColor=C_EMERALD, alignment=TA_CENTER)),
         Paragraph(f"${savings_10yr:,.0f}", ParagraphStyle("hs2", fontName="Helvetica-Bold", fontSize=44, textColor=C_BLUE, alignment=TA_CENTER))],
        [Paragraph("PROJECTED ANNUAL SAVINGS", ParagraphStyle("hl", fontName="Helvetica", fontSize=9, textColor=C_MUTED, alignment=TA_CENTER)),
         Paragraph("10-YEAR PROJECTION", ParagraphStyle("hl2", fontName="Helvetica", fontSize=9, textColor=C_MUTED, alignment=TA_CENTER))],
    ]
    ht = Table(headline, colWidths=[3.25 * inch, 3.25 * inch])
    ht.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_DARK_NAVY),
        ("BOX",           (0, 0), (-1, -1), 1.5, C_BLUE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
    ]))
    story.append(ht)
    story.append(Spacer(1, 0.35 * inch))

    insight = result.get("headline_insight", "")
    if insight:
        story.append(Paragraph(f'"{insight}"', ParagraphStyle("hi", fontName="Helvetica-BoldOblique", fontSize=12, textColor=C_AMBER, alignment=TA_CENTER, leading=18)))

    story.append(Spacer(1, 0.35 * inch))
    # Profile strip
    prof = [
        [Paragraph("ENTITY", ParagraphStyle("pl", fontName="Helvetica", fontSize=8, textColor=C_MUTED, alignment=TA_CENTER)),
         Paragraph("STATE", ParagraphStyle("pl", fontName="Helvetica", fontSize=8, textColor=C_MUTED, alignment=TA_CENTER)),
         Paragraph("ANNUAL PROFIT", ParagraphStyle("pl", fontName="Helvetica", fontSize=8, textColor=C_MUTED, alignment=TA_CENTER)),
         Paragraph("STRATEGIES", ParagraphStyle("pl", fontName="Helvetica", fontSize=8, textColor=C_MUTED, alignment=TA_CENTER))],
        [Paragraph(wizard_data.get("entity_type", "—").replace("_", " ").title(), ParagraphStyle("pv", fontName="Helvetica-Bold", fontSize=11, textColor=C_TEXT, alignment=TA_CENTER)),
         Paragraph(wizard_data.get("state", "—"), ParagraphStyle("pv", fontName="Helvetica-Bold", fontSize=11, textColor=C_TEXT, alignment=TA_CENTER)),
         Paragraph(f"${float(wizard_data.get('annual_profit', 0) or 0):,.0f}", ParagraphStyle("pv", fontName="Helvetica-Bold", fontSize=11, textColor=C_TEXT, alignment=TA_CENTER)),
         Paragraph(str(len([s for s in result.get("strategies", []) if s.get("approved_for_report", True)])), ParagraphStyle("pv", fontName="Helvetica-Bold", fontSize=11, textColor=C_EMERALD, alignment=TA_CENTER))],
    ]
    pt = Table(prof, colWidths=[1.625 * inch] * 4)
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
        ("BOX",        (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(pt)
    story.append(PageBreak())
    return story


def _build_executive_summary(result: dict, styles: dict) -> list:
    story = []
    story.append(Paragraph("Executive Summary", styles["Section_Title"]))
    story.append(_hr(C_BLUE))

    summary = result.get("executive_summary", "")
    for para in summary.split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), styles["Body"]))
            story.append(Spacer(1, 0.06 * inch))

    story.append(Spacer(1, 0.1 * inch))

    # Entity recommendation box
    entity_rec = result.get("entity_recommendation", "")
    entity_rat = result.get("entity_rationale", "")
    if entity_rec:
        box_data = [[
            Paragraph("RECOMMENDED ENTITY STRUCTURE", ParagraphStyle("rel", fontName="Helvetica", fontSize=8, textColor=C_MUTED)),
            Paragraph(entity_rec, ParagraphStyle("rev", fontName="Helvetica-Bold", fontSize=16, textColor=C_BLUE)),
            Paragraph(entity_rat, ParagraphStyle("rer", fontName="Helvetica", fontSize=9, textColor=C_LIGHT_GRAY, leading=13)),
        ]]
        bt = Table(box_data, colWidths=[1.5 * inch, 2.0 * inch, 3.0 * inch])
        bt.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_DARK_NAVY),
            ("BOX",           (0, 0), (-1, -1), 1, C_BLUE),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
            ("LINEAFTER",     (0, 0), (1, -1), 0.5, C_BORDER),
        ]))
        story.append(bt)

    story.append(Spacer(1, 0.15 * inch))

    # Urgent actions
    urgent = result.get("urgent_actions", [])
    if urgent:
        story.append(Paragraph("⚡ Urgent Actions — Do This Now", styles["Callout"]))
        for action in urgent[:5]:
            story.append(Paragraph(f"→  {action}", styles["Bullet"]))

    return story


def _build_charts_page(result: dict, styles: dict) -> list:
    story = []
    story.append(Paragraph("Tax Savings Overview", styles["Section_Title"]))
    story.append(_hr(C_BLUE))

    # Stats row
    current_tax   = float(result.get("current_estimated_tax", 0))
    optimized_tax = float(result.get("optimized_estimated_tax", 0))
    savings       = float(result.get("projected_annual_savings", 0))
    pct           = round(savings / max(current_tax, 1) * 100, 1)

    story.append(_stat_table([
        ("Current Annual Tax",    f"${current_tax:,.0f}",   "#ef4444"),
        ("Optimized Annual Tax",  f"${optimized_tax:,.0f}", "#3b82f6"),
        ("Annual Savings",        f"${savings:,.0f}",       "#10b981"),
        ("Tax Reduction",         f"{pct}%",                "#f59e0b"),
    ]))
    story.append(Spacer(1, 0.15 * inch))

    # Waterfall chart
    wf_buf = _mpl_waterfall(result)
    wf_img = Image(wf_buf, width=6.5 * inch, height=3.5 * inch)
    story.append(Paragraph("Savings Waterfall by Strategy Category", ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=11, textColor=C_MUTED, spaceAfter=4)))
    story.append(wf_img)
    story.append(Spacer(1, 0.15 * inch))

    # Top strategies bar chart
    strategies = result.get("strategies", [])
    if strategies:
        bar_buf = _mpl_bar_chart(strategies)
        bar_img = Image(bar_buf, width=6.5 * inch, height=3.0 * inch)
        story.append(Paragraph("Top Strategies by Annual Savings", ParagraphStyle("ct2", fontName="Helvetica-Bold", fontSize=11, textColor=C_MUTED, spaceAfter=4)))
        story.append(bar_img)

    return story


def _build_strategies(result: dict, styles: dict) -> list:
    story = []
    story.append(PageBreak())
    story.append(Paragraph("Tax Strategy Breakdown", styles["Section_Title"]))
    story.append(_hr(C_BLUE))
    story.append(Paragraph(
        "Each strategy below is a legally recognized tax planning technique. All savings estimates are conservative. "
        "Implementation requires review by a licensed CPA and/or tax attorney.",
        styles["Body_Small"]
    ))
    story.append(Spacer(1, 0.1 * inch))

    strategies = [s for s in result.get("strategies", []) if s.get("approved_for_report", True)]
    strategies = sorted(strategies, key=lambda x: x.get("estimated_annual_savings", 0), reverse=True)

    category_colors = {
        "entity_structure":  "#3b82f6", "retirement":      "#10b981",
        "depreciation":      "#f59e0b", "deductions":      "#06b6d4",
        "real_estate":       "#8b5cf6", "estate_planning":  "#f43f5e",
        "family_employment": "#84cc16", "state_tax":        "#fb923c",
        "credits":           "#e879f9", "qsbs":             "#fbbf24",
    }

    for i, s in enumerate(strategies, 1):
        cat   = s.get("category", "deductions")
        cat_c = category_colors.get(cat, "#64748b")
        items = []

        # Strategy header row
        header = [
            Paragraph(f"{i:02d}", ParagraphStyle("sn", fontName="Helvetica-Bold", fontSize=18, textColor=HexColor(cat_c), alignment=TA_CENTER)),
            [
                Paragraph(s.get("name", ""), styles["Strategy_Title"]),
                Paragraph(
                    f'{_priority_badge(s.get("priority","medium"))}  •  '
                    f'{_complexity_badge(s.get("complexity","medium"))}  •  '
                    f'Risk: <b>{s.get("risk_score", 5)}/10</b>  •  '
                    f'Timeline: <b>{s.get("timeline_days", 30)} days</b>',
                    ParagraphStyle("sm", fontName="Helvetica", fontSize=9, textColor=C_MUTED, leading=13),
                ),
            ],
            Paragraph(
                f'<b>${float(s.get("estimated_annual_savings", 0)):,.0f}</b><br/>'
                f'<font color="#64748b" size="8">per year</font>',
                ParagraphStyle("sa", fontName="Helvetica-Bold", fontSize=16, textColor=C_EMERALD, alignment=TA_RIGHT),
            ),
        ]
        ht = Table([header], colWidths=[0.5 * inch, 4.8 * inch, 1.2 * inch])
        ht.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_CARD),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (0, -1), 10),
            ("LEFTPADDING",   (1, 0), (1, -1), 8),
            ("RIGHTPADDING",  (-1, 0), (-1, -1), 12),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("LINEBELOW",     (0, 0), (-1, 0), 2, HexColor(cat_c)),
        ]))
        items.append(ht)

        # Explanation
        explanation = s.get("detailed_explanation", s.get("description", ""))
        if explanation:
            items.append(Spacer(1, 0.04 * inch))
            items.append(Paragraph(explanation, styles["Body"]))

        # Savings calculation
        calc = s.get("savings_calculation", {})
        if calc.get("formula"):
            formula_text = (
                f"<b>Calculation:</b> {calc['formula']}  "
                f"= <b>${float(calc.get('result', 0)):,.0f}</b>  "
                f"(Conservative: <b>${float(calc.get('conservative_result', 0)):,.0f}</b>)"
            )
            items.append(Paragraph(formula_text, styles["IRC_Citation"]))

        # IRC sections
        irc = s.get("irc_sections", [])
        if irc:
            items.append(Paragraph(f"IRC Sections: §{' · §'.join(str(x) for x in irc)}", styles["IRC_Citation"]))

        # Action items
        actions = s.get("action_items", [])
        if actions:
            items.append(Paragraph("Implementation Steps:", ParagraphStyle("aih", fontName="Helvetica-Bold", fontSize=9, textColor=C_MUTED, spaceBefore=4, spaceAfter=2)))
            for j, action in enumerate(actions[:5], 1):
                items.append(Paragraph(f"  {j}.  {action}", styles["Action_Step"]))

        # Caveats
        caveats = s.get("caveats", [])
        if caveats:
            items.append(Paragraph(f'⚠  <font color="#f59e0b">{caveats[0]}</font>', styles["Body_Small"]))

        story.append(KeepTogether(items))
        story.append(Spacer(1, 0.14 * inch))

    return story


def _build_roadmap(result: dict, styles: dict) -> list:
    story = []
    story.append(PageBreak())
    story.append(Paragraph("Implementation Roadmap", styles["Section_Title"]))
    story.append(_hr(C_BLUE))

    roadmap = result.get("roadmap", [])
    phase_colors = [C_BLUE, C_EMERALD, HexColor("#f59e0b"), HexColor("#8b5cf6")]

    for i, phase in enumerate(roadmap):
        color = phase_colors[i % len(phase_colors)]
        phase_num = phase.get("phase", i + 1)
        title     = phase.get("title", f"Phase {phase_num}")
        timeframe = phase.get("timeframe", "")
        est_savings = float(phase.get("estimated_savings", 0))
        milestones  = phase.get("milestones", [])
        strats      = phase.get("strategies", [])

        header = [
            Paragraph(f"Phase {phase_num}", ParagraphStyle("pn", fontName="Helvetica-Bold", fontSize=11, textColor=color, alignment=TA_CENTER)),
            Paragraph(f"<b>{title}</b><br/><font color='#64748b' size='9'>{timeframe}</font>",
                      ParagraphStyle("pt", fontName="Helvetica-Bold", fontSize=12, textColor=C_TEXT, leading=16)),
            Paragraph(f"<b>${est_savings:,.0f}</b><br/><font color='#64748b' size='8'>annual savings</font>",
                      ParagraphStyle("ps", fontName="Helvetica-Bold", fontSize=14, textColor=color, alignment=TA_RIGHT)),
        ]
        ht = Table([header], colWidths=[0.8 * inch, 4.8 * inch, 1.0 * inch])
        ht.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_CARD),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("LINEAFTER",     (0, 0), (0, -1), 3, color),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))

        body = []
        if strats:
            body.append(Paragraph("Strategies: " + "  •  ".join(strats[:4]), styles["Body_Small"]))
        for m in milestones[:4]:
            body.append(Paragraph(f"✓  {m}", styles["Bullet"]))

        story.append(KeepTogether([ht] + [Spacer(1, 0.04 * inch)] + body + [Spacer(1, 0.12 * inch)]))

    return story


def _build_state_portals(wizard_data: dict, styles: dict) -> list:
    story = []
    story.append(PageBreak())
    story.append(Paragraph("State Filing Portals & Resources", styles["Section_Title"]))
    story.append(_hr(C_BLUE))

    state_code = wizard_data.get("state", "").upper()
    state_info = get_state_info(state_code)

    story.append(Paragraph(
        f"Based on your state of {state_info.get('name', state_code)}, here are the official filing resources needed "
        "to implement your tax strategies.",
        styles["Body"]
    ))
    story.append(Spacer(1, 0.1 * inch))

    # Primary state card
    primary = [
        [Paragraph(f"{state_info.get('name', state_code)} — Primary Jurisdiction", ParagraphStyle("sth", fontName="Helvetica-Bold", fontSize=12, textColor=C_BLUE)), "", ""],
        [Paragraph("Secretary of State / Business Portal:", styles["Body_Small"]),
         Paragraph(state_info.get("sos", "See state SOS website"), ParagraphStyle("url", fontName="Helvetica", fontSize=9, textColor=C_BLUE, leading=13)),
         ""],
        [Paragraph("LLC Formation Fee:", styles["Body_Small"]),
         Paragraph(f"${state_info.get('llc_fee', 0):,}", styles["Body"]), ""],
        [Paragraph("Annual Report Fee:", styles["Body_Small"]),
         Paragraph(f"${state_info.get('annual_fee', 0):,} (due {state_info.get('annual_due', 'varies')})", styles["Body"]), ""],
        [Paragraph("State Income Tax Rate:", styles["Body_Small"]),
         Paragraph(
             f"{state_info.get('income_tax', 0):.1f}%" if not state_info.get("no_income_tax") else "✅ NO STATE INCOME TAX",
             ParagraphStyle("tax", fontName="Helvetica-Bold", fontSize=10, textColor=C_EMERALD if state_info.get("no_income_tax") else C_RED)
         ), ""],
    ]
    pt = Table(primary, colWidths=[2.5 * inch, 3.0 * inch, 1.0 * inch])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_DARK_NAVY),
        ("BACKGROUND", (0, 1), (-1, -1), C_CARD),
        ("BOX",        (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, C_BORDER),
        ("SPAN",       (0, 0), (-1, 0)),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    story.append(pt)
    story.append(Spacer(1, 0.2 * inch))

    # Favorable formation states
    story.append(Paragraph("Top Formation Jurisdictions for Holding Companies", styles["Strategy_Title"]))
    story.append(Spacer(1, 0.06 * inch))
    favor_data = [["State", "Benefit", "LLC Fee", "Annual"]]
    favor_states = [("WY", "Wyoming"), ("DE", "Delaware"), ("NV", "Nevada"), ("SD", "South Dakota")]
    for code, name in favor_states:
        si = get_state_info(code)
        favor_data.append([
            f"{name} ({code})",
            STATE_PORTALS.get(code, {}).get("name", ""),
            f"${si.get('llc_fee', 0):,}",
            f"${si.get('annual_fee', 0):,}",
        ])
    ft = Table(favor_data, colWidths=[2.0 * inch, 3.0 * inch, 1.0 * inch, 0.6 * inch])
    ft.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_BLUE_DARK),
        ("TEXTCOLOR",  (0, 0), (-1, 0), white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 1), (-1, -1), C_CARD),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_CARD, C_DARK_NAVY]),
        ("GRID",       (0, 0), (-1, -1), 0.3, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), C_LIGHT_GRAY),
    ]))
    story.append(ft)

    return story


def _build_attorney_referral(styles: dict) -> list:
    story = []
    story.append(PageBreak())
    story.append(Paragraph("Attorney Referral Template", styles["Section_Title"]))
    story.append(_hr(C_BLUE))
    story.append(Paragraph(
        "Use the following template when engaging a tax attorney or CPA to implement your strategies. "
        "Fill in the bracketed fields before sending.",
        styles["Body"]
    ))
    story.append(Spacer(1, 0.1 * inch))

    template_lines = ATTORNEY_REFERRAL_TEMPLATE.strip().split("\n")
    for line in template_lines:
        if line.startswith("━"):
            story.append(_hr(C_BORDER))
        elif line.strip() == "":
            story.append(Spacer(1, 0.04 * inch))
        elif line.isupper() and len(line) > 4:
            story.append(Paragraph(line, ParagraphStyle("tsh", fontName="Helvetica-Bold", fontSize=9, textColor=C_BLUE, spaceAfter=2)))
        elif line.startswith("─"):
            story.append(_hr(C_BORDER, thickness=0.3))
        else:
            story.append(Paragraph(line, styles["Body_Small"]))

    return story


def _build_disclaimer(styles: dict) -> list:
    story = []
    story.append(PageBreak())
    story.append(Paragraph("Legal Disclaimer & Disclosures", styles["Section_Title"]))
    story.append(_hr(C_RED))

    disclaimer_sections = [
        ("1. NOT LEGAL OR TAX ADVICE", """
This report was generated by ZeroTax AI, an artificial intelligence system trained on publicly available
tax law information. The content of this report does not constitute legal advice, tax advice, accounting
advice, or any other professional advice. ZeroTax AI is not a law firm, CPA firm, or financial advisory firm.
The information contained herein is for general informational and educational purposes only.

You should not rely on this report as a substitute for, and we strongly advise you to consult with, your
licensed tax attorney, certified public accountant, or other qualified professional before taking any action
based on information in this report. Your specific situation may differ materially from the general scenarios
analyzed in this report.
"""),
        ("2. ACCURACY AND CURRENCY OF INFORMATION", """
Tax laws change frequently. While ZeroTax AI incorporates information about the One Big Beautiful Bill Act
(OBBBA) and other recent legislation, the accuracy, completeness, or currency of any information in this
report is not guaranteed. Tax regulations are subject to interpretation, and the IRS, Treasury Department,
or courts may interpret relevant provisions differently than reflected herein.

IRC sections, contribution limits, income thresholds, and other numerical figures referenced in this report
are based on 2025 law as understood at the time of generation and may be subject to change. Always verify
current figures with official IRS publications or a qualified tax professional.
"""),
        ("3. SAVINGS ESTIMATES ARE NOT GUARANTEES", """
Any projected tax savings, dollar amounts, or percentage reductions stated in this report are estimates
based on the information you provided and general assumptions. Actual tax savings, if any, will depend on
your specific facts and circumstances, the accuracy of the information you provided, how strategies are
implemented, decisions made by the IRS upon examination, changes in applicable tax laws, and the professional
judgment of your licensed advisors.

ZeroTax AI makes no representation that any strategy discussed in this report will result in the estimated
savings or any savings at all. Past performance of similar strategies does not guarantee future results.
"""),
        ("4. IRS CIRCULAR 230 NOTICE", """
The tax information contained in this report was not intended or written to be used, and cannot be used,
for the purpose of (i) avoiding tax-related penalties under the Internal Revenue Code or (ii) promoting,
marketing, or recommending to another party any tax-related matter(s) addressed herein.

Pursuant to IRS Circular 230, any tax advice contained herein is not intended or written to be used, and
cannot be used, for the purposes of (1) avoiding penalties under the Internal Revenue Code or (2) promoting,
marketing or recommending to another party any transaction or tax-related matter(s) addressed herein.
"""),
        ("5. LISTED TRANSACTIONS AND HIGH-SCRUTINY STRATEGIES", """
Certain tax strategies have been designated as "listed transactions" or "transactions of interest" by the
IRS and require specific disclosure on Form 8886. Engaging in such transactions without proper disclosure
can result in substantial penalties. Before implementing any strategy described in this report, you should
consult with a qualified tax attorney to determine whether it constitutes a reportable transaction.

Strategies flagged in this report with risk scores of 7 or higher require careful review by qualified
professionals and may require additional documentation, legal opinions, or disclosures to withstand IRS scrutiny.
"""),
        ("6. STATE AND LOCAL TAX DISCLAIMER", """
This report focuses primarily on federal income tax strategies. State and local tax implications may vary
significantly by jurisdiction and may substantially affect the overall tax impact of any recommended strategy.
Some strategies that are advantageous for federal tax purposes may have neutral, negative, or complex
implications under applicable state and local tax laws.

ZeroTax AI's state-specific information is general in nature and may not reflect recent legislative or
regulatory changes in your state. Always consult a professional familiar with your state's specific tax laws.
"""),
        ("7. CONFIDENTIALITY AND DATA PRIVACY", """
This report is intended solely for the use of the individual or entity that commissioned it. It contains
confidential financial information and should be shared only with your trusted advisors. ZeroTax AI
processes financial data to generate this report and handles all data in accordance with our Privacy Policy.

We do not sell or share your financial data with third parties except as required to provide the service
or comply with legal obligations. For questions about data handling, contact privacy@zerotax.ai.
"""),
    ]

    for title, text in disclaimer_sections:
        story.append(Paragraph(title, ParagraphStyle("dt", fontName="Helvetica-Bold", fontSize=9, textColor=C_AMBER, spaceAfter=3, spaceBefore=8)))
        for para in text.strip().split("\n\n"):
            story.append(Paragraph(para.strip(), styles["Disclaimer"]))

    story.append(Spacer(1, 0.2 * inch))
    story.append(_hr(C_RED))
    story.append(Paragraph(
        f"Report generated by ZeroTax AI  •  {date.today().isoformat()}  •  "
        "For informational purposes only  •  Not legal or tax advice  •  "
        "Consult a licensed CPA or tax attorney before implementing any strategy.",
        styles["Footer"]
    ))

    return story


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def generate_pdf(result: dict, wizard_data: dict) -> bytes:
    """
    Generate a complete branded PDF report.

    Args:
        result:      AI analysis output dict.
        wizard_data: Raw wizard form data dict.

    Returns:
        PDF bytes suitable for st.download_button.
    """
    buf = io.BytesIO()
    styles = _build_styles()

    doc = BaseDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.55 * inch,
        title=f"ZeroTax AI — {wizard_data.get('business_name', 'Tax Report')}",
        author="ZeroTax AI",
        subject="Tax Optimization Analysis",
        creator="ZeroTax AI v1.0",
    )

    cover_frame  = Frame(0, 0, PAGE_W, PAGE_H, leftPadding=0.5*inch, rightPadding=0.5*inch, topPadding=0.3*inch, bottomPadding=0.3*inch)
    content_frame = Frame(0.5*inch, 0.5*inch, PAGE_W - inch, PAGE_H - 1.25*inch)

    doc.addPageTemplates([
        PageTemplate(id="cover",   frames=[cover_frame],   onPage=_cover_page_bg),
        PageTemplate(id="content", frames=[content_frame], onPage=_header_footer),
    ])

    story = []

    # Cover (uses 'cover' template)
    story += _build_cover(result, wizard_data, styles)

    # Switch to content template
    from reportlab.platypus import NextPageTemplate
    story.append(NextPageTemplate("content"))
    story.append(PageBreak())

    story += _build_executive_summary(result, styles)
    story.append(PageBreak())
    story += _build_charts_page(result, styles)
    story += _build_strategies(result, styles)
    story += _build_roadmap(result, styles)
    story += _build_state_portals(wizard_data, styles)
    story += _build_attorney_referral(styles)
    story += _build_disclaimer(styles)

    doc.build(story)
    buf.seek(0)
    return buf.read()
