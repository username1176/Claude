"""Celery tasks for healthspan analysis and weekly report generation.

Tasks:
 1. run_innerage_calculation — Compute biological age for a user.
 2. run_biomarker_predictions — Forecast all tracked biomarkers.
 3. generate_weekly_healthspan_report — Aggregate wearable + blood + microbiome data.
 4. schedule_healthspan_reports — Enqueue reports for all active users.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone

from celery import shared_task

from app.extensions import db

logger = logging.getLogger(__name__)


# ── InnerAge calculation ────────────────────────────────────────────────────


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def run_innerage_calculation(self, user_id: str, chronological_age: float, sex: str = "unknown"):
    """Compute biological age using latest available data for a user.

    Automatically pulls latest blood results, epigenetic data, and
    wearable metrics to build the most complete InnerAge estimate.
    """
    from app.models.blood import BloodResult, BloodUpload
    from app.models.wearable import DailyWearableData
    from app.models.epigenetics import EpigeneticAnalysis, EpigeneticUpload
    from app.models.healthspan import InnerAgeResult
    from app.utils.ml_analyzer import InnerAgeInput, calculate_inner_age
    import numpy as np

    try:
        biomarkers = InnerAgeInput(
            chronological_age=chronological_age,
            sex=sex,
        )

        # Pull latest blood results
        latest_upload = (
            BloodUpload.query.filter_by(user_id=user_id)
            .order_by(BloodUpload.test_date.desc())
            .first()
        )
        if latest_upload:
            results = BloodResult.query.filter_by(upload_id=latest_upload.id).all()
            marker_map = {r.marker_name.lower(): r.value for r in results}

            field_mapping = {
                "albumin": "albumin_g_l",
                "creatinine": "creatinine_umol_l",
                "glucose": "glucose_mmol_l",
                "crp": "crp_mg_dl",
                "c_reactive_protein": "crp_mg_dl",
                "lymphocyte_pct": "lymphocyte_pct",
                "mcv": "mcv_fl",
                "rdw": "rdw_pct",
                "alkaline_phosphatase": "alkaline_phosphatase_u_l",
                "wbc": "wbc_1000_ul",
            }
            for marker, field in field_mapping.items():
                if marker in marker_map:
                    setattr(biomarkers, field, marker_map[marker])

        # Pull latest epigenetic data
        epi_upload = (
            EpigeneticUpload.query.filter_by(user_id=user_id, data_type="methylation")
            .order_by(EpigeneticUpload.uploaded_at.desc())
            .first()
        )
        if epi_upload and epi_upload.analysis:
            biomarkers.global_methylation_avg = epi_upload.analysis.global_methylation_avg

        # Pull last 7 days of wearable data
        week_ago = date.today() - timedelta(days=7)
        wearable_data = DailyWearableData.query.filter(
            DailyWearableData.user_id == user_id,
            DailyWearableData.date >= week_ago,
        ).all()

        resting_hrs, hrvs, sleep_hours, steps_list = [], [], [], []
        for d in wearable_data:
            summary = {}
            try:
                summary = json.loads(d.summary_json) if d.summary_json else {}
            except (json.JSONDecodeError, TypeError):
                try:
                    summary = json.loads(d.data_json) if d.data_json else {}
                except (json.JSONDecodeError, TypeError):
                    pass

            if d.data_type == "heart_rate" and summary.get("resting_hr"):
                resting_hrs.append(float(summary["resting_hr"]))
            if d.data_type == "hrv" and summary.get("avg_hrv"):
                hrvs.append(float(summary["avg_hrv"]))
            if d.data_type == "sleep" and summary.get("total_sleep_minutes"):
                sleep_hours.append(float(summary["total_sleep_minutes"]) / 60)
            if d.data_type == "activity" and summary.get("steps"):
                steps_list.append(float(summary["steps"]))

        if resting_hrs:
            biomarkers.avg_resting_hr = float(np.mean(resting_hrs))
        if hrvs:
            biomarkers.avg_hrv_ms = float(np.mean(hrvs))
        if sleep_hours:
            biomarkers.avg_sleep_hours = float(np.mean(sleep_hours))
        if steps_list:
            biomarkers.avg_steps_daily = float(np.mean(steps_list))

        # Calculate
        result = calculate_inner_age(biomarkers)

        # Save
        record = InnerAgeResult(
            user_id=user_id,
            chronological_age=result.chronological_age,
            biological_age=result.biological_age,
            age_delta=result.age_delta,
            model_type=result.model_type,
            blood_score=result.blood_score,
            epigenetic_score=result.epigenetic_score,
            wearable_score=result.wearable_score,
            input_biomarkers_json=json.dumps({
                k: v for k, v in vars(biomarkers).items()
                if v is not None and k != "methylation_betas"
            }),
            breakdown_json=json.dumps(result.breakdown),
            confidence_low=result.confidence_low,
            confidence_high=result.confidence_high,
        )
        db.session.add(record)
        db.session.commit()

        logger.info(
            "InnerAge calculated for user %s: bio=%.1f, chrono=%.1f, delta=%+.1f",
            user_id, result.biological_age, result.chronological_age, result.age_delta,
        )
        return {"user_id": user_id, "biological_age": result.biological_age, "delta": result.age_delta}

    except Exception as exc:
        logger.exception("InnerAge calculation failed for user %s", user_id)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"error": str(exc)}


# ── Biomarker predictions ──────────────────────────────────────────────────


@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def run_biomarker_predictions(self, user_id: str, marker_names: list[str] | None = None, horizon_days: int = 180):
    """Run time-series predictions for a user's biomarkers.

    If marker_names is None, predicts all markers with >= 2 data points.
    """
    from app.models.blood import BloodResult, BloodUpload
    from app.models.healthspan import BiomarkerPrediction, BiomarkerZone
    from app.utils.ml_analyzer import PredictionInput, predict_biomarker_trend
    from dataclasses import asdict

    try:
        uploads = (
            BloodUpload.query.filter_by(user_id=user_id)
            .order_by(BloodUpload.test_date.asc())
            .all()
        )
        if not uploads:
            return {"user_id": user_id, "predictions": 0, "reason": "no_blood_data"}

        # Build marker history
        marker_history = {}
        for upload in uploads:
            results = BloodResult.query.filter_by(upload_id=upload.id).all()
            for r in results:
                key = r.marker_name.lower()
                if marker_names and key not in [m.lower() for m in marker_names]:
                    continue
                if key not in marker_history:
                    marker_history[key] = {
                        "dates": [], "values": [],
                        "display_name": r.marker_display_name,
                    }
                marker_history[key]["dates"].append(upload.test_date.isoformat())
                marker_history[key]["values"].append(r.value)

        prediction_count = 0
        for marker_name, history in marker_history.items():
            if len(history["dates"]) < 2:
                continue

            zone = BiomarkerZone.query.filter_by(
                user_id=user_id, marker_name=marker_name
            ).first()

            pred_input = PredictionInput(
                marker_name=marker_name,
                marker_display_name=history["display_name"],
                dates=history["dates"],
                values=history["values"],
                horizon_days=horizon_days,
                optimal_low=zone.optimal_low if zone else None,
                optimal_high=zone.optimal_high if zone else None,
            )

            result = predict_biomarker_trend(pred_input)

            record = BiomarkerPrediction(
                user_id=user_id,
                marker_name=result.marker_name,
                marker_display_name=result.marker_display_name,
                model_type=result.model_type,
                horizon_days=horizon_days,
                forecast_json=json.dumps(result.forecast),
                trend_direction=result.trend_direction,
                days_to_out_of_range=result.days_to_out_of_range,
                mae=result.mae,
                mape=result.mape,
                data_points_used=result.data_points_used,
            )
            db.session.add(record)
            prediction_count += 1

        db.session.commit()
        logger.info("Generated %d predictions for user %s", prediction_count, user_id)
        return {"user_id": user_id, "predictions": prediction_count}

    except Exception as exc:
        logger.exception("Biomarker prediction failed for user %s", user_id)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"error": str(exc)}


# ── Weekly healthspan report ────────────────────────────────────────────────


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_weekly_healthspan_report(self, user_id: str):
    """Generate a weekly healthspan report for a user.

    Aggregates:
     - 7 days of wearable data (sleep, activity, HR, HRV, stress)
     - Latest blood biomarkers
     - Latest microbiome diversity
     - Latest InnerAge
    Into a habit-outcome correlation report with actionable recommendations.
    """
    from app.models.wearable import DailyWearableData
    from app.models.blood import BloodResult, BloodUpload
    from app.models.microbiome import MicrobiomeAnalysis, MicrobiomeUpload
    from app.models.healthspan import HealthspanReport, InnerAgeResult
    from app.utils.ml_analyzer import compute_healthspan_report
    from dataclasses import asdict

    try:
        period_end = date.today()
        period_start = period_end - timedelta(days=7)

        # Wearable data
        wearable_data = DailyWearableData.query.filter(
            DailyWearableData.user_id == user_id,
            DailyWearableData.date >= period_start,
            DailyWearableData.date <= period_end,
        ).all()

        wearable_dicts = []
        for d in wearable_data:
            data = {}
            try:
                data = json.loads(d.data_json) if d.data_json else {}
            except (json.JSONDecodeError, TypeError):
                pass
            summary = {}
            try:
                summary = json.loads(d.summary_json) if d.summary_json else {}
            except (json.JSONDecodeError, TypeError):
                pass
            wearable_dicts.append({
                "data_type": d.data_type,
                "date": d.date.isoformat(),
                "summary": {**data, **summary},
            })

        # Latest blood markers
        blood_markers = None
        latest_upload = (
            BloodUpload.query.filter_by(user_id=user_id)
            .order_by(BloodUpload.test_date.desc())
            .first()
        )
        if latest_upload:
            results = BloodResult.query.filter_by(upload_id=latest_upload.id).all()
            blood_markers = [
                {"marker_name": r.marker_name.lower(), "value": r.value}
                for r in results
            ]

        # Latest microbiome diversity
        microbiome_diversity = None
        micro_upload = (
            MicrobiomeUpload.query.filter_by(user_id=user_id)
            .order_by(MicrobiomeUpload.id.desc())
            .first()
        )
        if micro_upload:
            micro_analysis = MicrobiomeAnalysis.query.filter_by(
                upload_id=micro_upload.id, status="complete"
            ).first()
            if micro_analysis and micro_analysis.shannon_diversity:
                microbiome_diversity = micro_analysis.shannon_diversity

        # Latest InnerAge
        innerage = None
        latest_ia = (
            InnerAgeResult.query.filter_by(user_id=user_id)
            .order_by(InnerAgeResult.calculated_at.desc())
            .first()
        )
        if latest_ia:
            innerage = latest_ia.biological_age

        # Compute report
        report_data = compute_healthspan_report(
            wearable_data=wearable_dicts,
            blood_markers=blood_markers,
            microbiome_diversity=microbiome_diversity,
            innerage=innerage,
            period_days=7,
        )

        # Save to database
        report = HealthspanReport(
            user_id=user_id,
            report_type="weekly",
            period_start=period_start,
            period_end=period_end,
            overall_score=report_data.overall_score,
            sleep_score=report_data.sleep_score,
            activity_score=report_data.activity_score,
            nutrition_score=report_data.nutrition_score,
            stress_score=report_data.stress_score,
            innerage_snapshot=innerage,
            habit_correlations_json=json.dumps(
                [asdict(c) for c in report_data.correlations]
            ),
            recommendations_json=json.dumps(report_data.recommendations),
            report_json=json.dumps({
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat(),
                },
                "wearable_days": len(wearable_dicts),
                "blood_markers_available": bool(blood_markers),
                "microbiome_diversity": microbiome_diversity,
                "innerage": innerage,
            }),
        )
        db.session.add(report)
        db.session.commit()

        logger.info(
            "Healthspan report generated for user %s: score=%.1f",
            user_id, report_data.overall_score,
        )
        return {
            "user_id": user_id,
            "report_id": report.id,
            "overall_score": report_data.overall_score,
        }

    except Exception as exc:
        logger.exception("Healthspan report failed for user %s", user_id)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"error": str(exc)}


# ── Scheduler: enqueue reports for all users ────────────────────────────────


@shared_task(bind=True)
def schedule_healthspan_reports(self):
    """Enqueue weekly healthspan reports for all users with wearable data.

    Called by Celery Beat every Sunday.
    """
    from app.models.wearable import WearableConnection
    from app.models.user import User

    active_connections = (
        WearableConnection.query.filter_by(status="active")
        .with_entities(WearableConnection.user_id)
        .distinct()
        .all()
    )

    user_ids = [c.user_id for c in active_connections]
    enqueued = 0

    for user_id in user_ids:
        try:
            generate_weekly_healthspan_report.delay(user_id)
            enqueued += 1
        except Exception:
            logger.debug("Could not enqueue report for user %s", user_id)

    logger.info("Scheduled %d weekly healthspan reports", enqueued)
    return {"enqueued": enqueued}


@shared_task(bind=True)
def schedule_all_predictions(self):
    """Enqueue biomarker predictions for all users with blood data.

    Called by Celery Beat monthly.
    """
    from app.models.blood import BloodUpload
    from sqlalchemy import func

    user_ids = (
        db.session.query(BloodUpload.user_id)
        .group_by(BloodUpload.user_id)
        .having(func.count(BloodUpload.id) >= 2)
        .all()
    )

    enqueued = 0
    for (user_id,) in user_ids:
        try:
            run_biomarker_predictions.delay(user_id)
            enqueued += 1
        except Exception:
            logger.debug("Could not enqueue predictions for user %s", user_id)

    logger.info("Scheduled %d biomarker prediction tasks", enqueued)
    return {"enqueued": enqueued}
