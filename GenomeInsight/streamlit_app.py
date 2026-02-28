"""
GenomeInsight — Interactive Preview
====================================
Streamlit app showcasing the cross-domain health-tech platform.
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
    page_title="GenomeInsight — Preview",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main-header {font-size: 2.4rem; font-weight: 700; margin-bottom: 0.2rem;}
    .sub-header  {font-size: 1.1rem; color: #6b7280; margin-bottom: 1.5rem;}
    .insight-card {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-left: 4px solid #0284c7;
        padding: 1rem 1.2rem;
        border-radius: 0.5rem;
        margin-bottom: 0.8rem;
    }
    .insight-card-warning {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border-left: 4px solid #d97706;
    }
    .insight-card-danger {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border-left: 4px solid #dc2626;
    }
    .metric-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
    }
    .disclaimer-box {
        background: #fefce8;
        border: 1px solid #fde68a;
        border-radius: 0.5rem;
        padding: 1rem;
        font-size: 0.85rem;
        color: #713f12;
    }
    .domain-badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.3rem;
    }
    .badge-genome      {background: #dbeafe; color: #1e40af;}
    .badge-blood       {background: #fee2e2; color: #991b1b;}
    .badge-epigenetics {background: #e0e7ff; color: #3730a3;}
    .badge-microbiome  {background: #d1fae5; color: #065f46;}
    .badge-wearable    {background: #fce7f3; color: #9d174d;}
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
#  Sidebar
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## GenomeInsight")
    st.caption("Privacy-first cross-domain health analysis")
    st.divider()

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
    )

    st.divider()
    st.markdown("**Data Domains**")
    enable_genome = st.toggle("Genome variants", value=True)
    enable_blood = st.toggle("Blood markers", value=True)
    enable_microbiome = st.toggle("Microbiome profile", value=True)
    enable_epigenetics = st.toggle("Epigenetic overlays", value=True)
    enable_wearable = st.toggle("Wearable data", value=True)

    st.divider()
    st.caption("385 backend tests passing")
    st.caption("20 integration tests")


# ═══════════════════════════════════════════════════════════════════════════
#  Helper functions
# ═══════════════════════════════════════════════════════════════════════════

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
            <strong>{insight.title}</strong>
            <span style="font-size:0.8rem; color:#6b7280;">
                Priority {insight.priority} | {insight.confidence} confidence
            </span>
        </div>
        <div style="margin: 0.4rem 0;">{badges}</div>
        <p style="margin: 0.5rem 0; font-size: 0.92rem;">{insight.body}</p>
        </div>""",
        unsafe_allow_html=True,
    )


def get_active_data():
    """Return data based on sidebar toggles."""
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
        '<div class="sub-header">Privacy-first health-tech platform analyzing '
        "genome, blood, epigenetic, microbiome, and wearable data for "
        "personalized cross-domain health insights.</div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Data Domains", "5", help="Genome, Blood, Epigenetics, Microbiome, Wearables")
    with col2:
        st.metric("Correlation Rules", "9", help="Multi-domain interaction rules")
    with col3:
        st.metric("Backend Tests", "385", delta="20 new integration")
    with col4:
        st.metric("API Endpoints", "35+", help="RESTful API with JWT auth")
    with col5:
        st.metric("Scheduled Tasks", "4", help="Celery Beat periodic tasks")

    st.divider()

    st.subheader("What was built")
    left, right = st.columns(2)
    with left:
        st.markdown("""
        **Core Platform**
        - Flask REST API with SQLAlchemy models
        - React 18 SPA with Material-UI
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
        **Microbiome Analysis** *(latest)*
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

    st.divider()

    st.subheader("Session work — microbiome finalization")
    st.markdown("""
    | Change | Details |
    |--------|---------|
    | **2 new correlator rules** | `gut_axis_methylation` (SLC6A4 + diversity + Vitamin D) and `mthfr_gut_methylation` (MTHFR + Bifidobacterium + epigenetic) |
    | **Stale-check task** | `check_and_reanalyze_stale` — daily Celery Beat task re-triggers microbiome analysis when new genome/blood/wearable data arrives |
    | **Disclaimers** | Microbiome-specific warnings in `UnifiedAnalysisResult` |
    | **20 integration tests** | Correlator rules, stale-check logic, display text, disclaimers, API routes |
    | **Docker updates** | scipy build deps, `MAX_MICROBIOME_FILE_SIZE_MB` env var |
    | **README.md** | Full microbiome docs, API endpoints, env vars, scheduled tasks |
    """)


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Genome & Blood
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Genome & Blood":
    st.markdown('<div class="main-header">Genome & Blood Data</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Genomic variants and blood biomarkers from the sample patient.</div>', unsafe_allow_html=True)

    left, right = st.columns(2)

    with left:
        st.subheader("Genome Variants")
        if enable_genome:
            df_v = pd.DataFrame(SAMPLE_VARIANTS)
            df_v.columns = ["rsID", "Gene", "Genotype", "Risk Level"]
            st.dataframe(df_v, use_container_width=True, hide_index=True)

            st.info(
                "These variants interact with microbiome, epigenetic, and blood "
                "data through our cross-domain correlation engine."
            )
        else:
            st.warning("Genome data is disabled in sidebar.")

    with right:
        st.subheader("Blood Markers")
        if enable_blood:
            df_b = pd.DataFrame(SAMPLE_BLOOD_MARKERS)
            df_b.columns = ["Marker", "Value", "Unit", "Flag"]

            def flag_color(flag):
                if flag == "H":
                    return "background-color: #fee2e2"
                elif flag == "L":
                    return "background-color: #fef3c7"
                return ""

            st.dataframe(df_b, use_container_width=True, hide_index=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("HbA1c", "6.0%", delta="High", delta_color="inverse")
            with col2:
                st.metric("Vitamin D", "15 ng/mL", delta="Low", delta_color="inverse")
            with col3:
                st.metric("hs-CRP", "4.5 mg/L", delta="High", delta_color="inverse")
        else:
            st.warning("Blood data is disabled in sidebar.")


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Microbiome
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Microbiome":
    st.markdown('<div class="main-header">Microbiome Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Gut microbiome composition, diversity, and enterotype classification.</div>', unsafe_allow_html=True)

    if not enable_microbiome:
        st.warning("Microbiome data is disabled in sidebar.")
    else:
        m = SAMPLE_MICROBIOME

        # Diversity metrics
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

        st.divider()

        # Phylum composition
        left, right = st.columns(2)
        with left:
            st.subheader("Phylum Composition")
            phylum_data = pd.DataFrame(m["composition"]["phylum"])
            phylum_data.columns = ["Phylum", "Relative Abundance"]

            chart_data = phylum_data.set_index("Phylum")
            st.bar_chart(chart_data, color="#0284c7")

            # F/B ratio
            firmicutes = next((p["abundance"] for p in m["composition"]["phylum"] if p["name"] == "Firmicutes"), 0)
            bacteroidetes = next((p["abundance"] for p in m["composition"]["phylum"] if p["name"] == "Bacteroidetes"), 0)
            fb_ratio = firmicutes / bacteroidetes if bacteroidetes > 0 else 0
            st.metric("Firmicutes / Bacteroidetes Ratio", f"{fb_ratio:.2f}",
                      delta="Elevated (>3)" if fb_ratio > 3 else "Normal", delta_color="inverse" if fb_ratio > 3 else "normal")

        with right:
            st.subheader("Genus Abundance")
            genus_data = pd.DataFrame(m["composition"]["genus"])
            genus_data.columns = ["Genus", "Relative Abundance"]

            chart_data_g = genus_data.set_index("Genus")
            st.bar_chart(chart_data_g, horizontal=True, color="#059669")

        st.divider()

        # Key genus table
        st.subheader("Key Genera Detail")
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
            '<div class="disclaimer-box">'
            "Microbiome analysis is an emerging science. Results vary significantly "
            "by sampling method, timing, diet, and medication. A single sample "
            "provides a snapshot, not a definitive assessment."
            "</div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Epigenetics & Wearables
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Epigenetics & Wearables":
    st.markdown('<div class="main-header">Epigenetics & Wearables</div>', unsafe_allow_html=True)

    left, right = st.columns(2)

    with left:
        st.subheader("Epigenetic Overlays")
        if enable_epigenetics:
            df_e = pd.DataFrame(SAMPLE_EPIGENETIC_OVERLAYS)
            df_e.columns = ["Gene", "Region", "Modification"]
            st.dataframe(df_e, use_container_width=True, hide_index=True)
            st.info("These overlays are cross-referenced with genome variants and microbiome data.")
        else:
            st.warning("Epigenetic data is disabled in sidebar.")

    with right:
        st.subheader("Wearable Summaries")
        if enable_wearable:
            for w in SAMPLE_WEARABLE:
                with st.expander(f"{w['data_type'].title()} — {w['date']}"):
                    for key, val in w["summary"].items():
                        label = key.replace("_", " ").title()
                        st.metric(label, str(val))
        else:
            st.warning("Wearable data is disabled in sidebar.")


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Cross-Domain Engine
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Cross-Domain Engine":
    st.markdown('<div class="main-header">Cross-Domain Correlation Engine</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        "Real-time execution of the 9-rule multi-domain engine with the sample patient. "
        "Toggle data domains in the sidebar to see how insights change.</div>",
        unsafe_allow_html=True,
    )

    variants, blood, wearable, microbiome, epigenetics = get_active_data()

    # Count active domains
    active_count = sum([
        bool(variants), bool(blood), bool(wearable),
        microbiome is not None, epigenetics is not None,
    ])
    st.info(f"Running engine with **{active_count}/5** data domains active.")

    # Run the actual correlator
    correlations = run_unified_correlation(
        user_variants=variants,
        blood_markers=blood,
        wearable_summaries=wearable,
        microbiome_profile=microbiome,
        epigenetic_overlays=epigenetics,
    )

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Insights Generated", len(correlations))
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

    st.divider()

    # Render insights sorted by priority
    correlations_sorted = sorted(correlations, key=lambda c: c.priority, reverse=True)

    for insight in correlations_sorted:
        render_insight_card(insight)

        # Expandable recommendations
        if insight.recommendations:
            with st.expander("Recommendations"):
                for rec in insight.recommendations:
                    st.markdown(f"- {rec}")

    if not correlations:
        st.info("No correlations generated. Try enabling more data domains in the sidebar.")


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Unified Report
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Unified Report":
    st.markdown('<div class="main-header">Unified Health Report</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Full unified analysis with AI narrative, domain summaries, and disclaimer.</div>',
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
    domain_icons = {
        "genome": "DNA", "blood": "Blood", "epigenetics": "Epigenetics",
        "microbiome": "Microbiome", "wearable": "Wearables"
    }
    for i, domain in enumerate(result.domains):
        with cols[i]:
            status_emoji = "Available" if domain.status == "available" else "Unavailable"
            color = "green" if domain.status == "available" else "gray"
            st.markdown(
                f"**{domain_icons.get(domain.domain, domain.domain)}**"
            )
            if domain.status == "available":
                st.success(f"{status_emoji}")
            else:
                st.error(f"{status_emoji}")
            if domain.metrics:
                for k, v in list(domain.metrics.items())[:3]:
                    st.caption(f"{k}: {v}")

    st.divider()

    # AI Narrative
    st.subheader("AI Narrative")
    st.markdown(result.ai_narrative)

    st.divider()

    # Correlations summary
    st.subheader(f"Cross-Domain Insights ({len(result.correlations)})")
    for insight in sorted(result.correlations, key=lambda c: c.priority, reverse=True):
        render_insight_card(insight)

    st.divider()

    # Disclaimer
    st.subheader("Disclaimer")
    st.markdown(
        f'<div class="disclaimer-box">{result.disclaimer}</div>',
        unsafe_allow_html=True,
    )

    # Raw JSON
    with st.expander("View raw JSON response"):
        st.json(result.to_dict())


# ═══════════════════════════════════════════════════════════════════════════
#  Page: Architecture
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Architecture":
    st.markdown('<div class="main-header">Architecture</div>', unsafe_allow_html=True)

    st.code("""
GenomeInsight/
├── backend/                  # Flask REST API
│   ├── app/
│   │   ├── api/              # Blueprints (auth, genome, blood, epigenetics,
│   │   │                     #   wearables, microbiome, analysis)
│   │   ├── models/           # SQLAlchemy models (user, genome, blood,
│   │   │                     #   epigenetics, wearable, microbiome)
│   │   ├── services/         # Genome analyzer, report generator, encryption
│   │   ├── tasks/            # Celery async tasks (genome, blood, epigenetics,
│   │   │                     #   wearable, microbiome)
│   │   └── utils/            # VCF parser, blood parser, epigenetics/microbiome
│   │                         #   analyzers, cross-domain correlator
│   ├── tests/                # Pytest test suite (385 tests)
│   ├── celery_worker.py      # Celery worker + Beat scheduler
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # React 18 SPA
│   ├── src/
│   │   ├── components/       # Dashboard, Upload, Report, Wearables,
│   │   │                     #   Microbiome, UnifiedReport
│   │   ├── contexts/         # AuthContext (JWT management)
│   │   └── services/         # Axios API client with auto-refresh
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml        # 5 services: backend, frontend, redis,
│                             #   celery, celery-beat
├── streamlit_app.py          # This demo app
└── .env.example
    """, language="text")

    st.divider()

    st.subheader("Celery Beat — Scheduled Tasks")
    tasks_data = [
        {"Task": "sync_all_active_connections", "Schedule": "Every 6 hours",
         "Queue": "wearables", "Description": "Pull wearable data from Terra API"},
        {"Task": "generate_daily_insights", "Schedule": "Daily 02:30 UTC",
         "Queue": "insights", "Description": "Cross-domain insight generation"},
        {"Task": "schedule_weekly_reanalysis", "Schedule": "Monday 03:00 UTC",
         "Queue": "analysis", "Description": "Re-run microbiome cross-domain correlations"},
        {"Task": "check_and_reanalyze_stale", "Schedule": "Daily 04:00 UTC",
         "Queue": "analysis", "Description": "Re-analyze when new genome/blood/wearable data arrives"},
    ]
    st.dataframe(pd.DataFrame(tasks_data), use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Multi-Domain Correlation Rules")
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

    st.divider()

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

    st.divider()

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

st.divider()
st.caption(
    "GenomeInsight is for informational and educational purposes only. "
    "It is NOT medical advice. Always consult a qualified healthcare provider."
)
