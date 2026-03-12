from __future__ import annotations

from app.core.exceptions import ValidationError
from app.schemas.content import ContentListQuery
from app.schemas.creator import CreatorListQuery


def _validate_min_max(
    min_value: int | float | None,
    max_value: int | float | None,
    field_name: str,
) -> None:
    if min_value is not None and max_value is not None and min_value > max_value:
        raise ValidationError(f"{field_name}: min value cannot be greater than max value")


def validate_content_list_query(query: ContentListQuery) -> None:
    _validate_min_max(query.min_subscriber_count, query.max_subscriber_count, "subscriber_count")
    _validate_min_max(query.min_views, query.max_views, "views")
    _validate_min_max(query.min_likes, query.max_likes, "likes")
    _validate_min_max(query.min_comments, query.max_comments, "comments")
    _validate_min_max(query.min_engagement_rate, query.max_engagement_rate, "engagement_rate")

    if (
        query.published_after is not None
        and query.published_before is not None
        and query.published_after > query.published_before
    ):
        raise ValidationError("published_after cannot be greater than published_before")


def validate_creator_list_query(query: CreatorListQuery) -> None:
    _validate_min_max(query.min_subscriber_count, query.max_subscriber_count, "subscriber_count")
    _validate_min_max(
        query.min_channel_view_count,
        query.max_channel_view_count,
        "channel_view_count",
    )
    _validate_min_max(query.min_video_count, query.max_video_count, "video_count")