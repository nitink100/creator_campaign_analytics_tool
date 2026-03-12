from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BaseModelMixin


class ContentMetric(BaseModelMixin, Base):
    __tablename__ = "content_metrics"
    __table_args__ = (
        UniqueConstraint(
            "content_item_id",
            "captured_at",
            name="uq_content_metrics_content_item_id_captured_at",
        ),
        Index("ix_content_metrics_content_item_id", "content_item_id"),
        Index("ix_content_metrics_views", "views"),
        Index("ix_content_metrics_likes", "likes"),
        Index("ix_content_metrics_comments", "comments"),
        Index("ix_content_metrics_engagement_rate", "engagement_rate"),
    )

    content_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("content_items.id"),
        nullable=False,
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    views: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    likes: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    comments: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    engagement_rate: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    extra_metrics: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    raw_payload: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    ingestion_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_runs.id"),
        nullable=True,
    )

    content_item = relationship("ContentItem", back_populates="metrics")
    ingestion_run = relationship("IngestionRun", back_populates="metric_snapshots")