"""GenomeInsight — Streamlit Web Application.

A privacy-first genome and health analysis dashboard. Upload VCF, blood,
microbiome, and WGS data to receive personalized health insights, InnerAge,
risk scoring, and AI-generated recommendations.

Streamlit Cloud auto-detects this file as the entry point.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import pandas as pd

# ── Allow imports from the backend package ───────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent / "GenomeInsight" / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services.genome_analyzer import (  # noqa: E402
    detect_genome_build,
    generate_recommendations,
    parse_vcf,
    score_risks,
)
from app.services.report_generator import (  # noqa: E402
    DISCLAIMER,
    generate_report_template,
)

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="GenomeInsight",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Wabi Sabi CSS ────────────────────────────────────────────────────────────

st.markdown("""
<style>
    :root {
        --earth-deep: #5C4B3F;
        --earth-mid: #7A7267;
        --moss: #8B9A7F;
        --mist: #A0B4C2;
        --clay: #C4A882;
        --linen: #F5F5F0;
        --warm-white: #FAFAF7;
    }
    .stApp { background-color: var(--warm-white); }
    .stMetric label { font-family: 'Georgia', serif !important; color: var(--earth-mid) !important; }
    .stMetric [data-testid="stMetricValue"] { color: var(--earth-deep) !important; }
    .stTabs [data-baseweb="tab"] { font-family: 'Georgia', serif !important; }
    div[data-testid="stExpander"] { border-color: rgba(92,75,63,0.08) !important; }
    .wabi-card {
        background: rgba(255,255,255,0.7);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(92,75,63,0.06);
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .age-gauge { text-align: center; padding: 1rem 0; }
    .age-value { font-size: 3rem; font-weight: 700; font-family: Georgia, serif; }
    .age-younger { color: var(--moss); }
    .age-older { color: #B8726D; }
    .age-neutral { color: var(--clay); }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🧬 GenomeInsight")
    st.caption("Personal Genome & Health Dashboard")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "Upload & Analyze",
            "Risk Overview",
            "Recommendations",
            "InnerAge",
            "Healthspan",
            "WGS & Ancestry",
            "AI Chat",
            "Full Report",
            "About",
        ],
        index=0,
    )

    st.markdown("---")
    st.warning(
        "**Disclaimer**: This tool is for informational and educational "
        "purposes only. It is NOT medical advice. InnerAge, predictions, "
        "and AI responses are statistical estimates.",
        icon="⚠️",
    )
    st.caption("v0.3.0 — Nebula + InsideTracker Preview")


# ── Session state initialization ─────────────────────────────────────────────

_defaults = {
    "variants": [],
    "risk_categories": [],
    "recommendations": [],
    "report_text": "",
    "genome_build": "",
    "innerage_result": None,
    "healthspan_scores": None,
    "ancestry_data": None,
    "chat_messages": [],
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helper functions ─────────────────────────────────────────────────────────


def _run_analysis(vcf_bytes: bytes) -> None:
    build = detect_genome_build(vcf_bytes)
    st.session_state.genome_build = build
    variants = parse_vcf(vcf_bytes)
    st.session_state.variants = variants
    risk_cats = score_risks(variants, {})
    st.session_state.risk_categories = risk_cats
    recs = generate_recommendations(variants)
    st.session_state.recommendations = recs
    report = generate_report_template(
        risk_categories=risk_cats,
        recommendations=recs,
        variant_count=len(variants),
        annotated_count=len([v for v in variants if v.rsid]),
    )
    st.session_state.report_text = report


def _risk_color(level: str) -> str:
    return {"low": "🟢", "average": "🟡", "elevated": "🟠", "high": "🔴"}.get(level, "⚪")


def _simulate_innerage(chrono_age: float, biomarkers: dict) -> dict:
    """Simulate InnerAge calculation for preview mode."""
    import random
    random.seed(int(chrono_age * 100) + sum(int(v * 100) for v in biomarkers.values()))

    blood_score = chrono_age + random.uniform(-5, 3)
    epi_score = chrono_age + random.uniform(-4, 4)
    wearable_score = chrono_age + random.uniform(-6, 2)
    bio_age = 0.50 * blood_score + 0.35 * epi_score + 0.15 * wearable_score

    return {
        "biological_age": round(bio_age, 1),
        "chronological_age": chrono_age,
        "age_delta": round(bio_age - chrono_age, 1),
        "blood_score": round(blood_score, 1),
        "epigenetic_score": round(epi_score, 1),
        "wearable_score": round(wearable_score, 1),
        "model_type": "ensemble (preview)",
        "confidence_low": round(bio_age - 2.5, 1),
        "confidence_high": round(bio_age + 2.5, 1),
    }


def _simulate_healthspan() -> dict:
    import random
    random.seed(42)
    return {
        "overall": random.randint(65, 90),
        "sleep": random.randint(55, 95),
        "activity": random.randint(50, 92),
        "nutrition": random.randint(58, 88),
        "stress": random.randint(45, 85),
        "innerage_snapshot": 37.2,
        "period": "2024-01-01 — 2024-01-07",
    }


def _simulate_ancestry() -> dict:
    return {
        "European": 0.62,
        "East Asian": 0.18,
        "African": 0.12,
        "South Asian": 0.05,
        "Native American": 0.03,
    }


def _simulate_chat_response(prompt: str) -> str:
    prompt_lower = prompt.lower()
    if "cholesterol" in prompt_lower:
        return (
            "Cholesterol is a waxy substance found in your blood. Your body needs it to build cells, "
            "but too much can increase heart disease risk.\n\n"
            "**Key markers:**\n"
            "- **Total Cholesterol**: Below 200 mg/dL is desirable\n"
            "- **LDL (\"bad\")**: Below 100 mg/dL is optimal\n"
            "- **HDL (\"good\")**: Above 60 mg/dL is protective\n\n"
            "Based on your genetic profile, some variants (like APOE) can influence your baseline "
            "cholesterol metabolism. I'd recommend discussing your results with your healthcare provider."
        )
    elif "biological age" in prompt_lower or "innerage" in prompt_lower:
        return (
            "Biological age is calculated using the **PhenoAge** model (Levine 2018), which uses "
            "9 blood biomarkers to estimate mortality risk, combined with the **Horvath epigenetic clock** "
            "and wearable fitness metrics.\n\n"
            "**The ensemble formula:**\n"
            "- 50% PhenoAge (blood biomarkers)\n"
            "- 35% Horvath clock (DNA methylation)\n"
            "- 15% Wearable modifiers (RHR, HRV, sleep, steps)\n\n"
            "A biological age *lower* than your chronological age suggests better-than-average health resilience."
        )
    elif "improve" in prompt_lower or "first" in prompt_lower:
        return (
            "Based on your health profile, here are my top suggestions:\n\n"
            "1. **Sleep Quality**: Aim for 7-9 hours with consistent wake times\n"
            "2. **Inflammation**: Your CRP levels affect PhenoAge — consider anti-inflammatory foods\n"
            "3. **Exercise**: Regular Zone 2 cardio (150 min/week) has the strongest effect on biological age\n"
            "4. **Microbiome Diversity**: High-fiber foods support gut health\n\n"
            "These are general suggestions — always consult your healthcare provider for personalized advice."
        )
    elif "microbiome" in prompt_lower:
        return (
            "Your microbiome analysis examines the composition of bacteria in your gut (or oral cavity).\n\n"
            "**Key metrics:**\n"
            "- **Shannon Diversity**: Higher is generally better (>3.0 is good)\n"
            "- **Firmicutes:Bacteroidetes ratio**: Should be balanced\n"
            "- **Red complex pathogens**: *P. gingivalis*, *T. denticola*, *T. forsythia* — linked to periodontal disease\n\n"
            "Oral microbiome health is increasingly linked to cardiovascular outcomes through systemic inflammation."
        )
    else:
        return (
            "That's a great question about your health data. In the full version of GenomeInsight, "
            "I would analyze your uploaded blood panels, genome variants, microbiome composition, "
            "and wearable metrics to provide a personalized answer.\n\n"
            "For now, try asking about:\n"
            "- Cholesterol levels\n"
            "- Biological age calculation\n"
            "- What to improve first\n"
            "- Microbiome results"
        )


# ── Pages ────────────────────────────────────────────────────────────────────


def page_upload():
    st.header("Upload & Analyze Genome")
    st.markdown(
        "Upload a **VCF file** from a genotyping service (23andMe, AncestryDNA, "
        "Nebula Genomics, etc.) to receive personalized health insights."
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded = st.file_uploader(
            "Choose a VCF file",
            type=["vcf", "txt", "gz"],
            help="Standard VCF 4.x format, plain or gzip-compressed (.vcf.gz). "
            "Files stay in your browser session and are never stored on disk.",
        )

        if uploaded is not None:
            raw_bytes = uploaded.read()

            if raw_bytes[:2] == b"\x1f\x8b":
                import gzip
                try:
                    vcf_bytes = gzip.decompress(raw_bytes)
                except Exception:
                    st.error("Failed to decompress .gz file. Is it a valid gzip archive?")
                    return
            else:
                vcf_bytes = raw_bytes

            if not vcf_bytes[:16].startswith(b"##fileformat=VCF"):
                st.error(
                    "This doesn't look like a valid VCF file. "
                    "Expected `##fileformat=VCF` header."
                )
                return

            with st.spinner("Analyzing genome variants..."):
                _run_analysis(vcf_bytes)

            st.success(
                f"Analysis complete! Found "
                f"**{len(st.session_state.variants):,}** variants "
                f"(build: {st.session_state.genome_build})."
            )

    with col2:
        st.markdown("#### Quick Stats")
        if st.session_state.variants:
            total = len(st.session_state.variants)
            with_rsid = len([v for v in st.session_state.variants if v.rsid])
            risk_count = len(st.session_state.risk_categories)
            rec_count = len(st.session_state.recommendations)

            st.metric("Total Variants", f"{total:,}")
            st.metric("Known rsIDs", f"{with_rsid:,}")
            st.metric("Risk Categories", risk_count)
            st.metric("Recommendations", rec_count)
        else:
            st.info("Upload a VCF file to see stats.")

    if st.session_state.variants:
        st.markdown("---")
        st.subheader("Parsed Variants")

        df = pd.DataFrame(
            [
                {
                    "rsID": v.rsid or "—",
                    "Chromosome": v.chromosome,
                    "Position": v.position,
                    "Ref": v.ref_allele,
                    "Alt": v.alt_allele,
                    "Genotype": v.genotype,
                    "Quality": v.quality,
                }
                for v in st.session_state.variants
            ]
        )

        col_a, col_b = st.columns(2)
        with col_a:
            chrom_filter = st.multiselect(
                "Filter by chromosome",
                sorted(df["Chromosome"].unique()),
                default=[],
            )
        with col_b:
            rsid_only = st.checkbox("Show only variants with rsID", value=False)

        filtered = df.copy()
        if chrom_filter:
            filtered = filtered[filtered["Chromosome"].isin(chrom_filter)]
        if rsid_only:
            filtered = filtered[filtered["rsID"] != "—"]

        st.dataframe(filtered, use_container_width=True, height=400)


def page_risks():
    st.header("Genetic Risk Overview")

    if not st.session_state.risk_categories:
        st.info("No analysis data yet. Go to **Upload & Analyze** to get started.")
        return

    for rc in st.session_state.risk_categories:
        icon = _risk_color(rc.level)
        with st.expander(
            f"{icon} {rc.label} — **{rc.level.title()}** ({rc.score}/10)",
            expanded=(rc.level in ("elevated", "high")),
        ):
            st.progress(rc.score / 10.0)
            if rc.key_variants:
                st.markdown("**Key Variants:**")
                for kv in rc.key_variants:
                    st.markdown(
                        f"- `{kv['rsid']}` ({kv['genotype']}) — {kv['note']} "
                        f"*(contribution: {kv['contribution']})*"
                    )
            else:
                st.markdown("*No specific high-impact variants identified in this category.*")


def page_recommendations():
    st.header("Personalized Recommendations")

    if not st.session_state.recommendations:
        st.info("No recommendations yet. Go to **Upload & Analyze** to get started.")
        return

    categories: dict[str, list] = {}
    for rec in st.session_state.recommendations:
        categories.setdefault(rec.category, []).append(rec)

    category_icons = {
        "diet": "🥗", "exercise": "🏃", "supplement": "💊",
        "lifestyle": "🧘", "pharmacogenomic": "💊",
    }

    for cat, recs in categories.items():
        icon = category_icons.get(cat, "📋")
        st.subheader(f"{icon} {cat.title()}")
        for rec in recs:
            confidence_color = {"high": "green", "medium": "orange", "low": "red"}.get(rec.confidence, "gray")
            st.markdown(f"#### {rec.title}")
            st.markdown(
                f"**Confidence:** :{confidence_color}[{rec.confidence.title()}] "
                f"| **Priority:** {rec.priority}/10 "
                f"| **Evidence:** `{rec.evidence_rsids}`"
            )
            st.markdown(rec.body)
            st.markdown("---")


def page_innerage():
    st.header("🧬 InnerAge — Biological Age")
    st.markdown("*Your biological age — a measure not of time passed, but of resilience within.*")

    st.info(
        "**Preview Mode**: Enter sample biomarkers below to see how InnerAge works. "
        "In the full app, values are pulled from your uploaded blood panels and wearable data.",
        icon="ℹ️",
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        chrono_age = st.number_input("Chronological Age", min_value=18, max_value=100, value=40)
        st.markdown("##### Blood Biomarkers")
        albumin = st.slider("Albumin (g/dL)", 2.5, 5.5, 4.5, 0.1)
        creatinine = st.slider("Creatinine (mg/dL)", 0.3, 3.0, 0.9, 0.1)
        glucose = st.slider("Glucose (mg/dL)", 60.0, 200.0, 90.0, 1.0)
        crp = st.slider("C-Reactive Protein (mg/L)", 0.0, 15.0, 0.5, 0.1)
        lymphocyte_pct = st.slider("Lymphocyte %", 10.0, 50.0, 30.0, 1.0)

    with col2:
        st.markdown("##### Additional Markers")
        mcv = st.slider("MCV (fL)", 70.0, 110.0, 90.0, 1.0)
        rdw = st.slider("RDW (%)", 10.0, 20.0, 13.0, 0.1)
        alp = st.slider("Alkaline Phosphatase (U/L)", 20.0, 200.0, 60.0, 1.0)
        wbc = st.slider("White Blood Cells (10³/μL)", 2.0, 15.0, 6.0, 0.1)

    if st.button("Calculate InnerAge", type="primary"):
        biomarkers = {
            "albumin": albumin, "creatinine": creatinine, "glucose": glucose,
            "crp": crp, "lymphocyte_pct": lymphocyte_pct, "mcv": mcv,
            "rdw": rdw, "alkaline_phosphatase": alp, "white_blood_cells": wbc,
        }

        with st.spinner("Computing biological age..."):
            result = _simulate_innerage(chrono_age, biomarkers)
            st.session_state.innerage_result = result

    result = st.session_state.innerage_result
    if result:
        st.markdown("---")

        delta = result["age_delta"]
        css_class = "age-younger" if delta < 0 else ("age-older" if delta > 3 else "age-neutral")
        delta_text = f"{abs(delta):.1f} years younger" if delta < 0 else (
            f"{delta:.1f} years older" if delta > 0 else "On track"
        )

        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown(f"""
            <div class="wabi-card age-gauge">
                <div style="color: #7A7267; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.1em;">
                    Biological Age
                </div>
                <div class="age-value {css_class}">{result['biological_age']}</div>
                <div style="color: #7A7267; font-size: 0.9rem; margin-top: 0.25rem;">
                    {delta_text}
                </div>
                <div style="color: #A8A8A8; font-size: 0.8rem; margin-top: 0.5rem;">
                    Chronological: {result['chronological_age']:.0f} ·
                    CI: {result['confidence_low']}–{result['confidence_high']} ·
                    Model: {result['model_type']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.subheader("Component Breakdown")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("Blood Biomarkers", f"{result['blood_score']:.1f}")
        with sc2:
            st.metric("Epigenetic Clock", f"{result['epigenetic_score']:.1f}")
        with sc3:
            st.metric("Wearable Fitness", f"{result['wearable_score']:.1f}")

        st.caption(
            "Weights: 50% PhenoAge (blood), 35% Horvath (epigenetic), 15% wearable modifiers. "
            "Full implementation uses exact Levine 2018 PhenoAge formula."
        )


def page_healthspan():
    st.header("📊 Healthspan Report")
    st.markdown("*Weekly rhythms of well-being — patterns emerging from stillness.*")

    st.info(
        "**Preview Mode**: Showing simulated weekly scores. In the full app, "
        "scores are computed from wearable data, blood panels, and microbiome results.",
        icon="ℹ️",
    )

    scores = _simulate_healthspan()
    st.session_state.healthspan_scores = scores

    st.markdown(f"**Period:** {scores['period']}")

    cols = st.columns(5)
    labels = ["Overall", "Sleep", "Activity", "Nutrition", "Stress"]
    keys = ["overall", "sleep", "activity", "nutrition", "stress"]
    colors = ["#8B9A7F", "#A0B4C2", "#C4A882", "#B89B8F", "#7A7267"]

    for i, (col, label, key) in enumerate(zip(cols, labels, keys)):
        with col:
            val = scores[key]
            st.markdown(f"""
            <div class="wabi-card" style="text-align: center;">
                <div style="color: #7A7267; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em;">
                    {label}
                </div>
                <div style="font-size: 2.2rem; font-weight: 700; color: {colors[i]}; font-family: Georgia, serif;">
                    {val}
                </div>
                <div style="width: 60%; height: 4px; margin: 0.5rem auto 0; border-radius: 2px; background: rgba(92,75,63,0.06);">
                    <div style="width: {val}%; height: 100%; border-radius: 2px; background: {colors[i]}; opacity: 0.6;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("Score Trends (Simulated)")
    import random
    random.seed(42)
    trend_data = []
    for week in range(8):
        trend_data.append({
            "Week": f"W{week+1}",
            "Overall": random.randint(62, 88),
            "Sleep": random.randint(55, 92),
            "Activity": random.randint(48, 90),
        })
    trend_df = pd.DataFrame(trend_data)
    st.line_chart(trend_df.set_index("Week"), color=["#8B9A7F", "#A0B4C2", "#C4A882"])

    if scores["innerage_snapshot"]:
        st.metric("InnerAge Snapshot", f"{scores['innerage_snapshot']:.1f}")

    st.caption(
        "Premium feature: Optimized biomarker zones, predictive trends (Prophet/ARIMA), "
        "and habit-outcome correlations are available with a Premium subscription."
    )


def page_wgs_ancestry():
    st.header("🌍 WGS & Ancestry")
    st.markdown("*Explore your full genome — each imperfection telling a story.*")

    tab1, tab2 = st.tabs(["Ancestry Composition", "WGS Upload"])

    with tab1:
        st.subheader("Ancestry Composition (Simulated)")
        ancestry = _simulate_ancestry()
        st.session_state.ancestry_data = ancestry

        cols = st.columns(len(ancestry))
        chart_colors = ["#8B9A7F", "#A0B4C2", "#C4A882", "#B89B8F", "#7A7267"]
        for i, (col, (pop, pct)) in enumerate(zip(cols, ancestry.items())):
            with col:
                color = chart_colors[i % len(chart_colors)]
                st.markdown(f"""
                <div style="text-align: center; padding: 0.5rem;">
                    <div style="width: 64px; height: 64px; border-radius: 50%; margin: 0 auto 0.5rem;
                         display: flex; align-items: center; justify-content: center;
                         background: {color}22; border: 2px solid {color};">
                        <span style="font-weight: 600; font-size: 0.95rem; color: {color};">
                            {pct*100:.0f}%
                        </span>
                    </div>
                    <div style="font-size: 0.8rem; color: #7A7267;">{pop}</div>
                </div>
                """, unsafe_allow_html=True)

        anc_df = pd.DataFrame({
            "Population": list(ancestry.keys()),
            "Proportion": [v * 100 for v in ancestry.values()],
        })
        st.bar_chart(anc_df.set_index("Population"), color="#8B9A7F")

        st.caption(
            "Ancestry is inferred from population-specific allele frequencies. "
            "Full resolution requires whole genome sequencing data."
        )

    with tab2:
        st.subheader("Whole Genome Sequencing Upload")
        st.markdown(
            "Upload FASTQ, FASTQ.GZ, or BAM files from whole genome sequencing services "
            "like Nebula Genomics, Dante Labs, or clinical labs."
        )

        uploaded_wgs = st.file_uploader(
            "Choose a WGS file",
            type=["fastq", "fq", "bam", "gz"],
            help="FASTQ, FASTQ.GZ, or BAM alignment files up to 2 GB.",
            key="wgs_uploader",
        )

        if uploaded_wgs:
            st.success(f"File received: **{uploaded_wgs.name}** ({uploaded_wgs.size / (1024*1024):.1f} MB)")
            st.info(
                "In the full app, this file would be encrypted and queued for variant calling, "
                "ancestry inference, and NCBI annotation via Celery background tasks."
            )

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            **Supported Formats**
            - FASTQ (.fastq, .fq)
            - Compressed FASTQ (.fastq.gz)
            - BAM alignment files (.bam)
            """)
        with c2:
            st.markdown("""
            **Analysis Pipeline**
            1. AES-256 encryption at rest
            2. Quality metrics (depth, read count)
            3. Variant calling (clinically relevant SNPs)
            4. Ancestry inference
            5. NCBI haplogroup annotation
            """)


def page_ai_chat():
    st.header("🤖 AI Health Chat")
    st.markdown("*A quiet conversation about your health — ask anything about your data.*")

    st.info(
        "**Preview Mode**: Responses are simulated. In the full app, this uses "
        "LangChain + OpenAI GPT-4o with your actual health data as context.",
        icon="ℹ️",
    )

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about your health data..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = _simulate_chat_response(prompt)
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

    if not st.session_state.chat_messages:
        st.markdown("**Suggested questions:**")
        suggestions = [
            "What does my cholesterol level mean?",
            "How is biological age calculated?",
            "What should I improve first?",
            "Explain my microbiome results",
        ]
        cols = st.columns(len(suggestions))
        for col, q in zip(cols, suggestions):
            with col:
                if st.button(q, key=f"suggest_{q[:20]}"):
                    st.session_state.chat_messages.append({"role": "user", "content": q})
                    response = _simulate_chat_response(q)
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    st.rerun()

    st.caption(
        "AI assistant — not medical advice. Always consult a healthcare provider. "
        "Premium subscription required in the full app."
    )


def page_report():
    st.header("Full Genome Report")

    if not st.session_state.report_text:
        st.info("No report generated yet. Go to **Upload & Analyze** to get started.")
        return

    st.markdown(st.session_state.report_text)
    st.download_button(
        label="Download Report as Markdown",
        data=st.session_state.report_text,
        file_name="genomeinsight_report.md",
        mime="text/markdown",
    )


def page_about():
    st.header("About GenomeInsight")

    st.markdown("""
GenomeInsight is a privacy-first health platform that analyzes genome, blood,
epigenetic, microbiome, and wearable data to provide personalized health insights.

### Features

| Feature | Free | Basic | Premium |
|---------|------|-------|---------|
| VCF/VCF.GZ genome upload | ✅ 3 uploads | ✅ 25 uploads | ✅ Unlimited |
| Blood panel tracking | ✅ Basic | ✅ Full history | ✅ Full + predictions |
| Microbiome analysis | ✅ Single | ✅ Multiple | ✅ Unlimited |
| Wearable integration | ❌ | ✅ | ✅ |
| InnerAge biological age | ❌ | ❌ | ✅ |
| Predictive biomarker trends | ❌ | ❌ | ✅ |
| AI Health Chat | ❌ | ❌ | ✅ |
| Weekly healthspan reports | ❌ | ❌ | ✅ |
| Blockchain data ownership | ❌ | ❌ | ✅ |
| WGS analysis & ancestry | ❌ | ❌ | ✅ |

### Technology Stack

- **Backend**: Python/Flask, SQLAlchemy 2.0, Celery + Redis
- **ML**: PhenoAge (Levine 2018), Horvath clock, Prophet/ARIMA forecasting
- **AI**: LangChain + OpenAI GPT-4o conversational health agent
- **Payments**: Stripe subscriptions (free/basic/premium tiers)
- **Blockchain**: ERC-721 NFTs on Ethereum for health data ownership
- **Security**: AES-256-GCM encryption, JWT auth, bcrypt hashing
- **Frontend**: React 18 + MUI + Tailwind (Wabi Sabi design system)

### Data Privacy

- All files encrypted with per-user AES-256-GCM keys
- No data shared with third parties
- Full data deletion available at any time
""")

    st.markdown("---")
    st.warning(DISCLAIMER, icon="⚠️")


# ── Router ───────────────────────────────────────────────────────────────────

_PAGES = {
    "Upload & Analyze": page_upload,
    "Risk Overview": page_risks,
    "Recommendations": page_recommendations,
    "InnerAge": page_innerage,
    "Healthspan": page_healthspan,
    "WGS & Ancestry": page_wgs_ancestry,
    "AI Chat": page_ai_chat,
    "Full Report": page_report,
    "About": page_about,
}

_PAGES[page]()
