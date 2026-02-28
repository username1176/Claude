"""Microbiome upload and analysis endpoints."""

import json
import os
import re

from flask import Blueprint, current_app, g, jsonify, request

from app.extensions import db, limiter
from app.models.audit import AuditLog
from app.models.microbiome import (
    MicrobiomeAnalysis,
    MicrobiomeTaxon,
    MicrobiomeUpload,
)
from app.api.decorators import login_required
from app.services.file_upload import UploadValidationError, save_upload

microbiome_bp = Blueprint(
    "microbiome", __name__, url_prefix="/api/v1/microbiome"
)

ALLOWED_FILE_TYPES = {"biom", "csv", "tsv", "fastq"}
ALLOWED_DATA_TYPES = {"16s_rrna", "shotgun", "its", "wgs"}
ALLOWED_SAMPLE_SOURCES = {"gut", "oral", "skin", "vaginal", "environmental"}

# Max file size for microbiome uploads (200 MB)
MAX_MICROBIOME_SIZE_BYTES = 200 * 1024 * 1024


def _sanitize_filename(name: str) -> str:
    """Strip path traversal and non-alphanumeric chars from a filename."""
    name = os.path.basename(name)
    name = re.sub(r"[^\w.\-]", "_", name)
    return name or "upload"


def _audit(action: str, **kwargs):
    log = AuditLog(
        user_id=g.current_user.id,
        action=action,
        ip_address=request.remote_addr,
        **kwargs,
    )
    db.session.add(log)


# -- Upload -------------------------------------------------------------------


@microbiome_bp.route("/upload", methods=["POST"])
@limiter.limit("10 per hour")
@login_required
def upload_microbiome():
    """Upload a microbiome data file (BIOM, OTU CSV/TSV, FASTQ)."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided. Use multipart field 'file'."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename."}), 400

    data_type = request.form.get("data_type", "").lower()
    if data_type not in ALLOWED_DATA_TYPES:
        return (
            jsonify({
                "error": f"Invalid data_type. Must be one of: {', '.join(sorted(ALLOWED_DATA_TYPES))}",
            }),
            400,
        )

    # Determine file_type from filename extension
    filename_lower = file.filename.lower()
    if filename_lower.endswith(".biom") or filename_lower.endswith(".biom.json"):
        file_type = "biom"
    elif filename_lower.endswith(".tsv"):
        file_type = "tsv"
    elif filename_lower.endswith((".fastq", ".fq", ".fastq.gz")):
        file_type = "fastq"
    else:
        file_type = "csv"

    if file_type not in ALLOWED_FILE_TYPES:
        return jsonify({"error": f"Unsupported file type: {file_type}"}), 400

    sample_source = request.form.get("sample_source", "").lower()
    if sample_source and sample_source not in ALLOWED_SAMPLE_SOURCES:
        sample_source = ""

    collection_date_str = request.form.get("collection_date", "")
    collection_date = None
    if collection_date_str:
        try:
            from datetime import date

            collection_date = date.fromisoformat(collection_date_str)
        except ValueError:
            pass

    sequencing_platform = request.form.get("sequencing_platform", "")

    user = g.current_user

    try:
        encrypted_path, sha256_hex, file_size = save_upload(
            file=file,
            file_type="csv",  # BIOM, OTU CSV/TSV, FASTQ are all text-based
            max_size_bytes=MAX_MICROBIOME_SIZE_BYTES,
            user_encrypted_dek=user.data_encryption_key_enc,
            master_key=current_app.config["MASTER_ENCRYPTION_KEY"],
        )
    except UploadValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    upload = MicrobiomeUpload(
        user_id=user.id,
        filename_original=_sanitize_filename(file.filename),
        file_path_encrypted=str(encrypted_path),
        file_hash_sha256=sha256_hex,
        file_type=file_type,
        data_type=data_type,
        sample_source=sample_source or None,
        collection_date=collection_date,
        sequencing_platform=sequencing_platform or None,
        status="uploaded",
        file_size_bytes=file_size,
    )
    db.session.add(upload)
    db.session.flush()

    analysis = MicrobiomeAnalysis(upload_id=upload.id, status="queued")
    db.session.add(analysis)

    _audit(
        "upload_microbiome",
        resource_type="MicrobiomeUpload",
        resource_id=upload.id,
    )
    db.session.commit()

    # Dispatch Celery background task
    celery_task_id = None
    try:
        from app.tasks.microbiome_tasks import run_microbiome_analysis

        task = run_microbiome_analysis.delay(analysis.id)
        celery_task_id = task.id
    except Exception:
        pass

    return (
        jsonify({
            "upload_id": upload.id,
            "analysis_id": analysis.id,
            "status": upload.status,
            "task_id": celery_task_id,
            "message": "Microbiome data received. Analysis will begin shortly.",
        }),
        202,
    )


# -- List uploads --------------------------------------------------------------


@microbiome_bp.route("/uploads", methods=["GET"])
@login_required
def list_uploads():
    uploads = (
        MicrobiomeUpload.query.filter_by(user_id=g.current_user.id)
        .order_by(MicrobiomeUpload.uploaded_at.desc())
        .all()
    )
    return jsonify([
        {
            "id": u.id,
            "filename": u.filename_original,
            "file_type": u.file_type,
            "data_type": u.data_type,
            "sample_source": u.sample_source,
            "collection_date": u.collection_date.isoformat() if u.collection_date else None,
            "status": u.status,
            "uploaded_at": u.uploaded_at.isoformat(),
            "file_size_bytes": u.file_size_bytes,
        }
        for u in uploads
    ])


# -- Get upload detail ---------------------------------------------------------


@microbiome_bp.route("/uploads/<upload_id>", methods=["GET"])
@login_required
def get_upload(upload_id: str):
    upload = MicrobiomeUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Microbiome upload not found."}), 404

    result = {
        "id": upload.id,
        "filename": upload.filename_original,
        "file_type": upload.file_type,
        "data_type": upload.data_type,
        "sample_source": upload.sample_source,
        "collection_date": upload.collection_date.isoformat() if upload.collection_date else None,
        "sequencing_platform": upload.sequencing_platform,
        "status": upload.status,
        "uploaded_at": upload.uploaded_at.isoformat(),
        "file_size_bytes": upload.file_size_bytes,
        "metrics": json.loads(upload.metrics_json) if upload.metrics_json else None,
    }
    if upload.analysis:
        result["analysis"] = {
            "id": upload.analysis.id,
            "status": upload.analysis.status,
            "enterotype": upload.analysis.enterotype,
            "started_at": (
                upload.analysis.started_at.isoformat()
                if upload.analysis.started_at
                else None
            ),
            "completed_at": (
                upload.analysis.completed_at.isoformat()
                if upload.analysis.completed_at
                else None
            ),
        }
    return jsonify(result)


# -- Delete upload -------------------------------------------------------------


@microbiome_bp.route("/uploads/<upload_id>", methods=["DELETE"])
@login_required
def delete_upload(upload_id: str):
    upload = MicrobiomeUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Microbiome upload not found."}), 404

    _audit(
        "delete_microbiome",
        resource_type="MicrobiomeUpload",
        resource_id=upload.id,
    )

    db.session.delete(upload)
    db.session.commit()

    return jsonify({"message": "Microbiome upload and associated data deleted."})


# -- Analysis results ----------------------------------------------------------


@microbiome_bp.route("/analysis/<analysis_id>", methods=["GET"])
@login_required
def get_analysis(analysis_id: str):
    """Return full analysis results including diversity, composition, and correlations."""
    analysis = (
        MicrobiomeAnalysis.query.join(MicrobiomeUpload)
        .filter(
            MicrobiomeAnalysis.id == analysis_id,
            MicrobiomeUpload.user_id == g.current_user.id,
        )
        .first()
    )
    if not analysis:
        return jsonify({"error": "Analysis not found."}), 404

    diversity = None
    if analysis.diversity_json:
        try:
            diversity = json.loads(analysis.diversity_json)
        except (json.JSONDecodeError, TypeError):
            pass

    composition = None
    if analysis.composition_json:
        try:
            composition = json.loads(analysis.composition_json)
        except (json.JSONDecodeError, TypeError):
            pass

    health_insights = None
    if analysis.health_insights_json:
        try:
            health_insights = json.loads(analysis.health_insights_json)
        except (json.JSONDecodeError, TypeError):
            pass

    genome_correlation = None
    if analysis.genome_correlation_json:
        try:
            genome_correlation = json.loads(analysis.genome_correlation_json)
        except (json.JSONDecodeError, TypeError):
            pass

    blood_correlation = None
    if analysis.blood_correlation_json:
        try:
            blood_correlation = json.loads(analysis.blood_correlation_json)
        except (json.JSONDecodeError, TypeError):
            pass

    lifestyle_recs = None
    if analysis.lifestyle_recs_json:
        try:
            lifestyle_recs = json.loads(analysis.lifestyle_recs_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return jsonify({
        "id": analysis.id,
        "upload_id": analysis.upload_id,
        "status": analysis.status,
        "total_read_count": analysis.total_read_count,
        "classified_read_count": analysis.classified_read_count,
        "enterotype": analysis.enterotype,
        "diversity": diversity,
        "composition": composition,
        "health_insights": health_insights,
        "genome_correlation": genome_correlation,
        "blood_correlation": blood_correlation,
        "lifestyle_recommendations": lifestyle_recs,
        "ai_summary": analysis.ai_summary_text,
        "started_at": (
            analysis.started_at.isoformat() if analysis.started_at else None
        ),
        "completed_at": (
            analysis.completed_at.isoformat() if analysis.completed_at else None
        ),
        "error_message": analysis.error_message,
        "disclaimer": (
            "Microbiome analysis is based on a single sample and may not reflect "
            "your typical microbiome composition. Results vary with diet, medication, "
            "and sample collection method. This is for informational purposes only "
            "and is NOT medical advice."
        ),
    })


# -- Taxa (paginated) ---------------------------------------------------------


@microbiome_bp.route("/analysis/<analysis_id>/taxa", methods=["GET"])
@login_required
def get_taxa(analysis_id: str):
    """Return paginated list of taxa."""
    analysis = (
        MicrobiomeAnalysis.query.join(MicrobiomeUpload)
        .filter(
            MicrobiomeAnalysis.id == analysis_id,
            MicrobiomeUpload.user_id == g.current_user.id,
        )
        .first()
    )
    if not analysis:
        return jsonify({"error": "Analysis not found."}), 404

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)
    level_filter = request.args.get("level")

    query = MicrobiomeTaxon.query.filter_by(upload_id=analysis.upload_id)
    if level_filter:
        query = query.filter(MicrobiomeTaxon.taxonomy_level == level_filter)

    query = query.order_by(MicrobiomeTaxon.relative_abundance.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for t in pagination.items:
        items.append({
            "id": t.id,
            "taxonomy_level": t.taxonomy_level,
            "taxonomy_name": t.taxonomy_name,
            "taxonomy_id": t.taxonomy_id,
            "relative_abundance": t.relative_abundance,
            "absolute_count": t.absolute_count,
            "confidence": t.confidence,
            "parent_taxon": t.parent_taxon,
        })

    return jsonify({
        "analysis_id": analysis_id,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "taxa": items,
    })


# -- Composition ---------------------------------------------------------------


@microbiome_bp.route("/analysis/<analysis_id>/composition", methods=["GET"])
@login_required
def get_composition(analysis_id: str):
    """Return composition breakdown at a given taxonomy level."""
    analysis = (
        MicrobiomeAnalysis.query.join(MicrobiomeUpload)
        .filter(
            MicrobiomeAnalysis.id == analysis_id,
            MicrobiomeUpload.user_id == g.current_user.id,
        )
        .first()
    )
    if not analysis:
        return jsonify({"error": "Analysis not found."}), 404

    if analysis.status != "complete":
        return (
            jsonify({
                "error": "Analysis is not yet complete.",
                "status": analysis.status,
            }),
            409,
        )

    composition = []
    if analysis.composition_json:
        try:
            composition = json.loads(analysis.composition_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return jsonify({
        "analysis_id": analysis_id,
        "enterotype": analysis.enterotype,
        "composition": composition,
    })


# -- Genome correlation --------------------------------------------------------


@microbiome_bp.route("/analysis/<analysis_id>/genome-correlation", methods=["GET"])
@login_required
def get_genome_correlation(analysis_id: str):
    """Return genome-microbiome cross-domain correlations."""
    analysis = (
        MicrobiomeAnalysis.query.join(MicrobiomeUpload)
        .filter(
            MicrobiomeAnalysis.id == analysis_id,
            MicrobiomeUpload.user_id == g.current_user.id,
        )
        .first()
    )
    if not analysis:
        return jsonify({"error": "Analysis not found."}), 404

    if analysis.status != "complete":
        return (
            jsonify({
                "error": "Analysis is not yet complete.",
                "status": analysis.status,
            }),
            409,
        )

    correlations = []
    if analysis.genome_correlation_json:
        try:
            correlations = json.loads(analysis.genome_correlation_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return jsonify({
        "analysis_id": analysis_id,
        "correlations": correlations,
        "disclaimer": (
            "Genome-microbiome correlations are based on population-level "
            "research and may not apply to your individual situation. "
            "This is NOT medical advice."
        ),
    })


# -- Re-trigger analysis -------------------------------------------------------


@microbiome_bp.route("/uploads/<upload_id>/analyze", methods=["POST"])
@login_required
def trigger_analysis(upload_id: str):
    """Manually (re)trigger analysis for an upload."""
    upload = MicrobiomeUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Microbiome upload not found."}), 404

    analysis = upload.analysis
    if not analysis:
        analysis = MicrobiomeAnalysis(upload_id=upload.id, status="queued")
        db.session.add(analysis)
        db.session.commit()

    if analysis.status == "running":
        return (
            jsonify({
                "error": "Analysis is already running.",
                "analysis_id": analysis.id,
            }),
            409,
        )

    analysis.status = "queued"
    analysis.error_message = None
    db.session.commit()

    celery_task_id = None
    try:
        from app.tasks.microbiome_tasks import run_microbiome_analysis

        task = run_microbiome_analysis.delay(analysis.id)
        celery_task_id = task.id
    except Exception:
        pass

    _audit(
        "trigger_microbiome_analysis",
        resource_type="MicrobiomeAnalysis",
        resource_id=analysis.id,
    )
    db.session.commit()

    return jsonify({
        "analysis_id": analysis.id,
        "status": analysis.status,
        "task_id": celery_task_id,
        "message": "Microbiome analysis (re)queued.",
    })


# -- Full cross-domain analysis ------------------------------------------------


@microbiome_bp.route("/full-analysis", methods=["POST"])
@login_required
def trigger_full_analysis():
    """Trigger combined analysis across all data types for the user.

    Re-analyses the most recent microbiome upload with fresh cross-domain
    correlations from genome, blood, and wearable data.
    """
    user = g.current_user

    latest_upload = (
        MicrobiomeUpload.query.filter_by(user_id=user.id)
        .order_by(MicrobiomeUpload.uploaded_at.desc())
        .first()
    )
    if not latest_upload:
        return jsonify({"error": "No microbiome uploads found."}), 404

    analysis = latest_upload.analysis
    if not analysis:
        analysis = MicrobiomeAnalysis(upload_id=latest_upload.id, status="queued")
        db.session.add(analysis)
        db.session.commit()

    if analysis.status == "running":
        return (
            jsonify({
                "error": "Analysis is already running.",
                "analysis_id": analysis.id,
            }),
            409,
        )

    analysis.status = "queued"
    analysis.error_message = None
    db.session.commit()

    celery_task_id = None
    try:
        from app.tasks.microbiome_tasks import run_microbiome_analysis

        task = run_microbiome_analysis.delay(analysis.id)
        celery_task_id = task.id
    except Exception:
        pass

    _audit(
        "trigger_full_microbiome_analysis",
        resource_type="MicrobiomeAnalysis",
        resource_id=analysis.id,
    )
    db.session.commit()

    return jsonify({
        "upload_id": latest_upload.id,
        "analysis_id": analysis.id,
        "status": analysis.status,
        "task_id": celery_task_id,
        "message": "Full cross-domain microbiome analysis queued.",
    })
