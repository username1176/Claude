"""GenomeInsight — Streamlit Web Application.

A privacy-first genome analysis dashboard. Upload a VCF file to receive
personalized health insights, risk scoring, and lifestyle recommendations
powered by public genome research databases.

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

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🧬 GenomeInsight")
    st.caption("Personal Genome Analysis Dashboard")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["Upload & Analyze", "Risk Overview", "Recommendations", "Full Report", "About"],
        index=0,
    )

    st.markdown("---")
    st.warning(
        "**Disclaimer**: This tool is for informational and educational "
        "purposes only. It is NOT medical advice.",
        icon="⚠️",
    )
    st.caption("v0.1.0 — Design Preview")


# ── Session state initialization ─────────────────────────────────────────────

if "variants" not in st.session_state:
    st.session_state.variants = []
if "risk_categories" not in st.session_state:
    st.session_state.risk_categories = []
if "recommendations" not in st.session_state:
    st.session_state.recommendations = []
if "report_text" not in st.session_state:
    st.session_state.report_text = ""
if "genome_build" not in st.session_state:
    st.session_state.genome_build = ""


# ── Helper functions ─────────────────────────────────────────────────────────


def _run_analysis(vcf_bytes: bytes) -> None:
    """Run the local analysis pipeline (no external APIs in demo mode)."""
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

            # Detect gzip-compressed files (magic bytes 1f 8b)
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

    # Show variant table
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
        st.info(
            "No analysis data yet. Go to **Upload & Analyze** to get started."
        )
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
                st.markdown(
                    "*No specific high-impact variants identified in this category.*"
                )


def page_recommendations():
    st.header("Personalized Recommendations")

    if not st.session_state.recommendations:
        st.info(
            "No recommendations yet. Go to **Upload & Analyze** to get started."
        )
        return

    categories: dict[str, list] = {}
    for rec in st.session_state.recommendations:
        categories.setdefault(rec.category, []).append(rec)

    category_icons = {
        "diet": "🥗",
        "exercise": "🏃",
        "supplement": "💊",
        "lifestyle": "🧘",
        "pharmacogenomic": "💊",
    }

    for cat, recs in categories.items():
        icon = category_icons.get(cat, "📋")
        st.subheader(f"{icon} {cat.title()}")

        for rec in recs:
            confidence_color = {
                "high": "green", "medium": "orange", "low": "red",
            }.get(rec.confidence, "gray")

            st.markdown(f"#### {rec.title}")
            st.markdown(
                f"**Confidence:** :{confidence_color}[{rec.confidence.title()}] "
                f"| **Priority:** {rec.priority}/10 "
                f"| **Evidence:** `{rec.evidence_rsids}`"
            )
            st.markdown(rec.body)
            st.markdown("---")


def page_report():
    st.header("Full Genome Report")

    if not st.session_state.report_text:
        st.info(
            "No report generated yet. Go to **Upload & Analyze** to get started."
        )
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

    st.markdown(
        """
GenomeInsight is a privacy-first web application that analyzes your genome data
to provide personalized health insights, risk assessments, and lifestyle
recommendations.

### How It Works

1. **Upload** your VCF file from a genotyping service (23andMe, AncestryDNA, etc.)
2. **Analysis** parses your genetic variants and cross-references them against
   curated databases of known health associations
3. **Risk Scoring** categorizes your genetic predispositions across health domains
4. **Recommendations** provides evidence-based, actionable lifestyle and dietary
   advice
5. **Report** generates a comprehensive, readable summary of all findings

### Data Privacy

- Your genome data **never leaves your browser session** in this demo
- No data is stored on disk or sent to external servers
- In the full application, all files are encrypted with per-user AES-256-GCM keys

### Architecture

The full application includes:
- **Backend**: Python/Flask REST API with SQLAlchemy + SQLite
- **Analysis Engine**: VCF parser + Ensembl VEP, ClinVar, GWAS Catalog, NCBI
  clients
- **AI Reports**: OpenAI integration for natural language report generation
- **Task Queue**: Celery + Redis for background genome analysis
- **Security**: Envelope encryption, JWT auth, bcrypt password hashing

### Databases Referenced

| Database | Purpose |
|----------|---------|
| Ensembl VEP | Variant functional consequences |
| ClinVar | Clinical significance (pathogenic/benign) |
| GWAS Catalog | Trait associations & odds ratios |
| NCBI Gene/dbSNP | Gene summaries & population frequencies |
| PharmGKB | Drug-gene interactions (future) |
"""
    )

    st.markdown("---")
    st.warning(DISCLAIMER, icon="⚠️")


# ── Router ───────────────────────────────────────────────────────────────────

_PAGES = {
    "Upload & Analyze": page_upload,
    "Risk Overview": page_risks,
    "Recommendations": page_recommendations,
    "Full Report": page_report,
    "About": page_about,
}

_PAGES[page]()
