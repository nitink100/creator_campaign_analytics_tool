from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.enums import CreatorSortFieldEnum, SortDirectionEnum
from app.schemas.common import PaginatedResponse, TimestampedSchema


class CreatorListQuery(BaseModel):
    user_id: str | None = None  # when set, only creators this user tracks
    creator_name: str | None = None
    platform: str | None = None

    min_subscriber_count: int | None = Field(default=None, ge=0)
    max_subscriber_count: int | None = Field(default=None, ge=0)

    min_channel_view_count: int | None = Field(default=None, ge=0)
    max_channel_view_count: int | None = Field(default=None, ge=0)

    min_video_count: int | None = Field(default=None, ge=0)
    max_video_count: int | None = Field(default=None, ge=0)

    sort_by: CreatorSortFieldEnum = CreatorSortFieldEnum.SUBSCRIBER_COUNT
    sort_direction: SortDirectionEnum = SortDirectionEnum.DESC

    limit: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    offset: int = Field(default=0, ge=0)


class CreatorListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    creator_id: str
    platform_creator_id: str
    creator_name: str
    creator_handle: str | None = None
    channel_url: str | None = None
    thumbnail_url: str | None = None

    subscriber_count: int | None = None
    channel_view_count: int | None = None
    video_count: int | None = None

    latest_avg_engagement_rate: float | None = None
    latest_total_views: int | None = None
    total_content_items: int | None = None


class CreatorDetail(TimestampedSchema):
    model_config = ConfigDict(from_attributes=True)

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

    last_ingested_run_id: str | None = None
    ingested_at: datetime | None = None


class PaginatedCreatorResponse(PaginatedResponse[CreatorListItem]):
    pass