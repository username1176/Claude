import uuid
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    tos_accepted_at: Mapped[datetime] = mapped_column(nullable=True)
    data_encryption_key_enc: Mapped[bytes] = mapped_column(
        db.LargeBinary, nullable=False
    )

    # Relationships
    genome_uploads = relationship(
        "GenomeUpload", back_populates="user", cascade="all, delete-orphan"
    )
    blood_uploads = relationship(
        "BloodUpload", back_populates="user", cascade="all, delete-orphan"
    )
    epigenetic_uploads = relationship(
        "EpigeneticUpload", back_populates="user", cascade="all, delete-orphan"
    )
    wearable_connections = relationship(
        "WearableConnection", back_populates="user", cascade="all, delete-orphan"
    )
    daily_wearable_data = relationship(
        "DailyWearableData", back_populates="user", cascade="all, delete-orphan"
    )
    daily_insights = relationship(
        "DailyInsight", back_populates="user", cascade="all, delete-orphan"
    )
    microbiome_uploads = relationship(
        "MicrobiomeUpload", back_populates="user", cascade="all, delete-orphan"
    )
    wgs_uploads = relationship(
        "WGSUpload", back_populates="user", cascade="all, delete-orphan"
    )
    ancestry_analyses = relationship(
        "AncestryAnalysis", back_populates="user", cascade="all, delete-orphan"
    )
    blockchain_records = relationship(
        "BlockchainRecord", back_populates="user", cascade="all, delete-orphan"
    )
    innerage_results = relationship(
        "InnerAgeResult", back_populates="user", cascade="all, delete-orphan"
    )
    biomarker_zones = relationship(
        "BiomarkerZone", back_populates="user", cascade="all, delete-orphan"
    )
    biomarker_predictions = relationship(
        "BiomarkerPrediction", back_populates="user", cascade="all, delete-orphan"
    )
    healthspan_reports = relationship(
        "HealthspanReport", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="user")

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
