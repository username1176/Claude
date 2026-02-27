import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class BloodUpload(db.Model):
    __tablename__ = "blood_uploads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    filename_original: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    test_date: Mapped[date] = mapped_column(Date, nullable=False)
    lab_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="blood_uploads")
    results = relationship(
        "BloodResult", back_populates="upload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<BloodUpload {self.id} date={self.test_date}>"


class BloodResult(db.Model):
    __tablename__ = "blood_results"
    __table_args__ = (
        Index("ix_blood_results_marker", "upload_id", "marker_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    upload_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("blood_uploads.id"), nullable=False
    )
    marker_name: Mapped[str] = mapped_column(String(100), nullable=False)
    marker_display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    reference_low: Mapped[float | None] = mapped_column()
    reference_high: Mapped[float | None] = mapped_column()
    flag: Mapped[str | None] = mapped_column(String(5))

    # Relationships
    upload = relationship("BloodUpload", back_populates="results")

    def __repr__(self) -> str:
        return f"<BloodResult {self.marker_display_name}={self.value} {self.unit}>"
