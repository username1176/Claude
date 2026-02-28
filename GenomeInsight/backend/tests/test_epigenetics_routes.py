"""Tests for epigenetics upload and analysis API routes."""

import io
import json
from pathlib import Path

import pytest

from app.extensions import db
from app.models.epigenetics import EpigeneticAnalysis, EpigeneticRegion

FIXTURES = Path(__file__).parent / "fixtures"


def _register_and_login(client, email="epi@test.com"):
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


def _upload_bed(client, headers):
    """Upload the sample BED fixture and return the response."""
    bed_data = (FIXTURES / "sample_histone.bed").read_bytes()
    return client.post(
        "/api/v1/epigenetics/upload",
        data={
            "file": (io.BytesIO(bed_data), "sample_histone.bed"),
            "data_type": "histone",
            "assay_type": "H3K27ac",
            "tissue_type": "blood",
        },
        headers=headers,
        content_type="multipart/form-data",
    )


def _upload_csv(client, headers):
    """Upload the sample methylation CSV fixture and return the response."""
    csv_data = (FIXTURES / "sample_methylation.csv").read_bytes()
    return client.post(
        "/api/v1/epigenetics/upload",
        data={
            "file": (io.BytesIO(csv_data), "sample_methylation.csv"),
            "data_type": "methylation",
            "tissue_type": "blood",
        },
        headers=headers,
        content_type="multipart/form-data",
    )


# ── Upload tests ──────────────────────────────────────────────────────────────


def test_upload_bed_success(client):
    headers = _register_and_login(client)
    resp = _upload_bed(client, headers)
    assert resp.status_code == 202

    data = resp.get_json()
    assert "upload_id" in data
    assert "analysis_id" in data
    assert data["status"] == "uploaded"
    assert "Analysis will begin" in data["message"]


def test_upload_csv_success(client):
    headers = _register_and_login(client)
    resp = _upload_csv(client, headers)
    assert resp.status_code == 202

    data = resp.get_json()
    assert "upload_id" in data
    assert "analysis_id" in data


def test_upload_no_file(client):
    headers = _register_and_login(client)
    resp = client.post(
        "/api/v1/epigenetics/upload",
        data={"data_type": "histone"},
        headers=headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "No file" in resp.get_json()["error"]


def test_upload_empty_filename(client):
    headers = _register_and_login(client)
    resp = client.post(
        "/api/v1/epigenetics/upload",
        data={
            "file": (io.BytesIO(b"data"), ""),
            "data_type": "histone",
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_invalid_data_type(client):
    headers = _register_and_login(client)
    bed_data = (FIXTURES / "sample_histone.bed").read_bytes()
    resp = client.post(
        "/api/v1/epigenetics/upload",
        data={
            "file": (io.BytesIO(bed_data), "sample.bed"),
            "data_type": "invalid_type",
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "data_type" in resp.get_json()["error"]


def test_upload_missing_data_type(client):
    headers = _register_and_login(client)
    bed_data = (FIXTURES / "sample_histone.bed").read_bytes()
    resp = client.post(
        "/api/v1/epigenetics/upload",
        data={
            "file": (io.BytesIO(bed_data), "sample.bed"),
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_requires_auth(client):
    bed_data = (FIXTURES / "sample_histone.bed").read_bytes()
    resp = client.post(
        "/api/v1/epigenetics/upload",
        data={
            "file": (io.BytesIO(bed_data), "sample.bed"),
            "data_type": "histone",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


# ── List uploads ──────────────────────────────────────────────────────────────


def test_list_uploads(client):
    headers = _register_and_login(client)
    _upload_bed(client, headers)
    _upload_csv(client, headers)

    resp = client.get("/api/v1/epigenetics/uploads", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert len(data) == 2
    data_types = {u["data_type"] for u in data}
    assert data_types == {"histone", "methylation"}


def test_list_uploads_empty(client):
    headers = _register_and_login(client)
    resp = client.get("/api/v1/epigenetics/uploads", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == []


# ── Get upload detail ────────────────────────────────────────────────────────


def test_get_upload_detail(client):
    headers = _register_and_login(client)
    upload_resp = _upload_bed(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]

    resp = client.get(f"/api/v1/epigenetics/uploads/{upload_id}", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["id"] == upload_id
    assert data["data_type"] == "histone"
    assert data["assay_type"] == "H3K27ac"
    assert data["tissue_type"] == "blood"
    assert "analysis" in data


def test_get_upload_not_found(client):
    headers = _register_and_login(client)
    resp = client.get("/api/v1/epigenetics/uploads/nonexistent", headers=headers)
    assert resp.status_code == 404


def test_cannot_access_other_users_upload(client, app):
    # User A uploads
    headers_a = _register_and_login(client, email="usera@test.com")
    upload_resp = _upload_bed(client, headers_a)
    upload_id = upload_resp.get_json()["upload_id"]

    # User B tries to access
    headers_b = _register_and_login(client, email="userb@test.com")
    resp = client.get(f"/api/v1/epigenetics/uploads/{upload_id}", headers=headers_b)
    assert resp.status_code == 404


# ── Delete upload ────────────────────────────────────────────────────────────


def test_delete_upload(client):
    headers = _register_and_login(client)
    upload_resp = _upload_bed(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]

    resp = client.delete(f"/api/v1/epigenetics/uploads/{upload_id}", headers=headers)
    assert resp.status_code == 200

    # Verify it's gone
    resp = client.get(f"/api/v1/epigenetics/uploads/{upload_id}", headers=headers)
    assert resp.status_code == 404


def test_delete_upload_not_found(client):
    headers = _register_and_login(client)
    resp = client.delete("/api/v1/epigenetics/uploads/nonexistent", headers=headers)
    assert resp.status_code == 404


def test_cannot_delete_other_users_upload(client, app):
    headers_a = _register_and_login(client, email="del_a@test.com")
    upload_resp = _upload_bed(client, headers_a)
    upload_id = upload_resp.get_json()["upload_id"]

    headers_b = _register_and_login(client, email="del_b@test.com")
    resp = client.delete(f"/api/v1/epigenetics/uploads/{upload_id}", headers=headers_b)
    assert resp.status_code == 404

    # Verify still exists for user A
    resp = client.get(f"/api/v1/epigenetics/uploads/{upload_id}", headers=headers_a)
    assert resp.status_code == 200


# ── Analysis results ──────────────────────────────────────────────────────────


def test_get_analysis(client):
    headers = _register_and_login(client)
    upload_resp = _upload_csv(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    resp = client.get(f"/api/v1/epigenetics/analysis/{analysis_id}", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["id"] == analysis_id
    assert data["status"] == "queued"
    assert "disclaimer" in data


def test_get_analysis_not_found(client):
    headers = _register_and_login(client)
    resp = client.get("/api/v1/epigenetics/analysis/nonexistent", headers=headers)
    assert resp.status_code == 404


# ── Regions (paginated) ──────────────────────────────────────────────────────


def test_get_regions_empty(client):
    headers = _register_and_login(client)
    upload_resp = _upload_bed(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    resp = client.get(f"/api/v1/epigenetics/analysis/{analysis_id}/regions", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["total"] == 0
    assert data["regions"] == []


def test_get_regions_with_data(client, app):
    headers = _register_and_login(client)
    upload_resp = _upload_bed(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]
    analysis_id = upload_resp.get_json()["analysis_id"]

    # Manually insert some regions
    with app.app_context():
        for i in range(3):
            region = EpigeneticRegion(
                upload_id=upload_id,
                chromosome="chr1",
                start_pos=1000 * i,
                end_pos=1000 * (i + 1),
                feature_type="promoter",
                nearest_gene="MTHFR",
            )
            db.session.add(region)
        db.session.commit()

    resp = client.get(f"/api/v1/epigenetics/analysis/{analysis_id}/regions", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["total"] == 3
    assert len(data["regions"]) == 3


def test_get_regions_pagination(client, app):
    headers = _register_and_login(client)
    upload_resp = _upload_bed(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]
    analysis_id = upload_resp.get_json()["analysis_id"]

    with app.app_context():
        for i in range(5):
            region = EpigeneticRegion(
                upload_id=upload_id,
                chromosome="chr1",
                start_pos=1000 * i,
                end_pos=1000 * (i + 1),
            )
            db.session.add(region)
        db.session.commit()

    resp = client.get(
        f"/api/v1/epigenetics/analysis/{analysis_id}/regions?page=1&per_page=2",
        headers=headers,
    )
    data = resp.get_json()
    assert data["total"] == 5
    assert len(data["regions"]) == 2
    assert data["pages"] == 3


def test_get_regions_chromosome_filter(client, app):
    headers = _register_and_login(client)
    upload_resp = _upload_bed(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]
    analysis_id = upload_resp.get_json()["analysis_id"]

    with app.app_context():
        db.session.add(EpigeneticRegion(
            upload_id=upload_id, chromosome="chr1", start_pos=100, end_pos=200,
        ))
        db.session.add(EpigeneticRegion(
            upload_id=upload_id, chromosome="chr17", start_pos=300, end_pos=400,
        ))
        db.session.commit()

    resp = client.get(
        f"/api/v1/epigenetics/analysis/{analysis_id}/regions?chromosome=chr1",
        headers=headers,
    )
    data = resp.get_json()
    assert data["total"] == 1
    assert data["regions"][0]["chromosome"] == "chr1"


# ── Genome overlay ────────────────────────────────────────────────────────────


def test_genome_overlay_not_complete(client):
    headers = _register_and_login(client)
    upload_resp = _upload_csv(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    resp = client.get(
        f"/api/v1/epigenetics/analysis/{analysis_id}/genome-overlay",
        headers=headers,
    )
    assert resp.status_code == 409
    assert "not yet complete" in resp.get_json()["error"]


def test_genome_overlay_complete(client, app):
    headers = _register_and_login(client)
    upload_resp = _upload_csv(client, headers)
    analysis_id = upload_resp.get_json()["analysis_id"]

    # Mark analysis as complete with overlay data
    with app.app_context():
        analysis = db.session.get(EpigeneticAnalysis, analysis_id)
        analysis.status = "complete"
        analysis.genome_overlay_json = json.dumps([
            {"gene": "MTHFR", "variant_rsid": "rs1801133", "risk_modifier": 0.85}
        ])
        db.session.commit()

    resp = client.get(
        f"/api/v1/epigenetics/analysis/{analysis_id}/genome-overlay",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "overlays" in data
    assert len(data["overlays"]) == 1
    assert data["overlays"][0]["gene"] == "MTHFR"
    assert "disclaimer" in data


# ── Re-trigger analysis ──────────────────────────────────────────────────────


def test_trigger_analysis(client):
    headers = _register_and_login(client)
    upload_resp = _upload_bed(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]

    resp = client.post(
        f"/api/v1/epigenetics/uploads/{upload_id}/analyze",
        headers=headers,
    )
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "queued"
    assert "analysis_id" in data


def test_trigger_analysis_while_running(client, app):
    headers = _register_and_login(client)
    upload_resp = _upload_bed(client, headers)
    upload_id = upload_resp.get_json()["upload_id"]
    analysis_id = upload_resp.get_json()["analysis_id"]

    # Mark analysis as running
    with app.app_context():
        analysis = db.session.get(EpigeneticAnalysis, analysis_id)
        analysis.status = "running"
        db.session.commit()

    resp = client.post(
        f"/api/v1/epigenetics/uploads/{upload_id}/analyze",
        headers=headers,
    )
    assert resp.status_code == 409
    assert "already running" in resp.get_json()["error"]


def test_trigger_analysis_not_found(client):
    headers = _register_and_login(client)
    resp = client.post(
        "/api/v1/epigenetics/uploads/nonexistent/analyze",
        headers=headers,
    )
    assert resp.status_code == 404
