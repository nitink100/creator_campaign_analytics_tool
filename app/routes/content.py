from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.deps.auth import get_current_user
from app.deps.db import get_db_session
from app.models.user import User
from app.repos.content.read import ContentReadRepo
from app.schemas.common import PaginationMeta
from app.schemas.content import (
    ContentDetail,
    ContentListItem,
    ContentListQuery,
    PaginatedContentResponse,
)
from app.utils.errors import map_app_error_to_http
from app.validations.query_validators import validate_content_list_query

router = APIRouter(prefix="/api/content", tags=["content"])
logger = get_logger(__name__)


@router.get("", response_model=PaginatedContentResponse)
async def list_content(
    creator_name: str | None = None,
    published_after: str | None = None,
    published_before: str | None = None,
    min_subscriber_count: int | None = None,
    max_subscriber_count: int | None = None,
    min_views: int | None = None,
    max_views: int | None = None,
    min_likes: int | None = None,
    max_likes: int | None = None,
    min_comments: int | None = None,
    max_comments: int | None = None,
    min_engagement_rate: float | None = None,
    max_engagement_rate: float | None = None,
    sort_by: str = "published_at",
    sort_direction: str = "desc",
    limit: int = 25,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PaginatedContentResponse:
    try:
        query = ContentListQuery(
            user_id=current_user.id,
            creator_name=creator_name,
            published_after=published_after,
            published_before=published_before,
            min_subscriber_count=min_subscriber_count,
            max_subscriber_count=max_subscriber_count,
            min_views=min_views,
            max_views=max_views,
            min_likes=min_likes,
            max_likes=max_likes,
            min_comments=min_comments,
            max_comments=max_comments,
            min_engagement_rate=min_engagement_rate,
            max_engagement_rate=max_engagement_rate,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=limit,
            offset=offset,
        )
        validate_content_list_query(query)

        repo = ContentReadRepo(db)
        rows, total = await repo.list_content(query)

        items = [ContentListItem.model_validate(row) for row in rows]
        return PaginatedContentResponse(
            success=True,
            message="Content fetched successfully",
            items=items,
            pagination=PaginationMeta(limit=query.limit, offset=query.offset, total=total),
        )
    except AppError as exc:
        logger.exception("Failed to list content")
        raise map_app_error_to_http(exc)


@router.get("/{content_id}", response_model=ContentDetail)
async def get_content_detail(
    content_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ContentDetail:
    try:
        repo = ContentReadRepo(db)
        item = await repo.get_by_id(content_id, user_id=current_user.id)
        return ContentDetail.model_validate(item)
    except AppError as exc:
        logger.exception("Failed to fetch content detail | content_id=%s", content_id)
        raise map_app_error_to_http(exc)