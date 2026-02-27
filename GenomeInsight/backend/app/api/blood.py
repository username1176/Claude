"""Blood test upload, results, and trend endpoints."""

from datetime import date

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import func

from app.extensions import db
from app.models.audit import AuditLog
from app.models.blood import BloodResult, BloodUpload
from app.api.decorators import login_required
from app.services.file_upload import UploadValidationError, save_upload

blood_bp = Blueprint("blood", __name__, url_prefix="/api/v1/blood")

ALLOWED_FILE_TYPES = {"pdf", "csv"}


def _audit(action: str, **kwargs):
    log = AuditLog(
        user_id=g.current_user.id,
        action=action,
        ip_address=request.remote_addr,
        **kwargs,
    )
    db.session.add(log)


# ── Upload ───────────────────────────────────────────────────────────────────


@blood_bp.route("/upload", methods=["POST"])
@login_required
def upload_blood():
    if "file" not in request.files:
        return jsonify({"error": "No file provided. Use multipart field 'file'."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename."}), 400

    # Determine file type from extension
    extension = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "").lower()
    if extension not in ALLOWED_FILE_TYPES:
        return jsonify({"error": f"Unsupported file type '{extension}'. Allowed: pdf, csv."}), 400

    # Parse test_date
    test_date_str = request.form.get("test_date", "")
    try:
        test_date = date.fromisoformat(test_date_str)
    except (ValueError, TypeError):
        return jsonify({"error": "test_date is required in ISO 8601 format (YYYY-MM-DD)."}), 400

    lab_name = request.form.get("lab_name", "").strip() or None
    user = g.current_user

    try:
        encrypted_path, _sha256, _size = save_upload(
            file=file,
            file_type=extension,
            max_size_bytes=current_app.config["MAX_BLOOD_FILE_SIZE_BYTES"],
            user_encrypted_dek=user.data_encryption_key_enc,
            master_key=current_app.config["MASTER_ENCRYPTION_KEY"],
        )
    except UploadValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    upload = BloodUpload(
        user_id=user.id,
        filename_original=file.filename,
        file_path_encrypted=str(encrypted_path),
        file_type=extension,
        test_date=test_date,
        lab_name=lab_name,
        status="uploaded",
    )
    db.session.add(upload)
    _audit("upload_blood", resource_type="BloodUpload", resource_id=upload.id)
    db.session.commit()

    return (
        jsonify(
            {
                "upload_id": upload.id,
                "status": upload.status,
                "message": "File received. Parsing will begin shortly.",
            }
        ),
        202,
    )


# ── List uploads ─────────────────────────────────────────────────────────────


@blood_bp.route("/uploads", methods=["GET"])
@login_required
def list_uploads():
    uploads = (
        BloodUpload.query.filter_by(user_id=g.current_user.id)
        .order_by(BloodUpload.test_date.desc())
        .all()
    )
    return jsonify(
        [
            {
                "id": u.id,
                "filename": u.filename_original,
                "file_type": u.file_type,
                "test_date": u.test_date.isoformat(),
                "lab_name": u.lab_name,
                "status": u.status,
                "uploaded_at": u.uploaded_at.isoformat(),
                "result_count": len(u.results),
            }
            for u in uploads
        ]
    )


# ── Get upload + parsed results ──────────────────────────────────────────────


@blood_bp.route("/uploads/<upload_id>", methods=["GET"])
@login_required
def get_upload(upload_id: str):
    upload = BloodUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Blood upload not found."}), 404

    return jsonify(
        {
            "id": upload.id,
            "filename": upload.filename_original,
            "file_type": upload.file_type,
            "test_date": upload.test_date.isoformat(),
            "lab_name": upload.lab_name,
            "status": upload.status,
            "uploaded_at": upload.uploaded_at.isoformat(),
            "results": [
                {
                    "id": r.id,
                    "marker_name": r.marker_name,
                    "marker_display_name": r.marker_display_name,
                    "value": r.value,
                    "unit": r.unit,
                    "reference_low": r.reference_low,
                    "reference_high": r.reference_high,
                    "flag": r.flag,
                }
                for r in upload.results
            ],
        }
    )


# ── Delete upload ────────────────────────────────────────────────────────────


@blood_bp.route("/uploads/<upload_id>", methods=["DELETE"])
@login_required
def delete_upload(upload_id: str):
    upload = BloodUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Blood upload not found."}), 404

    _audit("delete_blood", resource_type="BloodUpload", resource_id=upload.id)
    db.session.delete(upload)
    db.session.commit()

    return jsonify({"message": "Blood upload and associated results deleted."})


# ── Correct parsed results ───────────────────────────────────────────────────


@blood_bp.route("/uploads/<upload_id>/results", methods=["PUT"])
@login_required
def update_results(upload_id: str):
    """Allow users to manually correct parsed blood values."""
    upload = BloodUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Blood upload not found."}), 404

    data = request.get_json(silent=True)
    if not data or "results" not in data:
        return jsonify({"error": "Request body must contain 'results' array."}), 400

    existing = {r.id: r for r in upload.results}

    for item in data["results"]:
        result_id = item.get("id")
        if result_id and result_id in existing:
            r = existing[result_id]
            if "value" in item:
                r.value = float(item["value"])
            if "unit" in item:
                r.unit = item["unit"]
            if "reference_low" in item:
                r.reference_low = float(item["reference_low"]) if item["reference_low"] is not None else None
            if "reference_high" in item:
                r.reference_high = float(item["reference_high"]) if item["reference_high"] is not None else None

            # Recompute flag
            if r.reference_low is not None and r.value < r.reference_low:
                r.flag = "L"
            elif r.reference_high is not None and r.value > r.reference_high:
                r.flag = "H"
            else:
                r.flag = "N"

    _audit("update_blood_results", resource_type="BloodUpload", resource_id=upload.id)
    db.session.commit()

    return jsonify({"message": "Results updated."})


# ── Trends (time-series) ─────────────────────────────────────────────────────


@blood_bp.route("/trends", methods=["GET"])
@login_required
def get_trends():
    markers_param = request.args.get("markers", "")
    requested_markers = [m.strip() for m in markers_param.split(",") if m.strip()]

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    query = (
        db.session.query(BloodResult, BloodUpload.test_date)
        .join(BloodUpload, BloodResult.upload_id == BloodUpload.id)
        .filter(BloodUpload.user_id == g.current_user.id)
    )

    if requested_markers:
        query = query.filter(BloodResult.marker_name.in_(requested_markers))
    if from_date:
        query = query.filter(BloodUpload.test_date >= from_date)
    if to_date:
        query = query.filter(BloodUpload.test_date <= to_date)

    query = query.order_by(BloodUpload.test_date)
    rows = query.all()

    # Group by marker
    trends: dict = {}
    for result, test_date in rows:
        key = result.marker_name
        if key not in trends:
            trends[key] = {
                "display_name": result.marker_display_name,
                "unit": result.unit,
                "data_points": [],
                "reference_range": {
                    "low": result.reference_low,
                    "high": result.reference_high,
                },
            }
        trends[key]["data_points"].append(
            {
                "date": test_date.isoformat(),
                "value": result.value,
                "flag": result.flag,
            }
        )

    # Compute trend direction per marker
    for info in trends.values():
        points = info["data_points"]
        if len(points) >= 2:
            ref_high = info["reference_range"].get("high")
            first_val = points[0]["value"]
            last_val = points[-1]["value"]
            if ref_high and first_val > ref_high and last_val < first_val:
                info["trend_direction"] = "improving"
            elif ref_high and last_val > first_val:
                info["trend_direction"] = "worsening"
            else:
                info["trend_direction"] = "stable"
        else:
            info["trend_direction"] = "insufficient_data"

    return jsonify({"trends": trends})


# ── Available markers for this user ──────────────────────────────────────────


@blood_bp.route("/markers", methods=["GET"])
@login_required
def list_markers():
    """Return the distinct blood markers this user has uploaded."""
    rows = (
        db.session.query(
            BloodResult.marker_name,
            BloodResult.marker_display_name,
            func.count(BloodResult.id),
        )
        .join(BloodUpload, BloodResult.upload_id == BloodUpload.id)
        .filter(BloodUpload.user_id == g.current_user.id)
        .group_by(BloodResult.marker_name, BloodResult.marker_display_name)
        .all()
    )

    return jsonify(
        [
            {"marker_name": name, "display_name": display, "data_point_count": count}
            for name, display, count in rows
        ]
    )
