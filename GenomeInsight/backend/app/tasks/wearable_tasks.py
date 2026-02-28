"""Celery tasks for wearable data sync and daily insight generation.

Two main tasks:

1. ``sync_wearable_connection`` — Pull latest data from Terra for a
   single WearableConnection and persist as DailyWearableData.

2. ``sync_all_active_connections`` — Scheduled by Celery Beat every 6
   hours. Iterates all active connections and dispatches individual
   sync tasks.

3. ``generate_daily_insights`` — Scheduled by Celery Beat daily.
   Correlates wearable data with genome, blood, and epigenetics for
   each user with active wearable connections.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from celery import shared_task

from app.extensions import db
from app.models.wearable import (
    DailyInsight,
    DailyWearableData,
    WearableConnection,
)
from app.utils.wearable_client import (
    WEARABLE_DATA_TYPES,
    decrypt_token,
    extract_summary,
    generate_cross_domain_insights,
    generate_daily_report,
    pull_terra_data,
)

logger = logging.getLogger(__name__)


# ── Single connection sync ──────────────────────────────────────────────────


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def sync_wearable_connection(self, connection_id: str) -> dict:
    """Sync data for a single wearable connection.

    Pulls activity, sleep, heart_rate, hrv, spo2, and stress data
    for the date range since last sync (or last 7 days on first sync).

    Args:
        connection_id: UUID of the WearableConnection.

    Returns:
        Summary dict with counts and status.
    """
    from flask import current_app

    connection = db.session.get(WearableConnection, connection_id)
    if not connection:
        logger.error("WearableConnection %s not found", connection_id)
        return {"error": "Connection not found"}

    if connection.status != "active":
        logger.info("Skipping inactive connection %s (status=%s)",
                     connection_id, connection.status)
        return {"status": "skipped", "reason": f"Connection is {connection.status}"}

    try:
        terra_api_key = current_app.config.get("TERRA_API_KEY", "")
        terra_dev_id = current_app.config.get("TERRA_DEV_ID", "")

        if not terra_api_key:
            logger.info("No TERRA_API_KEY configured; skipping real data pull")
            connection.last_sync_at = datetime.now(timezone.utc)
            db.session.commit()
            return {"status": "skipped", "reason": "No Terra API key configured"}

        # Determine date range
        if connection.last_sync_at:
            start_date = connection.last_sync_at.date()
        else:
            start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        # Decrypt Terra user ID
        master_key = current_app.config["MASTER_ENCRYPTION_KEY"]
        from app.services.encryption import decrypt_dek
        user = connection.user
        dek = decrypt_dek(user.data_encryption_key_enc, master_key)

        terra_user_id = connection.terra_user_id

        import httpx
        total_records = 0

        with httpx.Client(
            timeout=httpx.Timeout(connect=10, read=30, write=10, pool=10)
        ) as client:
            for data_type in WEARABLE_DATA_TYPES:
                day_summaries = pull_terra_data(
                    terra_user_id=terra_user_id,
                    data_type=data_type,
                    start_date=start_date,
                    end_date=end_date,
                    terra_api_key=terra_api_key,
                    terra_dev_id=terra_dev_id,
                    client=client,
                )

                for ds in day_summaries:
                    _upsert_daily_data(
                        user_id=connection.user_id,
                        connection_id=connection.id,
                        data_date=ds.date,
                        data_type=ds.data_type,
                        raw_data=ds.raw_data,
                        summary=ds.summary,
                    )
                    total_records += 1

        connection.last_sync_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(
            "Synced connection %s: %d records across %d data types",
            connection_id, total_records, len(WEARABLE_DATA_TYPES),
        )
        return {
            "connection_id": connection_id,
            "status": "synced",
            "records": total_records,
        }

    except Exception as exc:
        logger.exception("Sync failed for connection %s: %s", connection_id, exc)
        connection.status = "error"
        db.session.commit()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"error": str(exc), "connection_id": connection_id}


# ── Sync all active connections (Celery Beat) ───────────────────────────────


@shared_task(bind=True, max_retries=0)
def sync_all_active_connections(self) -> dict:
    """Iterate all active wearable connections and dispatch sync tasks.

    Designed to be called by Celery Beat every 6 hours.
    """
    connections = (
        WearableConnection.query
        .filter_by(status="active")
        .all()
    )

    dispatched = 0
    for conn in connections:
        try:
            sync_wearable_connection.delay(conn.id)
            dispatched += 1
        except Exception:
            logger.exception("Failed to dispatch sync for connection %s", conn.id)

    logger.info("Dispatched sync for %d active connections", dispatched)
    return {"dispatched": dispatched, "total_active": len(connections)}


# ── Daily insight generation (Celery Beat) ──────────────────────────────────


@shared_task(bind=True, max_retries=1, default_retry_delay=120)
def generate_daily_insights(self, user_id: str | None = None) -> dict:
    """Generate cross-domain daily insights for users.

    When user_id is provided, generates for that user only.
    When None (Celery Beat), generates for all users with active connections.

    Args:
        user_id: Optional specific user to generate insights for.

    Returns:
        Summary dict with insight counts.
    """
    from flask import current_app

    if user_id:
        user_ids = [user_id]
    else:
        # Find all users with active wearable connections
        rows = (
            db.session.query(WearableConnection.user_id)
            .filter_by(status="active")
            .distinct()
            .all()
        )
        user_ids = [r[0] for r in rows]

    total_insights = 0
    for uid in user_ids:
        try:
            count = _generate_insights_for_user(uid)
            total_insights += count
        except Exception:
            logger.exception("Failed to generate insights for user %s", uid)

    logger.info("Generated %d insights for %d users", total_insights, len(user_ids))
    return {"users_processed": len(user_ids), "insights_generated": total_insights}


def _generate_insights_for_user(user_id: str) -> int:
    """Generate daily insights for a single user.

    Returns the number of insights created.
    """
    today = date.today()

    # Load recent wearable summaries (last 7 days for trends)
    recent_data = (
        DailyWearableData.query
        .filter_by(user_id=user_id)
        .filter(DailyWearableData.date >= today - timedelta(days=7))
        .order_by(DailyWearableData.date.desc())
        .all()
    )

    if not recent_data:
        return 0

    # Build wearable summaries list for today (or most recent day)
    wearable_summaries: list[dict] = []
    for wd in recent_data:
        summary = {}
        if wd.summary_json:
            try:
                summary = json.loads(wd.summary_json)
            except (json.JSONDecodeError, TypeError):
                pass

        wearable_summaries.append({
            "data_type": wd.data_type,
            "date": wd.date.isoformat(),
            "summary": summary,
        })

    # Load user's genome variants
    user_variants = _load_user_genome_variants(user_id)

    # Load user's latest blood markers
    blood_markers = _load_user_blood_markers(user_id)

    # Load epigenetic overlays
    epigenetic_overlays = _load_user_epigenetic_overlays(user_id)

    # Generate cross-domain insights
    insights = generate_cross_domain_insights(
        wearable_summaries=wearable_summaries,
        user_variants=user_variants,
        blood_markers=blood_markers,
        epigenetic_overlays=epigenetic_overlays,
    )

    # Persist insights
    count = 0
    for insight in insights:
        # Check if similar insight already exists for today
        existing = DailyInsight.query.filter_by(
            user_id=user_id,
            date=today,
            title=insight.title,
        ).first()
        if existing:
            continue

        db.session.add(DailyInsight(
            user_id=user_id,
            date=today,
            insight_type=insight.insight_type,
            title=insight.title,
            body=insight.body,
            data_sources_json=json.dumps(insight.data_sources),
            confidence=insight.confidence,
        ))
        count += 1

    db.session.commit()
    return count


# ── Data helpers ─────────────────────────────────────────────────────────────


def _upsert_daily_data(
    user_id: str,
    connection_id: str,
    data_date: date,
    data_type: str,
    raw_data: dict,
    summary: dict,
) -> None:
    """Insert or update a DailyWearableData record."""
    existing = DailyWearableData.query.filter_by(
        user_id=user_id,
        date=data_date,
        data_type=data_type,
    ).first()

    if existing:
        existing.data_json = json.dumps(raw_data)
        existing.summary_json = json.dumps(summary)
        existing.fetched_at = datetime.now(timezone.utc)
        existing.connection_id = connection_id
    else:
        db.session.add(DailyWearableData(
            user_id=user_id,
            connection_id=connection_id,
            date=data_date,
            data_type=data_type,
            data_json=json.dumps(raw_data),
            summary_json=json.dumps(summary),
        ))


def _load_user_genome_variants(user_id: str) -> list[dict]:
    """Load user's genome variants for cross-referencing."""
    from app.models.genome import GenomeAnalysis, GenomeUpload, Variant

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
    from app.models.blood import BloodResult, BloodUpload

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


def _load_user_epigenetic_overlays(user_id: str) -> list[dict]:
    """Load user's epigenetic overlay data."""
    from app.models.epigenetics import EpigeneticAnalysis, EpigeneticUpload

    latest_upload = (
        EpigeneticUpload.query
        .filter_by(user_id=user_id)
        .order_by(EpigeneticUpload.uploaded_at.desc())
        .first()
    )
    if not latest_upload or not latest_upload.analysis:
        return []

    analysis = latest_upload.analysis
    if analysis.status != "complete" or not analysis.genome_overlay_json:
        return []

    try:
        return json.loads(analysis.genome_overlay_json)
    except (json.JSONDecodeError, TypeError):
        return []
