"""Tests for genome upload and analysis API routes."""

import io
import json
from pathlib import Path
from unittest.mock import patch

FIXTURES = Path(__file__).parent / "fixtures"


def _register_and_login(client):
    """Helper: register a user and return an auth header dict."""
    client.post(
        "/api/v1/auth/register",
        data=json.dumps({
            "email": "genome@test.com",
            "password": "securepass12345",
            "tos_accepted": True,
        }),
        content_type="application/json",
    )
    resp = client.post(
        "/api/v1/auth/login",
        data=json.dumps({"email": "genome@test.com", "password": "securepass12345"}),
        content_type="application/json",
    )
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _upload_vcf(client, headers):
    """Upload the sample VCF and return the response JSON."""
    vcf_data = (FIXTURES / "sample.vcf").read_bytes()
    resp = client.post(
        "/api/v1/genome/upload",
        data={
            "file": (io.BytesIO(vcf_data), "sample.vcf"),
            "source_service": "23andme",
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    return resp


def test_upload_genome_success(client):
    headers = _register_and_login(client)
    resp = _upload_vcf(client, headers)
    assert resp.status_code == 202

    data = resp.get_json()
    assert "upload_id" in data
    assert "analysis_id" in data
    assert data["status"] == "uploaded"
    assert "File received" in data["message"]


def test_upload_genome_no_file(client):
    headers = _register_and_login(client)
    resp = client.post(
        "/api/v1/genome/upload",
        headers=headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_genome_invalid_file(client):
    headers = _register_and_login(client)
    resp = client.post(
        "/api/v1/genome/upload",
        data={"file": (io.BytesIO(b"not a VCF file"), "bad.vcf")},
        headers=headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "VCF" in resp.get_json()["error"]


def test_list_uploads(client):
    headers = _register_and_login(client)
    _upload_vcf(client, headers)

    resp = client.get("/api/v1/genome/uploads", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["source_service"] == "23andme"


def test_get_upload_detail(client):
    headers = _register_and_login(client)
    upload_resp = _upload_vcf(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]

    resp = client.get(f"/api/v1/genome/uploads/{upload_id}", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["id"] == upload_id
    assert "analysis" in data


def test_get_analysis(client):
    headers = _register_and_login(client)
    upload_resp = _upload_vcf(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    resp = client.get(f"/api/v1/genome/analysis/{analysis_id}", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["id"] == analysis_id
    assert data["status"] == "queued"


def test_get_report_not_complete(client):
    headers = _register_and_login(client)
    upload_resp = _upload_vcf(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    resp = client.get(f"/api/v1/genome/analysis/{analysis_id}/report", headers=headers)
    assert resp.status_code == 409


def test_delete_upload(client):
    headers = _register_and_login(client)
    upload_resp = _upload_vcf(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]

    resp = client.delete(f"/api/v1/genome/uploads/{upload_id}", headers=headers)
    assert resp.status_code == 200

    # Verify it's gone
    resp = client.get(f"/api/v1/genome/uploads/{upload_id}", headers=headers)
    assert resp.status_code == 404


def test_trigger_analysis(client):
    headers = _register_and_login(client)
    upload_resp = _upload_vcf(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]

    resp = client.post(f"/api/v1/genome/uploads/{upload_id}/analyze", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "queued"


def test_get_variants_empty(client):
    headers = _register_and_login(client)
    upload_resp = _upload_vcf(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    resp = client.get(f"/api/v1/genome/analysis/{analysis_id}/variants", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 0
    assert data["variants"] == []


def test_get_risks(client):
    headers = _register_and_login(client)
    upload_resp = _upload_vcf(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    resp = client.get(f"/api/v1/genome/analysis/{analysis_id}/risks", headers=headers)
    assert resp.status_code == 200


def test_upload_requires_auth(client):
    vcf_data = (FIXTURES / "sample.vcf").read_bytes()
    resp = client.post(
        "/api/v1/genome/upload",
        data={"file": (io.BytesIO(vcf_data), "sample.vcf")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_cannot_access_other_users_upload(client, app):
    # User A uploads
    headers_a = _register_and_login(client)
    upload_resp = _upload_vcf(client, headers_a)
    upload_id = upload_resp.get_json()["upload_id"]

    # User B tries to access
    client.post(
        "/api/v1/auth/register",
        data=json.dumps({
            "email": "other@test.com",
            "password": "securepass12345",
            "tos_accepted": True,
        }),
        content_type="application/json",
    )
    resp = client.post(
        "/api/v1/auth/login",
        data=json.dumps({"email": "other@test.com", "password": "securepass12345"}),
        content_type="application/json",
    )
    headers_b = {"Authorization": f"Bearer {resp.get_json()['access_token']}"}

    resp = client.get(f"/api/v1/genome/uploads/{upload_id}", headers=headers_b)
    assert resp.status_code == 404
