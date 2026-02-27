"""Genome upload and analysis endpoints."""

import json

from flask import Blueprint, current_app, g, jsonify, request

from app.extensions import db
from app.models.audit import AuditLog
from app.models.genome import (
    GenomeAnalysis,
    GenomeUpload,
    HealthRecommendation,
    Variant,
    VariantAnnotation,
)
from app.api.decorators import login_required
from app.services.file_upload import UploadValidationError, save_upload

genome_bp = Blueprint("genome", __name__, url_prefix="/api/v1/genome")

ALLOWED_SOURCES = {"23andme", "ancestry", "nebula", "other"}


def _audit(action: str, **kwargs):
    log = AuditLog(
        user_id=g.current_user.id,
        action=action,
        ip_address=request.remote_addr,
        **kwargs,
    )
    db.session.add(log)


# ── Upload ───────────────────────────────────────────────────────────────────


@genome_bp.route("/upload", methods=["POST"])
@login_required
def upload_genome():
    if "file" not in request.files:
        return jsonify({"error": "No file provided. Use multipart field 'file'."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename."}), 400

    source = request.form.get("source_service", "other").lower()
    if source not in ALLOWED_SOURCES:
        source = "other"

    user = g.current_user

    try:
        encrypted_path, sha256_hex, file_size = save_upload(
            file=file,
            file_type="vcf",
            max_size_bytes=current_app.config["MAX_VCF_SIZE_BYTES"],
            user_encrypted_dek=user.data_encryption_key_enc,
            master_key=current_app.config["MASTER_ENCRYPTION_KEY"],
        )
    except UploadValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    upload = GenomeUpload(
        user_id=user.id,
        filename_original=file.filename,
        file_path_encrypted=str(encrypted_path),
        file_hash_sha256=sha256_hex,
        source_service=source,
        status="uploaded",
        file_size_bytes=file_size,
    )
    db.session.add(upload)
    db.session.flush()  # Populate upload.id before referencing it

    analysis = GenomeAnalysis(upload_id=upload.id, status="queued")
    db.session.add(analysis)

    _audit("upload_genome", resource_type="GenomeUpload", resource_id=upload.id)
    db.session.commit()

    # Dispatch Celery background task
    celery_task_id = None
    try:
        from app.tasks.genome_tasks import run_genome_analysis

        task = run_genome_analysis.delay(analysis.id)
        celery_task_id = task.id
    except Exception:
        # If Celery/Redis is unavailable, analysis stays "queued"
        # and can be retried via POST /analyze endpoint below.
        pass

    return (
        jsonify(
            {
                "upload_id": upload.id,
                "analysis_id": analysis.id,
                "status": upload.status,
                "task_id": celery_task_id,
                "message": "File received. Analysis will begin shortly.",
            }
        ),
        202,
    )


# ── List uploads ─────────────────────────────────────────────────────────────


@genome_bp.route("/uploads", methods=["GET"])
@login_required
def list_uploads():
    uploads = (
        GenomeUpload.query.filter_by(user_id=g.current_user.id)
        .order_by(GenomeUpload.uploaded_at.desc())
        .all()
    )
    return jsonify(
        [
            {
                "id": u.id,
                "filename": u.filename_original,
                "source_service": u.source_service,
                "status": u.status,
                "uploaded_at": u.uploaded_at.isoformat(),
                "file_size_bytes": u.file_size_bytes,
            }
            for u in uploads
        ]
    )


# ── Get upload detail ────────────────────────────────────────────────────────


@genome_bp.route("/uploads/<upload_id>", methods=["GET"])
@login_required
def get_upload(upload_id: str):
    upload = GenomeUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Genome upload not found."}), 404

    result = {
        "id": upload.id,
        "filename": upload.filename_original,
        "source_service": upload.source_service,
        "genome_build": upload.genome_build,
        "status": upload.status,
        "uploaded_at": upload.uploaded_at.isoformat(),
        "file_size_bytes": upload.file_size_bytes,
    }
    if upload.analysis:
        result["analysis"] = {
            "id": upload.analysis.id,
            "status": upload.analysis.status,
            "variant_count": upload.analysis.variant_count,
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


@genome_bp.route("/uploads/<upload_id>", methods=["DELETE"])
@login_required
def delete_upload(upload_id: str):
    upload = GenomeUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Genome upload not found."}), 404

    _audit("delete_genome", resource_type="GenomeUpload", resource_id=upload.id)

    # In production, also delete the encrypted file from disk/S3
    db.session.delete(upload)
    db.session.commit()

    return jsonify({"message": "Genome upload and associated data deleted."})


# ── Analysis results ─────────────────────────────────────────────────────────


@genome_bp.route("/analysis/<analysis_id>", methods=["GET"])
@login_required
def get_analysis(analysis_id: str):
    analysis = (
        GenomeAnalysis.query.join(GenomeUpload)
        .filter(
            GenomeAnalysis.id == analysis_id,
            GenomeUpload.user_id == g.current_user.id,
        )
        .first()
    )
    if not analysis:
        return jsonify({"error": "Analysis not found."}), 404

    return jsonify(
        {
            "id": analysis.id,
            "upload_id": analysis.upload_id,
            "status": analysis.status,
            "variant_count": analysis.variant_count,
            "annotated_variant_count": analysis.annotated_variant_count,
            "risk_summary": analysis.risk_summary_json,
            "started_at": (
                analysis.started_at.isoformat() if analysis.started_at else None
            ),
            "completed_at": (
                analysis.completed_at.isoformat() if analysis.completed_at else None
            ),
            "error_message": analysis.error_message,
        }
    )


# ── Analysis report (AI-generated) ──────────────────────────────────────────


@genome_bp.route("/analysis/<analysis_id>/report", methods=["GET"])
@login_required
def get_report(analysis_id: str):
    analysis = (
        GenomeAnalysis.query.join(GenomeUpload)
        .filter(
            GenomeAnalysis.id == analysis_id,
            GenomeUpload.user_id == g.current_user.id,
        )
        .first()
    )
    if not analysis:
        return jsonify({"error": "Analysis not found."}), 404

    if analysis.status != "complete":
        return jsonify({"error": "Analysis is not yet complete.", "status": analysis.status}), 409

    return jsonify(
        {
            "analysis_id": analysis.id,
            "report": analysis.ai_report_text,
            "generated_at": (
                analysis.ai_report_generated_at.isoformat()
                if analysis.ai_report_generated_at
                else None
            ),
            "disclaimer": (
                "This report is for informational and educational purposes only. "
                "It is NOT medical advice and should NOT be used to diagnose, treat, "
                "or prevent any disease. Always consult a qualified healthcare provider."
            ),
        }
    )


# ── Recommendations ──────────────────────────────────────────────────────────


@genome_bp.route("/analysis/<analysis_id>/recommendations", methods=["GET"])
@login_required
def get_recommendations(analysis_id: str):
    analysis = (
        GenomeAnalysis.query.join(GenomeUpload)
        .filter(
            GenomeAnalysis.id == analysis_id,
            GenomeUpload.user_id == g.current_user.id,
        )
        .first()
    )
    if not analysis:
        return jsonify({"error": "Analysis not found."}), 404

    recs = (
        HealthRecommendation.query.filter_by(analysis_id=analysis_id)
        .order_by(HealthRecommendation.priority)
        .all()
    )

    return jsonify(
        {
            "analysis_id": analysis_id,
            "recommendations": [
                {
                    "id": r.id,
                    "category": r.category,
                    "title": r.title,
                    "body": r.body,
                    "confidence": r.confidence,
                    "priority": r.priority,
                    "evidence_rsids": r.evidence_rsids,
                    "evidence_sources": r.evidence_sources,
                }
                for r in recs
            ],
        }
    )


# ── Re-trigger analysis ─────────────────────────────────────────────────────


@genome_bp.route("/uploads/<upload_id>/analyze", methods=["POST"])
@login_required
def trigger_analysis(upload_id: str):
    """Manually (re)trigger analysis for an upload.

    Useful if the initial Celery dispatch failed or the analysis errored.
    """
    upload = GenomeUpload.query.filter_by(
        id=upload_id, user_id=g.current_user.id
    ).first()
    if not upload:
        return jsonify({"error": "Genome upload not found."}), 404

    analysis = upload.analysis
    if not analysis:
        analysis = GenomeAnalysis(upload_id=upload.id, status="queued")
        db.session.add(analysis)
        db.session.commit()

    if analysis.status == "running":
        return jsonify({"error": "Analysis is already running.", "analysis_id": analysis.id}), 409

    # Reset status for re-run
    analysis.status = "queued"
    analysis.error_message = None
    db.session.commit()

    celery_task_id = None
    try:
        from app.tasks.genome_tasks import run_genome_analysis

        task = run_genome_analysis.delay(analysis.id)
        celery_task_id = task.id
    except Exception:
        pass

    _audit("trigger_analysis", resource_type="GenomeAnalysis", resource_id=analysis.id)
    db.session.commit()

    return jsonify(
        {
            "analysis_id": analysis.id,
            "status": analysis.status,
            "task_id": celery_task_id,
            "message": "Analysis (re)queued.",
        }
    )


# ── Variants (paginated) ────────────────────────────────────────────────────


@genome_bp.route("/analysis/<analysis_id>/variants", methods=["GET"])
@login_required
def get_variants(analysis_id: str):
    """Return paginated variant list with their annotations."""
    analysis = (
        GenomeAnalysis.query.join(GenomeUpload)
        .filter(
            GenomeAnalysis.id == analysis_id,
            GenomeUpload.user_id == g.current_user.id,
        )
        .first()
    )
    if not analysis:
        return jsonify({"error": "Analysis not found."}), 404

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)
    rsid_filter = request.args.get("rsid")
    chromosome_filter = request.args.get("chromosome")

    query = Variant.query.filter_by(analysis_id=analysis_id)
    if rsid_filter:
        query = query.filter(Variant.rsid == rsid_filter)
    if chromosome_filter:
        query = query.filter(Variant.chromosome == chromosome_filter)

    query = query.order_by(Variant.chromosome, Variant.position)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for v in pagination.items:
        annotations = [
            {
                "source": a.source,
                "gene_symbol": a.gene_symbol,
                "consequence": a.consequence,
                "clinical_significance": a.clinical_significance,
                "condition_name": a.condition_name,
                "trait_association": a.trait_association,
                "odds_ratio": a.odds_ratio,
                "pubmed_ids": a.pubmed_ids,
            }
            for a in v.annotations
        ]
        items.append(
            {
                "id": v.id,
                "rsid": v.rsid,
                "chromosome": v.chromosome,
                "position": v.position,
                "ref_allele": v.ref_allele,
                "alt_allele": v.alt_allele,
                "genotype": v.genotype,
                "quality": v.quality,
                "annotations": annotations,
            }
        )

    return jsonify(
        {
            "analysis_id": analysis_id,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "variants": items,
        }
    )


# ── Risk summary ─────────────────────────────────────────────────────────────


@genome_bp.route("/analysis/<analysis_id>/risks", methods=["GET"])
@login_required
def get_risks(analysis_id: str):
    """Return the risk category summary for an analysis."""
    analysis = (
        GenomeAnalysis.query.join(GenomeUpload)
        .filter(
            GenomeAnalysis.id == analysis_id,
            GenomeUpload.user_id == g.current_user.id,
        )
        .first()
    )
    if not analysis:
        return jsonify({"error": "Analysis not found."}), 404

    risk_data = {}
    if analysis.risk_summary_json:
        try:
            risk_data = json.loads(analysis.risk_summary_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return jsonify(
        {
            "analysis_id": analysis_id,
            "status": analysis.status,
            "risk_categories": risk_data,
        }
    )
