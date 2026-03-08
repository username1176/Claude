"""Healthspan, InnerAge, and predictive biomarker endpoints."""

import json
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, current_app, g, jsonify, request

from app.extensions import db, limiter
from app.models.audit import AuditLog
from app.models.blood import BloodResult, BloodUpload
from app.models.healthspan import (
    BiomarkerPrediction,
    BiomarkerZone,
    HealthspanReport,
    InnerAgeResult,
)
from app.api.decorators import login_required

healthspan_bp = Blueprint("healthspan", __name__, url_prefix="/api/v1/healthspan")


def _audit(action: str, **kwargs):
    log = AuditLog(
        user_id=g.current_user.id,
        action=action,
        ip_address=request.remote_addr,
        **kwargs,
    )
    db.session.add(log)


# ── POST /api/v1/healthspan/calculate-innerage ──────────────────────────────


@healthspan_bp.route("/calculate-innerage", methods=["POST"])
@limiter.limit("20 per hour")
@login_required
def calculate_innerage():
    """Compute biological age from biomarkers, DNA methylation, and wearables.

    Accepts a JSON body with:
     - chronological_age (required)
     - sex (optional: male/female)
     - Blood biomarkers: albumin_g_l, creatinine_umol_l, glucose_mmol_l,
       crp_mg_dl, lymphocyte_pct, mcv_fl, rdw_pct,
       alkaline_phosphatase_u_l, wbc_1000_ul
     - Epigenetic: global_methylation_avg
     - Wearable: avg_resting_hr, avg_hrv_ms, avg_sleep_hours,
       avg_steps_daily, vo2_max_estimate
     - use_latest_blood (bool): auto-fill from latest blood results
     - use_latest_wearable (bool): auto-fill from latest wearable data
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required."}), 400

    chrono_age = body.get("chronological_age")
    if chrono_age is None:
        return jsonify({"error": "chronological_age is required."}), 400

    from app.utils.ml_analyzer import InnerAgeInput, calculate_inner_age

    biomarkers = InnerAgeInput(
        chronological_age=float(chrono_age),
        sex=body.get("sex", "unknown"),
    )

    # Auto-fill from latest blood results if requested
    if body.get("use_latest_blood"):
        _fill_from_latest_blood(biomarkers)

    # Auto-fill from latest wearable data if requested
    if body.get("use_latest_wearable"):
        _fill_from_latest_wearable(biomarkers)

    # Manual overrides from body
    for field_name in [
        "albumin_g_l", "creatinine_umol_l", "glucose_mmol_l", "crp_mg_dl",
        "lymphocyte_pct", "mcv_fl", "rdw_pct", "alkaline_phosphatase_u_l",
        "wbc_1000_ul", "global_methylation_avg", "avg_resting_hr",
        "avg_hrv_ms", "avg_sleep_hours", "avg_steps_daily", "vo2_max_estimate",
    ]:
        if field_name in body and body[field_name] is not None:
            setattr(biomarkers, field_name, float(body[field_name]))

    # Calculate
    result = calculate_inner_age(biomarkers)

    # Save to database
    record = InnerAgeResult(
        user_id=g.current_user.id,
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
    _audit("calculate_innerage", resource_type="InnerAgeResult", resource_id=record.id)
    db.session.commit()

    return jsonify({
        "id": record.id,
        "biological_age": result.biological_age,
        "chronological_age": result.chronological_age,
        "age_delta": result.age_delta,
        "model_type": result.model_type,
        "scores": {
            "blood": result.blood_score,
            "epigenetic": result.epigenetic_score,
            "wearable": result.wearable_score,
        },
        "breakdown": result.breakdown,
        "confidence": {
            "low": result.confidence_low,
            "high": result.confidence_high,
        },
        "interpretation": _interpret_age_delta(result.age_delta),
    })


# ── GET /api/v1/healthspan/innerage-history ─────────────────────────────────


@healthspan_bp.route("/innerage-history", methods=["GET"])
@login_required
def innerage_history():
    """Get historical InnerAge calculations for the current user."""
    results = (
        InnerAgeResult.query.filter_by(user_id=g.current_user.id)
        .order_by(InnerAgeResult.calculated_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "biological_age": r.biological_age,
            "chronological_age": r.chronological_age,
            "age_delta": r.age_delta,
            "model_type": r.model_type,
            "calculated_at": r.calculated_at.isoformat(),
        }
        for r in results
    ])


# ── POST /api/v1/healthspan/optimized-zones ─────────────────────────────────


@healthspan_bp.route("/optimized-zones", methods=["POST"])
@limiter.limit("20 per hour")
@login_required
def compute_zones():
    """Compute personalized optimal biomarker zones.

    Accepts JSON body with:
     - age (required)
     - sex (optional: male/female)
     - biomarkers (dict of marker_name: value)
     - genetic_variants (optional: dict of rsid: genotype)
     - use_latest_blood (bool): auto-fill from latest blood results
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required."}), 400

    age = body.get("age")
    if age is None:
        return jsonify({"error": "age is required."}), 400

    sex = body.get("sex", "unknown")
    biomarkers = body.get("biomarkers", {})
    genetic_variants = body.get("genetic_variants", {})

    # Auto-fill from latest blood
    if body.get("use_latest_blood"):
        latest_blood = _get_latest_blood_markers()
        for marker_name, value in latest_blood.items():
            if marker_name not in biomarkers:
                biomarkers[marker_name] = value

    if not biomarkers:
        return jsonify({"error": "No biomarkers provided."}), 400

    from app.utils.ml_analyzer import compute_all_zones
    from dataclasses import asdict

    zones = compute_all_zones(float(age), sex, biomarkers, genetic_variants)

    # Save to database
    for z in zones:
        existing = BiomarkerZone.query.filter_by(
            user_id=g.current_user.id, marker_name=z.marker_name
        ).first()
        if existing:
            existing.optimal_low = z.optimal_low
            existing.optimal_high = z.optimal_high
            existing.current_value = z.current_value
            existing.zone_status = z.zone_status
            existing.factors_json = json.dumps(z.factors)
            existing.recommendation = z.recommendation
            existing.updated_at = datetime.now(timezone.utc)
        else:
            db.session.add(BiomarkerZone(
                user_id=g.current_user.id,
                marker_name=z.marker_name,
                marker_display_name=z.marker_display_name,
                unit=z.unit,
                lab_ref_low=z.lab_ref_low,
                lab_ref_high=z.lab_ref_high,
                optimal_low=z.optimal_low,
                optimal_high=z.optimal_high,
                current_value=z.current_value,
                zone_status=z.zone_status,
                factors_json=json.dumps(z.factors),
                recommendation=z.recommendation,
            ))
    db.session.commit()

    return jsonify({
        "zones": [asdict(z) for z in zones],
        "summary": {
            "total": len(zones),
            "optimal": sum(1 for z in zones if z.zone_status == "optimal"),
            "at_risk": sum(1 for z in zones if z.zone_status == "at_risk"),
            "out_of_range": sum(1 for z in zones if z.zone_status == "out_of_range"),
        },
    })


# ── GET /api/v1/healthspan/zones ────────────────────────────────────────────


@healthspan_bp.route("/zones", methods=["GET"])
@login_required
def list_zones():
    """List saved biomarker zones for the current user."""
    zones = (
        BiomarkerZone.query.filter_by(user_id=g.current_user.id)
        .order_by(BiomarkerZone.marker_name)
        .all()
    )
    return jsonify([
        {
            "id": z.id,
            "marker_name": z.marker_name,
            "marker_display_name": z.marker_display_name,
            "unit": z.unit,
            "lab_ref": {"low": z.lab_ref_low, "high": z.lab_ref_high},
            "optimal": {"low": z.optimal_low, "high": z.optimal_high},
            "current_value": z.current_value,
            "zone_status": z.zone_status,
            "recommendation": z.recommendation,
            "updated_at": z.updated_at.isoformat(),
        }
        for z in zones
    ])


# ── POST /api/v1/healthspan/predict-trends ──────────────────────────────────


@healthspan_bp.route("/predict-trends", methods=["POST"])
@limiter.limit("10 per hour")
@login_required
def predict_trends():
    """Forecast biomarker trends using ML time-series models.

    Accepts JSON body with:
     - markers (list of marker names to predict, e.g. ["glucose", "total_cholesterol"])
     - horizon_days (optional, default 180)

    Uses historical blood results for the current user.
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required."}), 400

    marker_names = body.get("markers", [])
    if not marker_names:
        return jsonify({"error": "markers list is required."}), 400

    horizon_days = body.get("horizon_days", 180)

    from app.utils.ml_analyzer import PredictionInput, predict_biomarker_trend
    from dataclasses import asdict

    predictions = []
    for marker_name in marker_names:
        # Gather historical data
        history = _get_marker_history(marker_name)
        if len(history["dates"]) < 2:
            predictions.append({
                "marker_name": marker_name,
                "error": "Insufficient historical data (need >= 2 data points).",
                "data_points": len(history["dates"]),
            })
            continue

        # Get optimal zone if available
        zone = BiomarkerZone.query.filter_by(
            user_id=g.current_user.id, marker_name=marker_name
        ).first()

        pred_input = PredictionInput(
            marker_name=marker_name,
            marker_display_name=history.get("display_name", marker_name),
            dates=history["dates"],
            values=history["values"],
            horizon_days=horizon_days,
            optimal_low=zone.optimal_low if zone else None,
            optimal_high=zone.optimal_high if zone else None,
        )

        result = predict_biomarker_trend(pred_input)

        # Save to database
        record = BiomarkerPrediction(
            user_id=g.current_user.id,
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
        predictions.append(asdict(result))

    db.session.commit()

    return jsonify({"predictions": predictions})


# ── GET /api/v1/healthspan/report/<user_id> ─────────────────────────────────


@healthspan_bp.route("/report/<target_user_id>", methods=["GET"])
@login_required
def get_healthspan_report(target_user_id: str):
    """Get the latest weekly healthspan report for a user.

    Only accessible if the authenticated user matches the target user.
    """
    if target_user_id != g.current_user.id:
        return jsonify({"error": "Access denied."}), 403

    report_type = request.args.get("type", "weekly")
    report = (
        HealthspanReport.query.filter_by(
            user_id=target_user_id, report_type=report_type
        )
        .order_by(HealthspanReport.period_end.desc())
        .first()
    )

    if not report:
        return jsonify({"error": "No healthspan report found. Reports are generated weekly."}), 404

    report_data = {}
    if report.report_json:
        try:
            report_data = json.loads(report.report_json)
        except (json.JSONDecodeError, TypeError):
            pass

    correlations = []
    if report.habit_correlations_json:
        try:
            correlations = json.loads(report.habit_correlations_json)
        except (json.JSONDecodeError, TypeError):
            pass

    recommendations = []
    if report.recommendations_json:
        try:
            recommendations = json.loads(report.recommendations_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return jsonify({
        "id": report.id,
        "report_type": report.report_type,
        "period": {
            "start": report.period_start.isoformat(),
            "end": report.period_end.isoformat(),
        },
        "scores": {
            "overall": report.overall_score,
            "sleep": report.sleep_score,
            "activity": report.activity_score,
            "nutrition": report.nutrition_score,
            "stress": report.stress_score,
        },
        "innerage_snapshot": report.innerage_snapshot,
        "habit_correlations": correlations,
        "recommendations": recommendations,
        "full_report": report_data,
        "generated_at": report.generated_at.isoformat(),
    })


# ── GET /api/v1/healthspan/reports ──────────────────────────────────────────


@healthspan_bp.route("/reports", methods=["GET"])
@login_required
def list_healthspan_reports():
    """List all healthspan reports for the current user."""
    reports = (
        HealthspanReport.query.filter_by(user_id=g.current_user.id)
        .order_by(HealthspanReport.period_end.desc())
        .limit(52)
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "report_type": r.report_type,
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
            "overall_score": r.overall_score,
            "innerage_snapshot": r.innerage_snapshot,
            "generated_at": r.generated_at.isoformat(),
        }
        for r in reports
    ])


# ── Helpers ─────────────────────────────────────────────────────────────────

# Map blood result marker names to InnerAgeInput fields
_BLOOD_TO_INNERAGE = {
    "albumin": "albumin_g_l",
    "creatinine": "creatinine_umol_l",
    "glucose": "glucose_mmol_l",
    "crp": "crp_mg_dl",
    "c_reactive_protein": "crp_mg_dl",
    "lymphocyte_pct": "lymphocyte_pct",
    "lymphocyte": "lymphocyte_pct",
    "mcv": "mcv_fl",
    "mean_cell_volume": "mcv_fl",
    "rdw": "rdw_pct",
    "red_cell_distribution_width": "rdw_pct",
    "alkaline_phosphatase": "alkaline_phosphatase_u_l",
    "wbc": "wbc_1000_ul",
    "white_blood_cell": "wbc_1000_ul",
}


def _fill_from_latest_blood(biomarkers):
    """Fill InnerAge biomarkers from the user's most recent blood results."""
    latest_upload = (
        BloodUpload.query.filter_by(user_id=g.current_user.id)
        .order_by(BloodUpload.test_date.desc())
        .first()
    )
    if not latest_upload:
        return

    results = BloodResult.query.filter_by(upload_id=latest_upload.id).all()
    for r in results:
        field_name = _BLOOD_TO_INNERAGE.get(r.marker_name.lower())
        if field_name and getattr(biomarkers, field_name) is None:
            setattr(biomarkers, field_name, r.value)


def _fill_from_latest_wearable(biomarkers):
    """Fill InnerAge wearable metrics from the last 7 days of wearable data."""
    from app.models.wearable import DailyWearableData

    week_ago = date.today() - timedelta(days=7)
    data = (
        DailyWearableData.query.filter(
            DailyWearableData.user_id == g.current_user.id,
            DailyWearableData.date >= week_ago,
        ).all()
    )

    if not data:
        return

    import json as json_mod

    resting_hrs, hrvs, sleep_hours, steps_list = [], [], [], []
    for d in data:
        summary = {}
        try:
            summary = json_mod.loads(d.summary_json) if d.summary_json else {}
        except (json_mod.JSONDecodeError, TypeError):
            try:
                summary = json_mod.loads(d.data_json) if d.data_json else {}
            except (json_mod.JSONDecodeError, TypeError):
                pass

        if d.data_type == "heart_rate" and summary.get("resting_hr"):
            resting_hrs.append(float(summary["resting_hr"]))
        if d.data_type == "hrv" and summary.get("avg_hrv"):
            hrvs.append(float(summary["avg_hrv"]))
        if d.data_type == "sleep" and summary.get("total_sleep_minutes"):
            sleep_hours.append(float(summary["total_sleep_minutes"]) / 60)
        if d.data_type == "activity" and summary.get("steps"):
            steps_list.append(float(summary["steps"]))

    import numpy as np
    if resting_hrs and biomarkers.avg_resting_hr is None:
        biomarkers.avg_resting_hr = float(np.mean(resting_hrs))
    if hrvs and biomarkers.avg_hrv_ms is None:
        biomarkers.avg_hrv_ms = float(np.mean(hrvs))
    if sleep_hours and biomarkers.avg_sleep_hours is None:
        biomarkers.avg_sleep_hours = float(np.mean(sleep_hours))
    if steps_list and biomarkers.avg_steps_daily is None:
        biomarkers.avg_steps_daily = float(np.mean(steps_list))


def _get_latest_blood_markers() -> dict:
    """Get a dict of marker_name: value from the latest blood upload."""
    latest_upload = (
        BloodUpload.query.filter_by(user_id=g.current_user.id)
        .order_by(BloodUpload.test_date.desc())
        .first()
    )
    if not latest_upload:
        return {}

    results = BloodResult.query.filter_by(upload_id=latest_upload.id).all()
    return {r.marker_name.lower(): r.value for r in results}


def _get_marker_history(marker_name: str) -> dict:
    """Get historical values for a blood marker across all uploads."""
    uploads = (
        BloodUpload.query.filter_by(user_id=g.current_user.id)
        .order_by(BloodUpload.test_date.asc())
        .all()
    )

    dates = []
    values = []
    display_name = marker_name

    for upload in uploads:
        results = BloodResult.query.filter(
            BloodResult.upload_id == upload.id,
            BloodResult.marker_name.ilike(f"%{marker_name}%"),
        ).all()
        for r in results:
            dates.append(upload.test_date.isoformat())
            values.append(r.value)
            display_name = r.marker_display_name

    return {"dates": dates, "values": values, "display_name": display_name}


def _interpret_age_delta(delta: float) -> str:
    """Generate a human-readable interpretation of the age delta."""
    if delta <= -5:
        return (
            "Excellent! Your biological age is significantly younger than your "
            "chronological age. Your lifestyle and biomarkers indicate robust health."
        )
    elif delta <= -2:
        return (
            "Good. You are biologically younger than your chronological age, "
            "suggesting healthy aging patterns."
        )
    elif delta <= 2:
        return (
            "Your biological age is close to your chronological age. "
            "This is typical — consider optimizing sleep, exercise, and "
            "nutrition for potential improvement."
        )
    elif delta <= 5:
        return (
            "Your biological age is moderately elevated. Focus on inflammation "
            "reduction (lower CRP), improving sleep consistency, and increasing "
            "physical activity to lower your biological age."
        )
    else:
        return (
            "Your biological age is significantly elevated. This warrants "
            "attention — consult your healthcare provider about biomarkers "
            "outside optimal ranges. Prioritize sleep, stress management, "
            "and a nutrient-dense diet."
        )
