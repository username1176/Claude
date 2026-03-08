"""InsideTracker-inspired healthspan and biological age models."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class InnerAgeResult(db.Model):
    """Biological age calculation result (InsideTracker InnerAge-inspired).

    Combines blood biomarkers, DNA methylation, and optionally wearable
    metrics to compute a biological age distinct from chronological age.
    """

    __tablename__ = "innerage_results"
    __table_args__ = (
        Index("ix_innerage_user_date", "user_id", "calculated_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    chronological_age: Mapped[float] = mapped_column(Float, nullable=False)
    biological_age: Mapped[float] = mapped_column(Float, nullable=False)
    age_delta: Mapped[float] = mapped_column(Float, nullable=False)  # bio - chrono

    # Model used: horvath | phenoage | grimace | ensemble
    model_type: Mapped[str] = mapped_column(String(20), nullable=False, default="ensemble")

    # Component scores (JSON)
    blood_score: Mapped[float | None] = mapped_column(Float)
    epigenetic_score: Mapped[float | None] = mapped_column(Float)
    wearable_score: Mapped[float | None] = mapped_column(Float)

    # Input biomarker values used (JSON dict)
    input_biomarkers_json: Mapped[str | None] = mapped_column(Text)

    # Detailed breakdown (JSON: per-biomarker contributions)
    breakdown_json: Mapped[str | None] = mapped_column(Text)

    # Confidence interval
    confidence_low: Mapped[float | None] = mapped_column(Float)
    confidence_high: Mapped[float | None] = mapped_column(Float)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="complete"
    )
    calculated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="innerage_results")

    def __repr__(self) -> str:
        return (
            f"<InnerAgeResult bio={self.biological_age:.1f} "
            f"chrono={self.chronological_age:.1f} delta={self.age_delta:+.1f}>"
        )


class BiomarkerZone(db.Model):
    """Personalized optimal zone for a biomarker (InsideTracker OptimizedZones).

    Zones are computed per-user based on age, sex, genetics, and lifestyle
    factors using statistical models (population percentiles + genetic
    modifiers).
    """

    __tablename__ = "biomarker_zones"
    __table_args__ = (
        Index("ix_biomarker_zone_user_marker", "user_id", "marker_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    marker_name: Mapped[str] = mapped_column(String(100), nullable=False)
    marker_display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)

    # Standard lab reference range
    lab_ref_low: Mapped[float | None] = mapped_column(Float)
    lab_ref_high: Mapped[float | None] = mapped_column(Float)

    # Personalized optimized zone
    optimal_low: Mapped[float] = mapped_column(Float, nullable=False)
    optimal_high: Mapped[float] = mapped_column(Float, nullable=False)

    # Current value and status
    current_value: Mapped[float | None] = mapped_column(Float)
    zone_status: Mapped[str | None] = mapped_column(
        String(20)
    )  # optimal | at_risk | out_of_range

    # Factors used to compute zone (JSON)
    factors_json: Mapped[str | None] = mapped_column(Text)

    # Actionable recommendation
    recommendation: Mapped[str | None] = mapped_column(Text)

    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="biomarker_zones")

    def __repr__(self) -> str:
        return (
            f"<BiomarkerZone {self.marker_display_name} "
            f"[{self.optimal_low}-{self.optimal_high}] {self.unit}>"
        )


class BiomarkerPrediction(db.Model):
    """Time-series forecast for a biomarker (e.g., cholesterol over 6 months).

    Uses Prophet / ARIMA on historical blood + wearable data to predict
    future biomarker trajectories and flag potential out-of-range events.
    """

    __tablename__ = "biomarker_predictions"
    __table_args__ = (
        Index("ix_prediction_user_marker", "user_id", "marker_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    marker_name: Mapped[str] = mapped_column(String(100), nullable=False)
    marker_display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Model used: prophet | arima | linear
    model_type: Mapped[str] = mapped_column(String(20), nullable=False, default="prophet")

    # Forecast horizon in days
    horizon_days: Mapped[int] = mapped_column(nullable=False, default=180)

    # Forecast data (JSON array of {date, value, lower, upper})
    forecast_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Trend direction: improving | stable | declining
    trend_direction: Mapped[str | None] = mapped_column(String(20))

    # Predicted time to cross optimal zone boundary (days, null if stable)
    days_to_out_of_range: Mapped[int | None] = mapped_column()

    # Model quality metrics
    mae: Mapped[float | None] = mapped_column(Float)
    mape: Mapped[float | None] = mapped_column(Float)

    # Historical data points used
    data_points_used: Mapped[int | None] = mapped_column()

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="complete"
    )
    generated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="biomarker_predictions")

    def __repr__(self) -> str:
        return (
            f"<BiomarkerPrediction {self.marker_display_name} "
            f"trend={self.trend_direction}>"
        )


class HealthspanReport(db.Model):
    """Weekly/monthly healthspan report aggregating wearable + biomarker data.

    Mirrors InsideTracker's dashboard: actionable habits, sleep-microbiome
    connections, exercise-inflammation correlations, etc.
    """

    __tablename__ = "healthspan_reports"
    __table_args__ = (
        Index("ix_healthspan_user_period", "user_id", "period_start"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="weekly"
    )  # weekly | monthly

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Aggregate scores (0-100)
    overall_score: Mapped[float | None] = mapped_column(Float)
    sleep_score: Mapped[float | None] = mapped_column(Float)
    activity_score: Mapped[float | None] = mapped_column(Float)
    nutrition_score: Mapped[float | None] = mapped_column(Float)
    stress_score: Mapped[float | None] = mapped_column(Float)

    # InnerAge at report time
    innerage_snapshot: Mapped[float | None] = mapped_column(Float)

    # Habit correlations (JSON: [{habit, metric, correlation, insight}])
    habit_correlations_json: Mapped[str | None] = mapped_column(Text)

    # Top recommendations (JSON: [{title, body, category, priority}])
    recommendations_json: Mapped[str | None] = mapped_column(Text)

    # Full report body (JSON with all sections)
    report_json: Mapped[str | None] = mapped_column(Text)

    generated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="healthspan_reports")

    def __repr__(self) -> str:
        return (
            f"<HealthspanReport {self.report_type} "
            f"{self.period_start}–{self.period_end} score={self.overall_score}>"
        )
