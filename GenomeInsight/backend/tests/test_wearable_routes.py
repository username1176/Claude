"""Tests for wearable and insight API routes."""

import json
from datetime import date, datetime, timezone

from app.extensions import db
from app.models.wearable import DailyInsight, DailyWearableData, WearableConnection


def _register_and_login(client, email="wearable@test.com"):
    """Helper: register a user and return auth headers + user_id."""
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


def _create_connection(app, user_id, provider="fitbit", status="active"):
    """Helper: create a WearableConnection record directly."""
    with app.app_context():
        conn = WearableConnection(
            user_id=user_id,
            provider=provider,
            terra_user_id=f"terra_{provider}_{user_id[:8]}",
            status=status,
        )
        db.session.add(conn)
        db.session.commit()
        return conn.id


# ══════════════════════════════════════════════════════════════════════════════
# Wearable endpoints
# ══════════════════════════════════════════════════════════════════════════════


# ── Providers ────────────────────────────────────────────────────────────────


def test_list_providers(client):
    headers, _ = _register_and_login(client)
    resp = client.get("/api/v1/wearables/providers", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert "providers" in data
    providers = {p["provider"] for p in data["providers"]}
    assert "fitbit" in providers
    assert "garmin" in providers


def test_list_providers_shows_connected(client, app):
    headers, user_id = _register_and_login(client)
    _create_connection(app, user_id, "fitbit")

    resp = client.get("/api/v1/wearables/providers", headers=headers)
    data = resp.get_json()
    fitbit = next(p for p in data["providers"] if p["provider"] == "fitbit")
    assert fitbit["connected"] is True
    garmin = next(p for p in data["providers"] if p["provider"] == "garmin")
    assert garmin["connected"] is False


def test_providers_requires_auth(client):
    resp = client.get("/api/v1/wearables/providers")
    assert resp.status_code == 401


# ── Connect wearable ────────────────────────────────────────────────────────


def test_connect_wearable(client):
    headers, _ = _register_and_login(client)
    resp = client.post(
        "/api/v1/wearables/connect",
        data=json.dumps({"provider": "fitbit"}),
        headers=headers,
        content_type="application/json",
    )
    assert resp.status_code == 200

    data = resp.get_json()
    assert "auth_url" in data
    assert data["provider"] == "fitbit"
    assert "state" in data


def test_connect_unsupported_provider(client):
    headers, _ = _register_and_login(client)
    resp = client.post(
        "/api/v1/wearables/connect",
        data=json.dumps({"provider": "invalid_device"}),
        headers=headers,
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "Unsupported" in resp.get_json()["error"]


def test_connect_already_active(client, app):
    headers, user_id = _register_and_login(client)
    _create_connection(app, user_id, "fitbit")

    resp = client.post(
        "/api/v1/wearables/connect",
        data=json.dumps({"provider": "fitbit"}),
        headers=headers,
        content_type="application/json",
    )
    assert resp.status_code == 409
    assert "Already connected" in resp.get_json()["error"]


# ── OAuth callback ──────────────────────────────────────────────────────────


def test_oauth_callback(client):
    headers, _ = _register_and_login(client)
    resp = client.post(
        "/api/v1/wearables/callback",
        data=json.dumps({
            "code": "test-auth-code",
            "provider": "fitbit",
        }),
        headers=headers,
        content_type="application/json",
    )
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["provider"] == "fitbit"
    assert data["status"] == "active"
    assert "connection_id" in data


def test_oauth_callback_missing_code(client):
    headers, _ = _register_and_login(client)
    resp = client.post(
        "/api/v1/wearables/callback",
        data=json.dumps({"provider": "fitbit"}),
        headers=headers,
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "code" in resp.get_json()["error"].lower()


def test_oauth_callback_invalid_provider(client):
    headers, _ = _register_and_login(client)
    resp = client.post(
        "/api/v1/wearables/callback",
        data=json.dumps({"code": "test", "provider": "bad"}),
        headers=headers,
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_oauth_callback_reconnects_revoked(client, app):
    headers, user_id = _register_and_login(client)
    _create_connection(app, user_id, "fitbit", status="revoked")

    resp = client.post(
        "/api/v1/wearables/callback",
        data=json.dumps({"code": "new-code", "provider": "fitbit"}),
        headers=headers,
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "active"


# ── List connections ────────────────────────────────────────────────────────


def test_list_connections(client, app):
    headers, user_id = _register_and_login(client)
    _create_connection(app, user_id, "fitbit")
    _create_connection(app, user_id, "oura")

    resp = client.get("/api/v1/wearables/connections", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert len(data) == 2
    providers = {c["provider"] for c in data}
    assert providers == {"fitbit", "oura"}


def test_list_connections_empty(client):
    headers, _ = _register_and_login(client)
    resp = client.get("/api/v1/wearables/connections", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == []


# ── Disconnect ──────────────────────────────────────────────────────────────


def test_disconnect_wearable(client, app):
    headers, user_id = _register_and_login(client)
    conn_id = _create_connection(app, user_id, "fitbit")

    resp = client.delete(f"/api/v1/wearables/connections/{conn_id}", headers=headers)
    assert resp.status_code == 200
    assert "Disconnected" in resp.get_json()["message"]

    # Verify status changed
    resp = client.get("/api/v1/wearables/connections", headers=headers)
    connections = resp.get_json()
    fitbit = next(c for c in connections if c["provider"] == "fitbit")
    assert fitbit["status"] == "revoked"


def test_disconnect_not_found(client):
    headers, _ = _register_and_login(client)
    resp = client.delete("/api/v1/wearables/connections/nonexistent", headers=headers)
    assert resp.status_code == 404


def test_cannot_disconnect_other_users_connection(client, app):
    headers_a, user_a = _register_and_login(client, email="owner@test.com")
    conn_id = _create_connection(app, user_a, "fitbit")

    headers_b, _ = _register_and_login(client, email="stranger@test.com")
    resp = client.delete(f"/api/v1/wearables/connections/{conn_id}", headers=headers_b)
    assert resp.status_code == 404


# ── Manual sync ─────────────────────────────────────────────────────────────


def test_trigger_sync(client, app):
    headers, user_id = _register_and_login(client)
    conn_id = _create_connection(app, user_id, "fitbit")

    resp = client.post(f"/api/v1/wearables/connections/{conn_id}/sync", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "sync_queued"


def test_trigger_sync_revoked(client, app):
    headers, user_id = _register_and_login(client)
    conn_id = _create_connection(app, user_id, "fitbit", status="revoked")

    resp = client.post(f"/api/v1/wearables/connections/{conn_id}/sync", headers=headers)
    assert resp.status_code == 409


def test_trigger_sync_not_found(client):
    headers, _ = _register_and_login(client)
    resp = client.post("/api/v1/wearables/connections/bad-id/sync", headers=headers)
    assert resp.status_code == 404


# ── Query wearable data ────────────────────────────────────────────────────


def test_get_wearable_data_empty(client):
    headers, _ = _register_and_login(client)
    resp = client.get("/api/v1/wearables/data", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"] == []


def test_get_wearable_data_with_records(client, app):
    headers, user_id = _register_and_login(client)
    conn_id = _create_connection(app, user_id, "fitbit")

    with app.app_context():
        db.session.add(DailyWearableData(
            user_id=user_id,
            connection_id=conn_id,
            date=date(2026, 2, 27),
            data_type="activity",
            data_json=json.dumps({"steps": 8000}),
            summary_json=json.dumps({"steps": 8000, "active_minutes": 40}),
        ))
        db.session.add(DailyWearableData(
            user_id=user_id,
            connection_id=conn_id,
            date=date(2026, 2, 27),
            data_type="sleep",
            data_json=json.dumps({"total_sleep_minutes": 420}),
            summary_json=json.dumps({"total_sleep_minutes": 420}),
        ))
        db.session.commit()

    resp = client.get("/api/v1/wearables/data", headers=headers)
    data = resp.get_json()["data"]
    assert len(data) == 2


def test_get_wearable_data_filter_type(client, app):
    headers, user_id = _register_and_login(client)
    conn_id = _create_connection(app, user_id, "fitbit")

    with app.app_context():
        db.session.add(DailyWearableData(
            user_id=user_id, connection_id=conn_id,
            date=date(2026, 2, 27), data_type="activity",
            data_json="{}", summary_json="{}",
        ))
        db.session.add(DailyWearableData(
            user_id=user_id, connection_id=conn_id,
            date=date(2026, 2, 27), data_type="sleep",
            data_json="{}", summary_json="{}",
        ))
        db.session.commit()

    resp = client.get("/api/v1/wearables/data?type=sleep", headers=headers)
    data = resp.get_json()["data"]
    assert len(data) == 1
    assert data[0]["type"] == "sleep"


def test_get_wearable_data_invalid_type(client):
    headers, _ = _register_and_login(client)
    resp = client.get("/api/v1/wearables/data?type=invalid", headers=headers)
    assert resp.status_code == 400


def test_get_wearable_data_date_filter(client, app):
    headers, user_id = _register_and_login(client)
    conn_id = _create_connection(app, user_id, "fitbit")

    with app.app_context():
        db.session.add(DailyWearableData(
            user_id=user_id, connection_id=conn_id,
            date=date(2026, 2, 20), data_type="activity",
            data_json="{}", summary_json="{}",
        ))
        db.session.add(DailyWearableData(
            user_id=user_id, connection_id=conn_id,
            date=date(2026, 2, 27), data_type="activity",
            data_json="{}", summary_json="{}",
        ))
        db.session.commit()

    resp = client.get(
        "/api/v1/wearables/data?from_date=2026-02-25&to_date=2026-02-28",
        headers=headers,
    )
    data = resp.get_json()["data"]
    assert len(data) == 1
    assert data[0]["date"] == "2026-02-27"


# ── Latest data ─────────────────────────────────────────────────────────────


def test_get_latest_data_empty(client):
    headers, _ = _register_and_login(client)
    resp = client.get("/api/v1/wearables/data/latest", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"] == []
    assert resp.get_json()["date"] is None


def test_get_latest_data(client, app):
    headers, user_id = _register_and_login(client)
    conn_id = _create_connection(app, user_id, "fitbit")

    with app.app_context():
        db.session.add(DailyWearableData(
            user_id=user_id, connection_id=conn_id,
            date=date(2026, 2, 26), data_type="activity",
            data_json="{}", summary_json=json.dumps({"steps": 7000}),
        ))
        db.session.add(DailyWearableData(
            user_id=user_id, connection_id=conn_id,
            date=date(2026, 2, 27), data_type="activity",
            data_json="{}", summary_json=json.dumps({"steps": 9000}),
        ))
        db.session.add(DailyWearableData(
            user_id=user_id, connection_id=conn_id,
            date=date(2026, 2, 27), data_type="sleep",
            data_json="{}", summary_json=json.dumps({"total_sleep_minutes": 420}),
        ))
        db.session.commit()

    resp = client.get("/api/v1/wearables/data/latest", headers=headers)
    data = resp.get_json()
    assert data["date"] == "2026-02-27"
    assert len(data["data"]) == 2  # Activity + sleep from latest day


# ══════════════════════════════════════════════════════════════════════════════
# Insights endpoints
# ══════════════════════════════════════════════════════════════════════════════


def test_get_daily_insights_empty(client):
    headers, _ = _register_and_login(client)
    resp = client.get("/api/v1/insights/daily", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["insights"] == []
    assert "disclaimer" in data


def test_get_daily_insights_with_data(client, app):
    headers, user_id = _register_and_login(client)

    with app.app_context():
        db.session.add(DailyInsight(
            user_id=user_id,
            date=date.today(),
            insight_type="daily",
            title="Good sleep quality",
            body="Your deep sleep was 90 minutes.",
            data_sources_json=json.dumps(["wearable:sleep"]),
            confidence="medium",
        ))
        db.session.commit()

    resp = client.get("/api/v1/insights/daily", headers=headers)
    data = resp.get_json()
    assert len(data["insights"]) == 1
    assert data["insights"][0]["title"] == "Good sleep quality"
    assert data["insights"][0]["data_sources"] == ["wearable:sleep"]


def test_get_insight_history(client, app):
    headers, user_id = _register_and_login(client)

    with app.app_context():
        for i in range(5):
            db.session.add(DailyInsight(
                user_id=user_id,
                date=date(2026, 2, 20 + i),
                insight_type="daily",
                title=f"Insight {i}",
                body=f"Body {i}",
                confidence="medium",
            ))
        db.session.commit()

    resp = client.get("/api/v1/insights/history?page=1&per_page=3", headers=headers)
    data = resp.get_json()
    assert data["total"] == 5
    assert len(data["insights"]) == 3
    assert data["pages"] == 2


def test_get_insight_history_filter_type(client, app):
    headers, user_id = _register_and_login(client)

    with app.app_context():
        db.session.add(DailyInsight(
            user_id=user_id, date=date.today(),
            insight_type="daily", title="Daily", body="...", confidence="medium",
        ))
        db.session.add(DailyInsight(
            user_id=user_id, date=date.today(),
            insight_type="alert", title="Alert", body="...", confidence="high",
        ))
        db.session.commit()

    resp = client.get("/api/v1/insights/history?type=alert", headers=headers)
    data = resp.get_json()
    assert data["total"] == 1
    assert data["insights"][0]["type"] == "alert"


def test_trigger_insight_generation(client):
    headers, _ = _register_and_login(client)
    resp = client.post("/api/v1/insights/generate", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "queued"


def test_insights_require_auth(client):
    resp = client.get("/api/v1/insights/daily")
    assert resp.status_code == 401
