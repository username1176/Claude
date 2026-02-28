"""Blood test upload, parsing, results, trend, and change-analysis endpoints."""

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


def _result_to_dict(r: BloodResult) -> dict:
    """Serialise a BloodResult to a JSON-safe dict."""
    return {
        "id": r.id,
        "marker_name": r.marker_name,
        "marker_display_name": r.marker_display_name,
        "value": r.value,
        "unit": r.unit,
        "reference_low": r.reference_low,
        "reference_high": r.reference_high,
        "flag": r.flag,
    }


# ── Upload (POST /api/v1/blood/upload) ──────────────────────────────────────


@blood_bp.route("/upload", methods=["POST"])
@login_required
def upload_blood():
    """Accept a PDF or CSV blood-test file, encrypt it, parse markers, and
    persist the results.

    Form fields:
        file       – multipart file (required)
        test_date  – ISO 8601 date string YYYY-MM-DD (required)
        lab_name   – optional lab name
    """
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

    # ── Read raw bytes before encryption (for parsing) ───────────────────
    raw_bytes = file.read()
    file.seek(0)  # Rewind so save_upload can read again

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
    db.session.flush()  # Populate upload.id

    # ── Parse blood markers from the raw file ────────────────────────────
    from app.utils.blood_parser import parse_blood_file

    parsed_markers = parse_blood_file(raw_bytes, extension)
    for pm in parsed_markers:
        db.session.add(BloodResult(
            upload_id=upload.id,
            marker_name=pm.marker_name,
            marker_display_name=pm.marker_display_name,
            value=pm.value,
            unit=pm.unit,
            reference_low=pm.reference_low,
            reference_high=pm.reference_high,
            flag=pm.flag,
        ))

    if parsed_markers:
        upload.status = "parsed"

    _audit("upload_blood", resource_type="BloodUpload", resource_id=upload.id)
    db.session.commit()

    # Dispatch async change-analysis if there are previous uploads
    celery_task_id = None
    prev_count = (
        BloodUpload.query
        .filter(
            BloodUpload.user_id == user.id,
            BloodUpload.id != upload.id,
        )
        .count()
    )
    if prev_count > 0 and parsed_markers:
        try:
            from app.tasks.blood_tasks import run_blood_change_analysis
            task = run_blood_change_analysis.delay(upload.id)
            celery_task_id = task.id
        except Exception:
            pass  # Celery/Redis not available — user can trigger manually

    return (
        jsonify(
            {
                "upload_id": upload.id,
                "status": upload.status,
                "markers_parsed": len(parsed_markers),
                "task_id": celery_task_id,
                "message": (
                    f"File received and {len(parsed_markers)} markers parsed."
                    if parsed_markers
                    else "File received. No markers could be auto-parsed — use PUT to enter results manually."
                ),
            }
        ),
        202,
    )


# ── List uploads ────────────────────────────────────────────────────────────


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


# ── Get upload + parsed results ─────────────────────────────────────────────


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
            "results": [_result_to_dict(r) for r in upload.results],
        }
    )


# ── Delete upload ───────────────────────────────────────────────────────────


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


# ── Correct parsed results ──────────────────────────────────────────────────


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


# ── Blood history (GET /api/v1/blood/history) ───────────────────────────────


@blood_bp.route("/history", methods=["GET"])
@login_required
def blood_history():
    """Return a chronological list of uploads with per-upload result summaries
    and inter-upload change deltas.
    """
    uploads = (
        BloodUpload.query.filter_by(user_id=g.current_user.id)
        .order_by(BloodUpload.test_date.asc())
        .all()
    )
    if not uploads:
        return jsonify({"history": [], "total_uploads": 0})

    from app.utils.blood_parser import compute_deltas

    history: list[dict] = []
    prev_results: list[dict] | None = None

    for upload in uploads:
        curr_results = [_result_to_dict(r) for r in upload.results]

        entry: dict = {
            "upload_id": upload.id,
            "filename": upload.filename_original,
            "test_date": upload.test_date.isoformat(),
            "lab_name": upload.lab_name,
            "status": upload.status,
            "result_count": len(curr_results),
            "results": curr_results,
            "changes": None,
        }

        if prev_results is not None and curr_results:
            deltas = compute_deltas(prev_results, curr_results)
            entry["changes"] = [
                {
                    "marker_name": d.marker_name,
                    "marker_display_name": d.marker_display_name,
                    "previous_value": d.previous_value,
                    "current_value": d.current_value,
                    "unit": d.unit,
                    "absolute_change": d.absolute_change,
                    "percent_change": d.percent_change,
                    "direction": d.direction,
                    "improved": d.improved,
                }
                for d in deltas
            ]

        history.append(entry)
        if curr_results:
            prev_results = curr_results

    return jsonify({"history": history, "total_uploads": len(uploads)})


# ── Analyze changes (POST /api/v1/blood/analyze-changes) ────────────────────


@blood_bp.route("/analyze-changes", methods=["POST"])
@login_required
def analyze_changes():
    """Compare the latest upload with the previous one (or a specified pair),
    correlate with genome data, and return insights.

    Optional JSON body:
        current_upload_id  – defaults to the most recent upload
        previous_upload_id – defaults to the second most recent upload
    """
    data = request.get_json(silent=True) or {}
    user_id = g.current_user.id

    # Resolve current and previous uploads
    current_upload_id = data.get("current_upload_id")
    previous_upload_id = data.get("previous_upload_id")

    if current_upload_id:
        current_upload = BloodUpload.query.filter_by(
            id=current_upload_id, user_id=user_id
        ).first()
    else:
        current_upload = (
            BloodUpload.query.filter_by(user_id=user_id)
            .order_by(BloodUpload.test_date.desc())
            .first()
        )

    if not current_upload:
        return jsonify({"error": "No blood uploads found."}), 404

    if previous_upload_id:
        previous_upload = BloodUpload.query.filter_by(
            id=previous_upload_id, user_id=user_id
        ).first()
    else:
        previous_upload = (
            BloodUpload.query.filter(
                BloodUpload.user_id == user_id,
                BloodUpload.test_date < current_upload.test_date,
            )
            .order_by(BloodUpload.test_date.desc())
            .first()
        )

    # Compute marker deltas
    from app.utils.blood_parser import compute_deltas, cross_reference_genome

    curr_results = [_result_to_dict(r) for r in current_upload.results]

    deltas = []
    if previous_upload:
        prev_results = [_result_to_dict(r) for r in previous_upload.results]
        deltas = compute_deltas(prev_results, curr_results)

    # ── Genome cross-reference ───────────────────────────────────────────
    from app.models.genome import GenomeAnalysis, GenomeUpload, Variant

    genome_insights_data: list[dict] = []

    # Find the user's most recent completed genome analysis
    latest_analysis = (
        GenomeAnalysis.query.join(GenomeUpload)
        .filter(
            GenomeUpload.user_id == user_id,
            GenomeAnalysis.status == "complete",
        )
        .order_by(GenomeAnalysis.completed_at.desc())
        .first()
    )

    if latest_analysis:
        # Collect all non-reference rsIDs
        variants = Variant.query.filter(
            Variant.analysis_id == latest_analysis.id,
            Variant.rsid.isnot(None),
            Variant.genotype != "0/0",
        ).all()
        user_rsids = {v.rsid for v in variants}

        insights = cross_reference_genome(
            blood_markers=curr_results,
            user_rsids=user_rsids,
            deltas=deltas if deltas else None,
        )
        genome_insights_data = [
            {
                "rsid": gi.rsid,
                "risk_category": gi.risk_category,
                "marker_name": gi.marker_name,
                "marker_display_name": gi.marker_display_name,
                "value": gi.value,
                "unit": gi.unit,
                "flag": gi.flag,
                "insight": gi.insight,
                "priority": gi.priority,
            }
            for gi in insights
        ]

    # ── Compose summary insights ─────────────────────────────────────────
    summary_insights: list[str] = []
    for d in deltas:
        if d.direction == "unchanged":
            continue
        verb = "decreased" if d.direction == "decreased" else "increased"
        trend = ""
        if d.improved is True:
            trend = " — a positive trend"
        elif d.improved is False:
            trend = " — worth monitoring"
        summary_insights.append(
            f"{d.marker_display_name} {verb} {abs(d.percent_change):.1f}%"
            f" ({d.previous_value} → {d.current_value} {d.unit}){trend}."
        )

    _audit("analyze_blood_changes", resource_type="BloodUpload", resource_id=current_upload.id)
    db.session.commit()

    return jsonify({
        "current_upload": {
            "id": current_upload.id,
            "test_date": current_upload.test_date.isoformat(),
        },
        "previous_upload": {
            "id": previous_upload.id,
            "test_date": previous_upload.test_date.isoformat(),
        } if previous_upload else None,
        "deltas": [
            {
                "marker_name": d.marker_name,
                "marker_display_name": d.marker_display_name,
                "previous_value": d.previous_value,
                "current_value": d.current_value,
                "unit": d.unit,
                "absolute_change": d.absolute_change,
                "percent_change": d.percent_change,
                "direction": d.direction,
                "previous_flag": d.previous_flag,
                "current_flag": d.current_flag,
                "improved": d.improved,
            }
            for d in deltas
        ],
        "genome_insights": genome_insights_data,
        "summary": summary_insights,
    })


# ── Trends (time-series) ───────────────────────────────────────────────────


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


# ── Available markers for this user ─────────────────────────────────────────


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
