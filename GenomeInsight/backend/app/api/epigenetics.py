"""Epigenetics upload and analysis endpoints."""

import json
import os
import re

from flask import Blueprint, current_app, g, jsonify, request

from app.extensions import db, limiter
from app.models.audit import AuditLog
from app.models.epigenetics import (
    EpigeneticAnalysis,
    EpigeneticRegion,
    EpigeneticUpload,
)
from app.api.decorators import login_required
from app.services.file_upload import UploadValidationError, save_upload

epigenetics_bp = Blueprint(
    "epigenetics", __name__, url_prefix="/api/v1/epigenetics"
)

ALLOWED_DATA_TYPES = {"histone", "methylation"}
ALLOWED_ASSAY_TYPES = {
    "H3K27ac", "H3K4me3", "H3K4me1", "H3K27me3", "H3K36me3", "H3K9me3",
    "WGBS", "450K", "EPIC",
}
ALLOWED_TISSUE_TYPES = {
    "blood", "pbmc", "saliva", "liver", "brain", "adipose", "lung",
    "monocyte", "t_cell", "b_cell",
}

# Max file size for epigenetic uploads (100 MB)
MAX_EPIGENETICS_SIZE_BYTES = 100 * 1024 * 1024


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


# ── Upload ───────────────────────────────────────────────────────────────────


@epigenetics_bp.route("/upload", methods=["POST"])
@limiter.limit("10 per hour")
@login_required
def upload_epigenetics():
    """Upload a BED or CSV methylation file for epigenetic analysis."""
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

    assay_type = request.form.get("assay_type", "")
    if assay_type and assay_type not in ALLOWED_ASSAY_TYPES:
        assay_type = ""

    tissue_type = request.form.get("tissue_type", "")
    if tissue_type and tissue_type.lower() not in ALLOWED_TISSUE_TYPES:
        tissue_type = ""

    # Determine file_type from data_type or filename
    filename = file.filename.lower()
    if data_type == "histone":
        file_type = "bed"
    elif filename.endswith(".bed"):
        file_type = "bed"
    else:
        file_type = "csv"

    user = g.current_user

    try:
        # Use csv validation for both bed and csv (both are text-based)
        encrypted_path, sha256_hex, file_size = save_upload(
            file=file,
            file_type="csv",  # BED and methylation CSV are both text formats
            max_size_bytes=MAX_EPIGENETICS_SIZE_BYTES,
            user_encrypted_dek=user.data_encryption_key_enc,
            master_key=current_app.config["MASTER_ENCRYPTION_KEY"],
        )
    except UploadValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    upload = EpigeneticUpload(
        user_id=user.id,
        filename_original=_sanitize_filename(file.filename),
        file_path_encrypted=str(encrypted_path),
        file_hash_sha256=sha256_hex,
        file_type=file_type,
        data_type=data_type,
        assay_type=assay_type or None,
        tissue_type=tissue_type or None,
        status="uploaded",
        file_size_bytes=file_size,
    )
    db.session.add(upload)
    db.session.flush()

    analysis = EpigeneticAnalysis(upload_id=upload.id, status="queued")
    db.session.add(analysis)

    _audit(
        "upload_epigenetics",
        resource_type="EpigeneticUpload",
        resource_id=upload.id,
    )
    db.session.commit()

    # Dispatch Celery background task
    celery_task_id = None
    try:
        from app.tasks.epigenetics_tasks import run_epigenetics_analysis

        task = run_epigenetics_analysis.delay(analysis.id)
        celery_task_id = task.id
    except Exception:
        pass

    return (
        jsonify({
            "upload_id": upload.id,
            "analysis_id": analysis.id,
            "status": upload.status,
            "task_id": celery_task_id,
            "message": "Epigenetic data received. Analysis will begin shortly.",
        }),
        202,
    )


# ── List uploads ─────────────────────────────────────────────────────────────


@epigenetics_bp.route("/uploads", methods=["GET"])
@login_required
def list_uploads():
    uploads = (
        EpigeneticUpload.query.filter_by(user_id=g.current_user.id)
        .order_by(EpigeneticUpload.uploaded_at.desc())
        .all()
    )
    return jsonify([
        {
            "id": u.id,
            "filename": u.filename_original,
            "file_type": u.file_type,
            "data_type": u.data_type,
            "assay_type": u.assay_type,
            "tissue_type": u.tissue_type,
            "status": u.status,
            "uploaded_at": u.uploaded_at.isoformat(),
            "file_size_bytes": u.file_size_bytes,
        }
        for u in uploads
    ])


# ── Get upload detail ────────────────────────────────────────────────────────


@epigenetics_bp.route("/uploads/<upload_id>", methods=["GET"])
@login_required
def get_upload(upload_id: str):
    upload = EpigeneticUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Epigenetic upload not found."}), 404

    result = {
        "id": upload.id,
        "filename": upload.filename_original,
        "file_type": upload.file_type,
        "data_type": upload.data_type,
        "assay_type": upload.assay_type,
        "tissue_type": upload.tissue_type,
        "status": upload.status,
        "uploaded_at": upload.uploaded_at.isoformat(),
        "file_size_bytes": upload.file_size_bytes,
        "metrics": json.loads(upload.metrics_json) if upload.metrics_json else None,
    }
    if upload.analysis:
        result["analysis"] = {
            "id": upload.analysis.id,
            "status": upload.analysis.status,
            "region_count": upload.analysis.region_count,
            "annotated_region_count": upload.analysis.annotated_region_count,
            "global_methylation_avg": upload.analysis.global_methylation_avg,
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


# ── Delete upload ────────────────────────────────────────────────────────────


@epigenetics_bp.route("/uploads/<upload_id>", methods=["DELETE"])
@login_required
def delete_upload(upload_id: str):
    upload = EpigeneticUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Epigenetic upload not found."}), 404

    _audit(
        "delete_epigenetics",
        resource_type="EpigeneticUpload",
        resource_id=upload.id,
    )

    db.session.delete(upload)
    db.session.commit()

    return jsonify({"message": "Epigenetic upload and associated data deleted."})


# ── Analysis results ─────────────────────────────────────────────────────────


@epigenetics_bp.route("/analysis/<analysis_id>", methods=["GET"])
@login_required
def get_analysis(analysis_id: str):
    """Return full analysis results including insights and genome overlay."""
    analysis = (
        EpigeneticAnalysis.query.join(EpigeneticUpload)
        .filter(
            EpigeneticAnalysis.id == analysis_id,
            EpigeneticUpload.user_id == g.current_user.id,
        )
        .first()
    )
    if not analysis:
        return jsonify({"error": "Analysis not found."}), 404

    insights = None
    if analysis.insights_json:
        try:
            insights = json.loads(analysis.insights_json)
        except (json.JSONDecodeError, TypeError):
            pass

    genome_overlay = None
    if analysis.genome_overlay_json:
        try:
            genome_overlay = json.loads(analysis.genome_overlay_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return jsonify({
        "id": analysis.id,
        "upload_id": analysis.upload_id,
        "status": analysis.status,
        "region_count": analysis.region_count,
        "annotated_region_count": analysis.annotated_region_count,
        "global_methylation_avg": analysis.global_methylation_avg,
        "insights": insights,
        "genome_overlay": genome_overlay,
        "ai_summary": analysis.ai_summary_text,
        "started_at": (
            analysis.started_at.isoformat() if analysis.started_at else None
        ),
        "completed_at": (
            analysis.completed_at.isoformat() if analysis.completed_at else None
        ),
        "error_message": analysis.error_message,
        "disclaimer": (
            "Epigenetic annotations are based on population reference maps "
            "(ENCODE, Roadmap Epigenomics) and may not reflect your individual "
            "tissue-specific state. This is for informational purposes only "
            "and is NOT medical advice."
        ),
    })


# ── Regions (paginated) ──────────────────────────────────────────────────────


@epigenetics_bp.route("/analysis/<analysis_id>/regions", methods=["GET"])
@login_required
def get_regions(analysis_id: str):
    """Return paginated list of annotated regions."""
    analysis = (
        EpigeneticAnalysis.query.join(EpigeneticUpload)
        .filter(
            EpigeneticAnalysis.id == analysis_id,
            EpigeneticUpload.user_id == g.current_user.id,
        )
        .first()
    )
    if not analysis:
        return jsonify({"error": "Analysis not found."}), 404

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)
    chromosome_filter = request.args.get("chromosome")
    gene_filter = request.args.get("gene")

    query = EpigeneticRegion.query.filter_by(upload_id=analysis.upload_id)
    if chromosome_filter:
        query = query.filter(EpigeneticRegion.chromosome == chromosome_filter)
    if gene_filter:
        query = query.filter(EpigeneticRegion.nearest_gene == gene_filter)

    query = query.order_by(
        EpigeneticRegion.chromosome, EpigeneticRegion.start_pos
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for r in pagination.items:
        items.append({
            "id": r.id,
            "chromosome": r.chromosome,
            "start_pos": r.start_pos,
            "end_pos": r.end_pos,
            "feature_type": r.feature_type,
            "nearest_gene": r.nearest_gene,
            "methylation_beta": r.methylation_beta,
            "histone_mark": r.histone_mark,
            "signal_value": r.signal_value,
            "interpretation": r.interpretation,
        })

    return jsonify({
        "analysis_id": analysis_id,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "regions": items,
    })


# ── Genome overlay ───────────────────────────────────────────────────────────


@epigenetics_bp.route("/analysis/<analysis_id>/genome-overlay", methods=["GET"])
@login_required
def get_genome_overlay(analysis_id: str):
    """Return epigenetic annotations overlaid on genome variants."""
    analysis = (
        EpigeneticAnalysis.query.join(EpigeneticUpload)
        .filter(
            EpigeneticAnalysis.id == analysis_id,
            EpigeneticUpload.user_id == g.current_user.id,
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

    overlay = []
    if analysis.genome_overlay_json:
        try:
            overlay = json.loads(analysis.genome_overlay_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return jsonify({
        "analysis_id": analysis_id,
        "overlays": overlay,
        "disclaimer": (
            "Genome-epigenetic cross-references are experimental and based "
            "on population-level reference data. Risk modifiers are estimates "
            "and should NOT be used for clinical decisions."
        ),
    })


# ── Re-trigger analysis ─────────────────────────────────────────────────────


@epigenetics_bp.route("/uploads/<upload_id>/analyze", methods=["POST"])
@login_required
def trigger_analysis(upload_id: str):
    """Manually (re)trigger analysis for an upload."""
    upload = EpigeneticUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Epigenetic upload not found."}), 404

    analysis = upload.analysis
    if not analysis:
        analysis = EpigeneticAnalysis(upload_id=upload.id, status="queued")
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
        from app.tasks.epigenetics_tasks import run_epigenetics_analysis

        task = run_epigenetics_analysis.delay(analysis.id)
        celery_task_id = task.id
    except Exception:
        pass

    _audit(
        "trigger_epigenetics_analysis",
        resource_type="EpigeneticAnalysis",
        resource_id=analysis.id,
    )
    db.session.commit()

    return jsonify({
        "analysis_id": analysis.id,
        "status": analysis.status,
        "task_id": celery_task_id,
        "message": "Epigenetics analysis (re)queued.",
    })
