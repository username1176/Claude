"""
GenomeInsight — Interactive Preview
====================================
Streamlit app showcasing the cross-domain health-tech platform.
Wabi Sabi aesthetic: earth tones, organic textures, serene typography.
Run:  streamlit run streamlit_app.py
"""

import sys
import os
import json

# ---------------------------------------------------------------------------
# Ensure backend is on the path so we can import the real correlator engine
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import streamlit as st
import pandas as pd

# Import the actual engine
from app.utils.correlator import (
    CorrelationInsight,
    DomainSummary,
    UnifiedAnalysisResult,
    run_full_unified_analysis,
    run_unified_correlation,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GenomeInsight",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Wabi Sabi CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500&family=Noto+Serif+JP:wght@300;400;500&display=swap');

    /* ── Global ── */
    .stApp {
        background: #F5F5F0;
        font-family: 'Inter', sans-serif;
    }

    /* ── Linen texture overlay ── */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(139, 154, 127, 0.03) 2px,
            rgba(139, 154, 127, 0.03) 4px
        );
        pointer-events: none;
        z-index: 0;
    }

    /* ── Headers ── */
    .main-header {
        font-family: 'Crimson Text', serif;
        font-size: 2.6rem;
        font-weight: 600;
        color: #5C4B3F;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }
    .sub-header {
        font-family: 'Crimson Text', serif;
        font-style: italic;
        font-size: 1.15rem;
        color: #A8A8A8;
        margin-bottom: 2rem;
        line-height: 1.6;
    }

    /* ── Wabi Card ── */
    .wabi-card {
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(139, 154, 127, 0.2);
        border-radius: 12px 4px 12px 4px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        transition: all 0.4s ease;
    }
    .wabi-card:hover {
        box-shadow: 0 4px 20px rgba(92, 75, 63, 0.08);
    }

    /* ── Insight cards ── */
    .insight-card {
        background: rgba(245, 245, 240, 0.8);
        backdrop-filter: blur(6px);
        border-left: 3px solid #8B9A7F;
        border-radius: 2px 8px 8px 2px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        font-family: 'Inter', sans-serif;
    }
    .insight-card-warning {
        background: rgba(196, 168, 130, 0.12);
        backdrop-filter: blur(6px);
        border-left: 3px solid #C4A882;
        border-radius: 2px 8px 8px 2px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }
    .insight-card-danger {
        background: rgba(160, 120, 110, 0.1);
        backdrop-filter: blur(6px);
        border-left: 3px solid #A0786E;
        border-radius: 2px 8px 8px 2px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }

    .insight-title {
        font-family: 'Crimson Text', serif;
        font-size: 1.05rem;
        font-weight: 600;
        color: #5C4B3F;
    }
    .insight-meta {
        font-size: 0.78rem;
        color: #A8A8A8;
        font-family: 'Inter', sans-serif;
    }
    .insight-body {
        font-size: 0.9rem;
        color: #6B6B6B;
        line-height: 1.6;
        margin-top: 0.4rem;
    }

    /* ── Metric boxes ── */
    .metric-box {
        background: rgba(255, 255, 255, 0.5);
        border: 1px solid rgba(139, 154, 127, 0.15);
        border-radius: 8px 2px 8px 2px;
        padding: 1rem;
        text-align: center;
    }

    /* ── Domain badges ── */
    .domain-badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 500;
        font-family: 'Inter', sans-serif;
        margin-right: 0.3rem;
        letter-spacing: 0.02em;
    }
    .badge-genome      { background: rgba(160, 180, 194, 0.25); color: #5C7A8A; }
    .badge-blood       { background: rgba(160, 120, 110, 0.2);  color: #8A5C52; }
    .badge-epigenetics { background: rgba(139, 154, 127, 0.2);  color: #5C6B52; }
    .badge-microbiome  { background: rgba(196, 168, 130, 0.25); color: #7A6B52; }
    .badge-wearable    { background: rgba(168, 168, 168, 0.2);  color: #6B6B6B; }

    /* ── Disclaimer ── */
    .wabi-disclaimer {
        background: rgba(139, 154, 127, 0.08);
        border: 1px solid rgba(139, 154, 127, 0.15);
        border-radius: 4px 12px 4px 12px;
        padding: 1rem 1.2rem;
        font-family: 'Crimson Text', serif;
        font-style: italic;
        font-size: 0.9rem;
        color: #7A7A6B;
        line-height: 1.7;
    }

    /* ── Ink-wash divider ── */
    .ink-divider {
        height: 1px;
        background: linear-gradient(90deg,
            transparent 0%,
            rgba(139, 154, 127, 0.3) 20%,
            rgba(92, 75, 63, 0.2) 50%,
            rgba(139, 154, 127, 0.3) 80%,
            transparent 100%
        );
        margin: 1.5rem 0;
        border: none;
    }

    /* ── Wavy SVG separator ── */
    .wabi-wave {
        width: 100%;
        height: 24px;
        margin: 1rem 0;
    }
    .wabi-wave svg {
        width: 100%;
        height: 100%;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: rgba(245, 245, 240, 0.95);
        border-right: 1px solid rgba(139, 154, 127, 0.15);
    }
    [data-testid="stSidebar"] .stMarkdown h2 {
        font-family: 'Crimson Text', serif;
        color: #5C4B3F;
        letter-spacing: -0.01em;
    }

    /* ── Streamlit overrides ── */
    .stMetricLabel { font-family: 'Inter', sans-serif !important; }
    .stMetricValue { font-family: 'Crimson Text', serif !important; color: #5C4B3F !important; }

    h1, h2, h3 {
        font-family: 'Crimson Text', serif !important;
        color: #5C4B3F !important;
    }

    .stDataFrame {
        border-radius: 8px 2px 8px 2px;
        overflow: hidden;
    }

    /* ── Code block ── */
    .stCodeBlock {
        border-radius: 4px 12px 4px 12px;
        border: 1px solid rgba(139, 154, 127, 0.15);
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        font-family: 'Crimson Text', serif;
        color: #5C4B3F;
    }

    /* ── Footer ── */
    .wabi-footer {
        font-family: 'Crimson Text', serif;
        font-style: italic;
        font-size: 0.85rem;
        color: #A8A8A8;
        text-align: center;
        padding: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
#  Sample data (same fixtures used in our 385-test suite)
# ═══════════════════════════════════════════════════════════════════════════

SAMPLE_VARIANTS = [
    {"rsid": "rs9939609", "gene": "FTO", "genotype": "AT", "risk_level": "elevated"},
    {"rsid": "rs4680", "gene": "COMT", "genotype": "AG", "risk_level": "elevated"},
    {"rsid": "rs4988235", "gene": "LCT/MCM6", "genotype": "CC", "risk_level": "elevated"},
    {"rsid": "rs2066844", "gene": "NOD2", "genotype": "CT", "risk_level": "elevated"},
    {"rsid": "rs1801133", "gene": "MTHFR", "genotype": "CT", "risk_level": "elevated"},
]

SAMPLE_BLOOD_MARKERS = [
    {"marker_name": "hemoglobin_a1c", "value": 6.0, "unit": "%", "flag": "H"},
    {"marker_name": "hs_crp", "value": 4.5, "unit": "mg/L", "flag": "H"},
    {"marker_name": "calcium", "value": 7.5, "unit": "mg/dL", "flag": "L"},
    {"marker_name": "vitamin_d", "value": 15.0, "unit": "ng/mL", "flag": "L"},
    {"marker_name": "cholesterol_ldl", "value": 180, "unit": "mg/dL", "flag": "H"},
]

SAMPLE_WEARABLE = [
    {"data_type": "activity", "date": "2026-02-28",
     "summary": {"steps": 3500, "active_minutes": 12, "calories_burned": 1700}},
    {"data_type": "sleep", "date": "2026-02-28",
     "summary": {"total_sleep_minutes": 310, "deep_sleep_minutes": 30}},
    {"data_type": "stress", "date": "2026-02-28",
     "summary": {"stress_score": 75}},
    {"data_type": "hrv", "date": "2026-02-28",
     "summary": {"avg_hrv_ms": 22}},
]

SAMPLE_MICROBIOME = {
    "enterotype": "Bacteroides",
    "diversity": {"shannon": 2.2, "simpson": 0.70, "chao1": 70, "observed_otus": 25},
    "composition": {
        "phylum": [
            {"name": "Firmicutes", "abundance": 0.55},
            {"name": "Bacteroidetes", "abundance": 0.12},
            {"name": "Proteobacteria", "abundance": 0.20},
            {"name": "Actinobacteria", "abundance": 0.04},
            {"name": "Verrucomicrobia", "abundance": 0.05},
            {"name": "Other", "abundance": 0.04},
        ],
        "genus": [
            {"name": "Bacteroides", "abundance": 0.10},
            {"name": "Bifidobacterium", "abundance": 0.008},
            {"name": "Faecalibacterium", "abundance": 0.015},
            {"name": "Lactobacillus", "abundance": 0.003},
            {"name": "Roseburia", "abundance": 0.05},
            {"name": "Prevotella", "abundance": 0.04},
            {"name": "Akkermansia", "abundance": 0.03},
            {"name": "Ruminococcus", "abundance": 0.06},
        ],
    },
}

SAMPLE_EPIGENETIC_OVERLAYS = [
    {"gene": "TNF", "region": "promoter", "modification": "hypomethylated"},
    {"gene": "NOD2", "region": "enhancer", "modification": "H3K27ac"},
    {"gene": "SLC6A4", "region": "promoter", "modification": "hypermethylated"},
    {"gene": "MTHFR", "region": "exon1", "modification": "hypomethylated"},
    {"gene": "IL6", "region": "promoter", "modification": "hypomethylated"},
]


# ═══════════════════════════════════════════════════════════════════════════
#  Sidebar — organic, minimal
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## GenomeInsight")
    st.caption("_A quiet lens into your biology_")

    st.markdown('<div class="ink-divider"></div>', unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        [
            "Overview",
            "Genome & Blood",
            "Microbiome",
            "Epigenetics & Wearables",
            "Cross-Domain Engine",
            "Unified Report",
            "Architecture",
        ],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown('<div class="ink-divider"></div>', unsafe_allow_html=True)
    st.markdown("**Data Domains**")
    enable_genome = st.toggle("Genome variants", value=True)
    enable_blood = st.toggle("Blood markers", value=True)
    enable_microbiome = st.toggle("Microbiome profile", value=True)
    enable_epigenetics = st.toggle("Epigenetic overlays", value=True)
    enable_wearable = st.toggle("Wearable data", value=True)

    st.markdown('<div class="ink-divider"></div>', unsafe_allow_html=True)
    st.caption("_385 tests passing_")
    st.caption("_20 integration tests_")


# ═══════════════════════════════════════════════════════════════════════════
#  Helper functions
# ═══════════════════════════════════════════════════════════════════════════

def ink_divider():
    st.markdown('<div class="ink-divider"></div>', unsafe_allow_html=True)


def wave_divider():
    st.markdown(
        '<div class="wabi-wave">'
        '<svg viewBox="0 0 1200 24" preserveAspectRatio="none">'
        '<path d="M0,12 C150,24 350,0 600,12 C850,24 1050,0 1200,12" '
        'fill="none" stroke="rgba(139,154,127,0.25)" stroke-width="1"/>'
        '</svg></div>',
        unsafe_allow_html=True,
    )


def domain_badges(sources: list[str]) -> str:
    badge_map = {
        "genome": "badge-genome",
        "blood": "badge-blood",
        "epigenetics": "badge-epigenetics",
        "microbiome": "badge-microbiome",
        "wearable": "badge-wearable",
    }
    return " ".join(
        f'<span class="domain-badge {badge_map.get(s, "")}">{s}</span>'
        for s in sources
    )


def priority_color(priority: int) -> str:
    if priority >= 80:
        return "insight-card-danger"
    elif priority >= 60:
        return "insight-card-warning"
    return "insight-card"


def render_insight_card(insight: CorrelationInsight):
    css_class = priority_color(insight.priority)
    badges = domain_badges(insight.data_sources)
    st.markdown(
        f"""<div class="{css_class}">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="insight-title">{insight.title}</span>
            <span class="insight-meta">
                Priority {insight.priority} · {insight.confidence}
            </span>
        </div>
        <div style="margin: 0.4rem 0;">{badges}</div>
        <p class="insight-body">{insight.body}</p>
        </div>""",
        unsafe_allow_html=True,
    )


def get_active_data():
    v = SAMPLE_VARIANTS if enable_genome else []
    b = SAMPLE_BLOOD_MARKERS if enable_blood else []
    w = SAMPLE_WEARABLE if enable_wearable else []
    m = SAMPLE_MICROBIOME if enable_microbiome else None
    e = SAMPLE_EPIGENETIC_OVERLAYS if enable_epigenetics else None
    return v, b, w, m, e


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Overview
# ═══════════════════════════════════════════════════════════════════════════

if page == "Overview":
    st.markdown('<div class="main-header">GenomeInsight</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        "Where your biology whispers its story — genome, blood, epigenetics, "
        "microbiome, and wearable rhythms woven into quiet understanding."
        "</div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Domains", "5", help="Genome, Blood, Epigenetics, Microbiome, Wearables")
    with col2:
        st.metric("Correlations", "9", help="Multi-domain interaction rules")
    with col3:
        st.metric("Tests", "385", delta="20 new")
    with col4:
        st.metric("Endpoints", "35+", help="RESTful API with JWT auth")
    with col5:
        st.metric("Tasks", "4", help="Celery Beat periodic tasks")

    wave_divider()

    st.subheader("What Lives Here")
    left, right = st.columns(2)
    with left:
        st.markdown("""
        **Core Platform**
        - Flask REST API with SQLAlchemy models
        - React 18 SPA — Wabi Sabi aesthetic
        - AES-256-GCM envelope encryption
        - JWT auth with refresh tokens
        - Celery async task pipeline

        **Genome Analysis**
        - VCF file parsing (23andMe, AncestryDNA, Nebula)
        - ClinVar / Ensembl / GWAS annotation
        - Risk category scoring

        **Blood Test Tracking**
        - PDF / CSV auto-parsing
        - 60+ biomarkers with delta tracking
        - Trend visualization over time
        """)
    with right:
        st.markdown("""
        **Microbiome Analysis**
        - BIOM / OTU CSV / FASTQ file support
        - Shannon, Simpson, Chao1 diversity
        - Enterotype classification
        - Phyla ratios & F/B ratio
        - Cross-domain correlations

        **Epigenetics**
        - BED / CSV methylation data
        - ENCODE & Roadmap annotation
        - Genome variant cross-reference

        **Wearables**
        - Terra API (Fitbit, Garmin, Oura, WHOOP, Polar)
        - Activity, sleep, HRV, SpO2, stress
        """)

    wave_divider()

    st.subheader("Recent Work")
    st.markdown("""
    | Change | Details |
    |--------|---------|
    | **2 new correlator rules** | `gut_axis_methylation` and `mthfr_gut_methylation` |
    | **Stale-check task** | Daily Celery Beat re-triggers when new data arrives |
    | **Disclaimers** | Microbiome-specific warnings in `UnifiedAnalysisResult` |
    | **20 integration tests** | Correlator rules, stale-check, API routes |
    | **Wabi Sabi redesign** | Earth tones, organic textures, serene typography |
    """)


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Genome & Blood
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Genome & Blood":
    st.markdown('<div class="main-header">Genome & Blood</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        "The quiet code written in your DNA, reflected in your bloodstream."
        "</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        st.subheader("Genome Variants")
        if enable_genome:
            df_v = pd.DataFrame(SAMPLE_VARIANTS)
            df_v.columns = ["rsID", "Gene", "Genotype", "Risk Level"]
            st.dataframe(df_v, use_container_width=True, hide_index=True)
            st.markdown(
                '<div class="wabi-disclaimer">'
                "These variants interact with microbiome, epigenetic, and blood "
                "data through our cross-domain correlation engine."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Genome data is resting. Enable it in the sidebar.")

    with right:
        st.subheader("Blood Markers")
        if enable_blood:
            df_b = pd.DataFrame(SAMPLE_BLOOD_MARKERS)
            df_b.columns = ["Marker", "Value", "Unit", "Flag"]
            st.dataframe(df_b, use_container_width=True, hide_index=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("HbA1c", "6.0%", delta="High", delta_color="inverse")
            with col2:
                st.metric("Vitamin D", "15 ng/mL", delta="Low", delta_color="inverse")
            with col3:
                st.metric("hs-CRP", "4.5 mg/L", delta="High", delta_color="inverse")
        else:
            st.info("Blood data is resting. Enable it in the sidebar.")


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Microbiome
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Microbiome":
    st.markdown('<div class="main-header">Microbiome</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        "The garden within — trillions of companions shaping your health."
        "</div>",
        unsafe_allow_html=True,
    )

    if not enable_microbiome:
        st.info("Microbiome data is resting. Enable it in the sidebar.")
    else:
        m = SAMPLE_MICROBIOME

        st.subheader("Alpha Diversity")
        c1, c2, c3, c4 = st.columns(4)
        div = m["diversity"]
        with c1:
            st.metric("Shannon", f"{div['shannon']:.2f}", delta="Low (<3.0)", delta_color="inverse")
        with c2:
            st.metric("Simpson", f"{div['simpson']:.2f}")
        with c3:
            st.metric("Chao1", str(div["chao1"]))
        with c4:
            st.metric("Enterotype", m["enterotype"])

        ink_divider()

        left, right = st.columns(2)
        with left:
            st.subheader("Phylum Composition")
            phylum_data = pd.DataFrame(m["composition"]["phylum"])
            phylum_data.columns = ["Phylum", "Relative Abundance"]
            chart_data = phylum_data.set_index("Phylum")
            st.bar_chart(chart_data, color="#8B9A7F")

            firmicutes = next((p["abundance"] for p in m["composition"]["phylum"] if p["name"] == "Firmicutes"), 0)
            bacteroidetes = next((p["abundance"] for p in m["composition"]["phylum"] if p["name"] == "Bacteroidetes"), 0)
            fb_ratio = firmicutes / bacteroidetes if bacteroidetes > 0 else 0
            st.metric("F/B Ratio", f"{fb_ratio:.2f}",
                      delta="Elevated (>3)" if fb_ratio > 3 else "Normal",
                      delta_color="inverse" if fb_ratio > 3 else "normal")

        with right:
            st.subheader("Genus Abundance")
            genus_data = pd.DataFrame(m["composition"]["genus"])
            genus_data.columns = ["Genus", "Relative Abundance"]
            chart_data_g = genus_data.set_index("Genus")
            st.bar_chart(chart_data_g, horizontal=True, color="#C4A882")

        ink_divider()

        st.subheader("Key Genera")
        genus_df = pd.DataFrame(m["composition"]["genus"])
        genus_df.columns = ["Genus", "Abundance"]
        genus_df["Abundance %"] = (genus_df["Abundance"] * 100).round(2)
        genus_df["Status"] = genus_df.apply(
            lambda row: (
                "Low" if row["Genus"] in ("Bifidobacterium", "Lactobacillus", "Faecalibacterium") and row["Abundance"] < 0.02
                else "Normal"
            ),
            axis=1,
        )
        st.dataframe(genus_df[["Genus", "Abundance %", "Status"]], use_container_width=True, hide_index=True)

        st.markdown(
            '<div class="wabi-disclaimer">'
            "Microbiome analysis is an emerging science. Results vary by sampling method, "
            "timing, diet, and medication. A single sample provides a snapshot, not a "
            "definitive assessment — like observing a garden on one morning."
            "</div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Epigenetics & Wearables
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Epigenetics & Wearables":
    st.markdown('<div class="main-header">Epigenetics & Wearables</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        "The marks above your genes and the rhythms of your daily life."
        "</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        st.subheader("Epigenetic Overlays")
        if enable_epigenetics:
            df_e = pd.DataFrame(SAMPLE_EPIGENETIC_OVERLAYS)
            df_e.columns = ["Gene", "Region", "Modification"]
            st.dataframe(df_e, use_container_width=True, hide_index=True)
            st.markdown(
                '<div class="wabi-disclaimer">'
                "These overlays are cross-referenced with genome variants and microbiome data — "
                "layers upon layers of biological memory."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Epigenetic data is resting. Enable it in the sidebar.")

    with right:
        st.subheader("Wearable Rhythms")
        if enable_wearable:
            for w in SAMPLE_WEARABLE:
                with st.expander(f"{w['data_type'].title()} — {w['date']}"):
                    for key, val in w["summary"].items():
                        label = key.replace("_", " ").title()
                        st.metric(label, str(val))
        else:
            st.info("Wearable data is resting. Enable it in the sidebar.")


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Cross-Domain Engine
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Cross-Domain Engine":
    st.markdown('<div class="main-header">Cross-Domain Correlations</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        "Where separate streams of data converge — patterns emerge from the quiet interplay "
        "of genome, blood, gut, epigenetics, and daily rhythm."
        "</div>",
        unsafe_allow_html=True,
    )

    variants, blood, wearable, microbiome, epigenetics = get_active_data()

    active_count = sum([
        bool(variants), bool(blood), bool(wearable),
        microbiome is not None, epigenetics is not None,
    ])
    st.caption(f"_Running engine with {active_count}/5 data domains active._")

    correlations = run_unified_correlation(
        user_variants=variants,
        blood_markers=blood,
        wearable_summaries=wearable,
        microbiome_profile=microbiome,
        epigenetic_overlays=epigenetics,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Insights", len(correlations))
    with c2:
        high_priority = len([c for c in correlations if c.priority >= 80])
        st.metric("High Priority", high_priority)
    with c3:
        categories = set(c.category for c in correlations)
        st.metric("Categories", len(categories))
    with c4:
        all_sources = set()
        for c in correlations:
            all_sources.update(c.data_sources)
        st.metric("Domains Used", len(all_sources))

    wave_divider()

    correlations_sorted = sorted(correlations, key=lambda c: c.priority, reverse=True)

    for insight in correlations_sorted:
        render_insight_card(insight)
        if insight.recommendations:
            with st.expander("Recommendations"):
                for rec in insight.recommendations:
                    st.markdown(f"- {rec}")

    if not correlations:
        st.caption("_No correlations to show. Enable more data domains in the sidebar._")


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Unified Report
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Unified Report":
    st.markdown('<div class="main-header">Unified Health Report</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        "Weaving your health tapestry — domain summaries, cross-domain insights, "
        "and a quiet narrative of your biological landscape."
        "</div>",
        unsafe_allow_html=True,
    )

    variants, blood, wearable, microbiome, epigenetics = get_active_data()

    result = run_full_unified_analysis(
        user_id="demo-user",
        user_variants=variants,
        blood_markers=blood,
        wearable_summaries=wearable,
        microbiome_profile=microbiome,
        epigenetic_overlays=epigenetics,
    )

    # Domain status
    st.subheader("Domain Status")
    cols = st.columns(5)
    domain_labels = {
        "genome": "Genome", "blood": "Blood", "epigenetics": "Epigenetics",
        "microbiome": "Microbiome", "wearable": "Wearables"
    }
    for i, domain in enumerate(result.domains):
        with cols[i]:
            st.markdown(f"**{domain_labels.get(domain.domain, domain.domain)}**")
            if domain.status == "available":
                st.success("Available")
            else:
                st.error("Unavailable")
            if domain.metrics:
                for k, v in list(domain.metrics.items())[:3]:
                    st.caption(f"{k}: {v}")

    ink_divider()

    st.subheader("Narrative")
    st.markdown(f"_{result.ai_narrative}_")

    ink_divider()

    st.subheader(f"Cross-Domain Insights ({len(result.correlations)})")
    for insight in sorted(result.correlations, key=lambda c: c.priority, reverse=True):
        render_insight_card(insight)

    ink_divider()

    st.subheader("A Mindful Note")
    st.markdown(
        f'<div class="wabi-disclaimer">{result.disclaimer}</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Raw JSON"):
        st.json(result.to_dict())


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Architecture
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Architecture":
    st.markdown('<div class="main-header">Architecture</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        "The structure beneath — how the pieces fit together."
        "</div>",
        unsafe_allow_html=True,
    )

    st.code("""
GenomeInsight/
├── backend/                  # Flask REST API
│   ├── app/
│   │   ├── api/              # Blueprints (auth, genome, blood, epigenetics,
│   │   │                     #   wearables, microbiome, analysis)
│   │   ├── models/           # SQLAlchemy models
│   │   ├── services/         # Genome analyzer, report generator, encryption
│   │   ├── tasks/            # Celery async tasks
│   │   └── utils/            # VCF parser, blood parser, correlator
│   ├── tests/                # 385 tests
│   ├── celery_worker.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # React 18 — Wabi Sabi aesthetic
│   ├── src/
│   │   ├── components/       # Dashboard, Upload, Report, Wearables,
│   │   │                     #   Microbiome, UnifiedReport
│   │   ├── theme/            # wabiSabi.js — MUI earth-tone theme
│   │   ├── contexts/         # AuthContext (JWT)
│   │   └── services/         # Axios API client
│   ├── tailwind.config.js    # Custom Wabi Sabi palette
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml        # 5 services
├── streamlit_app.py          # This preview
└── .env.example
    """, language="text")

    wave_divider()

    st.subheader("Scheduled Tasks")
    tasks_data = [
        {"Task": "sync_all_active_connections", "Schedule": "Every 6 hours",
         "Queue": "wearables", "Description": "Pull wearable data from Terra API"},
        {"Task": "generate_daily_insights", "Schedule": "Daily 02:30 UTC",
         "Queue": "insights", "Description": "Cross-domain insight generation"},
        {"Task": "schedule_weekly_reanalysis", "Schedule": "Monday 03:00 UTC",
         "Queue": "analysis", "Description": "Re-run microbiome correlations"},
        {"Task": "check_and_reanalyze_stale", "Schedule": "Daily 04:00 UTC",
         "Queue": "analysis", "Description": "Re-analyze when new data arrives"},
    ]
    st.dataframe(pd.DataFrame(tasks_data), use_container_width=True, hide_index=True)

    wave_divider()

    st.subheader("Correlation Rules")
    rules_data = [
        {"ID": "lactose_triad", "Domains": "genome + microbiome + blood",
         "Trigger": "LCT/MCM6 CC + low Lactobacillus + low Calcium"},
        {"ID": "fto_obesity_loop", "Domains": "genome + microbiome + wearable",
         "Trigger": "FTO variant + high F/B ratio + <5000 steps"},
        {"ID": "comt_stress_gut", "Domains": "genome + microbiome + wearable",
         "Trigger": "COMT variant + low diversity + high stress"},
        {"ID": "inflammation_cascade", "Domains": "epigenetics + microbiome + blood",
         "Trigger": "TNF/IL6 hypomethylated + high Proteobacteria + high CRP"},
        {"ID": "sugar_gut_disruption", "Domains": "blood + microbiome + wearable",
         "Trigger": "High HbA1c + low Bifidobacterium + low activity"},
        {"ID": "crohns_risk_triad", "Domains": "genome + epigenetics + microbiome",
         "Trigger": "NOD2 variant + epigenetic overlay + low Faecalibacterium"},
        {"ID": "gut_axis_methylation", "Domains": "epigenetics + microbiome + blood",
         "Trigger": "SLC6A4 epigenetic + low diversity + low Vitamin D"},
        {"ID": "mthfr_gut_methylation", "Domains": "genome + microbiome + epigenetics",
         "Trigger": "MTHFR variant + low Bifidobacterium + MTHFR epigenetic"},
        {"ID": "sleep_gut_cycle", "Domains": "wearable + microbiome",
         "Trigger": "Poor sleep + low HRV + low diversity"},
    ]
    st.dataframe(pd.DataFrame(rules_data), use_container_width=True, hide_index=True)

    wave_divider()

    st.subheader("API Endpoints (35+)")
    api_sections = {
        "Auth (4)": "register, login, refresh, logout",
        "Genome (7)": "upload, list, analysis, risks, recommendations, report, variants",
        "Blood (5)": "upload, list, history, analyze-changes, trends",
        "Epigenetics (8)": "upload, list, detail, delete, analysis, regions, genome-overlay, re-analyze",
        "Microbiome (10)": "upload, list, detail, delete, analysis, taxa, composition, genome-correlation, re-analyze, full-analysis",
        "Wearables (8)": "providers, connect, callback, connections, disconnect, sync, data, latest",
        "Insights (3)": "daily, history, generate",
        "Unified Analysis (2)": "daily, generate",
    }
    for section, endpoints in api_sections.items():
        st.markdown(f"**{section}**: {endpoints}")

    wave_divider()

    st.subheader("Security")
    st.markdown("""
    - AES-256-GCM envelope encryption for all files and OAuth tokens
    - JWT access + refresh tokens with configurable expiry
    - CORS configured per-environment
    - Rate limiting (5/hr genome, 10/hr blood, 10/hr microbiome)
    - Filename sanitization against path traversal
    - Security headers (X-Content-Type-Options, X-Frame-Options, HSTS)
    """)


# ═══════════════════════════════════════════════════════════════════════════
#  Footer
# ═══════════════════════════════════════════════════════════════════════════

wave_divider()
st.markdown(
    '<div class="wabi-footer">'
    "GenomeInsight is for informational and educational purposes only. "
    "Not medical advice — consult a qualified healthcare provider."
    "<br><br>"
    "Like all things, this too shall change."
    "</div>",
    unsafe_allow_html=True,
)
