import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class EpigeneticUpload(db.Model):
    """Represents an uploaded epigenetic data file (BED or CSV)."""

    __tablename__ = "epigenetic_uploads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    filename_original: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # bed / csv
    data_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # histone / methylation
    assay_type: Mapped[str | None] = mapped_column(
        String(50)
    )  # H3K27ac, WGBS, 450K, EPIC, …
    tissue_type: Mapped[str | None] = mapped_column(String(100))  # blood, saliva, …
    metrics_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uploaded"
    )  # uploaded / parsing / analyzing / complete / error
    uploaded_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    file_size_bytes: Mapped[int] = mapped_column(nullable=False)

    # Relationships
    user = relationship("User", back_populates="epigenetic_uploads")
    analysis = relationship(
        "EpigeneticAnalysis",
        back_populates="upload",
        uselist=False,
        cascade="all, delete-orphan",
    )
    regions = relationship(
        "EpigeneticRegion",
        back_populates="upload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<EpigeneticUpload {self.id} type={self.data_type} status={self.status}>"


class EpigeneticAnalysis(db.Model):
    """Analysis results derived from an epigenetic upload."""

    __tablename__ = "epigenetic_analyses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    upload_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("epigenetic_uploads.id"),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued"
    )  # queued / running / complete / error
    region_count: Mapped[int | None] = mapped_column()
    annotated_region_count: Mapped[int | None] = mapped_column()
    global_methylation_avg: Mapped[float | None] = mapped_column()
    insights_json: Mapped[str | None] = mapped_column(Text)
    genome_overlay_json: Mapped[str | None] = mapped_column(Text)
    ai_summary_text: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text)

    # Relationships
    upload = relationship("EpigeneticUpload", back_populates="analysis")

    def __repr__(self) -> str:
        return f"<EpigeneticAnalysis {self.id} status={self.status}>"


class EpigeneticRegion(db.Model):
    """A parsed genomic region from an epigenetic data file."""

    __tablename__ = "epigenetic_regions"
    __table_args__ = (
        Index(
            "ix_epigenetic_regions_coords",
            "upload_id",
            "chromosome",
            "start_pos",
            "end_pos",
        ),
        Index("ix_epigenetic_regions_gene", "nearest_gene"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    upload_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("epigenetic_uploads.id"), nullable=False
    )
    chromosome: Mapped[str] = mapped_column(String(5), nullable=False)
    start_pos: Mapped[int] = mapped_column(nullable=False)
    end_pos: Mapped[int] = mapped_column(nullable=False)
    feature_type: Mapped[str | None] = mapped_column(
        String(20)
    )  # promoter / enhancer / insulator / gene_body / intergenic
    nearest_gene: Mapped[str | None] = mapped_column(String(50))
    methylation_beta: Mapped[float | None] = mapped_column()  # 0.0 – 1.0
    histone_mark: Mapped[str | None] = mapped_column(String(20))  # H3K27ac, H3K4me3
    signal_value: Mapped[float | None] = mapped_column()
    encode_overlap_json: Mapped[str | None] = mapped_column(Text)
    roadmap_overlap_json: Mapped[str | None] = mapped_column(Text)
    interpretation: Mapped[str | None] = mapped_column(Text)

    # Relationships
    upload = relationship("EpigeneticUpload", back_populates="regions")

    def __repr__(self) -> str:
        return f"<EpigeneticRegion {self.chromosome}:{self.start_pos}-{self.end_pos}>"
