from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    IngestionStatusEnum,
    IngestionTriggerEnum,
    PlatformEnum,
    SourceTypeEnum,
)
from app.db.base import Base, BaseModelMixin


class IngestionRun(BaseModelMixin, Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        Index("ix_ingestion_runs_status", "status"),
        Index("ix_ingestion_runs_platform", "platform"),
        Index("ix_ingestion_runs_source_type", "source_type"),
        Index("ix_ingestion_runs_started_at", "started_at"),
    )

    platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PlatformEnum.YOUTUBE.value,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SourceTypeEnum.API.value,
    )
    trigger_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=IngestionTriggerEnum.MANUAL.value,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=IngestionStatusEnum.PENDING.value,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    records_seen: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    creators_inserted: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    creators_updated: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    content_inserted: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    content_updated: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    metrics_inserted: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    metrics_updated: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    records_skipped: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    warnings_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    errors_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    error_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    config_snapshot: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    metric_snapshots = relationship(
        "ContentMetric",
        back_populates="ingestion_run",
    )