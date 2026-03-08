"""Stripe subscription and membership models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Subscription(db.Model):
    """User subscription managed via Stripe.

    Tiers:
      - free: limited uploads, no AI chatbot, no predictions
      - basic: more uploads, biomarker zones
      - premium: unlimited uploads, AI chatbot, predictions, healthspan reports
    """

    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscription_user", "user_id"),
        Index("ix_subscription_stripe_sub", "stripe_subscription_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, nullable=False
    )

    # Stripe identifiers
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    stripe_price_id: Mapped[str | None] = mapped_column(String(255))

    # Tier: free | basic | premium
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")

    # Stripe subscription status: active | past_due | canceled | trialing | incomplete
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")

    current_period_start: Mapped[datetime | None] = mapped_column()
    current_period_end: Mapped[datetime | None] = mapped_column()
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="subscription")

    @property
    def is_active(self) -> bool:
        return self.status in ("active", "trialing")

    @property
    def is_premium(self) -> bool:
        return self.tier == "premium" and self.is_active

    @property
    def is_basic_or_above(self) -> bool:
        return self.tier in ("basic", "premium") and self.is_active

    def __repr__(self) -> str:
        return f"<Subscription user={self.user_id} tier={self.tier} status={self.status}>"


class ChatMessage(db.Model):
    """Stores AI chatbot conversation messages for context and audit."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_user_session", "user_id", "session_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(36), nullable=False)

    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)

    tokens_used: Mapped[int | None] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="chat_messages")

    def __repr__(self) -> str:
        return f"<ChatMessage role={self.role} user={self.user_id}>"
