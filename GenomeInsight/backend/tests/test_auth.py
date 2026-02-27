"""Tests for authentication endpoints."""

import json


def _register(client, email="test@example.com", password="securepass12345", tos=True):
    return client.post(
        "/api/v1/auth/register",
        data=json.dumps(
            {"email": email, "password": password, "tos_accepted": tos}
        ),
        content_type="application/json",
    )


def _login(client, email="test@example.com", password="securepass12345"):
    return client.post(
        "/api/v1/auth/login",
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
    )


def test_register_success(client):
    resp = _register(client)
    assert resp.status_code == 201
    data = resp.get_json()
    assert "user_id" in data
    assert data["email"] == "test@example.com"


def test_register_duplicate_email(client):
    _register(client)
    resp = _register(client)
    assert resp.status_code == 409


def test_register_short_password(client):
    resp = _register(client, password="short")
    assert resp.status_code == 400
    assert "password" in resp.get_json()["details"]


def test_register_missing_tos(client):
    resp = _register(client, tos=False)
    assert resp.status_code == 400


def test_login_success(client):
    _register(client)
    resp = _login(client)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password(client):
    _register(client)
    resp = _login(client, password="wrongpassword!!")
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = _login(client, email="nobody@example.com")
    assert resp.status_code == 401


def test_protected_endpoint_without_token(client):
    resp = client.get("/api/v1/genome/uploads")
    assert resp.status_code == 401


def test_protected_endpoint_with_token(client):
    _register(client)
    login_resp = _login(client)
    token = login_resp.get_json()["access_token"]
    resp = client.get(
        "/api/v1/genome/uploads",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_refresh_token(client):
    _register(client)
    login_resp = _login(client)
    refresh = login_resp.get_json()["refresh_token"]

    resp = client.post(
        "/api/v1/auth/refresh",
        data=json.dumps({"refresh_token": refresh}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_delete_account(client):
    _register(client)
    login_resp = _login(client)
    token = login_resp.get_json()["access_token"]

    resp = client.delete(
        "/api/v1/auth/account",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Token should now fail since user is deleted
    resp = client.get(
        "/api/v1/genome/uploads",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
