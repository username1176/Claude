"""Whole-Genome Sequencing and Ancestry models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class WGSUpload(db.Model):
    """A whole-genome sequencing file upload (FASTQ or BAM)."""

    __tablename__ = "wgs_uploads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    filename_original: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_format: Mapped[str] = mapped_column(
        String(10), nullable=False, default="fastq"
    )  # fastq | bam
    depth: Mapped[float | None] = mapped_column(Float)
    read_count: Mapped[int | None] = mapped_column()
    avg_read_length: Mapped[float | None] = mapped_column(Float)
    avg_quality: Mapped[float | None] = mapped_column(Float)
    genome_build: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uploaded"
    )
    file_size_bytes: Mapped[int] = mapped_column(nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="wgs_uploads")
    ancestry_analysis = relationship(
        "AncestryAnalysis",
        back_populates="wgs_upload",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<WGSUpload {self.id} format={self.file_format} depth={self.depth}>"


class AncestryAnalysis(db.Model):
    """Deep ancestry analysis derived from WGS data."""

    __tablename__ = "ancestry_analyses"
    __table_args__ = (
        Index("ix_ancestry_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    wgs_upload_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wgs_uploads.id")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued"
    )

    # Haplogroup results
    mt_haplogroup: Mapped[str | None] = mapped_column(String(50))
    y_haplogroup: Mapped[str | None] = mapped_column(String(50))

    # Population composition (JSON: {"European": 0.65, "East Asian": 0.20, ...})
    population_composition_json: Mapped[str | None] = mapped_column(Text)

    # Neanderthal / archaic ancestry percentage
    archaic_ancestry_pct: Mapped[float | None] = mapped_column(Float)

    # Full report (JSON with migration paths, historical context, etc.)
    report_json: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text)

    # Relationships
    user = relationship("User", back_populates="ancestry_analyses")
    wgs_upload = relationship("WGSUpload", back_populates="ancestry_analysis")

    def __repr__(self) -> str:
        return f"<AncestryAnalysis {self.id} status={self.status}>"


class BlockchainRecord(db.Model):
    """On-chain record of health data ownership / anonymized data hash."""

    __tablename__ = "blockchain_records"
    __table_args__ = (
        Index("ix_blockchain_user", "user_id"),
        Index("ix_blockchain_tx", "tx_hash"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    data_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # wgs | genome | blood | microbiome | ancestry
    data_hash: Mapped[str] = mapped_column(String(66), nullable=False)  # 0x-prefixed keccak
    tx_hash: Mapped[str | None] = mapped_column(String(66))
    token_id: Mapped[int | None] = mapped_column()
    contract_address: Mapped[str | None] = mapped_column(String(42))
    chain_id: Mapped[int] = mapped_column(nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | confirmed | failed
    metadata_uri: Mapped[str | None] = mapped_column(String(512))  # IPFS CID
    is_listed_for_sale: Mapped[bool] = mapped_column(default=False)
    price_wei: Mapped[str | None] = mapped_column(String(78))  # uint256 as string
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="blockchain_records")

    def __repr__(self) -> str:
        return f"<BlockchainRecord {self.id} tx={self.tx_hash} status={self.status}>"
