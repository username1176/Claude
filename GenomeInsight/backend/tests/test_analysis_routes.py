"""Tests for the unified analysis API endpoint."""

import json
from datetime import date

import pytest

from app.extensions import db
from app.models.wearable import DailyInsight, DailyWearableData, WearableConnection


def _register_and_login(client, email="analysis@test.com"):
    """Helper: register a user and return an auth header dict."""
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
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_user_id(client, headers):
    """Extract user_id from a simple API call."""
    # Minimal introspection — list wearable providers to prove auth works
    resp = client.get("/api/v1/wearables/providers", headers=headers)
    assert resp.status_code == 200
    # We need the actual user ID; decode from JWT
    import jwt
    token = headers["Authorization"].split(" ")[1]
    payload = jwt.decode(token, options={"verify_signature": False})
    return payload.get("sub") or payload.get("user_id")


# ── Daily analysis endpoint ──────────────────────────────────────────────────


def test_daily_analysis_empty(client):
    """Daily analysis with no data should return structure with unavailable domains."""
    headers = _register_and_login(client)
    resp = client.get("/api/v1/analysis/daily", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert "analysis_date" in data
    assert "domains" in data
    assert "correlations" in data
    assert "daily_insights" in data
    assert "ai_narrative" in data
    assert "disclaimer" in data

    # All domains should be unavailable
    for domain_name in ("genome", "blood", "wearable", "microbiome", "epigenetics"):
        assert domain_name in data["domains"]
        assert data["domains"][domain_name]["status"] == "unavailable"


def test_daily_analysis_requires_auth(client):
    resp = client.get("/api/v1/analysis/daily")
    assert resp.status_code == 401


def test_daily_analysis_with_wearable_data(client, app):
    """Daily analysis with wearable data should return wearable domain as available."""
    headers = _register_and_login(client)
    user_id = _get_user_id(client, headers)

    # Seed wearable data directly
    with app.app_context():
        conn = WearableConnection(
            user_id=user_id,
            provider="fitbit",
            terra_user_id="terra-test",
            status="active",
        )
        db.session.add(conn)
        db.session.flush()

        db.session.add(DailyWearableData(
            user_id=user_id,
            connection_id=conn.id,
            date=date.today(),
            data_type="activity",
            data_json=json.dumps({"steps": 8000}),
            summary_json=json.dumps({"steps": 8000, "active_minutes": 45}),
        ))
        db.session.add(DailyWearableData(
            user_id=user_id,
            connection_id=conn.id,
            date=date.today(),
            data_type="sleep",
            data_json=json.dumps({}),
            summary_json=json.dumps({"total_sleep_minutes": 450, "deep_sleep_minutes": 90}),
        ))
        db.session.commit()

    resp = client.get("/api/v1/analysis/daily", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["domains"]["wearable"]["status"] == "available"
    assert "activity" in data["domains"]["wearable"]["metrics"]


def test_daily_analysis_with_daily_insights(client, app):
    """Daily analysis should include today's persisted insights."""
    headers = _register_and_login(client, email="insight-test@test.com")
    user_id = _get_user_id(client, headers)

    with app.app_context():
        db.session.add(DailyInsight(
            user_id=user_id,
            date=date.today(),
            insight_type="daily",
            title="Test insight",
            body="This is a test insight body.",
            data_sources_json=json.dumps(["wearable:activity"]),
            confidence="high",
        ))
        db.session.commit()

    resp = client.get("/api/v1/analysis/daily", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert len(data["daily_insights"]) == 1
    assert data["daily_insights"][0]["title"] == "Test insight"


def test_daily_analysis_narrative_present(client):
    """Response should always include an AI narrative."""
    headers = _register_and_login(client, email="narr@test.com")
    resp = client.get("/api/v1/analysis/daily", headers=headers)
    data = resp.get_json()
    assert "Unified Health Analysis" in data["ai_narrative"]


def test_daily_analysis_disclaimer_present(client):
    """Response should always include a disclaimer."""
    headers = _register_and_login(client, email="disc@test.com")
    resp = client.get("/api/v1/analysis/daily", headers=headers)
    data = resp.get_json()
    assert "NOT medical advice" in data["disclaimer"]


# ── Generate endpoint ────────────────────────────────────────────────────────


def test_trigger_unified_analysis(client):
    headers = _register_and_login(client, email="gen@test.com")
    resp = client.post("/api/v1/analysis/daily/generate", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "queued"
    assert "message" in data


def test_trigger_unified_analysis_requires_auth(client):
    resp = client.post("/api/v1/analysis/daily/generate")
    assert resp.status_code == 401


# ── User isolation ───────────────────────────────────────────────────────────


def test_user_isolation(client, app):
    """Each user only sees their own analysis data."""
    h1 = _register_and_login(client, email="alice-a@test.com")
    h2 = _register_and_login(client, email="bob-a@test.com")
    uid1 = _get_user_id(client, h1)

    with app.app_context():
        db.session.add(DailyInsight(
            user_id=uid1,
            date=date.today(),
            insight_type="daily",
            title="Alice's private insight",
            body="Only Alice should see this.",
            confidence="high",
        ))
        db.session.commit()

    r1 = client.get("/api/v1/analysis/daily", headers=h1).get_json()
    r2 = client.get("/api/v1/analysis/daily", headers=h2).get_json()

    assert len(r1["daily_insights"]) == 1
    assert len(r2["daily_insights"]) == 0
