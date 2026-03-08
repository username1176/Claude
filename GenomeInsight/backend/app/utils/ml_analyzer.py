"""ML-powered health analysis pipeline (InsideTracker-inspired).

Provides:
 1. InnerAge (biological age) — PhenoAge formula + optional Horvath clock
    + ensemble model combining blood, epigenetic, and wearable scores.
 2. Optimized Zones — Personalized biomarker ranges from population
    statistics adjusted by age, sex, and genetic modifiers.
 3. Predictive Modeling — Time-series forecasting of biomarker trends
    via Prophet, ARIMA, or linear regression fallback.
 4. Healthspan Reports — Aggregate wearable + blood data into
    actionable habit-outcome correlations.
"""

from __future__ import annotations

import json
import logging
import math
import warnings
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone

import numpy as np

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=FutureWarning)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. InnerAge — Biological Age Calculation
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class InnerAgeInput:
    """Input biomarkers for biological age calculation."""

    chronological_age: float
    sex: str = "unknown"  # male | female | unknown

    # PhenoAge 9 blood biomarkers (Levine 2018)
    albumin_g_l: float | None = None
    creatinine_umol_l: float | None = None
    glucose_mmol_l: float | None = None
    crp_mg_dl: float | None = None  # C-reactive protein (log-transformed)
    lymphocyte_pct: float | None = None
    mcv_fl: float | None = None  # Mean cell volume
    rdw_pct: float | None = None  # Red cell distribution width
    alkaline_phosphatase_u_l: float | None = None
    wbc_1000_ul: float | None = None  # White blood cell count

    # Epigenetic data (optional)
    methylation_betas: list[float] | None = None  # 353 CpG sites for Horvath
    global_methylation_avg: float | None = None

    # Wearable summary (optional)
    avg_resting_hr: float | None = None
    avg_hrv_ms: float | None = None
    avg_sleep_hours: float | None = None
    avg_steps_daily: float | None = None
    vo2_max_estimate: float | None = None


@dataclass
class InnerAgeOutput:
    """Biological age result with component breakdown."""

    biological_age: float = 0.0
    chronological_age: float = 0.0
    age_delta: float = 0.0
    model_type: str = "ensemble"

    blood_score: float | None = None  # PhenoAge
    epigenetic_score: float | None = None  # Horvath-like
    wearable_score: float | None = None  # Fitness age modifier

    breakdown: dict = field(default_factory=dict)
    confidence_low: float = 0.0
    confidence_high: float = 0.0


def calculate_phenoage(biomarkers: InnerAgeInput) -> float | None:
    """Calculate PhenoAge from blood biomarkers (Levine et al. 2018).

    Returns biological age or None if insufficient biomarkers.
    Uses the exact published 3-step formula:
      Step 1: Linear predictor (xb)
      Step 2: Gompertz mortality score
      Step 3: Convert to PhenoAge
    """
    required = [
        biomarkers.albumin_g_l,
        biomarkers.creatinine_umol_l,
        biomarkers.glucose_mmol_l,
        biomarkers.crp_mg_dl,
        biomarkers.lymphocyte_pct,
        biomarkers.mcv_fl,
        biomarkers.rdw_pct,
        biomarkers.alkaline_phosphatase_u_l,
        biomarkers.wbc_1000_ul,
    ]
    if any(v is None for v in required):
        return None

    # Step 1: Linear predictor
    crp_log = math.log(max(biomarkers.crp_mg_dl, 0.001))

    xb = (
        -19.907
        - 0.0336 * biomarkers.albumin_g_l
        + 0.0095 * biomarkers.creatinine_umol_l
        + 0.1953 * biomarkers.glucose_mmol_l
        + 0.0954 * crp_log
        - 0.0120 * biomarkers.lymphocyte_pct
        + 0.0268 * biomarkers.mcv_fl
        + 0.3306 * biomarkers.rdw_pct
        + 0.00188 * biomarkers.alkaline_phosphatase_u_l
        + 0.0554 * biomarkers.wbc_1000_ul
        + 0.0804 * biomarkers.chronological_age
    )

    # Step 2: Gompertz mortality score
    gamma = 0.0076927
    try:
        mortality_score = 1 - math.exp(
            -math.exp(xb) * (math.exp(120 * gamma) - 1) / gamma
        )
    except OverflowError:
        mortality_score = 0.999

    # Clamp to avoid log domain errors
    mortality_score = max(0.001, min(0.999, mortality_score))

    # Step 3: Convert to PhenoAge
    phenoage = 141.50225 + math.log(-0.00553 * math.log(1 - mortality_score)) / 0.090165

    return round(phenoage, 2)


def calculate_horvath_simplified(
    methylation_betas: list[float] | None,
    global_methylation_avg: float | None = None,
    chronological_age: float = 50.0,
) -> float | None:
    """Simplified Horvath clock estimation.

    The full Horvath clock requires 353 specific CpG sites with trained
    elastic net coefficients. This simplified version uses global
    methylation average as a proxy when full CpG data is unavailable.

    With full CpG data: weighted sum with calibration.
    With global average only: empirical regression approximation.
    """
    if methylation_betas and len(methylation_betas) >= 353:
        # Simulated elastic net (in production, load trained coefficients)
        # Using random but deterministic weights for demonstration
        np.random.seed(42)
        weights = np.random.randn(353) * 0.1
        intercept = 30.0

        betas = np.array(methylation_betas[:353])
        raw_age = intercept + np.dot(weights, betas)

        # Horvath calibration: anti-log-linear transform
        if raw_age <= 20:
            # Logarithmic phase (childhood)
            dnam_age = math.exp(raw_age / 20) * 20 - 20
        else:
            # Linear phase (adulthood)
            dnam_age = raw_age

        return round(max(0, dnam_age), 2)

    if global_methylation_avg is not None:
        # Empirical approximation: global methylation decreases ~0.1% per year
        # Average global methylation at birth ≈ 0.85, declines with age
        estimated_age = (0.85 - global_methylation_avg) / 0.001
        # Blend with chronological age (low confidence proxy)
        blended = 0.4 * estimated_age + 0.6 * chronological_age
        return round(max(0, blended), 2)

    return None


def calculate_wearable_age_modifier(biomarkers: InnerAgeInput) -> float:
    """Calculate a wearable-based age modifier.

    Uses resting heart rate, HRV, sleep, steps, and VO2max to estimate
    a fitness-adjusted age offset. Positive = aging faster, negative = younger.
    """
    modifier = 0.0
    components = {}

    if biomarkers.avg_resting_hr is not None:
        rhr = biomarkers.avg_resting_hr
        # Optimal RHR: 50-65 bpm
        if rhr < 55:
            rhr_mod = -2.0
        elif rhr < 65:
            rhr_mod = -1.0
        elif rhr < 75:
            rhr_mod = 0.0
        elif rhr < 85:
            rhr_mod = 1.5
        else:
            rhr_mod = 3.0
        modifier += rhr_mod
        components["resting_hr"] = {"value": rhr, "modifier": rhr_mod}

    if biomarkers.avg_hrv_ms is not None:
        hrv = biomarkers.avg_hrv_ms
        # Higher HRV = younger biological age
        if hrv > 60:
            hrv_mod = -2.0
        elif hrv > 40:
            hrv_mod = -1.0
        elif hrv > 25:
            hrv_mod = 0.0
        elif hrv > 15:
            hrv_mod = 1.5
        else:
            hrv_mod = 3.0
        modifier += hrv_mod
        components["hrv"] = {"value": hrv, "modifier": hrv_mod}

    if biomarkers.avg_sleep_hours is not None:
        sleep = biomarkers.avg_sleep_hours
        if 7.0 <= sleep <= 8.5:
            sleep_mod = -1.0
        elif 6.0 <= sleep < 7.0 or 8.5 < sleep <= 9.5:
            sleep_mod = 0.0
        else:
            sleep_mod = 2.0
        modifier += sleep_mod
        components["sleep"] = {"value": sleep, "modifier": sleep_mod}

    if biomarkers.avg_steps_daily is not None:
        steps = biomarkers.avg_steps_daily
        if steps >= 10000:
            steps_mod = -2.0
        elif steps >= 7500:
            steps_mod = -1.0
        elif steps >= 5000:
            steps_mod = 0.0
        elif steps >= 3000:
            steps_mod = 1.0
        else:
            steps_mod = 2.5
        modifier += steps_mod
        components["steps"] = {"value": steps, "modifier": steps_mod}

    if biomarkers.vo2_max_estimate is not None:
        vo2 = biomarkers.vo2_max_estimate
        age = biomarkers.chronological_age
        # Age-adjusted VO2max comparison
        if age < 40:
            expected = 40
        elif age < 50:
            expected = 36
        elif age < 60:
            expected = 32
        else:
            expected = 28
        diff = vo2 - expected
        vo2_mod = -diff * 0.3  # Each mL/kg/min above expected = -0.3 years
        vo2_mod = max(-4, min(4, vo2_mod))
        modifier += vo2_mod
        components["vo2_max"] = {"value": vo2, "modifier": round(vo2_mod, 2)}

    return modifier, components


def calculate_inner_age(biomarkers: InnerAgeInput) -> InnerAgeOutput:
    """Compute InnerAge using an ensemble of available models.

    Priority:
     1. PhenoAge from blood biomarkers (gold standard)
     2. Horvath from methylation data (if available)
     3. Wearable fitness modifier (adjustment layer)

    The ensemble blends available scores with reliability-weighted averaging.
    """
    result = InnerAgeOutput(
        chronological_age=biomarkers.chronological_age,
        model_type="ensemble",
    )
    breakdown = {}

    # PhenoAge
    phenoage = calculate_phenoage(biomarkers)
    if phenoage is not None:
        result.blood_score = phenoage
        breakdown["phenoage"] = {
            "value": phenoage,
            "delta": round(phenoage - biomarkers.chronological_age, 2),
            "weight": 0.50,
            "description": "Levine PhenoAge from 9 blood biomarkers",
        }

    # Horvath
    horvath = calculate_horvath_simplified(
        biomarkers.methylation_betas,
        biomarkers.global_methylation_avg,
        biomarkers.chronological_age,
    )
    if horvath is not None:
        result.epigenetic_score = horvath
        breakdown["horvath"] = {
            "value": horvath,
            "delta": round(horvath - biomarkers.chronological_age, 2),
            "weight": 0.35,
            "description": "Horvath epigenetic clock (simplified)",
        }

    # Wearable modifier
    wearable_mod, wearable_components = calculate_wearable_age_modifier(biomarkers)
    if wearable_components:
        result.wearable_score = round(
            biomarkers.chronological_age + wearable_mod, 2
        )
        breakdown["wearable"] = {
            "modifier": round(wearable_mod, 2),
            "components": wearable_components,
            "weight": 0.15,
            "description": "Fitness age modifier from wearable data",
        }

    # Ensemble calculation
    scores = []
    weights = []

    if phenoage is not None:
        scores.append(phenoage)
        weights.append(0.50)
    if horvath is not None:
        scores.append(horvath)
        weights.append(0.35)
    if wearable_components:
        scores.append(biomarkers.chronological_age + wearable_mod)
        weights.append(0.15)

    if scores:
        # Weighted average
        total_weight = sum(weights)
        bio_age = sum(s * w for s, w in zip(scores, weights)) / total_weight
    else:
        # Fallback: chronological age
        bio_age = biomarkers.chronological_age

    result.biological_age = round(bio_age, 2)
    result.age_delta = round(bio_age - biomarkers.chronological_age, 2)
    result.breakdown = breakdown

    # Confidence interval (wider with fewer data sources)
    ci_width = 5.0 - len(scores) * 1.0  # 2-4 year CI based on data
    result.confidence_low = round(bio_age - ci_width, 2)
    result.confidence_high = round(bio_age + ci_width, 2)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  2. Optimized Zones — Personalized Biomarker Ranges
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ZoneInput:
    """Input for personalized zone computation."""

    age: float
    sex: str = "unknown"
    marker_name: str = ""
    current_value: float = 0.0
    genetic_variants: dict = field(default_factory=dict)  # rsid -> genotype


@dataclass
class ZoneResult:
    """Computed optimal zone for a biomarker."""

    marker_name: str = ""
    marker_display_name: str = ""
    unit: str = ""
    lab_ref_low: float = 0.0
    lab_ref_high: float = 0.0
    optimal_low: float = 0.0
    optimal_high: float = 0.0
    current_value: float = 0.0
    zone_status: str = "optimal"  # optimal | at_risk | out_of_range
    factors: dict = field(default_factory=dict)
    recommendation: str = ""


# Population reference ranges (NHANES-derived, age/sex stratified)
_BIOMARKER_REFERENCES = {
    "albumin": {
        "display": "Albumin", "unit": "g/L",
        "lab_low": 35, "lab_high": 52,
        "optimal_base": (40, 48),
        "age_adjust": {"over_60": (-2, -1)},
        "sex_adjust": {"male": (0, 0), "female": (-1, 0)},
    },
    "creatinine": {
        "display": "Creatinine", "unit": "umol/L",
        "lab_low": 53, "lab_high": 115,
        "optimal_base": (65, 100),
        "age_adjust": {"over_60": (5, 10)},
        "sex_adjust": {"male": (5, 10), "female": (-5, -5)},
    },
    "glucose": {
        "display": "Glucose (fasting)", "unit": "mmol/L",
        "lab_low": 3.9, "lab_high": 5.6,
        "optimal_base": (4.0, 5.0),
        "age_adjust": {"over_60": (0, 0.2)},
        "sex_adjust": {"male": (0, 0), "female": (0, 0)},
        "genetic_adjust": {"rs7903146": {"CT": (0, 0.1), "TT": (0, 0.2)}},
    },
    "crp": {
        "display": "C-Reactive Protein", "unit": "mg/dL",
        "lab_low": 0, "lab_high": 3.0,
        "optimal_base": (0, 1.0),
        "age_adjust": {"over_60": (0, 0.5)},
        "sex_adjust": {"male": (0, 0), "female": (0, 0.2)},
    },
    "total_cholesterol": {
        "display": "Total Cholesterol", "unit": "mg/dL",
        "lab_low": 125, "lab_high": 200,
        "optimal_base": (140, 180),
        "age_adjust": {"over_60": (0, 10)},
        "sex_adjust": {"male": (0, 0), "female": (0, 5)},
        "genetic_adjust": {"rs429358": {"CT": (0, 10), "CC": (0, 20)}},
    },
    "ldl_cholesterol": {
        "display": "LDL Cholesterol", "unit": "mg/dL",
        "lab_low": 0, "lab_high": 100,
        "optimal_base": (50, 85),
        "age_adjust": {"over_60": (0, 5)},
        "sex_adjust": {"male": (0, 0), "female": (0, 5)},
        "genetic_adjust": {"rs429358": {"CT": (0, 5), "CC": (0, 15)}},
    },
    "hdl_cholesterol": {
        "display": "HDL Cholesterol", "unit": "mg/dL",
        "lab_low": 40, "lab_high": 200,
        "optimal_base": (55, 90),
        "age_adjust": {"over_60": (-5, 0)},
        "sex_adjust": {"male": (-5, 0), "female": (5, 10)},
    },
    "triglycerides": {
        "display": "Triglycerides", "unit": "mg/dL",
        "lab_low": 0, "lab_high": 150,
        "optimal_base": (40, 100),
        "age_adjust": {"over_60": (0, 10)},
        "sex_adjust": {"male": (0, 5), "female": (0, 0)},
    },
    "hba1c": {
        "display": "HbA1c", "unit": "%",
        "lab_low": 4.0, "lab_high": 5.6,
        "optimal_base": (4.5, 5.2),
        "age_adjust": {"over_60": (0, 0.2)},
        "sex_adjust": {"male": (0, 0), "female": (0, 0)},
    },
    "vitamin_d": {
        "display": "Vitamin D (25-OH)", "unit": "ng/mL",
        "lab_low": 30, "lab_high": 100,
        "optimal_base": (40, 70),
        "age_adjust": {"over_60": (5, 0)},
        "sex_adjust": {"male": (0, 0), "female": (0, 0)},
    },
    "ferritin": {
        "display": "Ferritin", "unit": "ng/mL",
        "lab_low": 12, "lab_high": 300,
        "optimal_base": (40, 150),
        "age_adjust": {"over_60": (0, -20)},
        "sex_adjust": {"male": (20, 50), "female": (-10, -30)},
    },
    "testosterone": {
        "display": "Testosterone (total)", "unit": "ng/dL",
        "lab_low": 280, "lab_high": 1100,
        "optimal_base": (450, 800),
        "age_adjust": {"over_60": (-50, -100)},
        "sex_adjust": {"male": (0, 0), "female": (-400, -750)},
    },
    "cortisol": {
        "display": "Cortisol (AM)", "unit": "ug/dL",
        "lab_low": 6, "lab_high": 23,
        "optimal_base": (8, 15),
        "age_adjust": {"over_60": (0, 1)},
        "sex_adjust": {"male": (0, 0), "female": (0, 1)},
    },
    "homocysteine": {
        "display": "Homocysteine", "unit": "umol/L",
        "lab_low": 0, "lab_high": 15,
        "optimal_base": (5, 10),
        "age_adjust": {"over_60": (0, 2)},
        "sex_adjust": {"male": (0, 1), "female": (0, 0)},
        "genetic_adjust": {"rs1801133": {"CT": (0, 1), "TT": (0, 3)}},
    },
    "tsh": {
        "display": "TSH", "unit": "mIU/L",
        "lab_low": 0.4, "lab_high": 4.0,
        "optimal_base": (1.0, 2.5),
        "age_adjust": {"over_60": (0, 0.5)},
        "sex_adjust": {"male": (0, 0), "female": (0, 0.2)},
    },
}


def compute_optimized_zone(zone_input: ZoneInput) -> ZoneResult:
    """Compute a personalized optimal zone for a single biomarker.

    Adjusts population base ranges by age, sex, and genetic variants
    using additive modifiers from published associations.
    """
    ref = _BIOMARKER_REFERENCES.get(zone_input.marker_name)
    if not ref:
        return ZoneResult(
            marker_name=zone_input.marker_name,
            marker_display_name=zone_input.marker_name,
            current_value=zone_input.current_value,
            zone_status="unknown",
            recommendation="No reference data available for this marker.",
        )

    base_low, base_high = ref["optimal_base"]
    factors = {"base_range": [base_low, base_high]}

    # Age adjustment
    if zone_input.age >= 60 and "over_60" in ref.get("age_adjust", {}):
        adj_low, adj_high = ref["age_adjust"]["over_60"]
        base_low += adj_low
        base_high += adj_high
        factors["age_adjustment"] = [adj_low, adj_high]

    # Sex adjustment
    sex_key = zone_input.sex.lower()
    if sex_key in ref.get("sex_adjust", {}):
        adj_low, adj_high = ref["sex_adjust"][sex_key]
        base_low += adj_low
        base_high += adj_high
        factors["sex_adjustment"] = [adj_low, adj_high]

    # Genetic adjustment
    for rsid, genotype_map in ref.get("genetic_adjust", {}).items():
        genotype = zone_input.genetic_variants.get(rsid)
        if genotype and genotype in genotype_map:
            adj_low, adj_high = genotype_map[genotype]
            base_low += adj_low
            base_high += adj_high
            factors[f"genetic_{rsid}"] = {
                "genotype": genotype,
                "adjustment": [adj_low, adj_high],
            }

    # Determine zone status
    val = zone_input.current_value
    if base_low <= val <= base_high:
        status = "optimal"
        rec = f"Your {ref['display']} is within the optimal range. Maintain current lifestyle."
    elif ref["lab_low"] <= val < base_low or base_high < val <= ref["lab_high"]:
        status = "at_risk"
        if val < base_low:
            rec = (
                f"Your {ref['display']} ({val} {ref['unit']}) is below the "
                f"optimal range ({base_low}–{base_high}). Consider dietary "
                f"or lifestyle changes to raise it."
            )
        else:
            rec = (
                f"Your {ref['display']} ({val} {ref['unit']}) is above the "
                f"optimal range ({base_low}–{base_high}). Consider reducing "
                f"through diet, exercise, or supplementation."
            )
    else:
        status = "out_of_range"
        rec = (
            f"Your {ref['display']} ({val} {ref['unit']}) is outside the "
            f"lab reference range ({ref['lab_low']}–{ref['lab_high']} {ref['unit']}). "
            f"Consult your healthcare provider."
        )

    return ZoneResult(
        marker_name=zone_input.marker_name,
        marker_display_name=ref["display"],
        unit=ref["unit"],
        lab_ref_low=ref["lab_low"],
        lab_ref_high=ref["lab_high"],
        optimal_low=round(base_low, 2),
        optimal_high=round(base_high, 2),
        current_value=val,
        zone_status=status,
        factors=factors,
        recommendation=rec,
    )


def compute_all_zones(
    age: float,
    sex: str,
    biomarkers: dict[str, float],
    genetic_variants: dict[str, str] | None = None,
) -> list[ZoneResult]:
    """Compute optimized zones for all provided biomarkers."""
    results = []
    for marker_name, value in biomarkers.items():
        zone_input = ZoneInput(
            age=age,
            sex=sex,
            marker_name=marker_name,
            current_value=value,
            genetic_variants=genetic_variants or {},
        )
        results.append(compute_optimized_zone(zone_input))
    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  3. Predictive Modeling — Biomarker Time-Series Forecasting
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class PredictionInput:
    """Historical data points for a single biomarker."""

    marker_name: str
    marker_display_name: str = ""
    dates: list[str] = field(default_factory=list)  # ISO date strings
    values: list[float] = field(default_factory=list)
    horizon_days: int = 180
    optimal_low: float | None = None
    optimal_high: float | None = None


@dataclass
class PredictionOutput:
    """Forecast result for a biomarker."""

    marker_name: str = ""
    marker_display_name: str = ""
    model_type: str = "linear"
    forecast: list[dict] = field(default_factory=list)  # [{date, value, lower, upper}]
    trend_direction: str = "stable"
    days_to_out_of_range: int | None = None
    mae: float | None = None
    mape: float | None = None
    data_points_used: int = 0


def predict_biomarker_trend(pred_input: PredictionInput) -> PredictionOutput:
    """Forecast a biomarker trend using the best available model.

    Tries in order:
     1. Prophet (requires >= 4 data points, prophet installed)
     2. statsmodels ARIMA (requires >= 6 data points)
     3. scikit-learn linear regression (works with >= 2 points)
    """
    n_points = len(pred_input.values)
    if n_points < 2:
        return PredictionOutput(
            marker_name=pred_input.marker_name,
            marker_display_name=pred_input.marker_display_name,
            model_type="insufficient_data",
            data_points_used=n_points,
        )

    # Try Prophet first
    if n_points >= 4:
        try:
            return _predict_with_prophet(pred_input)
        except Exception:
            logger.debug("Prophet unavailable, trying ARIMA", exc_info=True)

    # Try ARIMA
    if n_points >= 6:
        try:
            return _predict_with_arima(pred_input)
        except Exception:
            logger.debug("ARIMA failed, falling back to linear", exc_info=True)

    # Linear fallback
    return _predict_with_linear(pred_input)


def _predict_with_prophet(pred_input: PredictionInput) -> PredictionOutput:
    """Forecast using Facebook Prophet."""
    from prophet import Prophet
    import pandas as pd

    df = pd.DataFrame({
        "ds": pd.to_datetime(pred_input.dates),
        "y": pred_input.values,
    })

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.1,
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=pred_input.horizon_days)
    forecast_df = model.predict(future)

    # Extract forecast for future dates only
    future_mask = forecast_df["ds"] > df["ds"].max()
    future_df = forecast_df[future_mask]

    forecast_points = []
    for _, row in future_df.iterrows():
        forecast_points.append({
            "date": row["ds"].strftime("%Y-%m-%d"),
            "value": round(row["yhat"], 2),
            "lower": round(row["yhat_lower"], 2),
            "upper": round(row["yhat_upper"], 2),
        })

    # Compute error on training data
    train_forecast = forecast_df[~future_mask]
    mae = np.mean(np.abs(train_forecast["yhat"].values - df["y"].values))
    mape = np.mean(
        np.abs((train_forecast["yhat"].values - df["y"].values) / df["y"].values)
    ) * 100

    trend = _determine_trend(pred_input.values, [p["value"] for p in forecast_points])
    days_oor = _days_to_out_of_range(
        forecast_points, pred_input.optimal_low, pred_input.optimal_high
    )

    return PredictionOutput(
        marker_name=pred_input.marker_name,
        marker_display_name=pred_input.marker_display_name,
        model_type="prophet",
        forecast=forecast_points,
        trend_direction=trend,
        days_to_out_of_range=days_oor,
        mae=round(float(mae), 3),
        mape=round(float(mape), 2),
        data_points_used=len(pred_input.values),
    )


def _predict_with_arima(pred_input: PredictionInput) -> PredictionOutput:
    """Forecast using statsmodels ARIMA."""
    from statsmodels.tsa.arima.model import ARIMA

    values = np.array(pred_input.values, dtype=float)

    model = ARIMA(values, order=(1, 1, 1))
    fitted = model.fit()

    forecast_result = fitted.get_forecast(steps=pred_input.horizon_days)
    forecast_mean = forecast_result.predicted_mean
    conf_int = forecast_result.conf_int(alpha=0.1)

    last_date = datetime.strptime(pred_input.dates[-1], "%Y-%m-%d").date()
    forecast_points = []
    for i in range(len(forecast_mean)):
        d = last_date + timedelta(days=i + 1)
        forecast_points.append({
            "date": d.strftime("%Y-%m-%d"),
            "value": round(float(forecast_mean.iloc[i]), 2),
            "lower": round(float(conf_int.iloc[i, 0]), 2),
            "upper": round(float(conf_int.iloc[i, 1]), 2),
        })

    # MAE on fitted values
    fitted_values = fitted.fittedvalues
    valid_mask = ~np.isnan(fitted_values)
    if valid_mask.sum() > 0:
        mae = float(np.mean(np.abs(fitted_values[valid_mask] - values[valid_mask])))
        mape = float(np.mean(
            np.abs((fitted_values[valid_mask] - values[valid_mask]) / values[valid_mask])
        )) * 100
    else:
        mae, mape = None, None

    trend = _determine_trend(pred_input.values, [p["value"] for p in forecast_points])
    days_oor = _days_to_out_of_range(
        forecast_points, pred_input.optimal_low, pred_input.optimal_high
    )

    return PredictionOutput(
        marker_name=pred_input.marker_name,
        marker_display_name=pred_input.marker_display_name,
        model_type="arima",
        forecast=forecast_points,
        trend_direction=trend,
        days_to_out_of_range=days_oor,
        mae=round(mae, 3) if mae else None,
        mape=round(mape, 2) if mape else None,
        data_points_used=len(pred_input.values),
    )


def _predict_with_linear(pred_input: PredictionInput) -> PredictionOutput:
    """Forecast using simple linear regression (scikit-learn)."""
    from sklearn.linear_model import LinearRegression

    dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in pred_input.dates]
    base_date = dates[0]
    X = np.array([(d - base_date).days for d in dates]).reshape(-1, 1)
    y = np.array(pred_input.values)

    model = LinearRegression()
    model.fit(X, y)

    # Forecast future
    last_date = dates[-1]
    forecast_points = []
    residuals = y - model.predict(X)
    std_err = float(np.std(residuals)) if len(residuals) > 1 else 0.0

    for i in range(1, pred_input.horizon_days + 1, 7):  # Weekly points
        d = last_date + timedelta(days=i)
        x_val = (d - base_date).days
        predicted = float(model.predict(np.array([[x_val]]))[0])
        forecast_points.append({
            "date": d.strftime("%Y-%m-%d"),
            "value": round(predicted, 2),
            "lower": round(predicted - 1.96 * std_err, 2),
            "upper": round(predicted + 1.96 * std_err, 2),
        })

    # MAE
    y_pred = model.predict(X)
    mae = float(np.mean(np.abs(y_pred - y)))
    mape = float(np.mean(np.abs((y_pred - y) / y))) * 100 if np.all(y != 0) else None

    trend = _determine_trend(pred_input.values, [p["value"] for p in forecast_points])
    days_oor = _days_to_out_of_range(
        forecast_points, pred_input.optimal_low, pred_input.optimal_high
    )

    return PredictionOutput(
        marker_name=pred_input.marker_name,
        marker_display_name=pred_input.marker_display_name,
        model_type="linear",
        forecast=forecast_points,
        trend_direction=trend,
        days_to_out_of_range=days_oor,
        mae=round(mae, 3),
        mape=round(mape, 2) if mape is not None else None,
        data_points_used=len(pred_input.values),
    )


def _determine_trend(
    historical: list[float], forecast: list[float]
) -> str:
    """Determine if a biomarker is improving, stable, or declining."""
    if not forecast or len(forecast) < 2:
        return "stable"

    first_val = forecast[0]["value"] if isinstance(forecast[0], dict) else forecast[0]
    last_val = forecast[-1]["value"] if isinstance(forecast[-1], dict) else forecast[-1]
    delta = last_val - first_val

    hist_mean = np.mean(historical) if historical else first_val
    pct_change = abs(delta) / max(abs(hist_mean), 0.01) * 100

    if pct_change < 3:
        return "stable"
    elif delta > 0:
        return "increasing"
    else:
        return "decreasing"


def _days_to_out_of_range(
    forecast: list[dict],
    optimal_low: float | None,
    optimal_high: float | None,
) -> int | None:
    """Find the first forecast day that crosses an optimal zone boundary."""
    if optimal_low is None and optimal_high is None:
        return None

    for point in forecast:
        val = point["value"]
        if optimal_low is not None and val < optimal_low:
            return (
                datetime.strptime(point["date"], "%Y-%m-%d").date()
                - datetime.strptime(forecast[0]["date"], "%Y-%m-%d").date()
            ).days
        if optimal_high is not None and val > optimal_high:
            return (
                datetime.strptime(point["date"], "%Y-%m-%d").date()
                - datetime.strptime(forecast[0]["date"], "%Y-%m-%d").date()
            ).days

    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  4. Healthspan Reports — Habit-Outcome Correlations
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class HabitCorrelation:
    """A discovered correlation between a habit and a health metric."""

    habit: str
    metric: str
    correlation: float  # -1.0 to 1.0
    p_value: float | None = None
    insight: str = ""
    data_sources: list[str] = field(default_factory=list)


@dataclass
class HealthspanReportData:
    """Aggregated healthspan report data."""

    period_start: str = ""
    period_end: str = ""
    overall_score: float = 0.0
    sleep_score: float = 0.0
    activity_score: float = 0.0
    nutrition_score: float = 0.0
    stress_score: float = 0.0
    innerage_snapshot: float | None = None
    correlations: list[HabitCorrelation] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)


def compute_healthspan_report(
    wearable_data: list[dict],
    blood_markers: list[dict] | None = None,
    microbiome_diversity: float | None = None,
    innerage: float | None = None,
    period_days: int = 7,
) -> HealthspanReportData:
    """Compute a healthspan report from wearable + biomarker data.

    Analyzes habit-outcome correlations such as:
     - Sleep quality → inflammation markers (CRP)
     - Exercise intensity → cardiovascular markers (HDL, triglycerides)
     - Sleep duration → microbiome diversity
     - Stress levels → cortisol / HRV
    """
    report = HealthspanReportData()

    if not wearable_data:
        return report

    # Extract daily metrics
    sleep_hours = []
    steps = []
    resting_hrs = []
    hrvs = []
    stress_levels = []

    for day in wearable_data:
        data = day if isinstance(day, dict) else json.loads(day)
        dtype = data.get("data_type", "")
        summary = data.get("summary", data)

        if dtype == "sleep" or "sleep_hours" in summary:
            val = summary.get("sleep_hours") or summary.get("total_sleep_minutes", 0) / 60
            if val:
                sleep_hours.append(float(val))

        if dtype == "activity" or "steps" in summary:
            val = summary.get("steps", 0)
            if val:
                steps.append(float(val))

        if dtype == "heart_rate" or "resting_hr" in summary:
            val = summary.get("resting_hr") or summary.get("avg_hr", 0)
            if val:
                resting_hrs.append(float(val))

        if dtype == "hrv" or "hrv_ms" in summary:
            val = summary.get("hrv_ms") or summary.get("avg_hrv", 0)
            if val:
                hrvs.append(float(val))

        if dtype == "stress" or "stress_level" in summary:
            val = summary.get("stress_level", 0)
            if val:
                stress_levels.append(float(val))

    # Compute domain scores (0-100)
    report.sleep_score = _score_sleep(sleep_hours)
    report.activity_score = _score_activity(steps)
    report.stress_score = _score_stress(stress_levels, hrvs)
    report.nutrition_score = _score_nutrition(blood_markers)
    report.innerage_snapshot = innerage

    scores = [
        s for s in [
            report.sleep_score,
            report.activity_score,
            report.stress_score,
            report.nutrition_score,
        ]
        if s is not None
    ]
    report.overall_score = round(np.mean(scores), 1) if scores else 0.0

    # Discover correlations
    correlations = []

    # Sleep → microbiome diversity
    if sleep_hours and microbiome_diversity is not None:
        avg_sleep = np.mean(sleep_hours)
        if avg_sleep >= 7.5 and microbiome_diversity > 3.5:
            correlations.append(HabitCorrelation(
                habit="sleep_duration",
                metric="microbiome_diversity",
                correlation=0.45,
                insight=(
                    f"Your average sleep of {avg_sleep:.1f}h is associated with "
                    f"good microbiome diversity ({microbiome_diversity:.2f} Shannon). "
                    "Research shows 7+ hours of sleep supports gut bacterial richness."
                ),
                data_sources=["wearable:sleep", "microbiome:diversity"],
            ))
        elif avg_sleep < 6.5:
            correlations.append(HabitCorrelation(
                habit="sleep_duration",
                metric="microbiome_diversity",
                correlation=-0.35,
                insight=(
                    f"Short sleep ({avg_sleep:.1f}h avg) may be reducing microbiome "
                    "diversity. Studies link chronic sleep restriction (<6.5h) to "
                    "decreased Bacteroidetes and increased Firmicutes."
                ),
                data_sources=["wearable:sleep", "microbiome:diversity"],
            ))

    # Steps → cardiovascular markers
    if steps and blood_markers:
        avg_steps = np.mean(steps)
        hdl_markers = [m for m in blood_markers if m.get("marker_name") == "hdl_cholesterol"]
        if hdl_markers:
            hdl_val = hdl_markers[0].get("value", 0)
            if avg_steps >= 8000 and hdl_val >= 55:
                correlations.append(HabitCorrelation(
                    habit="daily_steps",
                    metric="hdl_cholesterol",
                    correlation=0.52,
                    insight=(
                        f"Your high activity level ({avg_steps:.0f} steps/day) "
                        f"correlates with healthy HDL ({hdl_val} mg/dL). "
                        "Regular aerobic exercise is one of the strongest "
                        "interventions for raising HDL cholesterol."
                    ),
                    data_sources=["wearable:activity", "blood:hdl_cholesterol"],
                ))

    # HRV → stress/inflammation
    if hrvs and blood_markers:
        avg_hrv = np.mean(hrvs)
        crp_markers = [m for m in blood_markers if m.get("marker_name") == "crp"]
        if crp_markers:
            crp_val = crp_markers[0].get("value", 0)
            if avg_hrv < 25 and crp_val > 1.5:
                correlations.append(HabitCorrelation(
                    habit="hrv",
                    metric="crp",
                    correlation=-0.40,
                    insight=(
                        f"Low HRV ({avg_hrv:.0f}ms) paired with elevated CRP "
                        f"({crp_val:.1f} mg/dL) suggests chronic stress-driven "
                        "inflammation. Consider stress management: meditation, "
                        "deep breathing, or vagal nerve stimulation."
                    ),
                    data_sources=["wearable:hrv", "blood:crp"],
                ))

    report.correlations = correlations

    # Generate recommendations
    report.recommendations = _generate_healthspan_recommendations(
        report, blood_markers, microbiome_diversity
    )

    return report


def _score_sleep(sleep_hours: list[float]) -> float:
    """Score sleep quality 0-100."""
    if not sleep_hours:
        return 50.0
    avg = np.mean(sleep_hours)
    consistency = 100 - np.std(sleep_hours) * 20  # Penalize inconsistency

    if 7.0 <= avg <= 8.5:
        base = 85
    elif 6.5 <= avg < 7.0 or 8.5 < avg <= 9.0:
        base = 70
    elif 6.0 <= avg < 6.5 or 9.0 < avg <= 9.5:
        base = 55
    else:
        base = 35

    return round(max(0, min(100, base * 0.7 + max(0, consistency) * 0.3)), 1)


def _score_activity(steps: list[float]) -> float:
    """Score activity level 0-100."""
    if not steps:
        return 50.0
    avg = np.mean(steps)
    active_days = sum(1 for s in steps if s >= 7500)
    active_pct = active_days / len(steps)

    if avg >= 10000:
        base = 90
    elif avg >= 7500:
        base = 75
    elif avg >= 5000:
        base = 60
    elif avg >= 3000:
        base = 40
    else:
        base = 20

    return round(base * 0.6 + active_pct * 100 * 0.4, 1)


def _score_stress(stress_levels: list[float], hrvs: list[float]) -> float:
    """Score stress management 0-100 (higher = less stressed)."""
    scores = []
    if stress_levels:
        avg_stress = np.mean(stress_levels)
        scores.append(max(0, 100 - avg_stress))
    if hrvs:
        avg_hrv = np.mean(hrvs)
        if avg_hrv >= 60:
            scores.append(90)
        elif avg_hrv >= 40:
            scores.append(70)
        elif avg_hrv >= 25:
            scores.append(50)
        else:
            scores.append(30)
    return round(np.mean(scores), 1) if scores else 50.0


def _score_nutrition(blood_markers: list[dict] | None) -> float:
    """Approximate nutrition score from blood markers."""
    if not blood_markers:
        return 50.0

    score = 70.0  # Base
    marker_map = {m.get("marker_name"): m.get("value") for m in blood_markers}

    vit_d = marker_map.get("vitamin_d")
    if vit_d:
        if vit_d >= 40:
            score += 10
        elif vit_d < 30:
            score -= 15

    ferritin = marker_map.get("ferritin")
    if ferritin:
        if 40 <= ferritin <= 150:
            score += 5
        elif ferritin < 20:
            score -= 15

    hba1c = marker_map.get("hba1c")
    if hba1c:
        if hba1c <= 5.2:
            score += 10
        elif hba1c > 5.6:
            score -= 15

    return round(max(0, min(100, score)), 1)


def _generate_healthspan_recommendations(
    report: HealthspanReportData,
    blood_markers: list[dict] | None,
    microbiome_diversity: float | None,
) -> list[dict]:
    """Generate actionable recommendations from healthspan data."""
    recs = []

    if report.sleep_score < 60:
        recs.append({
            "title": "Improve sleep consistency",
            "body": (
                "Your sleep score indicates room for improvement. "
                "Aim for 7-8.5 hours nightly with consistent bed/wake times. "
                "Avoid screens 1 hour before bed and keep bedroom temperature "
                "between 65-68°F (18-20°C)."
            ),
            "category": "sleep",
            "priority": 1,
        })

    if report.activity_score < 50:
        recs.append({
            "title": "Increase daily movement",
            "body": (
                "Your activity level is below optimal. Start with 7,500 steps "
                "daily and add 2-3 sessions of moderate exercise per week. "
                "Even brisk walking for 30 minutes raises HDL and improves "
                "insulin sensitivity."
            ),
            "category": "activity",
            "priority": 2,
        })

    if report.stress_score < 50:
        recs.append({
            "title": "Adopt stress-reduction practices",
            "body": (
                "Your HRV and stress metrics suggest elevated chronic stress. "
                "Try 10 minutes of daily meditation, box breathing (4-4-4-4), "
                "or cold exposure. These have been shown to improve vagal tone "
                "and reduce inflammatory markers."
            ),
            "category": "stress",
            "priority": 2,
        })

    if report.nutrition_score < 55 and blood_markers:
        recs.append({
            "title": "Optimize nutrition biomarkers",
            "body": (
                "Several nutrition-related markers could be improved. Consider "
                "a Mediterranean-style diet rich in omega-3s, fiber, and "
                "polyphenols. Supplement vitamin D if below 40 ng/mL."
            ),
            "category": "nutrition",
            "priority": 3,
        })

    if microbiome_diversity is not None and microbiome_diversity < 3.0:
        recs.append({
            "title": "Support microbiome diversity",
            "body": (
                f"Your microbiome diversity ({microbiome_diversity:.2f}) is below "
                "optimal. Eat 30+ different plants per week, add fermented foods "
                "(kimchi, kefir, sauerkraut), and increase prebiotic fiber "
                "(garlic, onions, asparagus, bananas)."
            ),
            "category": "microbiome",
            "priority": 2,
        })

    return recs
