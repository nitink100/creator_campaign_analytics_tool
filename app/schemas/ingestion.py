from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import (
    IngestionStatusEnum,
    IngestionTriggerEnum,
    PlatformEnum,
    SourceTypeEnum,
)
from app.schemas.common import APIResponse, TimestampedSchema


class IngestionRunRequest(BaseModel):
    platform: PlatformEnum = PlatformEnum.YOUTUBE
    source_type: SourceTypeEnum = SourceTypeEnum.API
    trigger_type: IngestionTriggerEnum = IngestionTriggerEnum.MANUAL
    channel_ids: list[str] | None = None
    user_id: str | None = None  # when set, sync only this user's tracked channels


class IngestionRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    platform: str
    source_type: str
    trigger_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    records_seen: int = 0
    creators_inserted: int = 0
    creators_updated: int = 0
    content_inserted: int = 0
    content_updated: int = 0
    metrics_inserted: int = 0
    metrics_updated: int = 0
    records_skipped: int = 0
    warnings_count: int = 0
    errors_count: int = 0
    error_summary: str | None = None
    duration_ms: int | None = None


class IngestionRunRead(TimestampedSchema):
    model_config = ConfigDict(from_attributes=True)

    platform: str
    source_type: str
    trigger_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    records_seen: int
    creators_inserted: int
    creators_updated: int
    content_inserted: int
    content_updated: int
    metrics_inserted: int
    metrics_updated: int
    records_skipped: int
    warnings_count: int
    errors_count: int
    error_summary: str | None = None
    config_snapshot: dict | None = None
    duration_ms: int | None = None


class IngestionRunResponse(APIResponse):
    data: IngestionRunRead


class IngestionRunDetailResponse(APIResponse):
    data: IngestionRunRead


class IngestionRunsListResponse(APIResponse):
    items: list[IngestionRunRead]


class IngestionStatusUpdate(BaseModel):
    status: IngestionStatusEnum
    error_summary: str | None = None
    finished_at: datetime | None = None