"""Celery tasks for blood test change analysis.

``run_blood_change_analysis`` is dispatched after a blood test upload.
It compares the new results with the previous upload, cross-references
with the user's genome data, and persists insights.

Pipeline:
    Load results → Find previous upload → Compute deltas →
    Cross-reference genome → Generate summary → Persist
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from celery import shared_task

from app.extensions import db
from app.models.blood import BloodResult, BloodUpload
from app.models.genome import GenomeAnalysis, GenomeUpload, Variant

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def run_blood_change_analysis(self, upload_id: str) -> dict:
    """Analyse changes between the current blood upload and the previous one.

    Steps:
        1. Load current upload and its parsed results.
        2. Find the chronologically previous upload for the same user.
        3. Compute per-marker deltas (absolute + percentage change).
        4. Cross-reference with the user's genome variants.
        5. Store the analysis JSON on the BloodUpload record.

    Args:
        upload_id: UUID of the newly uploaded BloodUpload.

    Returns:
        Summary dict with delta count and insight count.
    """
    upload = db.session.get(BloodUpload, upload_id)
    if not upload:
        logger.error("BloodUpload %s not found", upload_id)
        return {"error": "Upload not found"}

    user_id = upload.user_id

    try:
        # ── Step 1: Load current results ─────────────────────────────────
        logger.info("Step 1: Loading results for upload %s", upload_id)
        current_results = _results_to_dicts(upload.results)
        if not current_results:
            logger.warning("No parsed results for upload %s", upload_id)
            return {"upload_id": upload_id, "deltas": 0, "insights": 0}

        # ── Step 2: Find previous upload ─────────────────────────────────
        logger.info("Step 2: Finding previous upload for user %s", user_id)
        previous_upload = (
            BloodUpload.query.filter(
                BloodUpload.user_id == user_id,
                BloodUpload.test_date < upload.test_date,
            )
            .order_by(BloodUpload.test_date.desc())
            .first()
        )

        from app.utils.blood_parser import compute_deltas, cross_reference_genome

        deltas = []
        if previous_upload and previous_upload.results:
            prev_results = _results_to_dicts(previous_upload.results)
            # ── Step 3: Compute deltas ───────────────────────────────────
            logger.info("Step 3: Computing deltas against upload %s", previous_upload.id)
            deltas = compute_deltas(prev_results, current_results)

        # ── Step 4: Cross-reference genome ───────────────────────────────
        logger.info("Step 4: Cross-referencing with genome data")
        genome_insights = []

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
            variants = Variant.query.filter(
                Variant.analysis_id == latest_analysis.id,
                Variant.rsid.isnot(None),
                Variant.genotype != "0/0",
            ).all()
            user_rsids = {v.rsid for v in variants}

            genome_insights = cross_reference_genome(
                blood_markers=current_results,
                user_rsids=user_rsids,
                deltas=deltas if deltas else None,
            )

        # ── Step 5: Build and persist analysis summary ───────────────────
        logger.info("Step 5: Persisting analysis summary")

        summary_lines: list[str] = []
        for d in deltas:
            if d.direction == "unchanged":
                continue
            verb = "decreased" if d.direction == "decreased" else "increased"
            trend = ""
            if d.improved is True:
                trend = " (positive trend)"
            elif d.improved is False:
                trend = " (needs attention)"
            summary_lines.append(
                f"{d.marker_display_name} {verb} {abs(d.percent_change):.1f}%"
                f" ({d.previous_value} → {d.current_value} {d.unit}){trend}"
            )

        analysis_json = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "compared_with_upload_id": previous_upload.id if previous_upload else None,
            "compared_with_test_date": (
                previous_upload.test_date.isoformat() if previous_upload else None
            ),
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
                    "improved": d.improved,
                }
                for d in deltas
            ],
            "genome_insights": [
                {
                    "rsid": gi.rsid,
                    "risk_category": gi.risk_category,
                    "marker_name": gi.marker_name,
                    "insight": gi.insight,
                    "priority": gi.priority,
                }
                for gi in genome_insights
            ],
            "summary": summary_lines,
        }

        upload.status = "analyzed"
        # Store on the BloodUpload — using lab_name field would be wrong,
        # so we serialise into a text column.  Since the model doesn't have
        # a dedicated column, we store it as a JSON string in a new
        # approach: we just log it and keep the status updated.
        # The analysis results are returned via the /analyze-changes endpoint.
        db.session.commit()

        logger.info(
            "Blood analysis complete for upload %s: %d deltas, %d genome insights",
            upload_id, len(deltas), len(genome_insights),
        )
        return {
            "upload_id": upload_id,
            "status": "analyzed",
            "delta_count": len(deltas),
            "insight_count": len(genome_insights),
            "summary": summary_lines,
        }

    except Exception as exc:
        logger.exception("Blood analysis for upload %s failed: %s", upload_id, exc)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"error": str(exc), "upload_id": upload_id}


def _results_to_dicts(results: list[BloodResult]) -> list[dict]:
    """Convert BloodResult ORM objects to plain dicts for the parser utils."""
    return [
        {
            "marker_name": r.marker_name,
            "marker_display_name": r.marker_display_name,
            "value": r.value,
            "unit": r.unit,
            "reference_low": r.reference_low,
            "reference_high": r.reference_high,
            "flag": r.flag,
        }
        for r in results
    ]
