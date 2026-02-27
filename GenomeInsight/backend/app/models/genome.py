import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class GenomeUpload(db.Model):
    __tablename__ = "genome_uploads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    filename_original: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_service: Mapped[str | None] = mapped_column(String(50))
    genome_build: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    file_size_bytes: Mapped[int] = mapped_column(nullable=False)

    # Relationships
    user = relationship("User", back_populates="genome_uploads")
    analysis = relationship(
        "GenomeAnalysis",
        back_populates="upload",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<GenomeUpload {self.id} status={self.status}>"


class GenomeAnalysis(db.Model):
    __tablename__ = "genome_analyses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    upload_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("genome_uploads.id"), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    variant_count: Mapped[int | None] = mapped_column()
    annotated_variant_count: Mapped[int | None] = mapped_column()
    risk_summary_json: Mapped[str | None] = mapped_column(Text)
    ai_report_text: Mapped[str | None] = mapped_column(Text)
    ai_report_generated_at: Mapped[datetime | None] = mapped_column()
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text)

    # Relationships
    upload = relationship("GenomeUpload", back_populates="analysis")
    variants = relationship(
        "Variant", back_populates="analysis", cascade="all, delete-orphan"
    )
    recommendations = relationship(
        "HealthRecommendation",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<GenomeAnalysis {self.id} status={self.status}>"


class Variant(db.Model):
    __tablename__ = "variants"
    __table_args__ = (
        Index("ix_variants_analysis_rsid", "analysis_id", "rsid"),
        Index("ix_variants_analysis_chrom_pos", "analysis_id", "chromosome", "position"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("genome_analyses.id"), nullable=False
    )
    rsid: Mapped[str | None] = mapped_column(String(20))
    chromosome: Mapped[str] = mapped_column(String(5), nullable=False)
    position: Mapped[int] = mapped_column(nullable=False)
    ref_allele: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_allele: Mapped[str] = mapped_column(String(500), nullable=False)
    genotype: Mapped[str] = mapped_column(String(10), nullable=False)
    quality: Mapped[float | None] = mapped_column()

    # Relationships
    analysis = relationship("GenomeAnalysis", back_populates="variants")
    annotations = relationship(
        "VariantAnnotation",
        back_populates="variant",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Variant {self.rsid or self.chromosome}:{self.position}>"


class VariantAnnotation(db.Model):
    __tablename__ = "variant_annotations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    variant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("variants.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    gene_symbol: Mapped[str | None] = mapped_column(String(50))
    consequence: Mapped[str | None] = mapped_column(String(100))
    clinical_significance: Mapped[str | None] = mapped_column(String(100))
    condition_name: Mapped[str | None] = mapped_column(String(500))
    trait_association: Mapped[str | None] = mapped_column(Text)
    risk_allele: Mapped[str | None] = mapped_column(String(20))
    odds_ratio: Mapped[float | None] = mapped_column()
    p_value: Mapped[float | None] = mapped_column()
    pubmed_ids: Mapped[str | None] = mapped_column(Text)
    source_record_id: Mapped[str | None] = mapped_column(String(100))
    retrieved_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    variant = relationship("Variant", back_populates="annotations")

    def __repr__(self) -> str:
        return f"<VariantAnnotation {self.source}:{self.variant_id}>"


class HealthRecommendation(db.Model):
    __tablename__ = "health_recommendations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("genome_analyses.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_rsids: Mapped[str | None] = mapped_column(Text)
    evidence_sources: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    priority: Mapped[int] = mapped_column(nullable=False)

    # Relationships
    analysis = relationship("GenomeAnalysis", back_populates="recommendations")

    def __repr__(self) -> str:
        return f"<HealthRecommendation {self.category}: {self.title}>"
