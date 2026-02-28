"""Integration tests for the cross-domain analysis pipeline.

Tests the full path from wearable data + genome variants + blood markers
through insight generation and daily report output.
"""

import json
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from app.extensions import db
from app.models.user import User
from app.models.wearable import DailyInsight, DailyWearableData, WearableConnection
from app.utils.wearable_client import (
    CrossDomainInsight,
    generate_cross_domain_insights,
    generate_daily_report,
    extract_summary,
)


# ── Helper ────────────────────────────────────────────────────────────────


def _register_and_login(client, email="integration@test.com"):
    client.post(
        "/api/v1/auth/register",
        data=json.dumps({
            "email": email,
            "password": "securepass12345",
            "tos_accepted": True,
        }),
        content_type="application/json",
    )
    resp = client.post(
        "/api/v1/auth/login",
        data=json.dumps({"email": email, "password": "securepass12345"}),
        content_type="application/json",
    )
    data = resp.get_json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user_id"]


def _seed_wearable_data(app, user_id):
    """Seed two days of wearable data for a user."""
    with app.app_context():
        conn = WearableConnection(
            user_id=user_id,
            provider="fitbit",
            terra_user_id="terra_fitbit_test",
            status="active",
        )
        db.session.add(conn)
        db.session.flush()

        for d, steps, sleep in [
            (date(2026, 2, 27), 3500, 310),
            (date(2026, 2, 28), 8500, 450),
        ]:
            db.session.add(DailyWearableData(
                user_id=user_id,
                connection_id=conn.id,
                date=d,
                data_type="activity",
                data_json=json.dumps({"steps": steps}),
                summary_json=json.dumps({"steps": steps, "active_minutes": steps // 100}),
            ))
            db.session.add(DailyWearableData(
                user_id=user_id,
                connection_id=conn.id,
                date=d,
                data_type="sleep",
                data_json=json.dumps({"total_sleep_minutes": sleep}),
                summary_json=json.dumps({
                    "total_sleep_minutes": sleep,
                    "deep_sleep_minutes": sleep // 5,
                }),
            ))
        db.session.commit()
        return conn.id


# ── End-to-end pipeline tests ────────────────────────────────────────────


class TestCrossDomainPipeline:
    """Test the full cross-domain insight generation pipeline."""

    def test_full_pipeline_wearable_only(self):
        """Low-step wearable data produces alert insights."""
        wearable_summaries = [
            {"data_type": "activity", "summary": {"steps": 3000, "active_minutes": 15}},
            {"data_type": "sleep", "summary": {"total_sleep_minutes": 310, "deep_sleep_minutes": 40}},
            {"data_type": "heart_rate", "summary": {"avg_hr_bpm": 72, "resting_hr_bpm": 62}},
            {"data_type": "hrv", "summary": {"avg_hrv_ms": 38}},
        ]
        insights = generate_cross_domain_insights(wearable_summaries)

        # Should flag low steps and low sleep
        alert_titles = [i.title for i in insights if i.insight_type == "alert"]
        assert any("activity" in t.lower() or "step" in t.lower() for t in alert_titles)
        assert any("sleep" in t.lower() for t in alert_titles)

    def test_full_pipeline_with_genome_and_blood(self):
        """Genome + blood + wearable produces correlated insights."""
        wearable_summaries = [
            {"data_type": "activity", "summary": {"steps": 4000, "active_minutes": 20}},
            {"data_type": "sleep", "summary": {
                "total_sleep_minutes": 380,
                "deep_sleep_minutes": 50,
            }},
        ]
        user_variants = [
            {"rsid": "rs6265", "gene": "BDNF", "genotype": "G/A", "risk_level": "elevated"},
            {"rsid": "rs7903146", "gene": "TCF7L2", "genotype": "C/T", "risk_level": "elevated"},
        ]
        blood_markers = [
            {"marker_name": "hemoglobin_a1c", "value": 6.2, "unit": "%", "flag": "H"},
        ]
        insights = generate_cross_domain_insights(
            wearable_summaries,
            user_variants=user_variants,
            blood_markers=blood_markers,
        )

        # Should have BDNF sleep correlation
        bdnf = [i for i in insights if "BDNF" in i.title]
        assert len(bdnf) >= 1
        assert "wearable:sleep" in bdnf[0].data_sources
        assert "genome:rs6265" in bdnf[0].data_sources

        # Should have HbA1c + activity correlation
        hba1c = [i for i in insights if "hemoglobin_a1c" in i.title]
        assert len(hba1c) >= 1
        assert "blood:hemoglobin_a1c" in hba1c[0].data_sources

    def test_daily_report_integrates_all_sources(self):
        """Daily report includes metrics, insights, and disclaimer."""
        summaries = [
            {"data_type": "activity", "summary": {"steps": 7500, "active_minutes": 35}},
            {"data_type": "sleep", "summary": {"total_sleep_minutes": 420}},
            {"data_type": "heart_rate", "summary": {"avg_hr_bpm": 68, "resting_hr_bpm": 58}},
            {"data_type": "hrv", "summary": {"avg_hrv_ms": 52}},
        ]
        insights = [
            CrossDomainInsight(
                title="BDNF: deep sleep in healthy range",
                body="Your deep sleep of 84 minutes is good for BDNF variant carriers.",
                confidence="medium",
                data_sources=["wearable:sleep", "genome:rs6265"],
            ),
            CrossDomainInsight(
                title="Low activity detected",
                body="Steps below 8,000. Try a 30-minute walk.",
                confidence="high",
                insight_type="alert",
                data_sources=["wearable:activity"],
            ),
        ]
        report = generate_daily_report(
            insights=insights,
            wearable_summaries=summaries,
            report_date=date(2026, 2, 28),
        )

        assert "Daily Health Report" in report
        assert "2026-02-28" in report
        assert "7500" in report
        assert "420" in report
        assert "BDNF" in report
        assert "[ALERT]" in report
        assert "Disclaimer" in report

    def test_good_metrics_no_alerts(self):
        """Users with healthy metrics get no alert-type insights."""
        wearable_summaries = [
            {"data_type": "activity", "summary": {"steps": 12000, "active_minutes": 75}},
            {"data_type": "sleep", "summary": {
                "total_sleep_minutes": 480,
                "deep_sleep_minutes": 100,
            }},
            {"data_type": "heart_rate", "summary": {"avg_hr_bpm": 62, "resting_hr_bpm": 55}},
            {"data_type": "hrv", "summary": {"avg_hrv_ms": 65}},
        ]
        insights = generate_cross_domain_insights(wearable_summaries)
        alerts = [i for i in insights if i.insight_type == "alert"]
        assert len(alerts) == 0


# ── API integration tests ────────────────────────────────────────────────


class TestInsightAPIIntegration:
    """Test the insights API returns correct cross-domain data."""

    def test_daily_insights_with_seeded_data(self, client, app):
        headers, user_id = _register_and_login(client)
        _seed_wearable_data(app, user_id)

        # Seed some insights
        with app.app_context():
            db.session.add(DailyInsight(
                user_id=user_id,
                date=date(2026, 2, 28),
                insight_type="alert",
                title="Low activity detected",
                body="Only 3,500 steps on Feb 27.",
                data_sources_json=json.dumps(["wearable:activity"]),
                confidence="high",
            ))
            db.session.add(DailyInsight(
                user_id=user_id,
                date=date(2026, 2, 28),
                insight_type="correlation",
                title="BDNF sleep correlation",
                body="Deep sleep linked to BDNF variant.",
                data_sources_json=json.dumps(["wearable:sleep", "genome:rs6265"]),
                confidence="medium",
            ))
            db.session.commit()

        # Fetch daily insights
        resp = client.get("/api/v1/insights/daily", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["insights"]) == 2
        types = {i["type"] for i in data["insights"]}
        assert "alert" in types
        assert "correlation" in types

    def test_wearable_data_after_connect_and_seed(self, client, app):
        """Verify wearable data endpoint returns seeded records."""
        headers, user_id = _register_and_login(client, email="wearable_int@test.com")
        _seed_wearable_data(app, user_id)

        # Get latest data
        resp = client.get("/api/v1/wearables/data/latest", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["date"] == "2026-02-28"
        assert len(data["data"]) == 2  # activity + sleep

        # Get historical data
        resp = client.get("/api/v1/wearables/data?days=7", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["data"]) == 4  # 2 days x 2 types

    def test_insight_generation_endpoint_queues(self, client, app):
        """POST /insights/generate returns queued status."""
        headers, user_id = _register_and_login(client, email="gen@test.com")
        _seed_wearable_data(app, user_id)

        resp = client.post("/api/v1/insights/generate", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "queued"

    def test_insight_history_pagination(self, client, app):
        """Insight history supports pagination and type filter."""
        headers, user_id = _register_and_login(client, email="hist@test.com")

        with app.app_context():
            for i in range(7):
                db.session.add(DailyInsight(
                    user_id=user_id,
                    date=date(2026, 2, 20 + i),
                    insight_type="alert" if i % 2 == 0 else "recommendation",
                    title=f"Insight {i}",
                    body=f"Body {i}",
                    confidence="medium",
                ))
            db.session.commit()

        # Page 1
        resp = client.get(
            "/api/v1/insights/history?page=1&per_page=3",
            headers=headers,
        )
        data = resp.get_json()
        assert data["total"] == 7
        assert len(data["insights"]) == 3
        assert data["pages"] == 3

        # Filter by type
        resp = client.get(
            "/api/v1/insights/history?type=alert",
            headers=headers,
        )
        data = resp.get_json()
        assert data["total"] == 4  # indices 0, 2, 4, 6


# ── Summary extraction edge cases ────────────────────────────────────────


class TestExtractSummaryEdgeCases:
    """Edge cases for the extract_summary function."""

    def test_empty_activity_returns_defaults(self):
        """Activity extractor returns zero-valued defaults for empty input."""
        summary = extract_summary("activity", {})
        assert summary["steps"] == 0
        assert summary["active_minutes"] == 0

    def test_unknown_type_returns_empty(self):
        assert extract_summary("unknown_type", {"foo": "bar"}) == {}

    def test_mixed_formats_activity(self):
        """When both flat and nested keys exist, nested takes priority for steps."""
        data = {
            "steps": 5000,
            "distance_data": {"steps": 7000, "distance_meters": 5500},
            "calories_data": {"total_burned_calories": 2100},
        }
        summary = extract_summary("activity", data)
        assert summary["steps"] == 7000

    def test_spo2_returns_all_keys(self):
        """SpO2 extractor always returns both avg and min keys."""
        data = {"avg_spo2_pct": 96}
        summary = extract_summary("spo2", data)
        assert summary["avg_spo2_pct"] == 96
        assert "min_spo2_pct" in summary  # Always present with default 0

    def test_stress_full_data(self):
        data = {
            "stress_score": 72,
            "rest_stress_minutes": 45,
            "activity_stress_minutes": 120,
            "low_stress_minutes": 180,
        }
        summary = extract_summary("stress", data)
        assert summary["stress_score"] == 72
