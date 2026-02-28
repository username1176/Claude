"""Terra / ROOK wearable API client and cross-domain analysis engine.

Provides:
- OAuth2 flow helpers (generate auth URL, exchange code, refresh tokens)
- Daily data pull from Terra API
- Summary extraction from raw wearable payloads
- Cross-domain correlation engine (genome + epigenetics + blood + wearable)
- Daily insight generation with template fallback
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)

TERRA_BASE_URL = "https://api.tryterra.co/v2"

# Supported wearable providers through Terra
SUPPORTED_PROVIDERS = {
    "fitbit", "garmin", "apple_health", "oura", "whoop",
    "polar", "suunto", "withings", "samsung", "coros",
}

# Data types we pull from wearables
WEARABLE_DATA_TYPES = {"activity", "sleep", "heart_rate", "hrv", "spo2", "stress"}


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class TerraAuthResult:
    """Result from initiating a Terra OAuth flow."""

    auth_url: str
    state: str
    provider: str


@dataclass
class TerraTokens:
    """Tokens received after successful OAuth callback."""

    terra_user_id: str
    access_token: str
    refresh_token: str
    expires_at: datetime | None = None
    scopes: str = ""


@dataclass
class WearableDaySummary:
    """Normalised summary for a single day of wearable data."""

    data_type: str
    date: date
    raw_data: dict
    summary: dict


@dataclass
class CrossDomainInsight:
    """A single cross-domain insight correlating multiple data layers."""

    title: str
    body: str
    confidence: str  # low / medium / high
    insight_type: str = "daily"  # daily / weekly / alert
    data_sources: list[str] = field(default_factory=list)


# ── Known variant-wearable correlations ──────────────────────────────────────

# Maps rsID → (gene, wearable_metric, direction, insight_template)
_VARIANT_WEARABLE_RULES: list[dict] = [
    {
        "rsid": "rs6265",
        "gene": "BDNF",
        "metric": "sleep",
        "summary_key": "deep_sleep_minutes",
        "threshold_low": 60,
        "insight_template": (
            "Your BDNF {genotype} genotype (rs6265) affects neuroplasticity. "
            "Deep sleep ({value} min) is {assessment} for cognitive recovery. "
            "{recommendation}"
        ),
    },
    {
        "rsid": "rs7903146",
        "gene": "TCF7L2",
        "metric": "activity",
        "summary_key": "steps",
        "threshold_low": 7000,
        "insight_template": (
            "Your TCF7L2 variant (rs7903146 {genotype}) is associated with "
            "glucose regulation. Your step count of {value} is {assessment}. "
            "{recommendation}"
        ),
    },
    {
        "rsid": "rs1801133",
        "gene": "MTHFR",
        "metric": "heart_rate",
        "summary_key": "resting_hr_bpm",
        "threshold_high": 75,
        "insight_template": (
            "MTHFR {genotype} (rs1801133) can affect homocysteine levels and "
            "cardiovascular health. Your resting HR of {value} bpm is "
            "{assessment}. {recommendation}"
        ),
    },
    {
        "rsid": "rs4680",
        "gene": "COMT",
        "metric": "stress",
        "summary_key": "stress_score",
        "threshold_high": 70,
        "insight_template": (
            "COMT {genotype} (rs4680) affects dopamine metabolism and stress "
            "response. Your stress score of {value} is {assessment}. "
            "{recommendation}"
        ),
    },
    {
        "rsid": "rs1800497",
        "gene": "DRD2",
        "metric": "activity",
        "summary_key": "active_minutes",
        "threshold_low": 30,
        "insight_template": (
            "DRD2 {genotype} (rs1800497) influences reward-driven behaviour. "
            "Your {value} active minutes today are {assessment}. "
            "{recommendation}"
        ),
    },
    {
        "rsid": "rs9939609",
        "gene": "FTO",
        "metric": "activity",
        "summary_key": "steps",
        "threshold_low": 8000,
        "insight_template": (
            "FTO {genotype} (rs9939609) is linked to obesity risk. "
            "Your {value} steps are {assessment} for weight management. "
            "{recommendation}"
        ),
    },
    {
        "rsid": "rs762551",
        "gene": "CYP1A2",
        "metric": "heart_rate",
        "summary_key": "avg_hr_bpm",
        "threshold_high": 80,
        "insight_template": (
            "CYP1A2 {genotype} (rs762551) affects caffeine metabolism. "
            "Your average HR of {value} bpm is {assessment}. "
            "{recommendation}"
        ),
    },
]

# Blood marker ↔ wearable metric correlations
_BLOOD_WEARABLE_RULES: list[dict] = [
    {
        "blood_marker": "hemoglobin_a1c",
        "metric": "activity",
        "summary_key": "steps",
        "threshold_low": 7000,
        "insight_template": (
            "Your HbA1c of {blood_value} combined with {value} daily steps "
            "suggests {assessment}. {recommendation}"
        ),
    },
    {
        "blood_marker": "cortisol",
        "metric": "sleep",
        "summary_key": "total_sleep_minutes",
        "threshold_low": 360,
        "insight_template": (
            "Cortisol level of {blood_value} with {value} minutes of sleep "
            "indicates {assessment}. {recommendation}"
        ),
    },
    {
        "blood_marker": "vitamin_d",
        "metric": "activity",
        "summary_key": "active_minutes",
        "threshold_low": 30,
        "insight_template": (
            "Vitamin D at {blood_value} alongside {value} active minutes "
            "suggests {assessment}. {recommendation}"
        ),
    },
    {
        "blood_marker": "ferritin",
        "metric": "heart_rate",
        "summary_key": "resting_hr_bpm",
        "threshold_high": 80,
        "insight_template": (
            "Ferritin level of {blood_value} with resting HR of {value} bpm "
            "indicates {assessment}. {recommendation}"
        ),
    },
]


# ── OAuth helpers ────────────────────────────────────────────────────────────


def generate_terra_auth_url(
    provider: str,
    terra_api_key: str,
    redirect_uri: str,
) -> TerraAuthResult:
    """Build the Terra authentication URL for the given provider.

    In production this would call the Terra API to generate a widget
    session. Here we build the URL structure that the frontend will
    redirect to.

    Returns:
        TerraAuthResult with the auth_url, state token, and provider.
    """
    state = secrets.token_urlsafe(32)

    if terra_api_key:
        auth_url = (
            f"{TERRA_BASE_URL}/auth/generateWidgetSession"
            f"?provider={provider}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
        )
    else:
        # Fallback for development / testing without a real Terra key
        auth_url = (
            f"https://widget.tryterra.co/session/connect"
            f"?provider={provider}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
        )

    return TerraAuthResult(auth_url=auth_url, state=state, provider=provider)


def exchange_terra_token(
    code: str,
    terra_api_key: str,
    terra_dev_id: str,
    client: object | None = None,
) -> TerraTokens:
    """Exchange an OAuth authorization code for Terra tokens.

    In production, calls the Terra API. In development / testing mode,
    returns mock tokens.
    """
    if client and terra_api_key:
        try:
            resp = client.post(
                f"{TERRA_BASE_URL}/auth/authenticateUser",
                headers={
                    "x-api-key": terra_api_key,
                    "dev-id": terra_dev_id,
                },
                json={"code": code},
            )
            resp.raise_for_status()
            data = resp.json()
            return TerraTokens(
                terra_user_id=data.get("user", {}).get("user_id", ""),
                access_token=data.get("user", {}).get("access_token", ""),
                refresh_token=data.get("user", {}).get("refresh_token", ""),
                scopes="activity,sleep,heart_rate",
            )
        except Exception:
            logger.exception("Failed to exchange Terra token")
            raise

    # Development fallback: generate mock tokens
    return TerraTokens(
        terra_user_id=f"terra_mock_{secrets.token_hex(8)}",
        access_token=f"mock_access_{secrets.token_hex(16)}",
        refresh_token=f"mock_refresh_{secrets.token_hex(16)}",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        scopes="activity,sleep,heart_rate",
    )


def refresh_terra_token(
    refresh_token: str,
    terra_api_key: str,
    terra_dev_id: str,
    client: object | None = None,
) -> TerraTokens | None:
    """Refresh an expired Terra access token.

    Returns new tokens on success, None on failure.
    """
    if not client or not terra_api_key:
        return None

    try:
        resp = client.post(
            f"{TERRA_BASE_URL}/auth/refreshToken",
            headers={
                "x-api-key": terra_api_key,
                "dev-id": terra_dev_id,
            },
            json={"refresh_token": refresh_token},
        )
        resp.raise_for_status()
        data = resp.json()
        return TerraTokens(
            terra_user_id=data.get("user", {}).get("user_id", ""),
            access_token=data.get("user", {}).get("access_token", ""),
            refresh_token=data.get("user", {}).get("refresh_token", refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
    except Exception:
        logger.exception("Failed to refresh Terra token")
        return None


def revoke_terra_connection(
    terra_user_id: str,
    terra_api_key: str,
    terra_dev_id: str,
    client: object | None = None,
) -> bool:
    """Revoke a Terra connection (deauthenticate user)."""
    if not client or not terra_api_key:
        return True  # No real connection to revoke in dev mode

    try:
        resp = client.delete(
            f"{TERRA_BASE_URL}/auth/deauthenticateUser",
            headers={
                "x-api-key": terra_api_key,
                "dev-id": terra_dev_id,
            },
            json={"user_id": terra_user_id},
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception("Failed to revoke Terra connection for %s", terra_user_id)
        return False


# ── Data pull ────────────────────────────────────────────────────────────────


def pull_terra_data(
    terra_user_id: str,
    data_type: str,
    start_date: date,
    end_date: date,
    terra_api_key: str,
    terra_dev_id: str,
    client: object | None = None,
) -> list[WearableDaySummary]:
    """Pull daily data from Terra for a given user and date range.

    Returns a list of WearableDaySummary with raw data and extracted summaries.
    """
    if not client or not terra_api_key:
        return []

    # Map our data types to Terra API endpoints
    endpoint_map = {
        "activity": "daily",
        "sleep": "sleep",
        "heart_rate": "daily",
        "hrv": "daily",
        "spo2": "daily",
        "stress": "daily",
    }
    endpoint = endpoint_map.get(data_type, "daily")

    try:
        resp = client.get(
            f"{TERRA_BASE_URL}/{endpoint}",
            headers={
                "x-api-key": terra_api_key,
                "dev-id": terra_dev_id,
            },
            params={
                "user_id": terra_user_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.exception(
            "Failed to pull Terra %s data for user %s", data_type, terra_user_id
        )
        return []

    results: list[WearableDaySummary] = []
    for entry in data.get("data", []):
        day_date = _parse_terra_date(entry)
        if not day_date:
            continue

        summary = extract_summary(data_type, entry)
        results.append(WearableDaySummary(
            data_type=data_type,
            date=day_date,
            raw_data=entry,
            summary=summary,
        ))

    return results


def _parse_terra_date(entry: dict) -> date | None:
    """Extract the date from a Terra API data entry."""
    for key in ("metadata", ""):
        container = entry.get(key, entry) if key else entry
        if isinstance(container, dict):
            for date_key in ("start_time", "date", "timestamp"):
                val = container.get(date_key, "")
                if val:
                    try:
                        return date.fromisoformat(str(val)[:10])
                    except (ValueError, TypeError):
                        continue
    return None


# ── Summary extraction ───────────────────────────────────────────────────────


def extract_summary(data_type: str, raw_data: dict) -> dict:
    """Extract a normalised summary dict from raw Terra API data.

    Works with both real Terra payloads and simplified test data.
    """
    extractors = {
        "activity": _extract_activity_summary,
        "sleep": _extract_sleep_summary,
        "heart_rate": _extract_heart_rate_summary,
        "hrv": _extract_hrv_summary,
        "spo2": _extract_spo2_summary,
        "stress": _extract_stress_summary,
    }
    extractor = extractors.get(data_type, lambda d: {})
    return extractor(raw_data)


def _extract_activity_summary(data: dict) -> dict:
    """Extract activity summary from Terra daily data."""
    distance = data.get("distance_data", {})
    calories = data.get("calories_data", {})
    active = data.get("active_durations_data", {})

    # Support both nested Terra format and flat test data
    return {
        "steps": (
            distance.get("steps")
            or data.get("steps")
            or 0
        ),
        "active_minutes": (
            active.get("activity_seconds", 0) // 60
            if active.get("activity_seconds")
            else data.get("active_minutes", 0)
        ),
        "calories_burned": (
            calories.get("total_burned_calories")
            or data.get("calories_burned")
            or 0
        ),
        "distance_km": round(
            (distance.get("distance_meters", 0) or 0) / 1000, 2
        ) or data.get("distance_km", 0),
        "floors_climbed": (
            distance.get("floors_climbed")
            or data.get("floors_climbed")
            or 0
        ),
    }


def _extract_sleep_summary(data: dict) -> dict:
    """Extract sleep summary from Terra sleep data."""
    sleep_data = data.get("sleep_durations_data", {})
    asleep = sleep_data.get("asleep", {})

    total_sec = (
        sleep_data.get("total_sleep_seconds")
        or data.get("total_sleep_seconds")
        or 0
    )

    return {
        "total_sleep_minutes": (
            total_sec // 60
            if total_sec
            else data.get("total_sleep_minutes", 0)
        ),
        "deep_sleep_minutes": (
            (asleep.get("deep_sleep_seconds", 0) or 0) // 60
            or data.get("deep_sleep_minutes", 0)
        ),
        "rem_sleep_minutes": (
            (asleep.get("rem_sleep_seconds", 0) or 0) // 60
            or data.get("rem_sleep_minutes", 0)
        ),
        "light_sleep_minutes": (
            (asleep.get("light_sleep_seconds", 0) or 0) // 60
            or data.get("light_sleep_minutes", 0)
        ),
        "awakenings": (
            sleep_data.get("num_awakenings")
            or data.get("awakenings")
            or 0
        ),
        "sleep_score": data.get("sleep_score", 0),
    }


def _extract_heart_rate_summary(data: dict) -> dict:
    """Extract heart rate summary."""
    hr_data = data.get("heart_rate_data", {})
    summary = hr_data.get("summary", {})

    return {
        "avg_hr_bpm": (
            summary.get("avg_hr_bpm")
            or data.get("avg_hr_bpm")
            or 0
        ),
        "max_hr_bpm": (
            summary.get("max_hr_bpm")
            or data.get("max_hr_bpm")
            or 0
        ),
        "resting_hr_bpm": (
            summary.get("resting_hr_bpm")
            or data.get("resting_hr_bpm")
            or 0
        ),
    }


def _extract_hrv_summary(data: dict) -> dict:
    """Extract HRV summary."""
    hrv_data = data.get("hrv_data", {})
    return {
        "avg_hrv_ms": (
            hrv_data.get("avg_hrv_sdnn")
            or data.get("avg_hrv_ms")
            or 0
        ),
        "max_hrv_ms": hrv_data.get("max_hrv_sdnn") or data.get("max_hrv_ms", 0),
    }


def _extract_spo2_summary(data: dict) -> dict:
    """Extract SpO2 summary."""
    spo2_data = data.get("oxygen_data", {})
    return {
        "avg_spo2_pct": (
            spo2_data.get("avg_saturation_percentage")
            or data.get("avg_spo2_pct")
            or 0
        ),
        "min_spo2_pct": (
            spo2_data.get("min_saturation_percentage")
            or data.get("min_spo2_pct")
            or 0
        ),
    }


def _extract_stress_summary(data: dict) -> dict:
    """Extract stress summary."""
    stress_data = data.get("stress_data", {})
    return {
        "stress_score": (
            stress_data.get("stress_score")
            or data.get("stress_score")
            or 0
        ),
        "rest_stress_minutes": (
            stress_data.get("rest_stress_duration_seconds", 0) // 60
            if stress_data.get("rest_stress_duration_seconds")
            else data.get("rest_stress_minutes", 0)
        ),
        "high_stress_minutes": (
            stress_data.get("high_stress_duration_seconds", 0) // 60
            if stress_data.get("high_stress_duration_seconds")
            else data.get("high_stress_minutes", 0)
        ),
    }


# ── Encrypt/decrypt token helpers ────────────────────────────────────────────


def encrypt_token(token: str, dek: bytes) -> bytes:
    """Encrypt an OAuth token using the user's DEK (AES-256-GCM)."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(12)
    ct = AESGCM(dek).encrypt(nonce, token.encode("utf-8"), None)
    return nonce + ct


def decrypt_token(encrypted: bytes, dek: bytes) -> str:
    """Decrypt an OAuth token using the user's DEK."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = encrypted[:12]
    ct = encrypted[12:]
    return AESGCM(dek).decrypt(nonce, ct, None).decode("utf-8")


# ── Cross-domain correlation engine ─────────────────────────────────────────


def generate_cross_domain_insights(
    wearable_summaries: list[dict],
    user_variants: list[dict] | None = None,
    blood_markers: list[dict] | None = None,
    epigenetic_overlays: list[dict] | None = None,
) -> list[CrossDomainInsight]:
    """Correlate wearable data with genome, blood, and epigenetic data.

    Args:
        wearable_summaries: list of dicts with keys: data_type, summary, date
        user_variants: list of dicts with rsid, gene, genotype, risk_level
        blood_markers: list of dicts with marker_name, value, unit, flag
        epigenetic_overlays: list of genome-epigenetic overlay dicts

    Returns:
        list of CrossDomainInsight objects.
    """
    insights: list[CrossDomainInsight] = []

    # Index wearable summaries by data_type for quick lookup
    wearable_by_type: dict[str, dict] = {}
    for ws in wearable_summaries:
        dt = ws.get("data_type", "")
        if dt and ws.get("summary"):
            wearable_by_type[dt] = ws["summary"]

    if not wearable_by_type:
        return insights

    # 1. Variant ↔ Wearable correlations
    if user_variants:
        rsid_map = {v["rsid"]: v for v in user_variants if v.get("rsid")}

        for rule in _VARIANT_WEARABLE_RULES:
            rsid = rule["rsid"]
            variant = rsid_map.get(rsid)
            if not variant:
                continue

            metric = rule["metric"]
            summary = wearable_by_type.get(metric)
            if not summary:
                continue

            value = summary.get(rule["summary_key"])
            if value is None:
                continue

            # Assess against thresholds
            assessment, recommendation, confidence = _assess_metric(
                value, rule, variant.get("genotype", "")
            )

            body = rule["insight_template"].format(
                genotype=variant.get("genotype", "?"),
                value=value,
                assessment=assessment,
                recommendation=recommendation,
            )

            insights.append(CrossDomainInsight(
                title=f"{rule['gene']} + {metric}: {assessment}",
                body=body,
                confidence=confidence,
                data_sources=[f"genome:{rsid}", f"wearable:{metric}"],
            ))

    # 2. Blood ↔ Wearable correlations
    if blood_markers:
        marker_map = {m["marker_name"]: m for m in blood_markers if m.get("marker_name")}

        for rule in _BLOOD_WEARABLE_RULES:
            marker = marker_map.get(rule["blood_marker"])
            if not marker:
                continue

            metric = rule["metric"]
            summary = wearable_by_type.get(metric)
            if not summary:
                continue

            value = summary.get(rule["summary_key"])
            if value is None:
                continue

            assessment, recommendation, confidence = _assess_blood_wearable(
                value, rule, marker
            )

            body = rule["insight_template"].format(
                blood_value=f"{marker.get('value', '?')} {marker.get('unit', '')}".strip(),
                value=value,
                assessment=assessment,
                recommendation=recommendation,
            )

            insights.append(CrossDomainInsight(
                title=f"{rule['blood_marker']} + {metric}: {assessment}",
                body=body,
                confidence=confidence,
                data_sources=[
                    f"blood:{rule['blood_marker']}",
                    f"wearable:{metric}",
                ],
            ))

    # 3. Wearable-only trend insights (no genome/blood needed)
    activity_summary = wearable_by_type.get("activity", {})
    sleep_summary = wearable_by_type.get("sleep", {})

    steps = activity_summary.get("steps", 0)
    if steps and steps < 5000:
        insights.append(CrossDomainInsight(
            title="Low activity detected",
            body=(
                f"Your step count of {steps} is below the recommended minimum "
                "of 5,000 steps. Consider adding a short walk to your routine."
            ),
            confidence="high",
            insight_type="alert",
            data_sources=["wearable:activity"],
        ))

    total_sleep = sleep_summary.get("total_sleep_minutes", 0)
    if total_sleep and total_sleep < 360:
        insights.append(CrossDomainInsight(
            title="Insufficient sleep detected",
            body=(
                f"Your total sleep of {total_sleep} minutes ({total_sleep / 60:.1f} hours) "
                "is below the recommended 6 hours minimum. Chronic sleep deprivation "
                "affects immune function, cognition, and cardiovascular health."
            ),
            confidence="high",
            insight_type="alert",
            data_sources=["wearable:sleep"],
        ))

    return insights


def _assess_metric(
    value: float,
    rule: dict,
    genotype: str,
) -> tuple[str, str, str]:
    """Assess a wearable metric against rule thresholds.

    Returns: (assessment, recommendation, confidence)
    """
    threshold_low = rule.get("threshold_low")
    threshold_high = rule.get("threshold_high")

    if threshold_low is not None and value < threshold_low:
        return (
            "below optimal",
            f"Consider increasing your {rule['metric']} to support your {rule['gene']} genotype.",
            "medium",
        )
    elif threshold_high is not None and value > threshold_high:
        return (
            "elevated",
            f"Monitor your {rule['metric']} levels given your {rule['gene']} genotype.",
            "medium",
        )
    else:
        return (
            "within a healthy range",
            "Keep up your current routine.",
            "high",
        )


def _assess_blood_wearable(
    value: float,
    rule: dict,
    marker: dict,
) -> tuple[str, str, str]:
    """Assess a blood-wearable correlation.

    Returns: (assessment, recommendation, confidence)
    """
    threshold_low = rule.get("threshold_low")
    threshold_high = rule.get("threshold_high")
    flag = marker.get("flag", "N")

    if threshold_low is not None and value < threshold_low:
        assessment = "a need for more activity"
        recommendation = (
            "Increasing physical activity may help improve this blood marker."
        )
        confidence = "medium" if flag in ("H", "L") else "low"
    elif threshold_high is not None and value > threshold_high:
        assessment = "potential cardiovascular strain"
        recommendation = (
            "Consider discussing this pattern with your healthcare provider."
        )
        confidence = "medium"
    else:
        assessment = "a positive correlation"
        recommendation = "Your activity levels are supporting your health markers well."
        confidence = "high" if flag == "N" else "medium"

    return assessment, recommendation, confidence


# ── Template-based daily report ──────────────────────────────────────────────


def generate_daily_report(
    insights: list[CrossDomainInsight],
    wearable_summaries: list[dict],
    report_date: date | None = None,
    openai_api_key: str = "",
) -> str:
    """Generate a natural-language daily report combining all insights.

    Falls back to a template when no OpenAI key is available.
    """
    if report_date is None:
        report_date = date.today()

    # Build template report
    lines: list[str] = []
    lines.append(f"# Daily Health Report — {report_date.isoformat()}")
    lines.append("")

    # Wearable summaries section
    lines.append("## Today's Metrics")
    for ws in wearable_summaries:
        dt = ws.get("data_type", "unknown")
        summary = ws.get("summary", {})
        if not summary:
            continue
        lines.append(f"\n### {dt.replace('_', ' ').title()}")
        for key, val in summary.items():
            label = key.replace("_", " ").title()
            lines.append(f"- {label}: {val}")

    # Insights section
    if insights:
        lines.append("\n## Personalised Insights")
        for i, insight in enumerate(insights, 1):
            emoji_marker = ""
            if insight.insight_type == "alert":
                emoji_marker = "[ALERT] "
            lines.append(f"\n### {emoji_marker}{insight.title}")
            lines.append(insight.body)
            lines.append(f"*Confidence: {insight.confidence}*")
            if insight.data_sources:
                lines.append(f"*Sources: {', '.join(insight.data_sources)}*")
    else:
        lines.append("\n## Insights")
        lines.append("No cross-domain insights available today. Connect more "
                      "data sources for personalised health insights.")

    lines.append("\n---")
    lines.append(
        "*Disclaimer: This report is for informational purposes only and "
        "is NOT medical advice. Wearable data accuracy varies by device. "
        "Correlations between wearable metrics and genetic/blood data are "
        "observational and should not be used for clinical decisions. "
        "Consult a healthcare professional for medical guidance.*"
    )

    return "\n".join(lines)
