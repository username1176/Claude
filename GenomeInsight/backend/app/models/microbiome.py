"""Microbiome upload, analysis, and taxon models."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class MicrobiomeUpload(db.Model):
    """Represents an uploaded microbiome data file (BIOM, OTU CSV/TSV, FASTQ)."""

    __tablename__ = "microbiome_uploads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    filename_original: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # biom / csv / tsv / fastq
    data_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # 16s_rrna / shotgun / its / wgs
    sample_source: Mapped[str | None] = mapped_column(
        String(50)
    )  # gut / oral / skin / vaginal / environmental
    collection_date: Mapped[date | None] = mapped_column(Date)
    sequencing_platform: Mapped[str | None] = mapped_column(
        String(50)
    )  # illumina / nanopore / pacbio
    metrics_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uploaded"
    )  # uploaded / parsing / analyzing / complete / error
    uploaded_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    file_size_bytes: Mapped[int] = mapped_column(nullable=False)

    # Relationships
    user = relationship("User", back_populates="microbiome_uploads")
    analysis = relationship(
        "MicrobiomeAnalysis",
        back_populates="upload",
        uselist=False,
        cascade="all, delete-orphan",
    )
    taxa = relationship(
        "MicrobiomeTaxon",
        back_populates="upload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<MicrobiomeUpload {self.id} type={self.data_type} status={self.status}>"


class MicrobiomeAnalysis(db.Model):
    """Analysis results derived from a microbiome upload."""

    __tablename__ = "microbiome_analyses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    upload_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("microbiome_uploads.id"),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued"
    )  # queued / running / complete / error
    total_read_count: Mapped[int | None] = mapped_column()
    classified_read_count: Mapped[int | None] = mapped_column()
    taxonomy_level_counts_json: Mapped[str | None] = mapped_column(
        Text
    )  # {"phylum": 12, "genus": 85}
    composition_json: Mapped[str | None] = mapped_column(
        Text
    )  # Top-N taxa at each level
    diversity_json: Mapped[str | None] = mapped_column(
        Text
    )  # {"shannon": 3.2, "simpson": 0.89, "chao1": 245}
    enterotype: Mapped[str | None] = mapped_column(
        String(30)
    )  # Bacteroides / Prevotella / Ruminococcus
    health_insights_json: Mapped[str | None] = mapped_column(Text)
    genome_correlation_json: Mapped[str | None] = mapped_column(Text)
    blood_correlation_json: Mapped[str | None] = mapped_column(Text)
    lifestyle_recs_json: Mapped[str | None] = mapped_column(Text)
    ai_summary_text: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text)

    # Relationships
    upload = relationship("MicrobiomeUpload", back_populates="analysis")

    def __repr__(self) -> str:
        return f"<MicrobiomeAnalysis {self.id} status={self.status}>"


class MicrobiomeTaxon(db.Model):
    """A single taxon record parsed from a microbiome data file."""

    __tablename__ = "microbiome_taxa"
    __table_args__ = (
        Index("ix_microbiome_taxa_upload_level", "upload_id", "taxonomy_level"),
        Index(
            "ix_microbiome_taxa_abundance",
            "upload_id",
            "relative_abundance",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    upload_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("microbiome_uploads.id"), nullable=False
    )
    taxonomy_level: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # phylum / class / order / family / genus / species
    taxonomy_name: Mapped[str] = mapped_column(String(200), nullable=False)
    taxonomy_id: Mapped[str | None] = mapped_column(String(50))  # NCBI taxid
    relative_abundance: Mapped[float] = mapped_column(nullable=False)  # 0.0 – 1.0
    absolute_count: Mapped[int | None] = mapped_column()
    confidence: Mapped[float | None] = mapped_column()  # 0.0 – 1.0
    parent_taxon: Mapped[str | None] = mapped_column(String(200))

    # Relationships
    upload = relationship("MicrobiomeUpload", back_populates="taxa")

    def __repr__(self) -> str:
        return f"<MicrobiomeTaxon {self.taxonomy_level}:{self.taxonomy_name} ({self.relative_abundance:.3f})>"
