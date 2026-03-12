from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import APIResponse


class FilterConfigGroup(BaseModel):
    content: list[str]
    creator: list[str]


class SortConfigGroup(BaseModel):
    content: list[str]
    creator: list[str]


class IngestionCaps(BaseModel):
    max_channels_per_run: int
    max_videos_per_channel: int


class PlatformConfigItem(BaseModel):
    enabled_sources: list[str]
    default_source: str
    supported_filters: FilterConfigGroup
    supported_sort_fields: SortConfigGroup
    display_only_extra_fields: list[str]
    ingestion_caps: IngestionCaps


class PlatformsResponse(APIResponse):
    items: list[str]


class PlatformFilterConfigResponse(APIResponse):
    data: dict[str, PlatformConfigItem]