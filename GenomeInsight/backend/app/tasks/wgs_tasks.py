"""Celery tasks for WGS analysis and weekly report refresh.

Tasks:
 1. run_wgs_analysis    — Parse FASTQ/BAM, simulate variant calling, run ancestry inference.
 2. weekly_report_refresh — Query PubMed/NCBI for variant updates and refresh reports.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone

from celery import shared_task

from app.extensions import db

logger = logging.getLogger(__name__)


# ── WGS analysis pipeline ──────────────────────────────────────────────────


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_wgs_analysis(self, upload_id: str, ancestry_id: str):
    """Full WGS analysis pipeline.

    Steps:
     1. Decrypt and parse FASTQ/BAM for read statistics.
     2. Simulate variant calling (or invoke bcftools if available).
     3. Run ancestry inference (haplogroups, population composition).
     4. Query NCBI for haplogroup references.
     5. Save results to database.
    """
    from flask import current_app
    from app.models.wgs import AncestryAnalysis, WGSUpload
    from app.services.encryption import decrypt_dek, decrypt_file

    upload = db.session.get(WGSUpload, upload_id)
    ancestry = db.session.get(AncestryAnalysis, ancestry_id)

    if not upload or not ancestry:
        logger.error("WGS upload %s or ancestry %s not found", upload_id, ancestry_id)
        return {"error": "Records not found"}

    upload.status = "processing"
    ancestry.status = "running"
    ancestry.started_at = datetime.now(timezone.utc)
    db.session.commit()

    try:
        # Step 1: Decrypt file
        master_key = current_app.config["MASTER_ENCRYPTION_KEY"]
        user = upload.user
        dek = decrypt_dek(user.data_encryption_key_enc, master_key)
        plaintext = decrypt_file(upload.file_path_encrypted, dek)

        # Write temp file for parsing
        import tempfile
        import os
        suffix = ".fastq" if upload.file_format == "fastq" else ".bam"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(plaintext)
            tmp_path = tmp.name

        try:
            # Step 2: Parse reads
            from app.utils.wgs_analyzer import (
                parse_fastq_biopython,
                parse_bam,
                simulate_variant_calling,
                infer_ancestry,
                query_ncbi_haplogroup,
            )

            if upload.file_format == "bam":
                read_stats = parse_bam(tmp_path)
            else:
                read_stats = parse_fastq_biopython(tmp_path)

            # Update upload with read stats
            upload.depth = read_stats.estimated_depth
            upload.read_count = read_stats.total_reads
            upload.avg_read_length = read_stats.avg_read_length
            upload.avg_quality = read_stats.avg_quality

            # Step 3: Variant calling (simulated — use file hash as seed for reproducibility)
            seed = int(upload.file_hash_sha256[:8], 16)
            variants = simulate_variant_calling(read_stats, seed=seed)

            # Step 4: Ancestry inference
            ancestry_result = infer_ancestry(variants, seed=seed)

            # Step 5: Query NCBI for haplogroup references
            ncbi_api_key = current_app.config.get("NCBI_API_KEY", "")
            mt_ncbi = query_ncbi_haplogroup(
                ancestry_result.mt_haplogroup, "mt", ncbi_api_key
            )
            y_ncbi = query_ncbi_haplogroup(
                ancestry_result.y_haplogroup, "y", ncbi_api_key
            )

            # Build full report
            report = {
                "read_stats": asdict(read_stats),
                "variants_detected": len(variants),
                "variants": [asdict(v) for v in variants[:50]],  # Cap at 50 for JSON size
                "ancestry": {
                    "population_composition": ancestry_result.population_composition,
                    "archaic_ancestry_pct": ancestry_result.archaic_ancestry_pct,
                    "migration_paths": ancestry_result.migration_paths,
                    "historical_context": ancestry_result.historical_context,
                },
                "ncbi_references": {
                    "mt_haplogroup": mt_ncbi,
                    "y_haplogroup": y_ncbi,
                },
            }

            # Save to database
            ancestry.mt_haplogroup = ancestry_result.mt_haplogroup
            ancestry.y_haplogroup = ancestry_result.y_haplogroup
            ancestry.population_composition_json = json.dumps(
                ancestry_result.population_composition
            )
            ancestry.archaic_ancestry_pct = ancestry_result.archaic_ancestry_pct
            ancestry.report_json = json.dumps(report)
            ancestry.status = "complete"
            ancestry.completed_at = datetime.now(timezone.utc)

            upload.status = "analyzed"
            db.session.commit()

            logger.info(
                "WGS analysis complete: upload=%s, depth=%.2f, variants=%d, "
                "mt=%s, y=%s",
                upload_id, read_stats.estimated_depth, len(variants),
                ancestry_result.mt_haplogroup, ancestry_result.y_haplogroup,
            )

            return {
                "upload_id": upload_id,
                "ancestry_id": ancestry_id,
                "status": "complete",
                "depth": read_stats.estimated_depth,
                "variants": len(variants),
            }

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    except Exception as exc:
        logger.exception("WGS analysis failed for upload %s", upload_id)
        upload.status = "error"
        ancestry.status = "error"
        ancestry.error_message = str(exc)[:2000]
        db.session.commit()

        # Retry on transient failures
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        return {"error": str(exc)}


# ── Weekly report refresh ───────────────────────────────────────────────────


@shared_task(bind=True)
def weekly_report_refresh(self, user_id: str | None = None):
    """Refresh reports with new research from PubMed/NCBI.

    Queries NCBI for recent publications about variants found in user
    analyses and appends update summaries to existing reports.

    Args:
        user_id: If provided, only refresh for this user. Otherwise, refresh
                 for all users with completed analyses.
    """
    from flask import current_app
    from app.models.wgs import AncestryAnalysis, WGSUpload
    from app.models.genome import GenomeAnalysis, Variant
    from app.models.user import User

    ncbi_api_key = current_app.config.get("NCBI_API_KEY", "")

    if user_id:
        users = [db.session.get(User, user_id)]
        users = [u for u in users if u]
    else:
        users = User.query.all()

    total_updates = 0

    for user in users:
        try:
            updates = _refresh_user_reports(user, ncbi_api_key)
            total_updates += updates
        except Exception:
            logger.exception("Weekly refresh failed for user %s", user.id)

    logger.info("Weekly report refresh complete: %d updates across %d users",
                total_updates, len(users))

    return {"users_processed": len(users), "total_updates": total_updates}


def _refresh_user_reports(user, ncbi_api_key: str) -> int:
    """Refresh all reports for a single user. Returns count of updates."""
    from app.models.wgs import AncestryAnalysis
    from app.models.genome import GenomeAnalysis, Variant
    from app.utils.wgs_analyzer import query_ncbi_variant_updates

    updates = 0

    # Collect RSIDs from genome analyses
    rsids = set()
    analyses = (
        GenomeAnalysis.query.join(
            __import__("app.models.genome", fromlist=["GenomeUpload"]).GenomeUpload
        )
        .filter(
            __import__("app.models.genome", fromlist=["GenomeUpload"]).GenomeUpload.user_id == user.id,
            GenomeAnalysis.status == "complete",
        )
        .all()
    )

    for analysis in analyses:
        variants = Variant.query.filter_by(analysis_id=analysis.id).all()
        for v in variants:
            if v.rsid:
                rsids.add(v.rsid)

    # Also collect RSIDs from WGS ancestry analyses
    ancestry_analyses = AncestryAnalysis.query.filter_by(
        user_id=user.id, status="complete"
    ).all()

    for ancestry in ancestry_analyses:
        if ancestry.report_json:
            try:
                report = json.loads(ancestry.report_json)
                for v in report.get("variants", []):
                    if v.get("rsid"):
                        rsids.add(v["rsid"])
            except (json.JSONDecodeError, TypeError):
                pass

    if not rsids:
        return 0

    # Query NCBI for recent publications (batch in groups of 20)
    rsid_list = list(rsids)[:100]  # Cap to avoid excessive API calls
    variant_updates = query_ncbi_variant_updates(
        rsid_list, ncbi_api_key=ncbi_api_key
    )

    if not variant_updates:
        return 0

    # Append updates to ancestry reports
    update_summary = {
        "refresh_date": datetime.now(timezone.utc).isoformat(),
        "variant_updates": variant_updates,
        "total_new_publications": sum(u["count"] for u in variant_updates),
    }

    for ancestry in ancestry_analyses:
        if ancestry.report_json:
            try:
                report = json.loads(ancestry.report_json)
                if "weekly_updates" not in report:
                    report["weekly_updates"] = []
                report["weekly_updates"].append(update_summary)
                # Keep only last 12 weekly updates
                report["weekly_updates"] = report["weekly_updates"][-12:]
                ancestry.report_json = json.dumps(report)
                updates += 1
            except (json.JSONDecodeError, TypeError):
                pass

    # Also update genome analysis reports
    for analysis in analyses:
        if analysis.risk_summary_json:
            try:
                risk_data = json.loads(analysis.risk_summary_json)
                if "weekly_updates" not in risk_data:
                    risk_data["weekly_updates"] = []
                risk_data["weekly_updates"].append(update_summary)
                risk_data["weekly_updates"] = risk_data["weekly_updates"][-12:]
                analysis.risk_summary_json = json.dumps(risk_data)
                updates += 1
            except (json.JSONDecodeError, TypeError):
                pass

    if updates:
        db.session.commit()

    return updates


# ── Ancestry re-analysis ───────────────────────────────────────────────────


@shared_task(bind=True)
def schedule_ancestry_reanalysis(self, user_id: str | None = None):
    """Re-analyze ancestry data with updated reference populations.

    Called by the weekly beat schedule to check if any ancestry analyses
    should be refreshed (e.g., when new reference population data becomes
    available from NCBI).
    """
    from app.models.wgs import AncestryAnalysis

    if user_id:
        analyses = AncestryAnalysis.query.filter_by(
            user_id=user_id, status="complete"
        ).all()
    else:
        analyses = AncestryAnalysis.query.filter_by(status="complete").all()

    requeued = 0
    for analysis in analyses:
        if analysis.wgs_upload_id:
            try:
                run_wgs_analysis.delay(analysis.wgs_upload_id, analysis.id)
                requeued += 1
            except Exception:
                logger.debug("Could not requeue ancestry %s", analysis.id)

    logger.info("Scheduled %d ancestry re-analyses", requeued)
    return {"requeued": requeued}
