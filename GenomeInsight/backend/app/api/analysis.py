"""Unified cross-domain analysis endpoint.

Provides a single endpoint that aggregates genome, epigenetics, microbiome,
wearable, and blood data into a structured JSON response with domain
summaries, multi-domain correlations, and an AI narrative.
"""

import json
from datetime import date, timedelta

from flask import Blueprint, g, jsonify, request

from app.extensions import db, limiter
from app.models.audit import AuditLog
from app.api.decorators import login_required

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api/v1/analysis")


def _audit(action: str, **kwargs):
    log = AuditLog(
        user_id=g.current_user.id,
        action=action,
        ip_address=request.remote_addr,
        **kwargs,
    )
    db.session.add(log)


# ── Data loaders ─────────────────────────────────────────────────────────────

def _load_genome_variants(user_id: str) -> list[dict]:
    from app.models.genome import GenomeUpload, Variant

    latest = (
        GenomeUpload.query
        .filter_by(user_id=user_id)
        .order_by(GenomeUpload.uploaded_at.desc())
        .first()
    )
    if not latest or not latest.analysis or latest.analysis.status != "complete":
        return []

    variants = []
    for v in (
        Variant.query
        .filter_by(analysis_id=latest.analysis.id)
        .filter(Variant.rsid.isnot(None))
        .all()
    ):
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


def _load_blood_markers(user_id: str) -> list[dict]:
    from app.models.blood import BloodUpload

    latest = (
        BloodUpload.query
        .filter_by(user_id=user_id)
        .order_by(BloodUpload.test_date.desc())
        .first()
    )
    if not latest:
        return []
    return [
        {
            "marker_name": r.marker_name,
            "marker_display_name": r.marker_display_name,
            "value": r.value,
            "unit": r.unit,
            "flag": r.flag,
        }
        for r in latest.results
    ]


def _load_wearable_summaries(user_id: str, days: int = 7) -> list[dict]:
    from app.models.wearable import DailyWearableData

    records = (
        DailyWearableData.query
        .filter_by(user_id=user_id)
        .filter(DailyWearableData.date >= date.today() - timedelta(days=days))
        .order_by(DailyWearableData.date.desc())
        .all()
    )
    summaries = []
    for wd in records:
        summary = {}
        if wd.summary_json:
            try:
                summary = json.loads(wd.summary_json)
            except (json.JSONDecodeError, TypeError):
                pass
        summaries.append({
            "data_type": wd.data_type,
            "date": wd.date.isoformat(),
            "summary": summary,
        })
    return summaries


def _load_microbiome_profile(user_id: str) -> dict | None:
    from app.models.microbiome import MicrobiomeUpload

    latest = (
        MicrobiomeUpload.query
        .filter_by(user_id=user_id)
        .order_by(MicrobiomeUpload.uploaded_at.desc())
        .first()
    )
    if not latest or not latest.analysis or latest.analysis.status != "complete":
        return None

    analysis = latest.analysis
    profile: dict = {"enterotype": analysis.enterotype}

    for field_name, json_field in [
        ("diversity", "diversity_json"),
        ("composition", "composition_json"),
        ("insights", "health_insights_json"),
    ]:
        raw = getattr(analysis, json_field, None)
        if raw:
            try:
                profile[field_name] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass

    return profile


def _load_epigenetic_overlays(user_id: str) -> list[dict]:
    from app.models.epigenetics import EpigeneticUpload

    latest = (
        EpigeneticUpload.query
        .filter_by(user_id=user_id)
        .order_by(EpigeneticUpload.uploaded_at.desc())
        .first()
    )
    if not latest or not latest.analysis:
        return []
    analysis = latest.analysis
    if analysis.status != "complete" or not analysis.genome_overlay_json:
        return []
    try:
        return json.loads(analysis.genome_overlay_json)
    except (json.JSONDecodeError, TypeError):
        return []


def _load_daily_insights(user_id: str) -> list[dict]:
    """Load today's persisted DailyInsight records."""
    from app.models.wearable import DailyInsight

    today = date.today()
    records = (
        DailyInsight.query
        .filter_by(user_id=user_id, date=today)
        .order_by(DailyInsight.generated_at.desc())
        .all()
    )
    result = []
    for i in records:
        sources = []
        if i.data_sources_json:
            try:
                sources = json.loads(i.data_sources_json)
            except (json.JSONDecodeError, TypeError):
                pass
        result.append({
            "title": i.title,
            "body": i.body,
            "category": i.insight_type,
            "confidence": i.confidence,
            "data_sources": sources,
            "generated_at": i.generated_at.isoformat(),
        })
    return result


# ── Daily analysis endpoint ──────────────────────────────────────────────────


@analysis_bp.route("/daily", methods=["GET"])
@login_required
def daily_analysis():
    """Return a unified daily analysis spanning all data domains.

    Response structure:
        {
            "analysis_date": "2026-02-28",
            "domains": { genome, epigenetics, microbiome, wearable, blood },
            "correlations": [...ranked multi-domain insights...],
            "daily_insights": [...today's persisted insights...],
            "ai_narrative": "...",
            "disclaimer": "..."
        }
    """
    from app.utils.correlator import run_full_unified_analysis

    user_id = g.current_user.id

    # Load all domain data
    user_variants = _load_genome_variants(user_id)
    blood_markers = _load_blood_markers(user_id)
    wearable_summaries = _load_wearable_summaries(user_id)
    microbiome_profile = _load_microbiome_profile(user_id)
    epigenetic_overlays = _load_epigenetic_overlays(user_id)
    daily_insights = _load_daily_insights(user_id)

    # Run unified analysis
    result = run_full_unified_analysis(
        user_id=user_id,
        user_variants=user_variants,
        blood_markers=blood_markers,
        wearable_summaries=wearable_summaries,
        microbiome_profile=microbiome_profile,
        epigenetic_overlays=epigenetic_overlays,
        existing_insights=daily_insights,
    )

    # Convert to JSON structure grouped by domain
    domains_dict = {}
    for d in result.domains:
        domains_dict[d.domain] = {
            "status": d.status,
            "last_updated": d.last_updated,
            "highlights": d.highlights,
            "metrics": d.metrics,
        }

    return jsonify({
        "analysis_date": result.analysis_date,
        "domains": domains_dict,
        "correlations": [c.to_dict() for c in result.correlations],
        "daily_insights": daily_insights,
        "ai_narrative": result.ai_narrative,
        "disclaimer": result.disclaimer,
    })


# ── Force unified analysis regeneration ──────────────────────────────────────


@analysis_bp.route("/daily/generate", methods=["POST"])
@limiter.limit("5 per hour")
@login_required
def trigger_unified_analysis():
    """Force re-generation of daily insights with unified correlator.

    This dispatches the daily insight task (which now includes the
    unified correlator) and returns immediately.
    """
    celery_task_id = None
    try:
        from app.tasks.wearable_tasks import generate_daily_insights
        task = generate_daily_insights.delay(g.current_user.id)
        celery_task_id = task.id
    except Exception:
        pass

    _audit("trigger_unified_analysis", resource_type="DailyInsight")
    db.session.commit()

    return jsonify({
        "status": "queued",
        "task_id": celery_task_id,
        "message": "Unified daily analysis queued. Use GET /api/v1/analysis/daily to retrieve results.",
    })
