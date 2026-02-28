"""Integration tests for microbiome finalization.

Covers:
- New correlator rules (gut-axis methylation, MTHFR-gut)
- Stale-check re-analysis task logic
- Microbiome + correlator end-to-end data flow
- Disclaimer text in analysis output
- Cross-domain display text assertions
"""

import json
import sys
import types
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from app.extensions import db
from app.utils.correlator import (
    CorrelationInsight,
    run_full_unified_analysis,
    run_unified_correlation,
)

# --------------------------------------------------------------------------- #
# Celery is not installed in the test environment.  We inject a lightweight    #
# mock into sys.modules so that `from celery import shared_task` resolves to  #
# a no-op decorator and the task function can be called directly.             #
# --------------------------------------------------------------------------- #
if "celery" not in sys.modules:
    _celery_mock = types.ModuleType("celery")

    def _shared_task(_fn=None, bind=False, **_kw):
        """Fake shared_task: returns the raw function (or a passthrough decorator)."""
        def _wrap(fn):
            import functools

            if bind:
                # Celery passes the task instance as first arg when bind=True.
                # We supply a lightweight mock so the function can be called
                # without arguments in tests.
                _self_mock = MagicMock()
                _self_mock.request = MagicMock(retries=0)
                _self_mock.max_retries = _kw.get("max_retries", 3)

                @functools.wraps(fn)
                def _bound(*args, **kwargs):
                    return fn(_self_mock, *args, **kwargs)

                _bound.delay = lambda *a, **k: None
                _bound.apply_async = lambda *a, **k: None
                return _bound
            else:
                fn.delay = lambda *a, **k: None
                fn.apply_async = lambda *a, **k: None
                return fn

        if _fn is not None:
            return _wrap(_fn)
        return _wrap

    _celery_mock.shared_task = _shared_task  # type: ignore[attr-defined]
    _celery_mock.Celery = MagicMock  # type: ignore[attr-defined]
    sys.modules["celery"] = _celery_mock


@pytest.fixture()
def app():
    flask_app = create_app("testing")
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


# ── Fixture data ────────────────────────────────────────────────────────────


@pytest.fixture()
def full_variants():
    """Variants that trigger multiple rules."""
    return [
        {"rsid": "rs9939609", "gene": "FTO", "genotype": "AT", "risk_level": "elevated"},
        {"rsid": "rs4680", "gene": "COMT", "genotype": "AG", "risk_level": "elevated"},
        {"rsid": "rs4988235", "gene": "LCT/MCM6", "genotype": "CC", "risk_level": "elevated"},
        {"rsid": "rs2066844", "gene": "NOD2", "genotype": "CT", "risk_level": "elevated"},
        {"rsid": "rs1801133", "gene": "MTHFR", "genotype": "CT", "risk_level": "elevated"},
    ]


@pytest.fixture()
def full_blood_markers():
    return [
        {"marker_name": "hemoglobin_a1c", "value": 6.0, "unit": "%", "flag": "H"},
        {"marker_name": "hs_crp", "value": 4.5, "unit": "mg/L", "flag": "H"},
        {"marker_name": "calcium", "value": 7.5, "unit": "mg/dL", "flag": "L"},
        {"marker_name": "vitamin_d", "value": 15.0, "unit": "ng/mL", "flag": "L"},
        {"marker_name": "cholesterol_ldl", "value": 180, "unit": "mg/dL", "flag": "H"},
    ]


@pytest.fixture()
def full_wearable_summaries():
    return [
        {"data_type": "activity", "date": "2026-02-28",
         "summary": {"steps": 3500, "active_minutes": 12, "calories_burned": 1700}},
        {"data_type": "sleep", "date": "2026-02-28",
         "summary": {"total_sleep_minutes": 310, "deep_sleep_minutes": 30}},
        {"data_type": "stress", "date": "2026-02-28",
         "summary": {"stress_score": 75}},
        {"data_type": "hrv", "date": "2026-02-28",
         "summary": {"avg_hrv_ms": 22}},
    ]


@pytest.fixture()
def full_microbiome_profile():
    return {
        "enterotype": "Bacteroides",
        "diversity": {"shannon": 2.2, "simpson": 0.70, "chao1": 70, "observed_otus": 25},
        "composition": {
            "phylum": [
                {"name": "Firmicutes", "abundance": 0.55},
                {"name": "Bacteroidetes", "abundance": 0.12},
                {"name": "Proteobacteria", "abundance": 0.20},
                {"name": "Actinobacteria", "abundance": 0.04},
            ],
            "genus": [
                {"name": "Bacteroides", "abundance": 0.10},
                {"name": "Bifidobacterium", "abundance": 0.008},
                {"name": "Faecalibacterium", "abundance": 0.015},
                {"name": "Lactobacillus", "abundance": 0.003},
                {"name": "Roseburia", "abundance": 0.05},
            ],
        },
    }


@pytest.fixture()
def full_epigenetic_overlays():
    return [
        {"gene": "TNF", "region": "promoter", "modification": "hypomethylated"},
        {"gene": "NOD2", "region": "enhancer", "modification": "H3K27ac"},
        {"gene": "SLC6A4", "region": "promoter", "modification": "hypermethylated"},
        {"gene": "MTHFR", "region": "exon1", "modification": "hypomethylated"},
        {"gene": "IL6", "region": "promoter", "modification": "hypomethylated"},
    ]


# ── New correlator rule tests ───────────────────────────────────────────────


class TestGutAxisMethylationRule:
    """Tests for the gut_axis_methylation rule (SLC6A4 + diversity + Vitamin D)."""

    def test_gut_axis_methylation_fires(
        self, full_variants, full_blood_markers, full_wearable_summaries,
        full_microbiome_profile, full_epigenetic_overlays,
    ):
        """SLC6A4 epigenetic + low diversity + low Vitamin D → gut-axis insight."""
        correlations = run_unified_correlation(
            user_variants=full_variants,
            blood_markers=full_blood_markers,
            wearable_summaries=full_wearable_summaries,
            microbiome_profile=full_microbiome_profile,
            epigenetic_overlays=full_epigenetic_overlays,
        )
        titles = [c.title for c in correlations]
        assert any("gut axis" in t.lower() and "epigenetic" in t.lower() for t in titles)

    def test_gut_axis_body_mentions_serotonin(
        self, full_variants, full_blood_markers, full_wearable_summaries,
        full_microbiome_profile, full_epigenetic_overlays,
    ):
        correlations = run_unified_correlation(
            user_variants=full_variants,
            blood_markers=full_blood_markers,
            wearable_summaries=full_wearable_summaries,
            microbiome_profile=full_microbiome_profile,
            epigenetic_overlays=full_epigenetic_overlays,
        )
        gut_axis = [c for c in correlations if "SLC6A4" in c.body or "serotonin" in c.body]
        assert len(gut_axis) >= 1
        assert "serotonin" in gut_axis[0].body.lower()

    def test_gut_axis_not_fired_without_slc6a4_overlay(
        self, full_variants, full_blood_markers, full_wearable_summaries,
        full_microbiome_profile,
    ):
        """Without the SLC6A4 epigenetic overlay, rule should not fire."""
        overlays = [{"gene": "TNF", "region": "promoter", "modification": "hypomethylated"}]
        correlations = run_unified_correlation(
            user_variants=full_variants,
            blood_markers=full_blood_markers,
            wearable_summaries=full_wearable_summaries,
            microbiome_profile=full_microbiome_profile,
            epigenetic_overlays=overlays,
        )
        titles = [c.title for c in correlations]
        assert not any("SLC6A4" in t or "serotonin" in t.lower() for t in titles)


class TestMthfrGutMethylationRule:
    """Tests for the mthfr_gut_methylation rule (MTHFR + Bifidobacterium + epigenetic)."""

    def test_mthfr_gut_axis_fires(
        self, full_variants, full_blood_markers, full_wearable_summaries,
        full_microbiome_profile, full_epigenetic_overlays,
    ):
        """MTHFR variant + low Bifidobacterium + MTHFR epigenetic → folate-gut axis."""
        correlations = run_unified_correlation(
            user_variants=full_variants,
            blood_markers=full_blood_markers,
            wearable_summaries=full_wearable_summaries,
            microbiome_profile=full_microbiome_profile,
            epigenetic_overlays=full_epigenetic_overlays,
        )
        titles = [c.title for c in correlations]
        assert any("MTHFR" in t for t in titles)

    def test_mthfr_body_mentions_folate(
        self, full_variants, full_blood_markers, full_wearable_summaries,
        full_microbiome_profile, full_epigenetic_overlays,
    ):
        correlations = run_unified_correlation(
            user_variants=full_variants,
            blood_markers=full_blood_markers,
            wearable_summaries=full_wearable_summaries,
            microbiome_profile=full_microbiome_profile,
            epigenetic_overlays=full_epigenetic_overlays,
        )
        mthfr = [c for c in correlations if "MTHFR" in c.title]
        assert len(mthfr) >= 1
        assert "folate" in mthfr[0].body.lower()

    def test_mthfr_has_three_data_sources(
        self, full_variants, full_blood_markers, full_wearable_summaries,
        full_microbiome_profile, full_epigenetic_overlays,
    ):
        correlations = run_unified_correlation(
            user_variants=full_variants,
            blood_markers=full_blood_markers,
            wearable_summaries=full_wearable_summaries,
            microbiome_profile=full_microbiome_profile,
            epigenetic_overlays=full_epigenetic_overlays,
        )
        mthfr = [c for c in correlations if "MTHFR" in c.title]
        assert len(mthfr) >= 1
        assert set(mthfr[0].data_sources) == {"genome", "microbiome", "epigenetics"}


# ── Cross-domain display text tests ─────────────────────────────────────────


class TestCrossDomainDisplayText:
    """Verify that cross-domain insights produce proper display text."""

    def test_all_correlations_have_body(
        self, full_variants, full_blood_markers, full_wearable_summaries,
        full_microbiome_profile, full_epigenetic_overlays,
    ):
        correlations = run_unified_correlation(
            user_variants=full_variants,
            blood_markers=full_blood_markers,
            wearable_summaries=full_wearable_summaries,
            microbiome_profile=full_microbiome_profile,
            epigenetic_overlays=full_epigenetic_overlays,
        )
        for c in correlations:
            assert len(c.body) > 20, f"Correlation '{c.title}' body is too short"
            assert "{" not in c.body, f"Unformatted template in '{c.title}': {c.body[:80]}"

    def test_all_correlations_have_recommendations(
        self, full_variants, full_blood_markers, full_wearable_summaries,
        full_microbiome_profile, full_epigenetic_overlays,
    ):
        correlations = run_unified_correlation(
            user_variants=full_variants,
            blood_markers=full_blood_markers,
            wearable_summaries=full_wearable_summaries,
            microbiome_profile=full_microbiome_profile,
            epigenetic_overlays=full_epigenetic_overlays,
        )
        for c in correlations:
            assert len(c.recommendations) >= 1, f"'{c.title}' has no recommendations"

    def test_full_analysis_narrative_covers_findings(
        self, full_variants, full_blood_markers, full_wearable_summaries,
        full_microbiome_profile, full_epigenetic_overlays,
    ):
        result = run_full_unified_analysis(
            user_id="integration-user",
            user_variants=full_variants,
            blood_markers=full_blood_markers,
            wearable_summaries=full_wearable_summaries,
            microbiome_profile=full_microbiome_profile,
            epigenetic_overlays=full_epigenetic_overlays,
        )
        assert "Priority Findings" in result.ai_narrative
        assert result.analysis_date

    def test_full_analysis_all_domains_available(
        self, full_variants, full_blood_markers, full_wearable_summaries,
        full_microbiome_profile, full_epigenetic_overlays,
    ):
        result = run_full_unified_analysis(
            user_id="integration-user",
            user_variants=full_variants,
            blood_markers=full_blood_markers,
            wearable_summaries=full_wearable_summaries,
            microbiome_profile=full_microbiome_profile,
            epigenetic_overlays=full_epigenetic_overlays,
        )
        available = [d for d in result.domains if d.status == "available"]
        assert len(available) == 5

    def test_to_dict_json_serializable(
        self, full_variants, full_blood_markers, full_wearable_summaries,
        full_microbiome_profile, full_epigenetic_overlays,
    ):
        result = run_full_unified_analysis(
            user_id="integration-user",
            user_variants=full_variants,
            blood_markers=full_blood_markers,
            wearable_summaries=full_wearable_summaries,
            microbiome_profile=full_microbiome_profile,
            epigenetic_overlays=full_epigenetic_overlays,
        )
        serialized = json.dumps(result.to_dict())
        assert len(serialized) > 100


# ── Stale-check task tests ──────────────────────────────────────────────────


class TestCheckAndReanalyzeStale:
    """Tests for the check_and_reanalyze_stale Celery task."""

    def _create_user(self):
        from app.models.user import User
        user = User(
            email="stale-test@example.com",
            password_hash="hashed",
            tos_accepted_at=datetime.now(timezone.utc),
            data_encryption_key_enc=b"\x00" * 32,
        )
        db.session.add(user)
        db.session.commit()
        return user

    def _create_microbiome_upload(self, user, completed_days_ago=3):
        from app.models.microbiome import MicrobiomeAnalysis, MicrobiomeUpload
        upload = MicrobiomeUpload(
            user_id=user.id,
            filename_original="test.biom",
            file_type="biom",
            data_type="16s_rrna",
            file_hash_sha256="a" * 64,
            file_path_encrypted="/tmp/test.enc",
            file_size_bytes=1000,
            status="complete",
        )
        db.session.add(upload)
        db.session.flush()

        analysis = MicrobiomeAnalysis(
            upload_id=upload.id,
            status="complete",
            completed_at=datetime.now(timezone.utc) - timedelta(days=completed_days_ago),
        )
        db.session.add(analysis)
        db.session.commit()
        return upload, analysis

    def test_skips_when_no_new_data(self, app):
        """Should skip re-analysis when no cross-domain data is newer."""
        user = self._create_user()
        self._create_microbiome_upload(user, completed_days_ago=1)

        from app.tasks.microbiome_tasks import check_and_reanalyze_stale
        with patch("app.tasks.microbiome_tasks.run_microbiome_analysis") as mock_task:
            mock_task.delay = lambda *a, **kw: None
            result = check_and_reanalyze_stale()

        assert result["dispatched"] == 0
        assert result["skipped"] == 1

    def test_triggers_when_newer_blood(self, app):
        """Should trigger re-analysis when a new blood upload exists."""
        from app.models.blood import BloodUpload
        user = self._create_user()
        self._create_microbiome_upload(user, completed_days_ago=3)

        # Add a blood upload from yesterday (newer than analysis)
        blood = BloodUpload(
            user_id=user.id,
            filename_original="blood.csv",
            file_type="csv",
            file_path_encrypted="/tmp/blood.enc",
            status="parsed",
            test_date=date(2026, 2, 27),
        )
        blood.uploaded_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.session.add(blood)
        db.session.commit()

        from app.tasks.microbiome_tasks import check_and_reanalyze_stale
        with patch("app.tasks.microbiome_tasks.run_microbiome_analysis") as mock_task:
            mock_task.delay = lambda *a, **kw: None
            result = check_and_reanalyze_stale()

        assert result["dispatched"] == 1

    def test_triggers_when_newer_genome(self, app):
        """Should trigger re-analysis when a new genome upload exists."""
        from app.models.genome import GenomeUpload
        user = self._create_user()
        self._create_microbiome_upload(user, completed_days_ago=3)

        genome = GenomeUpload(
            user_id=user.id,
            filename_original="genome.vcf",
            file_hash_sha256="b" * 64,
            file_path_encrypted="/tmp/genome.enc",
            file_size_bytes=5000,
            source_service="other",
            status="uploaded",
        )
        genome.uploaded_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.session.add(genome)
        db.session.commit()

        from app.tasks.microbiome_tasks import check_and_reanalyze_stale
        with patch("app.tasks.microbiome_tasks.run_microbiome_analysis") as mock_task:
            mock_task.delay = lambda *a, **kw: None
            result = check_and_reanalyze_stale()

        assert result["dispatched"] == 1


# ── Disclaimer tests ────────────────────────────────────────────────────────


class TestDisclaimerContent:
    """Verify disclaimers contain proper microbiome warnings."""

    def test_unified_result_disclaimer(self):
        result = run_full_unified_analysis(
            user_id="test",
            user_variants=[],
            blood_markers=[],
            wearable_summaries=[],
        )
        assert "NOT medical advice" in result.disclaimer
        assert "informational" in result.disclaimer

    def test_narrative_includes_disclaimer(self):
        result = run_full_unified_analysis(
            user_id="test",
            user_variants=[],
            blood_markers=[],
            wearable_summaries=[],
        )
        assert "NOT" in result.ai_narrative
        assert "medical" in result.ai_narrative.lower()

    def test_correlation_insight_serialization(self):
        insight = CorrelationInsight(
            title="Test Microbiome Insight",
            body="Microbiome-gut axis: Epigenetic changes may explain improved blood markers.",
            category="cross_domain",
            confidence="medium",
            priority=80,
            data_sources=["microbiome", "epigenetics", "blood"],
            recommendations=["Consult physician"],
        )
        d = insight.to_dict()
        assert "Microbiome-gut axis" in d["body"]
        assert len(d["data_sources"]) == 3


# ── Analysis route disclaimer test ──────────────────────────────────────────


class TestAnalysisRouteDisclaimer:
    """Verify the /api/v1/analysis/daily endpoint returns disclaimer."""

    def _register_and_login(self, client):
        client.post("/api/v1/auth/register", json={
            "email": "discl@test.com", "password": "TestPass123!", "tos_accepted": True,
        })
        res = client.post("/api/v1/auth/login", json={
            "email": "discl@test.com", "password": "TestPass123!",
        })
        return res.json["access_token"]

    def test_daily_analysis_returns_disclaimer(self, client):
        token = self._register_and_login(client)
        res = client.get(
            "/api/v1/analysis/daily",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json
        assert "disclaimer" in data
        assert "NOT" in data["disclaimer"]

    def test_daily_analysis_returns_correlations_key(self, client):
        token = self._register_and_login(client)
        res = client.get(
            "/api/v1/analysis/daily",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = res.json
        assert "correlations" in data
        assert isinstance(data["correlations"], list)

    def test_daily_analysis_returns_domains(self, client):
        token = self._register_and_login(client)
        res = client.get(
            "/api/v1/analysis/daily",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = res.json
        assert "domains" in data
        assert isinstance(data["domains"], dict)
