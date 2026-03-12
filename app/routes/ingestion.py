from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.deps.auth import get_current_admin_user, get_current_user
from app.deps.db import get_db_session
from app.models.user import User
from app.repos.ingestion_run.read import IngestionRunReadRepo
from app.schemas.ingestion import (
    IngestionRunDetailResponse,
    IngestionRunRequest,
    IngestionRunResponse,
    IngestionRunRead,
    IngestionRunsListResponse,
)
from app.services.ingestion.sync_runner import dispatch_ingestion
from app.utils.errors import map_app_error_to_http

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])
logger = get_logger(__name__)


# ── Existing endpoints ───────────────────────────────────────


@router.post("/run", response_model=IngestionRunResponse)
async def trigger_ingestion(
    request: IngestionRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> IngestionRunResponse:
    try:
        logger.info(
            "Ingestion trigger requested | user_id=%s platform=%s trigger_type=%s",
            current_user.id,
            request.platform.value,
            request.trigger_type.value,
        )
        # Scope sync to this user's tracked channels when channel_ids not explicitly provided
        req = request.model_copy(update={"user_id": request.user_id or current_user.id})
        result = await dispatch_ingestion(db=db, request=req, background_tasks=background_tasks)
        return IngestionRunResponse(
            success=True,
            message="Ingestion completed",
            data=result,
        )
    except AppError as exc:
        logger.exception("Ingestion trigger failed")
        raise map_app_error_to_http(exc)


@router.get("/runs", response_model=IngestionRunsListResponse)
async def list_ingestion_runs(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
) -> IngestionRunsListResponse:
    try:
        repo = IngestionRunReadRepo(db)
        runs = await repo.list_runs(limit=limit, offset=offset)
        items = [IngestionRunRead.model_validate(run) for run in runs]
        return IngestionRunsListResponse(
            success=True,
            message="Ingestion runs fetched successfully",
            items=items,
        )
    except AppError as exc:
        logger.exception("Failed to list ingestion runs")
        raise map_app_error_to_http(exc)


@router.get("/runs/{run_id}", response_model=IngestionRunDetailResponse)
async def get_ingestion_run(
    run_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> IngestionRunDetailResponse:
    try:
        repo = IngestionRunReadRepo(db)
        run = await repo.get_by_id(run_id)
        data = IngestionRunRead.model_validate(run)
        return IngestionRunDetailResponse(
            success=True,
            message="Ingestion run fetched successfully",
            data=data,
        )
    except AppError as exc:
        logger.exception("Failed to fetch ingestion run | run_id=%s", run_id)
        raise map_app_error_to_http(exc)


# ── Channel management ──────────────────────────────────────

from pydantic import BaseModel
from app.core.config import get_settings
from app.services.ingestion.youtube_api_adapter import YouTubeAPIAdapter
from app.services.ingestion.quota_tracker import QuotaTracker


class ChannelsResponse(BaseModel):
    success: bool = True
    message: str
    channel_ids: list[str]
    total: int


from app.core.enums import PlatformEnum
from app.repos.creator.read import CreatorReadRepo


@router.get("/channels", response_model=ChannelsResponse)
async def list_channels(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ChannelsResponse:
    repo = CreatorReadRepo(db)
    ids = await repo.get_tracked_channel_ids(
        PlatformEnum.YOUTUBE.value, user_id=current_user.id,
    )
    return ChannelsResponse(
        message=f"{len(ids)} channels tracked",
        channel_ids=ids,
        total=len(ids),
    )


# ── Discovery endpoints ─────────────────────────────────────


class ChannelPreview(BaseModel):
    channel_id: str
    name: str
    handle: str = ""
    description: str = ""
    subscribers: Optional[int] = None
    thumbnail_url: str = ""
    already_tracked: bool = False


class ResolveRequest(BaseModel):
    query: str


class ResolveResponse(BaseModel):
    success: bool = True
    channel: Optional[ChannelPreview] = None
    message: str = ""
    quota: dict = {}


class SearchResponse(BaseModel):
    success: bool = True
    results: list[ChannelPreview] = []
    message: str = ""
    quota: dict = {}


class CategoriesResponse(BaseModel):
    success: bool = True
    categories: list[dict] = []
    quota: dict = {}


class TrendingResponse(BaseModel):
    success: bool = True
    creators: list[ChannelPreview] = []
    message: str = ""
    quota: dict = {}


class TrackRequest(BaseModel):
    channel_id: str


class TrackResponse(BaseModel):
    success: bool = True
    message: str = ""
    channel: Optional[ChannelPreview] = None
    quota: dict = {}


async def _enrich_tracked(
    previews: list[dict], db: AsyncSession, user_id: str,
) -> list[ChannelPreview]:
    """Attach 'already_tracked' flag to preview dicts for this user."""
    repo = CreatorReadRepo(db)
    tracked_ids = await repo.get_tracked_channel_ids(
        PlatformEnum.YOUTUBE.value, user_id=user_id,
    )
    tracked = set(tracked_ids)
    return [
        ChannelPreview(**p, already_tracked=p.get("channel_id", "") in tracked)
        for p in previews
    ]


async def _quota() -> dict:
    return await QuotaTracker().get_usage()


@router.post("/channels/resolve", response_model=ResolveResponse)
async def resolve_channel(
    request: ResolveRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ResolveResponse:
    """Resolve a handle, URL, or keyword to a YouTube channel."""
    query = request.query.strip()
    if not query or query == "@":
        return ResolveResponse(
            success=False,
            message="Please enter a valid handle, URL, or channel name.",
            quota=await _quota(),
        )

    try:
        adapter = YouTubeAPIAdapter()
        result = await adapter.resolve_channel(query)
        if not result:
            return ResolveResponse(
                success=False,
                message=f"No channel found for '{request.query}'",
                quota=await _quota(),
            )
        repo = CreatorReadRepo(db)
        tracked_ids = await repo.get_tracked_channel_ids(
            PlatformEnum.YOUTUBE.value, user_id=current_user.id,
        )
        tracked = set(tracked_ids)
        preview = ChannelPreview(
            **result,
            already_tracked=result["channel_id"] in tracked,
        )
        return ResolveResponse(
            channel=preview,
            message=f"Found: {preview.name}",
            quota=await _quota(),
        )
    except AppError as exc:
        raise map_app_error_to_http(exc)


@router.get("/channels/search", response_model=SearchResponse)
async def search_channels(
    q: str,
    limit: int = 5,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    """Search YouTube channels by keyword (100 quota units)."""
    tracker = QuotaTracker()
    if not await tracker.can_search():
        return SearchResponse(
            success=False,
            message="Quota limit approaching — search disabled. Try using @handles or URLs instead.",
            quota=await _quota(),
        )
    try:
        adapter = YouTubeAPIAdapter()
        results = await adapter.search_channels(q, limit=min(limit, 10))
        previews = await _enrich_tracked(results, db, current_user.id)
        return SearchResponse(
            results=previews,
            message=f"{len(previews)} channel(s) found",
            quota=await _quota(),
        )
    except AppError as exc:
        return SearchResponse(
            success=False,
            message=str(exc),
            quota=await _quota(),
        )
    except Exception as exc:
        logger.exception("Search failed")
        return SearchResponse(
            success=False,
            message="An unexpected error occurred during search.",
            quota=await _quota(),
        )


@router.get("/categories", response_model=CategoriesResponse)
async def get_categories(region: str = "US") -> CategoriesResponse:
    """List YouTube video categories (1 quota unit)."""
    try:
        adapter = YouTubeAPIAdapter()
        categories = await adapter.fetch_categories(region_code=region)
        return CategoriesResponse(categories=categories, quota=await _quota())
    except AppError as exc:
        raise map_app_error_to_http(exc)


@router.get("/trending", response_model=TrendingResponse)
async def get_trending(
    category_id: str,
    region: str = "US",
    limit: int = 20,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TrendingResponse:
    """Fetch trending creators in a YouTube category (2 quota units)."""
    tracker = QuotaTracker()
    if not await tracker.can_browse():
        return TrendingResponse(
            success=False,
            message="Quota limit approaching — trending disabled.",
            quota=await _quota(),
        )
    try:
        adapter = YouTubeAPIAdapter()
        results = await adapter.fetch_trending_by_category(
            category_id=category_id,
            region_code=region,
            max_results=min(limit, 50),
        )
        previews = await _enrich_tracked(results, db, current_user.id)
        return TrendingResponse(
            creators=previews,
            message=f"{len(previews)} trending creator(s) in category {category_id}",
            quota=await _quota(),
        )
    except AppError as exc:
        raise map_app_error_to_http(exc)


class UntrackRequest(BaseModel):
    channel_ids: list[str]


@router.post("/channels/untrack")
async def untrack_channels(
    request: UntrackRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Remove channels from this user's tracking (removes user_tracked_creator links only)."""
    from sqlalchemy import delete, select
    from app.models.creator_profile import CreatorProfile
    from app.models.user_tracked_creator import UserTrackedCreator

    to_remove = set(cid.strip() for cid in request.channel_ids if cid.strip())
    if not to_remove:
        return {"success": False, "message": "No channel IDs provided"}

    stmt = select(CreatorProfile.id).where(
        CreatorProfile.deleted_at.is_(None),
        (CreatorProfile.platform_creator_id.in_(to_remove))
        | (CreatorProfile.id.in_(to_remove)),
    )
    result = await db.execute(stmt)
    profile_ids = [r[0] for r in result.all()]
    if not profile_ids:
        return {"success": True, "message": "0 creator(s) untracked (none found)"}

    delete_stmt = delete(UserTrackedCreator).where(
        UserTrackedCreator.user_id == current_user.id,
        UserTrackedCreator.creator_profile_id.in_(profile_ids),
    )
    result = await db.execute(delete_stmt)
    removed_count = result.rowcount
    await db.commit()
    logger.info("User %s untracked %d creator(s)", current_user.id, removed_count)
    return {
        "success": True,
        "message": f"{removed_count} creator(s) untracked",
    }


@router.post("/channels/track", response_model=TrackResponse)
async def track_channel(
    request: TrackRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TrackResponse:
    """Add a channel to this user's tracking and sync its data."""
    channel_id = request.channel_id.strip()
    if not channel_id:
        return TrackResponse(success=False, message="Channel ID is required", quota=await _quota())

    logger.info("User %s tracking channel: %s", current_user.id, channel_id)

    try:
        from app.schemas.ingestion import IngestionRunRequest as RunReq
        from app.core.enums import PlatformEnum, SourceTypeEnum, IngestionTriggerEnum
        from app.services.ingestion.orchestrator import IngestionOrchestrator
        from app.repos.creator.read import CreatorReadRepo
        from app.repos.creator.write import CreatorWriteRepo

        sync_request = RunReq(
            platform=PlatformEnum.YOUTUBE,
            source_type=SourceTypeEnum.API,
            trigger_type=IngestionTriggerEnum.MANUAL,
            channel_ids=[channel_id],
        )
        orchestrator = IngestionOrchestrator(db)
        await orchestrator.run(sync_request)
        creator_read = CreatorReadRepo(db)
        creator_write = CreatorWriteRepo(db)
        profile = await creator_read.get_by_platform_creator_id(
            platform=PlatformEnum.YOUTUBE.value,
            platform_creator_id=channel_id,
            include_deleted=False,
        )
        if profile:
            await creator_write.add_user_tracked_creator(current_user.id, profile.id)
        await db.commit()
    except Exception as exc:
        logger.warning("Mini-sync after track failed: %s", exc)
        return TrackResponse(
            message=f"Channel {channel_id} tracked. Sync failed: {exc}. Click Sync Now to retry.",
            quota=await _quota(),
        )

    try:
        adapter = YouTubeAPIAdapter()
        info = await adapter.resolve_channel(channel_id)
        if info:
            preview = ChannelPreview(**info, already_tracked=True)
            return TrackResponse(
                message=f"{preview.name} added and synced!",
                channel=preview,
                quota=await _quota(),
            )
    except Exception:
        pass

    return TrackResponse(
        message=f"Channel {channel_id} tracked and synced.",
        quota=await _quota(),
    )


@router.get("/quota")
async def get_quota() -> dict:
    """Return current YouTube API quota usage."""
    return await QuotaTracker().get_usage()