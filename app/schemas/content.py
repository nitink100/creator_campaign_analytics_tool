from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.enums import ContentSortFieldEnum, SortDirectionEnum
from app.schemas.common import PaginatedResponse, TimestampedSchema


class ContentListQuery(BaseModel):
    user_id: str | None = None  # when set, only content from creators this user tracks
    creator_name: str | None = None

    published_after: datetime | None = None
    published_before: datetime | None = None

    min_subscriber_count: int | None = Field(default=None, ge=0)
    max_subscriber_count: int | None = Field(default=None, ge=0)

    min_views: int | None = Field(default=None, ge=0)
    max_views: int | None = Field(default=None, ge=0)

    min_likes: int | None = Field(default=None, ge=0)
    max_likes: int | None = Field(default=None, ge=0)

    min_comments: int | None = Field(default=None, ge=0)
    max_comments: int | None = Field(default=None, ge=0)

    min_engagement_rate: float | None = Field(default=None, ge=0)
    max_engagement_rate: float | None = Field(default=None, ge=0)

    sort_by: ContentSortFieldEnum = ContentSortFieldEnum.PUBLISHED_AT
    sort_direction: SortDirectionEnum = SortDirectionEnum.DESC

    limit: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    offset: int = Field(default=0, ge=0)


class ContentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    content_id: str
    platform_content_id: str
    creator_id: str
    creator_name: str
    subscriber_count: int | None = None

    title: str
    published_at: datetime | None = None
    content_url: str | None = None
    category_id: str | None = None
    thumbnail_url: str | None = None

    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    engagement_rate: float | None = None


class ContentDetail(TimestampedSchema):
    model_config = ConfigDict(from_attributes=True)

    platform: str
    creator_profile_id: str
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

    last_ingested_run_id: str | None = None
    ingested_at: datetime | None = None


class PaginatedContentResponse(PaginatedResponse[ContentListItem]):
    pass