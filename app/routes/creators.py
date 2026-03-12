from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.deps.auth import get_current_user
from app.deps.db import get_db_session
from app.models.user import User
from app.repos.creator.read import CreatorReadRepo
from app.schemas.common import PaginationMeta
from app.schemas.creator import (
    CreatorDetail,
    CreatorListItem,
    CreatorListQuery,
    PaginatedCreatorResponse,
)
from app.utils.errors import map_app_error_to_http
from app.validations.query_validators import validate_creator_list_query

router = APIRouter(prefix="/api/creators", tags=["creators"])
logger = get_logger(__name__)


@router.get("", response_model=PaginatedCreatorResponse)
async def list_creators(
    creator_name: str | None = None,
    platform: str | None = None,
    min_subscriber_count: int | None = None,
    max_subscriber_count: int | None = None,
    min_channel_view_count: int | None = None,
    max_channel_view_count: int | None = None,
    min_video_count: int | None = None,
    max_video_count: int | None = None,
    sort_by: str = "subscriber_count",
    sort_direction: str = "desc",
    limit: int = 25,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PaginatedCreatorResponse:
    try:
        query = CreatorListQuery(
            user_id=current_user.id,
            creator_name=creator_name,
            platform=platform,
            min_subscriber_count=min_subscriber_count,
            max_subscriber_count=max_subscriber_count,
            min_channel_view_count=min_channel_view_count,
            max_channel_view_count=max_channel_view_count,
            min_video_count=min_video_count,
            max_video_count=max_video_count,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=limit,
            offset=offset,
        )
        validate_creator_list_query(query)

        repo = CreatorReadRepo(db)
        rows, total = await repo.list_creators(query)

        items = [CreatorListItem.model_validate(row) for row in rows]
        return PaginatedCreatorResponse(
            success=True,
            message="Creators fetched successfully",
            items=items,
            pagination=PaginationMeta(limit=query.limit, offset=query.offset, total=total),
        )
    except AppError as exc:
        logger.exception("Failed to list creators")
        raise map_app_error_to_http(exc)


@router.get("/{creator_id}", response_model=CreatorDetail)
async def get_creator_detail(
    creator_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CreatorDetail:
    try:
        repo = CreatorReadRepo(db)
        creator = await repo.get_by_id(creator_id, user_id=current_user.id)
        return CreatorDetail.model_validate(creator)
    except AppError as exc:
        logger.exception("Failed to fetch creator detail | creator_id=%s", creator_id)
        raise map_app_error_to_http(exc)