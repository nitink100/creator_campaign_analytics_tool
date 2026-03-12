from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class NormalizedCreatorRecord:
    platform: str
    source_type: str
    platform_creator_id: str
    creator_name: str
    creator_handle: str | None = None
    channel_url: str | None = None
    creator_description: str | None = None
    country_code: str | None = None
    created_at_platform: datetime | None = None
    subscriber_count: int | None = None
    channel_view_count: int | None = None
    video_count: int | None = None
    uploads_playlist_id: str | None = None
    thumbnail_url: str | None = None
    extra_metrics: dict | None = None
    raw_payload: dict | None = None
    ingested_at: datetime | None = None


@dataclass(slots=True)
class NormalizedContentRecord:
    platform: str
    platform_creator_id: str
    platform_content_id: str
    content_type: str
    title: str
    description: str | None = None
    published_at: datetime | None = None
    content_url: str | None = None
    category_id: str | None = None
    channel_title_snapshot: str | None = None
    thumbnail_url: str | None = None
    tags_json: list | None = None
    extra_metrics: dict | None = None
    raw_payload: dict | None = None
    ingested_at: datetime | None = None


@dataclass(slots=True)
class NormalizedMetricRecord:
    platform_content_id: str
    captured_at: datetime
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    engagement_rate: float | None = None
    extra_metrics: dict | None = None
    raw_payload: dict | None = None


@dataclass(slots=True)
class NormalizedIngestionPayload:
    creators: list[NormalizedCreatorRecord] = field(default_factory=list)
    content_items: list[NormalizedContentRecord] = field(default_factory=list)
    metric_snapshots: list[NormalizedMetricRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    records_seen: int = 0