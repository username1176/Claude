"""Tests for microbiome upload and analysis API routes."""

import io
import json
from pathlib import Path

import pytest

from app.extensions import db
from app.models.microbiome import MicrobiomeAnalysis, MicrobiomeTaxon, MicrobiomeUpload

FIXTURES = Path(__file__).parent / "fixtures"


def _register_and_login(client, email="micro@test.com"):
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


def _upload_csv(client, headers):
    """Upload the sample OTU CSV fixture and return the response."""
    csv_data = (FIXTURES / "sample_otu_table.csv").read_bytes()
    return client.post(
        "/api/v1/microbiome/upload",
        data={
            "file": (io.BytesIO(csv_data), "sample_otu_table.csv"),
            "data_type": "16s_rrna",
            "sample_source": "gut",
        },
        headers=headers,
        content_type="multipart/form-data",
    )


def _upload_biom(client, headers):
    """Upload the sample BIOM fixture and return the response."""
    biom_data = (FIXTURES / "sample_biom.json").read_bytes()
    return client.post(
        "/api/v1/microbiome/upload",
        data={
            "file": (io.BytesIO(biom_data), "sample_biom.biom"),
            "data_type": "16s_rrna",
            "sample_source": "gut",
        },
        headers=headers,
        content_type="multipart/form-data",
    )


# -- Upload tests ─────────────────────────────────────────────────────────────


def test_upload_csv_success(client):
    headers = _register_and_login(client)
    resp = _upload_csv(client, headers)
    assert resp.status_code == 202

    data = resp.get_json()
    assert "upload_id" in data
    assert "analysis_id" in data
    assert data["status"] == "uploaded"
    assert "Analysis will begin" in data["message"]


def test_upload_biom_success(client):
    headers = _register_and_login(client)
    resp = _upload_biom(client, headers)
    assert resp.status_code == 202

    data = resp.get_json()
    assert "upload_id" in data
    assert "analysis_id" in data


def test_upload_no_file(client):
    headers = _register_and_login(client)
    resp = client.post(
        "/api/v1/microbiome/upload",
        data={"data_type": "16s_rrna"},
        headers=headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "No file" in resp.get_json()["error"]


def test_upload_invalid_data_type(client):
    headers = _register_and_login(client)
    csv_data = (FIXTURES / "sample_otu_table.csv").read_bytes()
    resp = client.post(
        "/api/v1/microbiome/upload",
        data={
            "file": (io.BytesIO(csv_data), "sample.csv"),
            "data_type": "invalid_type",
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "Invalid data_type" in resp.get_json()["error"]


def test_upload_empty_filename(client):
    headers = _register_and_login(client)
    resp = client.post(
        "/api/v1/microbiome/upload",
        data={
            "file": (io.BytesIO(b"test"), ""),
            "data_type": "16s_rrna",
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_requires_auth(client):
    csv_data = (FIXTURES / "sample_otu_table.csv").read_bytes()
    resp = client.post(
        "/api/v1/microbiome/upload",
        data={
            "file": (io.BytesIO(csv_data), "sample.csv"),
            "data_type": "16s_rrna",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


# -- List uploads ─────────────────────────────────────────────────────────────


def test_list_uploads_empty(client):
    headers = _register_and_login(client)
    resp = client.get("/api/v1/microbiome/uploads", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_uploads_after_upload(client):
    headers = _register_and_login(client)
    _upload_csv(client, headers)
    resp = client.get("/api/v1/microbiome/uploads", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["data_type"] == "16s_rrna"
    assert data[0]["sample_source"] == "gut"
    assert data[0]["status"] == "uploaded"


# -- Get upload detail ────────────────────────────────────────────────────────


def test_get_upload_detail(client):
    headers = _register_and_login(client)
    upload_resp = _upload_csv(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]

    resp = client.get(f"/api/v1/microbiome/uploads/{upload_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == upload_id
    assert data["data_type"] == "16s_rrna"
    assert "analysis" in data


def test_get_upload_not_found(client):
    headers = _register_and_login(client)
    resp = client.get("/api/v1/microbiome/uploads/nonexistent", headers=headers)
    assert resp.status_code == 404


def test_get_upload_other_user(client):
    """Uploads are scoped per user — other user can't see them."""
    headers1 = _register_and_login(client, email="user1@test.com")
    upload_resp = _upload_csv(client, headers1)
    upload_id = upload_resp.get_json()["upload_id"]

    headers2 = _register_and_login(client, email="user2@test.com")
    resp = client.get(f"/api/v1/microbiome/uploads/{upload_id}", headers=headers2)
    assert resp.status_code == 404


# -- Delete upload ────────────────────────────────────────────────────────────


def test_delete_upload(client):
    headers = _register_and_login(client)
    upload_resp = _upload_csv(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]

    resp = client.delete(f"/api/v1/microbiome/uploads/{upload_id}", headers=headers)
    assert resp.status_code == 200
    assert "deleted" in resp.get_json()["message"].lower()

    # Confirm it's gone
    resp2 = client.get(f"/api/v1/microbiome/uploads/{upload_id}", headers=headers)
    assert resp2.status_code == 404


def test_delete_nonexistent(client):
    headers = _register_and_login(client)
    resp = client.delete("/api/v1/microbiome/uploads/nonexistent", headers=headers)
    assert resp.status_code == 404


# -- Analysis results ─────────────────────────────────────────────────────────


def test_get_analysis(client):
    headers = _register_and_login(client)
    upload_resp = _upload_csv(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    resp = client.get(f"/api/v1/microbiome/analysis/{analysis_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == analysis_id
    assert data["status"] == "queued"
    assert "disclaimer" in data


def test_get_analysis_not_found(client):
    headers = _register_and_login(client)
    resp = client.get("/api/v1/microbiome/analysis/nonexistent", headers=headers)
    assert resp.status_code == 404


# -- Taxa endpoint ────────────────────────────────────────────────────────────


def test_get_taxa(client):
    headers = _register_and_login(client)
    upload_resp = _upload_csv(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    resp = client.get(f"/api/v1/microbiome/analysis/{analysis_id}/taxa", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "taxa" in data
    assert data["total"] == 0  # No taxa stored yet (analysis hasn't run)


# -- Composition endpoint ─────────────────────────────────────────────────────


def test_get_composition_not_complete(client):
    headers = _register_and_login(client)
    upload_resp = _upload_csv(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    resp = client.get(f"/api/v1/microbiome/analysis/{analysis_id}/composition", headers=headers)
    assert resp.status_code == 409  # Not yet complete


# -- Genome correlation endpoint ──────────────────────────────────────────────


def test_get_genome_correlation_not_complete(client):
    headers = _register_and_login(client)
    upload_resp = _upload_csv(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    resp = client.get(
        f"/api/v1/microbiome/analysis/{analysis_id}/genome-correlation",
        headers=headers,
    )
    assert resp.status_code == 409


# -- Re-trigger analysis ──────────────────────────────────────────────────────


def test_retrigger_analysis(client):
    headers = _register_and_login(client)
    upload_resp = _upload_csv(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]

    resp = client.post(f"/api/v1/microbiome/uploads/{upload_id}/analyze", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "queued"
    assert "analysis_id" in data


def test_retrigger_nonexistent(client):
    headers = _register_and_login(client)
    resp = client.post("/api/v1/microbiome/uploads/nonexistent/analyze", headers=headers)
    assert resp.status_code == 404


# -- Full analysis endpoint ───────────────────────────────────────────────────


def test_full_analysis(client):
    headers = _register_and_login(client)
    _upload_csv(client, headers)

    resp = client.post("/api/v1/microbiome/full-analysis", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "upload_id" in data
    assert "analysis_id" in data
    assert data["status"] == "queued"


def test_full_analysis_no_uploads(client):
    headers = _register_and_login(client)
    resp = client.post("/api/v1/microbiome/full-analysis", headers=headers)
    assert resp.status_code == 404


# -- Multi-user isolation ─────────────────────────────────────────────────────


def test_user_isolation(client):
    """Each user only sees their own uploads."""
    h1 = _register_and_login(client, email="alice@test.com")
    h2 = _register_and_login(client, email="bob@test.com")

    _upload_csv(client, h1)
    _upload_csv(client, h2)

    r1 = client.get("/api/v1/microbiome/uploads", headers=h1).get_json()
    r2 = client.get("/api/v1/microbiome/uploads", headers=h2).get_json()

    assert len(r1) == 1
    assert len(r2) == 1
    assert r1[0]["id"] != r2[0]["id"]
