from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import PlatformEnum, SourceTypeEnum
from app.db.base import Base, BaseModelMixin


class CreatorProfile(BaseModelMixin, Base):
    __tablename__ = "creator_profiles"
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "platform_creator_id",
            name="uq_creator_profiles_platform_creator_id",
        ),
        Index("ix_creator_profiles_creator_name", "creator_name"),
        Index("ix_creator_profiles_subscriber_count", "subscriber_count"),
        Index("ix_creator_profiles_channel_view_count", "channel_view_count"),
        Index("ix_creator_profiles_video_count", "video_count"),
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

    platform_creator_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    creator_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    creator_handle: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    channel_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    creator_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    country_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    is_tracked: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )
    created_at_platform: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    subscriber_count: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    channel_view_count: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    video_count: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    uploads_playlist_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    thumbnail_url: Mapped[str | None] = mapped_column(
        Text,
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

    last_ingested_run_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
    ingested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def creator_id(self) -> str:
        return self.id

    @property
    def latest_avg_engagement_rate(self) -> float | None:
        return getattr(self, "_latest_avg_engagement_rate", None)

    @property
    def latest_total_views(self) -> int | None:
        return getattr(self, "_latest_total_views", None)

    @property
    def total_content_items(self) -> int | None:
        return getattr(self, "_total_content_items", self.video_count)