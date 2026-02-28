"""Celery tasks for epigenetics analysis.

The main task, ``run_epigenetics_analysis``, is dispatched after an
epigenetic file upload and orchestrates the pipeline:

    Decrypt file → Parse BED/CSV → Annotate regions → Query ENCODE →
    Query Roadmap → Cross-reference genome → Generate AI summary → Persist
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
from celery import shared_task

from app.extensions import db
from app.models.epigenetics import (
    EpigeneticAnalysis,
    EpigeneticRegion,
    EpigeneticUpload,
)
from app.models.genome import GenomeAnalysis, GenomeUpload, Variant, VariantAnnotation
from app.services.encryption import decrypt_dek, decrypt_file
from app.utils.epigenetics_analyzer import (
    annotate_regions,
    cross_reference_genome,
    generate_epigenetics_ai_summary,
    parse_bed,
    parse_methylation_csv,
)

logger = logging.getLogger(__name__)


def _update_analysis(analysis: EpigeneticAnalysis, **kwargs) -> None:
    """Update analysis fields and commit."""
    for key, value in kwargs.items():
        setattr(analysis, key, value)
    db.session.commit()


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_epigenetics_analysis(self, analysis_id: str) -> dict:
    """Run the full epigenetics analysis pipeline.

    Args:
        analysis_id: UUID of the EpigeneticAnalysis record.

    Returns:
        Summary dict with counts and status.
    """
    from flask import current_app

    analysis = db.session.get(EpigeneticAnalysis, analysis_id)
    if not analysis:
        logger.error("EpigeneticAnalysis %s not found", analysis_id)
        return {"error": "Analysis not found"}

    upload = analysis.upload
    if not upload:
        _update_analysis(analysis, status="error", error_message="Upload record missing")
        return {"error": "Upload record missing"}

    _update_analysis(analysis, status="running", started_at=datetime.now(timezone.utc))

    try:
        # ── Step 1: Decrypt and parse file ────────────────────────────────
        logger.info("Step 1: Decrypting and parsing epigenetic file for analysis %s", analysis_id)

        master_key = current_app.config["MASTER_ENCRYPTION_KEY"]
        user = upload.user
        dek = decrypt_dek(user.data_encryption_key_enc, master_key)

        encrypted_path = Path(upload.file_path_encrypted)
        file_bytes = decrypt_file(encrypted_path, dek)

        if upload.data_type == "histone":
            parsed_regions = parse_bed(file_bytes, assay_type=upload.assay_type)
        elif upload.data_type == "methylation":
            parsed_regions = parse_methylation_csv(file_bytes)
        else:
            _update_analysis(
                analysis,
                status="error",
                error_message=f"Unknown data_type: {upload.data_type}",
            )
            return {"error": f"Unknown data_type: {upload.data_type}"}

        if not parsed_regions:
            _update_analysis(
                analysis,
                status="error",
                error_message="No regions found in file. Check file format.",
            )
            return {"error": "No regions parsed"}

        analysis.region_count = len(parsed_regions)
        db.session.commit()

        # ── Step 2: Annotate regions (feature type, ENCODE, Roadmap) ──────
        logger.info("Step 2: Annotating %d regions", len(parsed_regions))

        try:
            client = httpx.Client(
                timeout=httpx.Timeout(connect=10, read=30, write=10, pool=10)
            )
        except Exception:
            client = None

        try:
            region_annotations = annotate_regions(
                parsed_regions,
                client=client,
                assay_type=upload.assay_type,
                tissue_type=upload.tissue_type,
            )
        finally:
            if client:
                client.close()

        # ── Step 3: Persist parsed regions ─────────────────────────────────
        logger.info("Step 3: Storing %d parsed regions", len(parsed_regions))

        annotated_count = 0
        global_betas: list[float] = []

        for region in parsed_regions:
            key = f"{region.chromosome}:{region.start_pos}-{region.end_pos}"
            ann = region_annotations.get(key, {})

            encode_json = json.dumps(ann.get("encode_experiments", []))
            roadmap_json = json.dumps(ann.get("roadmap", {}))

            # Build interpretation
            interpretation = ""
            roadmap_info = ann.get("roadmap", {})
            state_label = roadmap_info.get("state_label", "")
            gene = ann.get("nearest_gene", "")
            feature = ann.get("feature_type", "intergenic")

            if state_label:
                interpretation = f"{feature.title()} region"
                if gene:
                    interpretation += f" near {gene}"
                interpretation += f" — {state_label}."

            has_annotation = bool(gene or state_label or ann.get("encode_experiments"))
            if has_annotation:
                annotated_count += 1

            if region.methylation_beta is not None:
                global_betas.append(region.methylation_beta)

            db.session.add(
                EpigeneticRegion(
                    upload_id=upload.id,
                    chromosome=region.chromosome,
                    start_pos=region.start_pos,
                    end_pos=region.end_pos,
                    feature_type=feature,
                    nearest_gene=gene,
                    methylation_beta=region.methylation_beta,
                    histone_mark=region.histone_mark,
                    signal_value=region.signal_value,
                    encode_overlap_json=encode_json,
                    roadmap_overlap_json=roadmap_json,
                    interpretation=interpretation,
                )
            )

        db.session.commit()

        analysis.annotated_region_count = annotated_count
        global_avg = sum(global_betas) / len(global_betas) if global_betas else None
        analysis.global_methylation_avg = global_avg
        db.session.commit()

        # ── Step 4: Cross-reference with genome variants ───────────────────
        logger.info("Step 4: Cross-referencing with genome data")

        user_variants = _load_user_genome_variants(user.id)
        overlays = cross_reference_genome(
            parsed_regions, region_annotations, user_variants
        )

        overlay_data = [
            {
                "variant_rsid": ov.variant_rsid,
                "gene": ov.gene,
                "variant_risk": ov.variant_risk,
                "region_coords": ov.region_coords,
                "feature_type": ov.feature_type,
                "methylation_beta": ov.methylation_beta,
                "histone_mark": ov.histone_mark,
                "interpretation": ov.interpretation,
                "adjusted_risk_modifier": ov.adjusted_risk_modifier,
            }
            for ov in overlays
        ]
        analysis.genome_overlay_json = json.dumps(overlay_data)
        db.session.commit()

        # ── Step 5: Generate AI summary ────────────────────────────────────
        logger.info("Step 5: Generating epigenetics summary")

        openai_key = current_app.config.get("OPENAI_API_KEY", "")
        summary = generate_epigenetics_ai_summary(
            region_count=len(parsed_regions),
            annotated_count=annotated_count,
            global_methylation_avg=global_avg,
            overlays=overlays,
            data_type=upload.data_type,
            openai_api_key=openai_key,
        )

        # Build insights JSON
        insights = {
            "region_count": len(parsed_regions),
            "annotated_count": annotated_count,
            "global_methylation_avg": global_avg,
            "genome_overlays": len(overlays),
            "data_type": upload.data_type,
            "assay_type": upload.assay_type,
        }

        # Compute metrics for upload record
        metrics = {
            "region_count": len(parsed_regions),
            "annotated_count": annotated_count,
            "global_methylation_avg": global_avg,
            "feature_breakdown": _compute_feature_breakdown(region_annotations),
        }
        upload.metrics_json = json.dumps(metrics)
        upload.status = "complete"

        # ── Step 6: Finalize ───────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        _update_analysis(
            analysis,
            status="complete",
            insights_json=json.dumps(insights),
            ai_summary_text=summary,
            completed_at=now,
        )

        logger.info(
            "Epigenetics analysis %s complete: %d regions, %d annotated, %d genome overlays",
            analysis_id, len(parsed_regions), annotated_count, len(overlays),
        )
        return {
            "analysis_id": analysis_id,
            "status": "complete",
            "region_count": len(parsed_regions),
            "annotated_count": annotated_count,
            "genome_overlays": len(overlays),
        }

    except Exception as exc:
        logger.exception("Epigenetics analysis %s failed: %s", analysis_id, exc)
        _update_analysis(
            analysis,
            status="error",
            error_message=str(exc)[:2000],
            completed_at=datetime.now(timezone.utc),
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"error": str(exc), "analysis_id": analysis_id}


def _load_user_genome_variants(user_id: str) -> list[dict]:
    """Load user's genome variants for cross-referencing.

    Returns a simplified list of dicts with rsid, gene, genotype, risk_level.
    """
    variants: list[dict] = []

    # Find the user's most recent completed genome analysis
    latest_upload = (
        GenomeUpload.query
        .filter_by(user_id=user_id)
        .order_by(GenomeUpload.uploaded_at.desc())
        .first()
    )
    if not latest_upload or not latest_upload.analysis:
        return variants

    analysis = latest_upload.analysis
    if analysis.status != "complete":
        return variants

    # Load risk summary to determine per-category levels
    risk_levels: dict[str, str] = {}
    if analysis.risk_summary_json:
        try:
            risk_data = json.loads(analysis.risk_summary_json)
            for cat, info in risk_data.items():
                if isinstance(info, dict):
                    risk_levels[cat] = info.get("level", "unknown")
        except (json.JSONDecodeError, TypeError):
            pass

    # Load variants with annotations
    db_variants = (
        Variant.query
        .filter_by(analysis_id=analysis.id)
        .all()
    )

    for v in db_variants:
        if not v.rsid:
            continue

        gene = ""
        for ann in v.annotations:
            if ann.gene_symbol:
                gene = ann.gene_symbol
                break

        # Determine risk level from annotations
        risk = "unknown"
        for ann in v.annotations:
            if ann.clinical_significance:
                sig = ann.clinical_significance.lower()
                if "pathogenic" in sig:
                    risk = "high"
                elif "risk" in sig:
                    risk = "elevated"
                elif "benign" in sig:
                    risk = "low"
                break

        variants.append({
            "rsid": v.rsid,
            "gene": gene,
            "genotype": v.genotype,
            "risk_level": risk,
        })

    return variants


def _compute_feature_breakdown(annotations: dict[str, dict]) -> dict[str, int]:
    """Count regions by feature type."""
    breakdown: dict[str, int] = {}
    for ann in annotations.values():
        ft = ann.get("feature_type", "unknown")
        breakdown[ft] = breakdown.get(ft, 0) + 1
    return breakdown
