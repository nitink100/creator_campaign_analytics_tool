from __future__ import annotations

from app.core.enums import ContentTypeEnum, PlatformEnum, SourceTypeEnum
from app.core.exceptions import ValidationError
from app.services.ingestion.normalizer import (
    NormalizedContentRecord,
    NormalizedCreatorRecord,
    NormalizedMetricRecord,
)
from app.utils.datetime_utils import ensure_utc
from app.utils.math_utils import compute_engagement_rate


def validate_creator_record(record: NormalizedCreatorRecord) -> NormalizedCreatorRecord:
    if not record.platform_creator_id:
        raise ValidationError("creator record is missing platform_creator_id")
    if not record.creator_name:
        raise ValidationError("creator record is missing creator_name")
    if record.platform not in {member.value for member in PlatformEnum}:
        raise ValidationError(f"unsupported platform: {record.platform}")
    if record.source_type not in {member.value for member in SourceTypeEnum}:
        raise ValidationError(f"unsupported source_type: {record.source_type}")

    record.created_at_platform = ensure_utc(record.created_at_platform)
    record.ingested_at = ensure_utc(record.ingested_at)

    # Defensive metrics safety
    if record.subscriber_count is not None and record.subscriber_count < 0:
        record.subscriber_count = 0
    if record.video_count is not None and record.video_count < 0:
        record.video_count = 0
    if record.channel_view_count is not None and record.channel_view_count < 0:
        record.channel_view_count = 0

    return record


def validate_content_record(record: NormalizedContentRecord) -> NormalizedContentRecord:
    if not record.platform_creator_id:
        raise ValidationError("content record is missing platform_creator_id")
    if not record.platform_content_id:
        raise ValidationError("content record is missing platform_content_id")
    if not record.title:
        raise ValidationError("content record is missing title")
    if record.content_type != ContentTypeEnum.VIDEO.value:
        raise ValidationError(f"unsupported content_type: {record.content_type}")

    record.published_at = ensure_utc(record.published_at)
    record.ingested_at = ensure_utc(record.ingested_at)
    return record


def validate_metric_record(record: NormalizedMetricRecord) -> NormalizedMetricRecord:
    if not record.platform_content_id:
        raise ValidationError("metric record is missing platform_content_id")

    record.captured_at = ensure_utc(record.captured_at)
    if record.captured_at is None:
        raise ValidationError("metric record is missing captured_at")

    if record.views is not None and record.views < 0:
        raise ValidationError("metric record has negative views")
    if record.likes is not None and record.likes < 0:
        raise ValidationError("metric record has negative likes")
    if record.comments is not None and record.comments < 0:
        raise ValidationError("metric record has negative comments")

    record.engagement_rate = compute_engagement_rate(
        views=record.views,
        likes=record.likes,
        comments=record.comments,
    )
    return record