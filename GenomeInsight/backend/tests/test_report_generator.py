"""Tests for the AI report generator."""

from app.services.genome_analyzer import Recommendation, RiskCategory
from app.services.report_generator import (
    DISCLAIMER,
    _build_prompt,
    generate_report,
    generate_report_template,
)


def _sample_risks():
    return [
        RiskCategory(
            category="cardiovascular",
            label="Cardiovascular Health",
            score=6.8,
            level="elevated",
            key_variants=[
                {"rsid": "rs10757274", "genotype": "1/1", "note": "9p21.3 CAD risk", "contribution": 1.95}
            ],
        ),
        RiskCategory(
            category="nutritional",
            label="Nutritional Metabolism",
            score=4.3,
            level="average",
            key_variants=[
                {"rsid": "rs1801133", "genotype": "0/1", "note": "MTHFR C677T", "contribution": 1.3}
            ],
        ),
    ]


def _sample_recs():
    return [
        Recommendation(
            category="supplement",
            title="Consider methylfolate supplementation",
            body="Your MTHFR C677T variant reduces folate conversion...",
            evidence_rsids="rs1801133",
            evidence_sources='[{"source": "curated_rules"}]',
            confidence="high",
            priority=2,
        ),
    ]


def test_template_report_contains_all_sections():
    report = generate_report_template(_sample_risks(), _sample_recs(), 1000, 50)

    assert "Executive Summary" in report
    assert "Genetic Risk Overview" in report
    assert "Personalized Recommendations" in report
    assert "Lifestyle Tweaks" in report
    assert "What This Means For You" in report


def test_template_report_contains_disclaimer():
    report = generate_report_template(_sample_risks(), _sample_recs(), 1000, 50)
    assert "IMPORTANT DISCLAIMER" in report


def test_template_report_mentions_variant_counts():
    report = generate_report_template(_sample_risks(), _sample_recs(), 1234, 56)
    assert "1,234" in report
    assert "56" in report


def test_template_report_includes_risk_data():
    report = generate_report_template(_sample_risks(), _sample_recs(), 1000, 50)
    assert "Cardiovascular Health" in report
    assert "rs10757274" in report
    assert "elevated" in report.lower() or "Elevated" in report


def test_template_report_includes_recommendations():
    report = generate_report_template(_sample_risks(), _sample_recs(), 1000, 50)
    assert "Consider methylfolate supplementation" in report
    assert "rs1801133" in report


def test_template_report_handles_no_risks():
    report = generate_report_template([], [], 500, 0)
    assert "No significantly elevated risk" in report or "No risk categories" in report


def test_generate_report_uses_template_without_key():
    report = generate_report(_sample_risks(), _sample_recs(), 1000, 50, openai_api_key="")
    assert "IMPORTANT DISCLAIMER" in report
    assert "Executive Summary" in report


def test_build_prompt_contains_data():
    prompt = _build_prompt(_sample_risks(), _sample_recs(), 1000, 50)
    assert "rs10757274" in prompt
    assert "MTHFR" in prompt or "methylfolate" in prompt.lower()
    assert "1000" in prompt
    assert "IMPORTANT DISCLAIMER" in prompt
