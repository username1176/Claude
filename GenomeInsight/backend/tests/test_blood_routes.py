"""Tests for blood upload, history, and change-analysis API routes."""

import io
import json
from pathlib import Path
from unittest.mock import patch

FIXTURES = Path(__file__).parent / "fixtures"


def _register_and_login(client, email="blood@test.com"):
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


def _upload_csv(client, headers, filename="sample_blood.csv", test_date="2025-01-15"):
    """Upload a CSV blood file and return the response."""
    csv_data = (FIXTURES / filename).read_bytes()
    return client.post(
        "/api/v1/blood/upload",
        data={
            "file": (io.BytesIO(csv_data), filename),
            "test_date": test_date,
            "lab_name": "Test Lab",
        },
        headers=headers,
        content_type="multipart/form-data",
    )


# ── Upload tests ────────────────────────────────────────────────────────────


class TestUploadBlood:
    def test_upload_csv_success(self, client):
        headers = _register_and_login(client)
        resp = _upload_csv(client, headers)
        assert resp.status_code == 202

        data = resp.get_json()
        assert "upload_id" in data
        assert data["status"] == "parsed"
        assert data["markers_parsed"] == 19

    def test_upload_no_file(self, client):
        headers = _register_and_login(client)
        resp = client.post(
            "/api/v1/blood/upload",
            data={"test_date": "2025-01-15"},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "No file" in resp.get_json()["error"]

    def test_upload_bad_extension(self, client):
        headers = _register_and_login(client)
        resp = client.post(
            "/api/v1/blood/upload",
            data={
                "file": (io.BytesIO(b"data"), "report.docx"),
                "test_date": "2025-01-15",
            },
            headers=headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.get_json()["error"]

    def test_upload_missing_test_date(self, client):
        headers = _register_and_login(client)
        csv_data = (FIXTURES / "sample_blood.csv").read_bytes()
        resp = client.post(
            "/api/v1/blood/upload",
            data={"file": (io.BytesIO(csv_data), "blood.csv")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "test_date" in resp.get_json()["error"]

    def test_upload_requires_auth(self, client):
        csv_data = (FIXTURES / "sample_blood.csv").read_bytes()
        resp = client.post(
            "/api/v1/blood/upload",
            data={
                "file": (io.BytesIO(csv_data), "blood.csv"),
                "test_date": "2025-01-15",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 401


# ── List / detail / delete ──────────────────────────────────────────────────


class TestBloodCRUD:
    def test_list_uploads(self, client):
        headers = _register_and_login(client)
        _upload_csv(client, headers)
        resp = client.get("/api/v1/blood/uploads", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["result_count"] == 19

    def test_get_upload_detail(self, client):
        headers = _register_and_login(client)
        upload_resp = _upload_csv(client, headers)
        upload_id = upload_resp.get_json()["upload_id"]

        resp = client.get(f"/api/v1/blood/uploads/{upload_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["results"]) == 19
        assert data["test_date"] == "2025-01-15"
        assert data["lab_name"] == "Test Lab"

    def test_get_upload_not_found(self, client):
        headers = _register_and_login(client)
        resp = client.get("/api/v1/blood/uploads/nonexistent", headers=headers)
        assert resp.status_code == 404

    def test_delete_upload(self, client):
        headers = _register_and_login(client)
        upload_resp = _upload_csv(client, headers)
        upload_id = upload_resp.get_json()["upload_id"]

        resp = client.delete(f"/api/v1/blood/uploads/{upload_id}", headers=headers)
        assert resp.status_code == 200

        # Verify gone
        resp = client.get(f"/api/v1/blood/uploads/{upload_id}", headers=headers)
        assert resp.status_code == 404

    def test_cross_user_isolation(self, client):
        """User B cannot see User A's blood uploads."""
        headers_a = _register_and_login(client, email="user_a@test.com")
        upload_resp = _upload_csv(client, headers_a)
        upload_id = upload_resp.get_json()["upload_id"]

        headers_b = _register_and_login(client, email="user_b@test.com")
        resp = client.get(f"/api/v1/blood/uploads/{upload_id}", headers=headers_b)
        assert resp.status_code == 404


# ── Update results ──────────────────────────────────────────────────────────


class TestUpdateResults:
    def test_correct_parsed_value(self, client):
        headers = _register_and_login(client)
        upload_resp = _upload_csv(client, headers)
        upload_id = upload_resp.get_json()["upload_id"]

        # Get the results
        detail = client.get(f"/api/v1/blood/uploads/{upload_id}", headers=headers).get_json()
        result_id = detail["results"][0]["id"]

        # Correct the value
        resp = client.put(
            f"/api/v1/blood/uploads/{upload_id}/results",
            data=json.dumps({
                "results": [
                    {"id": result_id, "value": 190.0}
                ]
            }),
            headers=headers,
            content_type="application/json",
        )
        assert resp.status_code == 200

        # Verify updated
        detail = client.get(f"/api/v1/blood/uploads/{upload_id}", headers=headers).get_json()
        updated = next(r for r in detail["results"] if r["id"] == result_id)
        assert updated["value"] == 190.0


# ── Blood history ───────────────────────────────────────────────────────────


class TestBloodHistory:
    def test_history_single_upload(self, client):
        headers = _register_and_login(client)
        _upload_csv(client, headers)

        resp = client.get("/api/v1/blood/history", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_uploads"] == 1
        assert data["history"][0]["changes"] is None  # No previous to compare

    def test_history_with_changes(self, client):
        headers = _register_and_login(client)
        _upload_csv(client, headers, filename="sample_blood.csv", test_date="2025-01-15")
        _upload_csv(client, headers, filename="sample_blood_followup.csv", test_date="2025-04-15")

        resp = client.get("/api/v1/blood/history", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_uploads"] == 2

        # First entry has no changes
        assert data["history"][0]["changes"] is None
        # Second entry has changes
        changes = data["history"][1]["changes"]
        assert len(changes) > 0

        # Total cholesterol decreased: 210 → 195
        chol = next(c for c in changes if c["marker_name"] == "TOTAL_CHOLESTEROL")
        assert chol["direction"] == "decreased"
        assert chol["previous_value"] == 210.0
        assert chol["current_value"] == 195.0

    def test_history_empty(self, client):
        headers = _register_and_login(client)
        resp = client.get("/api/v1/blood/history", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["total_uploads"] == 0


# ── Analyze changes ─────────────────────────────────────────────────────────


class TestAnalyzeChanges:
    def test_analyze_with_two_uploads(self, client):
        headers = _register_and_login(client)
        _upload_csv(client, headers, filename="sample_blood.csv", test_date="2025-01-15")
        _upload_csv(client, headers, filename="sample_blood_followup.csv", test_date="2025-04-15")

        resp = client.post(
            "/api/v1/blood/analyze-changes",
            headers=headers,
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()

        assert data["current_upload"] is not None
        assert data["previous_upload"] is not None
        assert len(data["deltas"]) > 0
        assert isinstance(data["summary"], list)

        # Check cholesterol delta
        chol_delta = next(d for d in data["deltas"] if d["marker_name"] == "TOTAL_CHOLESTEROL")
        assert chol_delta["direction"] == "decreased"
        assert chol_delta["improved"] is True

    def test_analyze_single_upload(self, client):
        headers = _register_and_login(client)
        _upload_csv(client, headers)

        resp = client.post(
            "/api/v1/blood/analyze-changes",
            headers=headers,
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["previous_upload"] is None
        assert data["deltas"] == []

    def test_analyze_no_uploads(self, client):
        headers = _register_and_login(client)
        resp = client.post(
            "/api/v1/blood/analyze-changes",
            headers=headers,
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_analyze_specific_uploads(self, client):
        headers = _register_and_login(client)
        r1 = _upload_csv(client, headers, filename="sample_blood.csv", test_date="2025-01-15")
        r2 = _upload_csv(client, headers, filename="sample_blood_followup.csv", test_date="2025-04-15")

        id1 = r1.get_json()["upload_id"]
        id2 = r2.get_json()["upload_id"]

        resp = client.post(
            "/api/v1/blood/analyze-changes",
            data=json.dumps({
                "current_upload_id": id2,
                "previous_upload_id": id1,
            }),
            headers=headers,
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["current_upload"]["id"] == id2
        assert data["previous_upload"]["id"] == id1


# ── Trends ──────────────────────────────────────────────────────────────────


class TestTrends:
    def test_trend_multiple_uploads(self, client):
        headers = _register_and_login(client)
        _upload_csv(client, headers, filename="sample_blood.csv", test_date="2025-01-15")
        _upload_csv(client, headers, filename="sample_blood_followup.csv", test_date="2025-04-15")

        resp = client.get(
            "/api/v1/blood/trends?markers=TOTAL_CHOLESTEROL,LDL",
            headers=headers,
        )
        assert resp.status_code == 200
        trends = resp.get_json()["trends"]

        assert "TOTAL_CHOLESTEROL" in trends
        chol = trends["TOTAL_CHOLESTEROL"]
        assert len(chol["data_points"]) == 2
        assert chol["trend_direction"] in ("improving", "worsening", "stable")


# ── Markers listing ─────────────────────────────────────────────────────────


class TestMarkers:
    def test_list_markers(self, client):
        headers = _register_and_login(client)
        _upload_csv(client, headers)

        resp = client.get("/api/v1/blood/markers", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 19
        names = {m["marker_name"] for m in data}
        assert "TOTAL_CHOLESTEROL" in names
        assert "GLUCOSE" in names
