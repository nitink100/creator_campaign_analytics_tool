from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import APIResponse


class KPICard(BaseModel):
    label: str
    value: int | float | str | None
    subtitle: str | None = None


class PlatformBreakdownItem(BaseModel):
    platform: str
    creator_count: int
    content_count: int
    avg_engagement_rate: float | None = None
    total_views: int | None = None


class TopContentItem(BaseModel):
    content_id: str
    title: str
    creator_name: str
    content_url: str | None = None
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    engagement_rate: float | None = None
    published_at: datetime | None = None


class TopCreatorItem(BaseModel):
    creator_id: str
    creator_name: str
    channel_url: str | None = None
    thumbnail_url: str | None = None
    subscriber_count: int | None = None
    latest_avg_engagement_rate: float | None = None
    latest_total_views: int | None = None
    total_content_items: int | None = None


class AnalyticsSummary(BaseModel):
    total_creators: int
    total_content_items: int
    total_metric_snapshots: int
    avg_engagement_rate: float | None = None
    total_views: int | None = None
    top_creator_name: str | None = None
    top_content_title: str | None = None
    platform_breakdown: list[PlatformBreakdownItem]


class AnalyticsSummaryResponse(APIResponse):
    data: AnalyticsSummary


class TopContentResponse(APIResponse):
    items: list[TopContentItem]


class TopCreatorsResponse(APIResponse):
    items: list[TopCreatorItem]


class PlatformBreakdownResponse(APIResponse):
    items: list[PlatformBreakdownItem]


class DashboardKPIResponse(APIResponse):
    items: list[KPICard]