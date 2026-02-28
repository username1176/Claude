"""Tests for wearable client utilities."""

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.utils.wearable_client import (
    CrossDomainInsight,
    TerraAuthResult,
    TerraTokens,
    WearableDaySummary,
    encrypt_token,
    decrypt_token,
    exchange_terra_token,
    extract_summary,
    generate_cross_domain_insights,
    generate_daily_report,
    generate_terra_auth_url,
    SUPPORTED_PROVIDERS,
    WEARABLE_DATA_TYPES,
)


# ── OAuth helpers ────────────────────────────────────────────────────────────


class TestGenerateTerraAuthUrl:
    def test_returns_auth_result_with_api_key(self):
        result = generate_terra_auth_url(
            provider="fitbit",
            terra_api_key="test-key",
            redirect_uri="http://localhost/callback",
        )
        assert isinstance(result, TerraAuthResult)
        assert result.provider == "fitbit"
        assert "fitbit" in result.auth_url
        assert result.state  # Non-empty state token
        assert "generateWidgetSession" in result.auth_url

    def test_returns_fallback_url_without_api_key(self):
        result = generate_terra_auth_url(
            provider="garmin",
            terra_api_key="",
            redirect_uri="http://localhost/callback",
        )
        assert "widget.tryterra.co" in result.auth_url
        assert result.provider == "garmin"

    def test_state_is_unique(self):
        r1 = generate_terra_auth_url("fitbit", "", "http://localhost/cb")
        r2 = generate_terra_auth_url("fitbit", "", "http://localhost/cb")
        assert r1.state != r2.state


class TestExchangeTerraToken:
    def test_dev_fallback_without_client(self):
        tokens = exchange_terra_token(
            code="test-code",
            terra_api_key="",
            terra_dev_id="",
        )
        assert isinstance(tokens, TerraTokens)
        assert tokens.terra_user_id.startswith("terra_mock_")
        assert tokens.access_token.startswith("mock_access_")
        assert tokens.refresh_token.startswith("mock_refresh_")
        assert tokens.expires_at is not None

    def test_real_exchange_with_mock_client(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "user": {
                "user_id": "terra-user-123",
                "access_token": "real-access-token",
                "refresh_token": "real-refresh-token",
            }
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp

        tokens = exchange_terra_token(
            code="auth-code",
            terra_api_key="real-key",
            terra_dev_id="dev-123",
            client=mock_client,
        )
        assert tokens.terra_user_id == "terra-user-123"
        assert tokens.access_token == "real-access-token"

    def test_raises_on_api_error(self):
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("Connection refused")

        with pytest.raises(Exception, match="Connection refused"):
            exchange_terra_token(
                code="bad-code",
                terra_api_key="key",
                terra_dev_id="dev",
                client=mock_client,
            )


# ── Token encryption ────────────────────────────────────────────────────────


class TestTokenEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        dek = AESGCM.generate_key(bit_length=256)
        token = "my-secret-access-token"
        encrypted = encrypt_token(token, dek)
        decrypted = decrypt_token(encrypted, dek)
        assert decrypted == token

    def test_different_encryptions_differ(self):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        dek = AESGCM.generate_key(bit_length=256)
        token = "test-token"
        enc1 = encrypt_token(token, dek)
        enc2 = encrypt_token(token, dek)
        assert enc1 != enc2  # Different nonces


# ── Summary extraction ───────────────────────────────────────────────────────


class TestExtractSummary:
    def test_activity_flat_format(self):
        data = {"steps": 8500, "active_minutes": 45, "calories_burned": 2100}
        summary = extract_summary("activity", data)
        assert summary["steps"] == 8500
        assert summary["active_minutes"] == 45
        assert summary["calories_burned"] == 2100

    def test_activity_terra_nested_format(self):
        data = {
            "distance_data": {"steps": 9200, "distance_meters": 7500, "floors_climbed": 10},
            "calories_data": {"total_burned_calories": 2300},
            "active_durations_data": {"activity_seconds": 3600},
        }
        summary = extract_summary("activity", data)
        assert summary["steps"] == 9200
        assert summary["active_minutes"] == 60
        assert summary["calories_burned"] == 2300
        assert summary["distance_km"] == 7.5
        assert summary["floors_climbed"] == 10

    def test_sleep_flat_format(self):
        data = {
            "total_sleep_minutes": 420,
            "deep_sleep_minutes": 90,
            "rem_sleep_minutes": 105,
            "light_sleep_minutes": 225,
            "awakenings": 3,
            "sleep_score": 82,
        }
        summary = extract_summary("sleep", data)
        assert summary["total_sleep_minutes"] == 420
        assert summary["deep_sleep_minutes"] == 90
        assert summary["sleep_score"] == 82

    def test_sleep_terra_nested_format(self):
        data = {
            "sleep_durations_data": {
                "total_sleep_seconds": 25200,
                "asleep": {
                    "deep_sleep_seconds": 5400,
                    "rem_sleep_seconds": 6300,
                    "light_sleep_seconds": 13500,
                },
                "num_awakenings": 2,
            }
        }
        summary = extract_summary("sleep", data)
        assert summary["total_sleep_minutes"] == 420
        assert summary["deep_sleep_minutes"] == 90
        assert summary["rem_sleep_minutes"] == 105
        assert summary["awakenings"] == 2

    def test_heart_rate_summary(self):
        data = {"avg_hr_bpm": 68, "max_hr_bpm": 145, "resting_hr_bpm": 58}
        summary = extract_summary("heart_rate", data)
        assert summary["avg_hr_bpm"] == 68
        assert summary["resting_hr_bpm"] == 58

    def test_hrv_summary(self):
        data = {"avg_hrv_ms": 45, "max_hrv_ms": 80}
        summary = extract_summary("hrv", data)
        assert summary["avg_hrv_ms"] == 45

    def test_spo2_summary(self):
        data = {"avg_spo2_pct": 97, "min_spo2_pct": 94}
        summary = extract_summary("spo2", data)
        assert summary["avg_spo2_pct"] == 97

    def test_stress_summary(self):
        data = {"stress_score": 55, "rest_stress_minutes": 30}
        summary = extract_summary("stress", data)
        assert summary["stress_score"] == 55

    def test_unknown_type_returns_empty(self):
        summary = extract_summary("unknown_type", {"foo": "bar"})
        assert summary == {}


# ── Cross-domain insights ───────────────────────────────────────────────────


class TestGenerateCrossDomainInsights:
    def test_wearable_only_low_steps_alert(self):
        wearable_summaries = [
            {"data_type": "activity", "summary": {"steps": 3000, "active_minutes": 10}},
        ]
        insights = generate_cross_domain_insights(wearable_summaries)
        assert any("Low activity" in i.title for i in insights)

    def test_wearable_only_low_sleep_alert(self):
        wearable_summaries = [
            {"data_type": "sleep", "summary": {"total_sleep_minutes": 300}},
        ]
        insights = generate_cross_domain_insights(wearable_summaries)
        assert any("sleep" in i.title.lower() for i in insights)

    def test_no_alert_for_good_metrics(self):
        wearable_summaries = [
            {"data_type": "activity", "summary": {"steps": 10000, "active_minutes": 60}},
            {"data_type": "sleep", "summary": {"total_sleep_minutes": 480}},
        ]
        insights = generate_cross_domain_insights(wearable_summaries)
        # No alerts when metrics are good
        alerts = [i for i in insights if i.insight_type == "alert"]
        assert len(alerts) == 0

    def test_variant_wearable_correlation(self):
        wearable_summaries = [
            {"data_type": "sleep", "summary": {"deep_sleep_minutes": 45, "total_sleep_minutes": 400}},
        ]
        user_variants = [
            {"rsid": "rs6265", "gene": "BDNF", "genotype": "G/A", "risk_level": "elevated"},
        ]
        insights = generate_cross_domain_insights(
            wearable_summaries, user_variants=user_variants
        )
        bdnf_insights = [i for i in insights if "BDNF" in i.title]
        assert len(bdnf_insights) >= 1
        assert "genome:rs6265" in bdnf_insights[0].data_sources
        assert "wearable:sleep" in bdnf_insights[0].data_sources

    def test_variant_above_threshold_is_healthy(self):
        wearable_summaries = [
            {"data_type": "sleep", "summary": {"deep_sleep_minutes": 90}},
        ]
        user_variants = [
            {"rsid": "rs6265", "gene": "BDNF", "genotype": "G/G", "risk_level": "low"},
        ]
        insights = generate_cross_domain_insights(
            wearable_summaries, user_variants=user_variants
        )
        bdnf_insights = [i for i in insights if "BDNF" in i.title]
        assert len(bdnf_insights) >= 1
        assert "healthy range" in bdnf_insights[0].title

    def test_blood_wearable_correlation(self):
        wearable_summaries = [
            {"data_type": "activity", "summary": {"steps": 4000, "active_minutes": 15}},
        ]
        blood_markers = [
            {"marker_name": "hemoglobin_a1c", "value": 6.1, "unit": "%", "flag": "H"},
        ]
        insights = generate_cross_domain_insights(
            wearable_summaries, blood_markers=blood_markers
        )
        hba1c_insights = [i for i in insights if "hemoglobin_a1c" in i.title]
        assert len(hba1c_insights) >= 1
        assert "blood:hemoglobin_a1c" in hba1c_insights[0].data_sources

    def test_empty_summaries_returns_empty(self):
        insights = generate_cross_domain_insights([])
        assert insights == []

    def test_no_matching_variants_returns_wearable_only(self):
        wearable_summaries = [
            {"data_type": "activity", "summary": {"steps": 3000}},
        ]
        user_variants = [
            {"rsid": "rs999999", "gene": "UNKNOWN", "genotype": "A/A"},
        ]
        insights = generate_cross_domain_insights(
            wearable_summaries, user_variants=user_variants
        )
        # Should still produce wearable-only alerts (low steps)
        assert any("Low activity" in i.title for i in insights)


# ── Daily report ─────────────────────────────────────────────────────────────


class TestGenerateDailyReport:
    def test_report_contains_metrics(self):
        summaries = [
            {"data_type": "activity", "summary": {"steps": 8000, "active_minutes": 40}},
            {"data_type": "sleep", "summary": {"total_sleep_minutes": 420}},
        ]
        insights = [
            CrossDomainInsight(
                title="Good sleep quality",
                body="Your deep sleep was above average.",
                confidence="medium",
                data_sources=["wearable:sleep"],
            ),
        ]
        report = generate_daily_report(
            insights=insights,
            wearable_summaries=summaries,
            report_date=date(2026, 2, 28),
        )
        assert "Daily Health Report" in report
        assert "2026-02-28" in report
        assert "8000" in report
        assert "Good sleep quality" in report
        assert "Disclaimer" in report

    def test_empty_insights_still_has_structure(self):
        report = generate_daily_report(
            insights=[],
            wearable_summaries=[],
            report_date=date(2026, 2, 28),
        )
        assert "Daily Health Report" in report
        assert "No cross-domain insights" in report

    def test_alert_type_marked(self):
        insights = [
            CrossDomainInsight(
                title="Low steps",
                body="Only 2000 steps today.",
                confidence="high",
                insight_type="alert",
                data_sources=["wearable:activity"],
            ),
        ]
        report = generate_daily_report(
            insights=insights,
            wearable_summaries=[],
        )
        assert "[ALERT]" in report


# ── Constants ────────────────────────────────────────────────────────────────


class TestConstants:
    def test_supported_providers(self):
        assert "fitbit" in SUPPORTED_PROVIDERS
        assert "garmin" in SUPPORTED_PROVIDERS
        assert "oura" in SUPPORTED_PROVIDERS
        assert len(SUPPORTED_PROVIDERS) >= 5

    def test_data_types(self):
        assert "activity" in WEARABLE_DATA_TYPES
        assert "sleep" in WEARABLE_DATA_TYPES
        assert "heart_rate" in WEARABLE_DATA_TYPES
        assert "hrv" in WEARABLE_DATA_TYPES
