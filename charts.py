"""ZeroTax AI — Plotly chart builders for the Streamlit UI."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Any

# ─── Theme ────────────────────────────────────────────────────────────────────

THEME = dict(
    bg_primary    = "#080a0f",
    bg_card       = "#13161e",
    bg_plot       = "#0d1117",
    accent_blue   = "#3b82f6",
    accent_emerald= "#10b981",
    accent_amber  = "#f59e0b",
    accent_red    = "#ef4444",
    accent_purple = "#8b5cf6",
    text_primary  = "#f1f5f9",
    text_muted    = "#64748b",
    grid_color    = "#1e2534",
    border        = "#1e2534",
)

PLOTLY_LAYOUT = dict(
    paper_bgcolor = THEME["bg_primary"],
    plot_bgcolor  = THEME["bg_plot"],
    font          = dict(family="Inter, sans-serif", color=THEME["text_primary"]),
    margin        = dict(l=20, r=20, t=40, b=20),
    legend        = dict(bgcolor="rgba(0,0,0,0)", bordercolor=THEME["border"]),
    xaxis         = dict(gridcolor=THEME["grid_color"], zerolinecolor=THEME["grid_color"]),
    yaxis         = dict(gridcolor=THEME["grid_color"], zerolinecolor=THEME["grid_color"]),
)


def _apply_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


# ─── Waterfall Chart ─────────────────────────────────────────────────────────

def waterfall_chart(result: dict) -> go.Figure:
    """Tax savings waterfall: current tax → each strategy → optimized tax."""
    current_tax   = result.get("current_estimated_tax", 0)
    optimized_tax = result.get("optimized_estimated_tax", 0)
    breakdown     = result.get("savings_breakdown", {})

    labels = ["Current Tax"]
    values = [current_tax]
    measures = ["absolute"]
    colors = ["#475569"]

    category_labels = {
        "entity_restructuring": "Entity Restructuring",
        "retirement_plans":     "Retirement Plans",
        "qbi_deduction":        "QBI Deduction §199A",
        "depreciation":         "Depreciation §168",
        "family_employment":    "Family Employment",
        "state_tax":            "State Tax Strategy",
        "other_deductions":     "Other Deductions",
    }
    palette = [
        THEME["accent_emerald"], THEME["accent_blue"],
        THEME["accent_purple"],  THEME["accent_amber"],
        "#06b6d4", "#f43f5e",    "#84cc16",
    ]

    for i, (key, label) in enumerate(category_labels.items()):
        saving = breakdown.get(key, 0)
        if saving > 0:
            labels.append(label)
            values.append(-saving)
            measures.append("relative")
            colors.append(palette[i % len(palette)])

    labels.append("Optimized Tax")
    values.append(optimized_tax)
    measures.append("absolute")
    colors.append(THEME["accent_blue"])

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        connector=dict(line=dict(color=THEME["border"], width=1, dash="dot")),
        increasing=dict(marker_color=THEME["accent_red"]),
        decreasing=dict(marker_color=THEME["accent_emerald"]),
        totals=dict(marker_color=THEME["accent_blue"]),
        textposition="outside",
        text=[f"${abs(v):,.0f}" for v in values],
        textfont=dict(color=THEME["text_primary"], size=11),
    ))

    total_saved = current_tax - optimized_tax
    fig.update_layout(
        title=dict(text=f"Tax Savings Waterfall  •  ${total_saved:,.0f} Annual Reduction", font=dict(size=16, color=THEME["text_primary"])),
        height=420,
        **PLOTLY_LAYOUT,
    )
    return fig


# ─── Strategy Bar Chart ───────────────────────────────────────────────────────

def strategy_bar_chart(strategies: list, max_items: int = 12) -> go.Figure:
    """Horizontal bar chart of top strategies by savings."""
    approved = [s for s in strategies if s.get("approved_for_report", True)]
    top = sorted(approved, key=lambda x: x.get("estimated_annual_savings", 0), reverse=True)[:max_items]

    names  = [s["name"][:45] + ("…" if len(s["name"]) > 45 else "") for s in top]
    savings = [s.get("estimated_annual_savings", 0) for s in top]
    risks  = [s.get("risk_score", 5) for s in top]

    color_map = {range(1, 4): THEME["accent_emerald"], range(4, 7): THEME["accent_blue"], range(7, 11): THEME["accent_amber"]}
    bar_colors = []
    for r in risks:
        if r <= 3:   bar_colors.append(THEME["accent_emerald"])
        elif r <= 6: bar_colors.append(THEME["accent_blue"])
        else:        bar_colors.append(THEME["accent_amber"])

    fig = go.Figure(go.Bar(
        y=names[::-1],
        x=savings[::-1],
        orientation="h",
        marker_color=bar_colors[::-1],
        text=[f"${s:,.0f}" for s in savings[::-1]],
        textposition="outside",
        textfont=dict(color=THEME["text_primary"], size=11),
        hovertemplate="<b>%{y}</b><br>Annual Savings: $%{x:,.0f}<extra></extra>",
    ))

    legend_items = [
        go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color=THEME["accent_emerald"]), name="Low Risk (1–3)"),
        go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color=THEME["accent_blue"]),    name="Med Risk (4–6)"),
        go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color=THEME["accent_amber"]),   name="High Risk (7+)"),
    ]
    for item in legend_items:
        fig.add_trace(item)

    fig.update_layout(
        title=dict(text="Annual Tax Savings by Strategy", font=dict(size=16, color=THEME["text_primary"])),
        height=max(350, 32 * len(top) + 80),
        xaxis_title="Annual Tax Savings ($)",
        showlegend=True,
        **PLOTLY_LAYOUT,
    )
    return fig


# ─── Scenario Comparison ─────────────────────────────────────────────────────

def scenario_chart(scenarios: list, current_tax: float) -> go.Figure:
    """Grouped bar comparing Conservative / Optimal / Aggressive scenarios."""
    if not scenarios:
        return go.Figure()

    labels     = ["Current Tax"] + [s.get("label", s.get("name", "")) for s in scenarios]
    tax_values = [current_tax]   + [current_tax - s.get("annual_savings", 0) for s in scenarios]
    savings    = [0]             + [s.get("annual_savings", 0) for s in scenarios]
    colors     = [THEME["text_muted"], THEME["accent_emerald"], THEME["accent_blue"], THEME["accent_purple"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Tax Owed",
        x=labels,
        y=tax_values,
        marker_color=colors,
        text=[f"${v:,.0f}" for v in tax_values],
        textposition="inside",
        textfont=dict(color="white", size=12),
        hovertemplate="<b>%{x}</b><br>Tax Owed: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Savings",
        x=labels,
        y=savings,
        marker_color=["rgba(0,0,0,0)"] + [c + "55" for c in colors[1:]],
        text=[""] + [f"Save ${v:,.0f}" for v in savings[1:]],
        textposition="outside",
        textfont=dict(color=THEME["accent_emerald"], size=11, family="Inter Bold"),
        hovertemplate="<b>%{x}</b><br>Annual Savings: $%{y:,.0f}<extra></extra>",
    ))

    fig.update_layout(
        barmode="overlay",
        title=dict(text="Scenario Comparison — Annual Tax Owed", font=dict(size=16, color=THEME["text_primary"])),
        height=380,
        **PLOTLY_LAYOUT,
    )
    return fig


# ─── Risk Matrix ─────────────────────────────────────────────────────────────

def risk_matrix_chart(strategies: list) -> go.Figure:
    """Bubble chart: savings vs. risk score, sized by complexity."""
    approved = [s for s in strategies if s.get("approved_for_report", True)]
    if not approved:
        return go.Figure()

    complexity_size = {"simple": 10, "medium": 16, "complex": 22, "attorney_required": 28}
    category_colors = {
        "entity_structure": THEME["accent_blue"],
        "retirement":       THEME["accent_emerald"],
        "depreciation":     THEME["accent_amber"],
        "deductions":       "#06b6d4",
        "real_estate":      "#8b5cf6",
        "estate_planning":  "#f43f5e",
        "family_employment":"#84cc16",
        "state_tax":        "#fb923c",
        "credits":          "#e879f9",
        "other":            THEME["text_muted"],
    }

    fig = go.Figure()

    for s in approved:
        cat = s.get("category", "other")
        fig.add_trace(go.Scatter(
            x=[s.get("risk_score", 5)],
            y=[s.get("estimated_annual_savings", 0)],
            mode="markers+text",
            marker=dict(
                size=complexity_size.get(s.get("complexity", "medium"), 16),
                color=category_colors.get(cat, THEME["text_muted"]),
                line=dict(color="white", width=1),
                opacity=0.85,
            ),
            text=[s["name"][:20] + ("…" if len(s["name"]) > 20 else "")],
            textposition="top center",
            textfont=dict(size=9, color=THEME["text_primary"]),
            hovertemplate=(
                f"<b>{s['name']}</b><br>"
                f"Annual Savings: ${s.get('estimated_annual_savings', 0):,.0f}<br>"
                f"Risk Score: {s.get('risk_score', 5)}/10<br>"
                f"Complexity: {s.get('complexity', 'medium')}<br>"
                f"Category: {cat}<extra></extra>"
            ),
            name=cat.replace("_", " ").title(),
            showlegend=False,
        ))

    # Add quadrant shading
    fig.add_vrect(x0=0, x1=4, fillcolor="rgba(16,185,129,0.05)", line_width=0, annotation_text="Low Risk", annotation_position="top left", annotation_font=dict(color=THEME["accent_emerald"], size=10))
    fig.add_vrect(x0=4, x1=7, fillcolor="rgba(59,130,246,0.05)", line_width=0, annotation_text="Med Risk", annotation_position="top left", annotation_font=dict(color=THEME["accent_blue"], size=10))
    fig.add_vrect(x0=7, x1=10, fillcolor="rgba(239,68,68,0.05)", line_width=0, annotation_text="High Risk", annotation_position="top left", annotation_font=dict(color=THEME["accent_red"], size=10))

    fig.update_layout(
        title=dict(text="Risk vs. Savings Matrix  (bubble size = complexity)", font=dict(size=15, color=THEME["text_primary"])),
        xaxis_title="IRS Risk Score (1=minimal → 10=listed transaction)",
        yaxis_title="Annual Tax Savings ($)",
        xaxis=dict(range=[0, 10.5], tickmode="linear", tick0=0, dtick=1, **PLOTLY_LAYOUT.get("xaxis", {})),
        height=440,
        **PLOTLY_LAYOUT,
    )
    return fig


# ─── Implementation Timeline ──────────────────────────────────────────────────

def roadmap_gantt(roadmap: list) -> go.Figure:
    """Gantt-style implementation timeline."""
    if not roadmap:
        return go.Figure()

    phase_colors = [THEME["accent_blue"], THEME["accent_emerald"], THEME["accent_amber"], THEME["accent_purple"]]
    phase_x = [(0, 30), (31, 90), (91, 365), (366, 730)]

    fig = go.Figure()
    for i, phase in enumerate(roadmap[:4]):
        x0, x1 = phase_x[i]
        color = phase_colors[i % len(phase_colors)]
        fig.add_trace(go.Bar(
            name=phase.get("title", f"Phase {i+1}"),
            x=[x1 - x0],
            y=[phase.get("title", f"Phase {i+1}")],
            base=[x0],
            orientation="h",
            marker_color=color,
            marker_line=dict(color="rgba(255,255,255,0.2)", width=1),
            text=[f"${phase.get('estimated_savings', 0):,.0f}/yr"],
            textposition="inside",
            textfont=dict(color="white", size=11),
            hovertemplate=(
                f"<b>{phase.get('title', '')}</b><br>"
                f"Timeframe: {phase.get('timeframe', '')}<br>"
                f"Strategies: {', '.join(phase.get('strategies', [])[:3])}<br>"
                f"Savings: ${phase.get('estimated_savings', 0):,.0f}/yr<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=dict(text="Implementation Roadmap", font=dict(size=16, color=THEME["text_primary"])),
        barmode="overlay",
        xaxis=dict(
            tickvals=[0, 30, 90, 180, 365, 548, 730],
            ticktext=["Day 0", "Day 30", "Day 90", "6 Mo", "Year 1", "18 Mo", "Year 2"],
            gridcolor=THEME["grid_color"],
        ),
        height=280,
        **PLOTLY_LAYOUT,
    )
    return fig


# ─── Savings Gauge ────────────────────────────────────────────────────────────

def savings_gauge(projected_savings: float, current_tax: float) -> go.Figure:
    """Gauge showing % tax reduction achieved."""
    pct = min(100, round(projected_savings / max(current_tax, 1) * 100, 1))

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=pct,
        domain=dict(x=[0, 1], y=[0, 1]),
        title=dict(text="Tax Reduction %", font=dict(size=18, color=THEME["text_primary"])),
        delta=dict(reference=15, increasing=dict(color=THEME["accent_emerald"])),
        number=dict(suffix="%", font=dict(size=36, color=THEME["text_primary"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor="white"),
            bar=dict(color=THEME["accent_emerald"]),
            bgcolor=THEME["bg_card"],
            borderwidth=2,
            bordercolor=THEME["border"],
            steps=[
                dict(range=[0, 15],  color=THEME["bg_plot"]),
                dict(range=[15, 30], color="rgba(59,130,246,0.1)"),
                dict(range=[30, 60], color="rgba(16,185,129,0.1)"),
                dict(range=[60, 100],color="rgba(16,185,129,0.2)"),
            ],
            threshold=dict(line=dict(color=THEME["accent_amber"], width=3), thickness=0.75, value=30),
        ),
    ))
    fig.update_layout(height=260, **PLOTLY_LAYOUT)
    return fig


# ─── 10-Year Projection ───────────────────────────────────────────────────────

def ten_year_projection(current_tax: float, optimized_tax: float) -> go.Figure:
    """Area chart showing cumulative savings over 10 years."""
    years = list(range(0, 11))
    current_cumulative  = [current_tax * y for y in years]
    optimized_cumulative = [optimized_tax * y for y in years]
    savings_cumulative  = [c - o for c, o in zip(current_cumulative, optimized_cumulative)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=current_cumulative,
        name="Without ZeroTax", mode="lines",
        line=dict(color=THEME["accent_red"], width=2, dash="dash"),
        fill=None,
    ))
    fig.add_trace(go.Scatter(
        x=years, y=optimized_cumulative,
        name="With ZeroTax", mode="lines",
        line=dict(color=THEME["accent_emerald"], width=3),
        fill="tonexty",
        fillcolor="rgba(16,185,129,0.12)",
    ))
    fig.add_trace(go.Scatter(
        x=years, y=savings_cumulative,
        name="Cumulative Savings", mode="lines+markers",
        line=dict(color=THEME["accent_blue"], width=2),
        marker=dict(size=6, color=THEME["accent_blue"]),
        yaxis="y2",
    ))

    fig.update_layout(
        title=dict(text="10-Year Tax Trajectory", font=dict(size=16, color=THEME["text_primary"])),
        xaxis_title="Year",
        yaxis_title="Cumulative Tax Paid ($)",
        yaxis2=dict(title="Cumulative Savings ($)", overlaying="y", side="right", showgrid=False, color=THEME["accent_blue"]),
        height=380,
        **PLOTLY_LAYOUT,
    )
    return fig
