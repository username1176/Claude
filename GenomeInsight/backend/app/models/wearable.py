import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class WearableConnection(db.Model):
    """OAuth connection to a wearable data provider (via Terra / ROOK)."""

    __tablename__ = "wearable_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_wearable_user_provider"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # fitbit, garmin, apple_health, oura, whoop, etc.
    terra_user_id: Mapped[str | None] = mapped_column(
        String(100), unique=True
    )  # User ID in Terra/ROOK system
    access_token_enc: Mapped[bytes | None] = mapped_column(
        db.LargeBinary
    )  # AES-encrypted with user DEK
    refresh_token_enc: Mapped[bytes | None] = mapped_column(
        db.LargeBinary
    )  # AES-encrypted with user DEK
    token_expires_at: Mapped[datetime | None] = mapped_column()
    scopes: Mapped[str | None] = mapped_column(Text)  # Comma-separated scopes
    connected_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    last_sync_at: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active / expired / revoked / error

    # Relationships
    user = relationship("User", back_populates="wearable_connections")
    daily_data = relationship(
        "DailyWearableData",
        back_populates="connection",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<WearableConnection {self.provider} user={self.user_id} status={self.status}>"


class DailyWearableData(db.Model):
    """A single day's wearable data point for a specific data type."""

    __tablename__ = "daily_wearable_data"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "date", "data_type",
            name="uq_wearable_user_date_type",
        ),
        Index("ix_daily_wearable_user_date", "user_id", "date"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    connection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wearable_connections.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    data_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # activity, sleep, heart_rate, hrv, spo2, stress
    data_json: Mapped[str] = mapped_column(Text, nullable=False)  # Raw API payload
    summary_json: Mapped[str | None] = mapped_column(Text)  # Computed summaries
    fetched_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="daily_wearable_data")
    connection = relationship("WearableConnection", back_populates="daily_data")

    def __repr__(self) -> str:
        return f"<DailyWearableData {self.data_type} {self.date} user={self.user_id}>"


class DailyInsight(db.Model):
    """Cross-domain daily insight combining genome, epigenetics, blood, and wearable data."""

    __tablename__ = "daily_insights"
    __table_args__ = (
        Index("ix_daily_insight_user_date", "user_id", "date"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    insight_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # daily, weekly, alert
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data_sources_json: Mapped[str | None] = mapped_column(
        Text
    )  # JSON list of source identifiers
    confidence: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium"
    )  # low / medium / high
    generated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="daily_insights")

    def __repr__(self) -> str:
        return f"<DailyInsight {self.insight_type} {self.date} user={self.user_id}>"
