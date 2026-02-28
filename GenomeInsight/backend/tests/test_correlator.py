"""Tests for the unified cross-domain correlator engine."""

import pytest

from app.utils.correlator import (
    CorrelationInsight,
    DomainSummary,
    UnifiedAnalysisResult,
    build_blood_summary,
    build_epigenetics_summary,
    build_genome_summary,
    build_microbiome_summary,
    build_wearable_summary,
    run_full_unified_analysis,
    run_unified_correlation,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_variants():
    return [
        {"rsid": "rs9939609", "gene": "FTO", "genotype": "AT", "risk_level": "elevated"},
        {"rsid": "rs4680", "gene": "COMT", "genotype": "AG", "risk_level": "elevated"},
        {"rsid": "rs4988235", "gene": "LCT/MCM6", "genotype": "CC", "risk_level": "elevated"},
        {"rsid": "rs2066844", "gene": "NOD2", "genotype": "CT", "risk_level": "elevated"},
    ]


@pytest.fixture()
def sample_blood_markers():
    return [
        {"marker_name": "hemoglobin_a1c", "marker_display_name": "HbA1c",
         "value": 6.0, "unit": "%", "flag": "H"},
        {"marker_name": "hs_crp", "marker_display_name": "hs-CRP",
         "value": 4.5, "unit": "mg/L", "flag": "H"},
        {"marker_name": "calcium", "marker_display_name": "Calcium",
         "value": 7.5, "unit": "mg/dL", "flag": "L"},
        {"marker_name": "vitamin_d", "marker_display_name": "Vitamin D",
         "value": 15.0, "unit": "ng/mL", "flag": "L"},
    ]


@pytest.fixture()
def sample_wearable_summaries():
    return [
        {"data_type": "activity", "date": "2026-02-28",
         "summary": {"steps": 4500, "active_minutes": 15, "calories_burned": 1800}},
        {"data_type": "sleep", "date": "2026-02-28",
         "summary": {"total_sleep_minutes": 320, "deep_sleep_minutes": 35}},
        {"data_type": "stress", "date": "2026-02-28",
         "summary": {"stress_score": 72}},
        {"data_type": "hrv", "date": "2026-02-28",
         "summary": {"avg_hrv_ms": 25}},
        {"data_type": "heart_rate", "date": "2026-02-28",
         "summary": {"avg_hr_bpm": 78, "resting_hr_bpm": 68}},
    ]


@pytest.fixture()
def sample_microbiome_profile():
    return {
        "enterotype": "Bacteroides",
        "diversity": {"shannon": 2.3, "simpson": 0.72, "chao1": 80, "observed_otus": 30},
        "composition": {
            "phylum": [
                {"name": "Firmicutes", "abundance": 0.55},
                {"name": "Bacteroidetes", "abundance": 0.15},
                {"name": "Proteobacteria", "abundance": 0.18},
                {"name": "Actinobacteria", "abundance": 0.05},
            ],
            "genus": [
                {"name": "Bacteroides", "abundance": 0.12},
                {"name": "Roseburia", "abundance": 0.08},
                {"name": "Bifidobacterium", "abundance": 0.01},
                {"name": "Faecalibacterium", "abundance": 0.02},
                {"name": "Lactobacillus", "abundance": 0.005},
            ],
        },
    }


@pytest.fixture()
def sample_epigenetic_overlays():
    return [
        {"gene": "TNF", "region": "promoter", "modification": "hypomethylated"},
        {"gene": "NOD2", "region": "enhancer", "modification": "H3K27ac"},
        {"gene": "IL6", "region": "promoter", "modification": "hypomethylated"},
    ]


# ── Multi-domain correlation tests ──────────────────────────────────────────


class TestRunUnifiedCorrelation:
    def test_fto_obesity_loop(self, sample_variants, sample_blood_markers,
                              sample_wearable_summaries, sample_microbiome_profile):
        """FTO variant + high F/B ratio + low steps → metabolic risk loop."""
        correlations = run_unified_correlation(
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
            microbiome_profile=sample_microbiome_profile,
        )
        titles = [c.title for c in correlations]
        assert any("FTO" in t for t in titles)

    def test_comt_stress_gut(self, sample_variants, sample_blood_markers,
                             sample_wearable_summaries, sample_microbiome_profile):
        """COMT variant + low diversity + high stress → gut-brain axis."""
        correlations = run_unified_correlation(
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
            microbiome_profile=sample_microbiome_profile,
        )
        titles = [c.title for c in correlations]
        assert any("COMT" in t for t in titles)

    def test_lactose_triad(self, sample_variants, sample_blood_markers,
                           sample_wearable_summaries, sample_microbiome_profile):
        """LCT variant + low Lactobacillus + low calcium → lactose triad."""
        correlations = run_unified_correlation(
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
            microbiome_profile=sample_microbiome_profile,
        )
        titles = [c.title for c in correlations]
        assert any("Lactose" in t or "lactose" in t for t in titles)

    def test_inflammation_cascade(self, sample_variants, sample_blood_markers,
                                  sample_wearable_summaries,
                                  sample_microbiome_profile,
                                  sample_epigenetic_overlays):
        """TNF epigenetic + high Proteobacteria + high CRP → inflammation cascade."""
        correlations = run_unified_correlation(
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
            microbiome_profile=sample_microbiome_profile,
            epigenetic_overlays=sample_epigenetic_overlays,
        )
        titles = [c.title for c in correlations]
        assert any("inflammation" in t.lower() for t in titles)

    def test_sugar_gut_disruption(self, sample_variants, sample_blood_markers,
                                  sample_wearable_summaries,
                                  sample_microbiome_profile):
        """High HbA1c + low Bifidobacterium + low steps."""
        correlations = run_unified_correlation(
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
            microbiome_profile=sample_microbiome_profile,
        )
        titles = [c.title for c in correlations]
        assert any("sugar" in t.lower() or "Bifidobacterium" in t for t in titles)

    def test_sleep_gut_cycle(self, sample_variants, sample_blood_markers,
                             sample_wearable_summaries,
                             sample_microbiome_profile):
        """Low diversity + poor sleep + low HRV."""
        correlations = run_unified_correlation(
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
            microbiome_profile=sample_microbiome_profile,
        )
        titles = [c.title for c in correlations]
        assert any("sleep" in t.lower() and "HRV" in t for t in titles)

    def test_crohns_triad(self, sample_variants, sample_blood_markers,
                          sample_wearable_summaries,
                          sample_microbiome_profile,
                          sample_epigenetic_overlays):
        """NOD2 variant + NOD2 epigenetic + low Faecalibacterium."""
        correlations = run_unified_correlation(
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
            microbiome_profile=sample_microbiome_profile,
            epigenetic_overlays=sample_epigenetic_overlays,
        )
        titles = [c.title for c in correlations]
        assert any("NOD2" in t for t in titles)

    def test_results_sorted_by_priority(self, sample_variants, sample_blood_markers,
                                        sample_wearable_summaries,
                                        sample_microbiome_profile,
                                        sample_epigenetic_overlays):
        """Results should be sorted by priority descending."""
        correlations = run_unified_correlation(
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
            microbiome_profile=sample_microbiome_profile,
            epigenetic_overlays=sample_epigenetic_overlays,
        )
        priorities = [c.priority for c in correlations]
        assert priorities == sorted(priorities, reverse=True)

    def test_no_data_returns_empty(self):
        """No data sources → no correlations."""
        result = run_unified_correlation(
            user_variants=[],
            blood_markers=[],
            wearable_summaries=[],
        )
        assert result == []

    def test_wearable_only_returns_inferred_only(self, sample_wearable_summaries):
        """Wearable-only → only wearable-based inferred insights, no genome/blood rules."""
        result = run_unified_correlation(
            user_variants=[],
            blood_markers=[],
            wearable_summaries=sample_wearable_summaries,
        )
        # Should not trigger any multi-domain rule that requires genome or blood
        for c in result:
            assert "genome" not in c.data_sources
            assert "blood" not in c.data_sources


# ── Inferred microbiome insight tests ────────────────────────────────────────


class TestInferredMicrobiomeInsights:
    def test_high_sugar_inference(self, sample_blood_markers, sample_wearable_summaries):
        """High HbA1c + low active minutes → sugar-gut disruption inference."""
        correlations = run_unified_correlation(
            user_variants=[],
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
        )
        titles = [c.title for c in correlations]
        assert any("sugar" in t.lower() and "microbiome" in t.lower() for t in titles)

    def test_stress_sleep_inference(self, sample_wearable_summaries):
        """High stress + low deep sleep → gut disruption inference."""
        correlations = run_unified_correlation(
            user_variants=[],
            blood_markers=[],
            wearable_summaries=sample_wearable_summaries,
        )
        titles = [c.title for c in correlations]
        assert any("stress" in t.lower() and "sleep" in t.lower() for t in titles)

    def test_inference_without_microbiome(self, sample_blood_markers,
                                          sample_wearable_summaries):
        """Inferred insights should work even without a microbiome sample."""
        correlations = run_unified_correlation(
            user_variants=[],
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
            microbiome_profile=None,
        )
        # Should have at least the inferred insights
        assert len(correlations) > 0
        assert all(c.category == "cross_domain" for c in correlations)


# ── Domain summary builders ─────────────────────────────────────────────────


class TestDomainSummaries:
    def test_genome_summary_available(self, sample_variants):
        summary = build_genome_summary(sample_variants)
        assert summary.status == "available"
        assert summary.metrics["total_variants"] == 4

    def test_genome_summary_unavailable(self):
        summary = build_genome_summary([])
        assert summary.status == "unavailable"

    def test_blood_summary_with_flags(self, sample_blood_markers):
        summary = build_blood_summary(sample_blood_markers)
        assert summary.status == "available"
        assert summary.metrics["flagged_high"] == 2
        assert summary.metrics["flagged_low"] == 2

    def test_blood_summary_unavailable(self):
        summary = build_blood_summary([])
        assert summary.status == "unavailable"

    def test_wearable_summary(self, sample_wearable_summaries):
        summary = build_wearable_summary(sample_wearable_summaries)
        assert summary.status == "available"
        assert "activity" in summary.metrics
        assert "sleep" in summary.metrics
        assert len(summary.highlights) >= 1

    def test_wearable_summary_unavailable(self):
        summary = build_wearable_summary([])
        assert summary.status == "unavailable"

    def test_microbiome_summary(self, sample_microbiome_profile):
        summary = build_microbiome_summary(sample_microbiome_profile)
        assert summary.status == "available"
        assert summary.metrics["enterotype"] == "Bacteroides"

    def test_microbiome_summary_unavailable(self):
        summary = build_microbiome_summary(None)
        assert summary.status == "unavailable"

    def test_epigenetics_summary(self, sample_epigenetic_overlays):
        summary = build_epigenetics_summary(sample_epigenetic_overlays)
        assert summary.status == "available"
        assert summary.metrics["genes_affected"] == 3

    def test_epigenetics_summary_unavailable(self):
        summary = build_epigenetics_summary([])
        assert summary.status == "unavailable"


# ── Full unified analysis ───────────────────────────────────────────────────


class TestRunFullUnifiedAnalysis:
    def test_full_analysis_structure(self, sample_variants, sample_blood_markers,
                                     sample_wearable_summaries,
                                     sample_microbiome_profile,
                                     sample_epigenetic_overlays):
        result = run_full_unified_analysis(
            user_id="test-user-id",
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
            microbiome_profile=sample_microbiome_profile,
            epigenetic_overlays=sample_epigenetic_overlays,
        )
        assert isinstance(result, UnifiedAnalysisResult)
        assert result.user_id == "test-user-id"
        assert len(result.domains) == 5
        assert len(result.correlations) > 0
        assert "Unified Health Analysis" in result.ai_narrative
        assert "NOT medical advice" in result.disclaimer

    def test_full_analysis_to_dict(self, sample_variants, sample_blood_markers,
                                   sample_wearable_summaries):
        result = run_full_unified_analysis(
            user_id="test-user",
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
        )
        d = result.to_dict()
        assert "user_id" in d
        assert "domains" in d
        assert "correlations" in d
        assert isinstance(d["domains"], list)

    def test_all_domains_present(self, sample_variants, sample_blood_markers,
                                  sample_wearable_summaries):
        result = run_full_unified_analysis(
            user_id="test-user",
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
        )
        domain_names = {d.domain for d in result.domains}
        assert domain_names == {"genome", "blood", "wearable", "microbiome", "epigenetics"}

    def test_narrative_mentions_missing_domains(self, sample_wearable_summaries):
        """Narrative should mention unavailable data sources."""
        result = run_full_unified_analysis(
            user_id="test-user",
            user_variants=[],
            blood_markers=[],
            wearable_summaries=sample_wearable_summaries,
        )
        assert "Missing" in result.ai_narrative or "missing" in result.ai_narrative.lower()

    def test_existing_insights_merged(self, sample_variants, sample_blood_markers,
                                       sample_wearable_summaries):
        existing = [
            {"title": "Custom insight", "body": "Test body", "category": "daily",
             "confidence": "medium", "data_sources": ["custom"], "priority": 30},
        ]
        result = run_full_unified_analysis(
            user_id="test-user",
            user_variants=sample_variants,
            blood_markers=sample_blood_markers,
            wearable_summaries=sample_wearable_summaries,
            existing_insights=existing,
        )
        titles = [c.title for c in result.correlations]
        assert "Custom insight" in titles


# ── CorrelationInsight dataclass ─────────────────────────────────────────────


class TestCorrelationInsight:
    def test_to_dict(self):
        insight = CorrelationInsight(
            title="Test",
            body="Test body",
            category="cross_domain",
            confidence="high",
            priority=80,
            data_sources=["genome", "microbiome"],
            recommendations=["Eat more fiber"],
            tags=["gut_health"],
        )
        d = insight.to_dict()
        assert d["title"] == "Test"
        assert d["priority"] == 80
        assert "genome" in d["data_sources"]
        assert "Eat more fiber" in d["recommendations"]
