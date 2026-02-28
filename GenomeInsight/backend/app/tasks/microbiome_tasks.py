"""Celery tasks for microbiome analysis.

The main task, ``run_microbiome_analysis``, is dispatched after a
microbiome file upload and orchestrates the pipeline:

    Decrypt file -> Parse BIOM/CSV/FASTQ -> Compute diversity ->
    Classify enterotype -> Generate insights -> Cross-domain correlations ->
    AI summary -> Persist

A weekly re-analysis task re-runs cross-domain correlations when
new data (genome, blood, wearable) becomes available.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task

from app.extensions import db
from app.models.microbiome import (
    MicrobiomeAnalysis,
    MicrobiomeTaxon,
    MicrobiomeUpload,
)
from app.services.encryption import decrypt_dek, decrypt_file
from app.utils.microbiome_analyzer import (
    classify_enterotype,
    compute_alpha_diversity,
    compute_composition,
    compute_phyla_ratios,
    correlate_microbiome_blood,
    correlate_microbiome_genome,
    correlate_microbiome_wearables,
    generate_microbiome_ai_summary,
    generate_microbiome_insights,
    parse_biom_json,
    parse_fastq_metadata,
    parse_otu_csv,
)

logger = logging.getLogger(__name__)


def _update_analysis(analysis: MicrobiomeAnalysis, **kwargs) -> None:
    """Update analysis fields and commit."""
    for key, value in kwargs.items():
        setattr(analysis, key, value)
    db.session.commit()


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_microbiome_analysis(self, analysis_id: str) -> dict:
    """Run the full microbiome analysis pipeline.

    Args:
        analysis_id: UUID of the MicrobiomeAnalysis record.

    Returns:
        Summary dict with counts and status.
    """
    from flask import current_app

    analysis = db.session.get(MicrobiomeAnalysis, analysis_id)
    if not analysis:
        logger.error("MicrobiomeAnalysis %s not found", analysis_id)
        return {"error": "Analysis not found"}

    upload = analysis.upload
    if not upload:
        _update_analysis(analysis, status="error", error_message="Upload record missing")
        return {"error": "Upload record missing"}

    _update_analysis(analysis, status="running", started_at=datetime.now(timezone.utc))

    try:
        # -- Step 1: Decrypt and parse file ------------------------------------
        logger.info("Step 1: Decrypting and parsing microbiome file for analysis %s", analysis_id)

        master_key = current_app.config["MASTER_ENCRYPTION_KEY"]
        user = upload.user
        dek = decrypt_dek(user.data_encryption_key_enc, master_key)

        encrypted_path = Path(upload.file_path_encrypted)
        file_bytes = decrypt_file(encrypted_path, dek)

        taxa = []
        fastq_metadata = None

        if upload.file_type == "biom":
            taxa = parse_biom_json(file_bytes)
        elif upload.file_type in ("csv", "tsv"):
            taxa = parse_otu_csv(file_bytes)
        elif upload.file_type == "fastq":
            fastq_metadata = parse_fastq_metadata(file_bytes)
            # FASTQ files don't produce taxa directly; store metadata
            upload.metrics_json = json.dumps(fastq_metadata)
            upload.status = "complete"
            _update_analysis(
                analysis,
                status="complete",
                total_read_count=fastq_metadata.get("read_count", 0),
                ai_summary_text=fastq_metadata.get("note", ""),
                completed_at=datetime.now(timezone.utc),
            )
            return {
                "analysis_id": analysis_id,
                "status": "complete",
                "type": "fastq_metadata",
                "read_count": fastq_metadata.get("read_count", 0),
            }
        else:
            _update_analysis(
                analysis,
                status="error",
                error_message=f"Unknown file_type: {upload.file_type}",
            )
            return {"error": f"Unknown file_type: {upload.file_type}"}

        if not taxa:
            _update_analysis(
                analysis,
                status="error",
                error_message="No taxa found in file. Check file format.",
            )
            return {"error": "No taxa parsed"}

        total_reads = sum(t.absolute_count for t in taxa)
        analysis.total_read_count = total_reads
        analysis.classified_read_count = len(taxa)
        db.session.commit()

        # -- Step 2: Persist taxa ----------------------------------------------
        logger.info("Step 2: Storing %d taxa", len(taxa))

        # Clear previous taxa if re-running
        MicrobiomeTaxon.query.filter_by(upload_id=upload.id).delete()

        for taxon in taxa:
            db.session.add(MicrobiomeTaxon(
                upload_id=upload.id,
                taxonomy_level=taxon.taxonomy_level,
                taxonomy_name=taxon.taxonomy_name,
                taxonomy_id=taxon.taxonomy_id or None,
                relative_abundance=taxon.relative_abundance,
                absolute_count=taxon.absolute_count,
                confidence=taxon.confidence,
                parent_taxon=taxon.parent_taxon or None,
            ))
        db.session.commit()

        # -- Step 3: Compute diversity metrics ---------------------------------
        logger.info("Step 3: Computing diversity metrics")

        diversity = compute_alpha_diversity(taxa)
        analysis.diversity_json = json.dumps(diversity)
        db.session.commit()

        # -- Step 4: Composition and phyla ratios ------------------------------
        logger.info("Step 4: Computing composition and phyla ratios")

        composition = {
            "phylum": compute_composition(taxa, "phylum"),
            "genus": compute_composition(taxa, "genus"),
            "family": compute_composition(taxa, "family"),
        }
        analysis.composition_json = json.dumps(composition)

        phyla_ratios = compute_phyla_ratios(taxa)
        enterotype = classify_enterotype(taxa)
        analysis.enterotype = enterotype
        db.session.commit()

        # Track level counts
        level_counts: dict[str, int] = {}
        for t in taxa:
            level_counts[t.taxonomy_level] = level_counts.get(t.taxonomy_level, 0) + 1
        analysis.taxonomy_level_counts_json = json.dumps(level_counts)
        db.session.commit()

        # -- Step 5: Generate health insights ----------------------------------
        logger.info("Step 5: Generating health insights")

        insights = generate_microbiome_insights(
            diversity=diversity,
            phyla_ratios=phyla_ratios,
            enterotype=enterotype,
            taxa=taxa,
        )
        analysis.health_insights_json = json.dumps([asdict(i) for i in insights])
        db.session.commit()

        # -- Step 6: Cross-domain correlations ---------------------------------
        logger.info("Step 6: Computing cross-domain correlations")

        user_variants = _load_user_genome_variants(user.id)
        genome_correlations = correlate_microbiome_genome(
            taxa=taxa,
            phyla_ratios=phyla_ratios,
            user_variants=user_variants,
        )
        analysis.genome_correlation_json = json.dumps(
            [asdict(c) for c in genome_correlations]
        )

        blood_markers = _load_user_blood_markers(user.id)
        blood_correlations = correlate_microbiome_blood(
            taxa=taxa,
            diversity=diversity,
            phyla_ratios=phyla_ratios,
            blood_markers=blood_markers,
        )
        analysis.blood_correlation_json = json.dumps(
            [asdict(c) for c in blood_correlations]
        )

        wearable_summaries = _load_user_wearable_summaries(user.id)
        wearable_correlations = correlate_microbiome_wearables(
            diversity=diversity,
            phyla_ratios=phyla_ratios,
            wearable_summaries=wearable_summaries,
        )
        analysis.lifestyle_recs_json = json.dumps(
            [asdict(c) for c in wearable_correlations]
        )
        db.session.commit()

        # -- Step 7: Generate AI summary ---------------------------------------
        logger.info("Step 7: Generating AI summary")

        openai_key = current_app.config.get("OPENAI_API_KEY", "")
        summary = generate_microbiome_ai_summary(
            diversity=diversity,
            phyla_ratios=phyla_ratios,
            enterotype=enterotype,
            insights=insights,
            genome_correlations=genome_correlations,
            data_type=upload.data_type,
            openai_api_key=openai_key,
        )

        # Compute metrics for upload record
        metrics = {
            "taxa_count": len(taxa),
            "diversity": diversity,
            "phyla_ratios": phyla_ratios,
            "enterotype": enterotype,
            "insights_count": len(insights),
            "genome_correlations_count": len(genome_correlations),
            "blood_correlations_count": len(blood_correlations),
            "wearable_correlations_count": len(wearable_correlations),
        }
        upload.metrics_json = json.dumps(metrics)
        upload.status = "complete"

        # -- Step 8: Finalize --------------------------------------------------
        now = datetime.now(timezone.utc)
        _update_analysis(
            analysis,
            status="complete",
            ai_summary_text=summary,
            completed_at=now,
        )

        logger.info(
            "Microbiome analysis %s complete: %d taxa, diversity Shannon=%.2f, "
            "%d insights, %d genome correlations",
            analysis_id, len(taxa), diversity.get("shannon", 0),
            len(insights), len(genome_correlations),
        )
        return {
            "analysis_id": analysis_id,
            "status": "complete",
            "taxa_count": len(taxa),
            "diversity": diversity,
            "enterotype": enterotype,
            "insights_count": len(insights),
            "genome_correlations": len(genome_correlations),
        }

    except Exception as exc:
        logger.exception("Microbiome analysis %s failed: %s", analysis_id, exc)
        _update_analysis(
            analysis,
            status="error",
            error_message=str(exc)[:2000],
            completed_at=datetime.now(timezone.utc),
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"error": str(exc), "analysis_id": analysis_id}


@shared_task(bind=True, max_retries=0)
def schedule_weekly_reanalysis(self) -> dict:
    """Re-run cross-domain correlations for all users with microbiome data.

    Scheduled by Celery Beat weekly. This picks up new genome, blood,
    or wearable data that arrived since the last analysis.
    """
    uploads = (
        MicrobiomeUpload.query
        .filter_by(status="complete")
        .all()
    )

    dispatched = 0
    for upload in uploads:
        if upload.analysis and upload.analysis.status == "complete":
            try:
                run_microbiome_analysis.delay(upload.analysis.id)
                dispatched += 1
            except Exception:
                logger.exception(
                    "Failed to dispatch re-analysis for upload %s", upload.id
                )

    logger.info("Dispatched weekly re-analysis for %d microbiome uploads", dispatched)
    return {"dispatched": dispatched, "total_complete": len(uploads)}


@shared_task(bind=True, max_retries=0)
def check_and_reanalyze_stale(self) -> dict:
    """Re-analyze microbiome uploads whose cross-domain data has changed.

    Scheduled by Celery Beat daily. Checks whether new genome, blood,
    or wearable data has arrived since the last microbiome analysis
    completed, and re-triggers if so.

    This ensures cross-domain correlations stay fresh when users upload
    new blood tests, connect a wearable, or add genome data after their
    microbiome sample was already processed.
    """
    from app.models.blood import BloodUpload
    from app.models.genome import GenomeUpload
    from app.models.wearable import DailyWearableData

    uploads = (
        MicrobiomeUpload.query
        .filter_by(status="complete")
        .all()
    )

    dispatched = 0
    skipped = 0

    for upload in uploads:
        analysis = upload.analysis
        if not analysis or analysis.status != "complete" or not analysis.completed_at:
            continue

        completed = analysis.completed_at
        user_id = upload.user_id

        # Check if any cross-domain data is newer than the last analysis
        has_newer_genome = (
            GenomeUpload.query
            .filter_by(user_id=user_id)
            .filter(GenomeUpload.uploaded_at > completed)
            .first()
        ) is not None

        has_newer_blood = (
            BloodUpload.query
            .filter_by(user_id=user_id)
            .filter(BloodUpload.uploaded_at > completed)
            .first()
        ) is not None

        has_newer_wearable = (
            DailyWearableData.query
            .filter_by(user_id=user_id)
            .filter(DailyWearableData.fetched_at > completed)
            .first()
        ) is not None

        if has_newer_genome or has_newer_blood or has_newer_wearable:
            try:
                run_microbiome_analysis.delay(analysis.id)
                dispatched += 1
                logger.info(
                    "Re-analyzing microbiome %s: new data (genome=%s, blood=%s, wearable=%s)",
                    analysis.id, has_newer_genome, has_newer_blood, has_newer_wearable,
                )
            except Exception:
                logger.exception(
                    "Failed to dispatch re-analysis for upload %s", upload.id
                )
        else:
            skipped += 1

    logger.info(
        "Stale-check complete: dispatched=%d, skipped=%d, total=%d",
        dispatched, skipped, len(uploads),
    )
    return {"dispatched": dispatched, "skipped": skipped, "total": len(uploads)}


# -- Data helpers --------------------------------------------------------------


def _load_user_genome_variants(user_id: str) -> list[dict]:
    """Load user's genome variants for cross-referencing."""
    from app.models.genome import GenomeUpload, Variant

    variants: list[dict] = []
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

    db_variants = (
        Variant.query
        .filter_by(analysis_id=analysis.id)
        .filter(Variant.rsid.isnot(None))
        .all()
    )
    for v in db_variants:
        gene = ""
        risk = "unknown"
        for ann in v.annotations:
            if ann.gene_symbol:
                gene = ann.gene_symbol
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


def _load_user_blood_markers(user_id: str) -> list[dict]:
    """Load user's latest blood test markers."""
    from app.models.blood import BloodUpload

    latest_upload = (
        BloodUpload.query
        .filter_by(user_id=user_id)
        .order_by(BloodUpload.test_date.desc())
        .first()
    )
    if not latest_upload:
        return []

    return [
        {
            "marker_name": r.marker_name,
            "marker_display_name": r.marker_display_name,
            "value": r.value,
            "unit": r.unit,
            "flag": r.flag,
        }
        for r in latest_upload.results
    ]


def _load_user_wearable_summaries(user_id: str) -> list[dict]:
    """Load user's recent wearable data summaries."""
    import json as json_mod
    from datetime import date, timedelta

    from app.models.wearable import DailyWearableData

    recent_data = (
        DailyWearableData.query
        .filter_by(user_id=user_id)
        .filter(DailyWearableData.date >= date.today() - timedelta(days=7))
        .order_by(DailyWearableData.date.desc())
        .all()
    )

    summaries: list[dict] = []
    for wd in recent_data:
        summary = {}
        if wd.summary_json:
            try:
                summary = json_mod.loads(wd.summary_json)
            except (json_mod.JSONDecodeError, TypeError):
                pass
        summaries.append({
            "data_type": wd.data_type,
            "date": wd.date.isoformat(),
            "summary": summary,
        })

    return summaries
