from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ContentTypeEnum, PlatformEnum
from app.db.base import Base, BaseModelMixin


class ContentItem(BaseModelMixin, Base):
    __tablename__ = "content_items"
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "platform_content_id",
            name="uq_content_items_platform_content_id",
        ),
        Index("ix_content_items_creator_profile_id", "creator_profile_id"),
        Index("ix_content_items_published_at", "published_at"),
        Index("ix_content_items_category_id", "category_id"),
    )

    platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PlatformEnum.YOUTUBE.value,
    )
    creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id"),
        nullable=False,
    )

    platform_content_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ContentTypeEnum.VIDEO.value,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    content_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    category_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    channel_title_snapshot: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    thumbnail_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    tags_json: Mapped[list | None] = mapped_column(
        JSON,
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
    )

    creator_profile = relationship("CreatorProfile", backref="content_items")
    metrics = relationship(
        "ContentMetric",
        back_populates="content_item",
        cascade="all, delete-orphan",
    )