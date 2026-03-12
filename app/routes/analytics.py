from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.deps.auth import get_current_user
from app.deps.db import get_db_session
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    DashboardKPIResponse,
    KPICard,
    PlatformBreakdownResponse,
    TopContentResponse,
    TopCreatorsResponse,
)
from app.services.analytics.creator_analytics_service import CreatorAnalyticsService
from app.services.analytics.content_analytics_service import ContentAnalyticsService
from app.services.analytics.summary_service import SummaryAnalyticsService
from app.utils.errors import map_app_error_to_http

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
logger = get_logger(__name__)


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_summary(
    days: int = 0,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsSummaryResponse:
    try:
        service = SummaryAnalyticsService(db)
        data = await service.get_summary(days=days, user_id=current_user.id)

        return AnalyticsSummaryResponse(
            success=True,
            message="Analytics summary fetched successfully",
            data=data,
        )
    except AppError as exc:
        logger.exception("Failed to fetch analytics summary")
        raise map_app_error_to_http(exc)


@router.get("/top-content", response_model=TopContentResponse)
async def get_top_content(
    limit: int = 50,
    days: int = 0,
    creator_name: str | None = None,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TopContentResponse:
    try:
        service = ContentAnalyticsService(db)
        items = await service.get_top_content(
            limit, days=days, creator_name=creator_name, user_id=current_user.id,
        )

        return TopContentResponse(
            success=True,
            message="Top content fetched successfully",
            items=items,
        )
    except AppError as exc:
        logger.exception("Failed to fetch top content")
        raise map_app_error_to_http(exc)


@router.get("/top-creators", response_model=TopCreatorsResponse)
async def get_top_creators(
    limit: int = 10,
    days: int = 0,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TopCreatorsResponse:
    try:
        service = CreatorAnalyticsService(db)
        items = await service.get_top_creators(limit, days=days, user_id=current_user.id)
        # #region agent log
        try:
            import json
            with open("/Users/nitinkanna/Documents/CreatorCampaignAnalyticsTool/.cursor/debug-bfc2c2.log", "a") as f:
                f.write(json.dumps({"hypothesisId": "H2", "location": "analytics.py:get_top_creators", "message": "top-creators response", "data": {"user_id": current_user.id, "items_count": len(items)}, "timestamp": __import__("time").time() * 1000}) + "\n")
        except Exception:
            pass
        # #endregion
        return TopCreatorsResponse(
            success=True,
            message="Top creators fetched successfully",
            items=items,
        )
    except AppError as exc:
        logger.exception("Failed to fetch top creators")
        raise map_app_error_to_http(exc)


@router.get("/kpis", response_model=DashboardKPIResponse)
async def get_dashboard_kpis(
    days: int = 0,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DashboardKPIResponse:
    try:
        service = SummaryAnalyticsService(db)
        summary = await service.get_summary(days=days, user_id=current_user.id)

        items = [
            KPICard(label="Creators", value=summary.total_creators),
            KPICard(label="Content Items", value=summary.total_content_items),
            KPICard(label="Views", value=summary.total_views),
            KPICard(label="Avg Engagement", value=summary.avg_engagement_rate),
        ]

        return DashboardKPIResponse(
            success=True,
            message="Dashboard KPIs fetched successfully",
            items=items,
        )
    except AppError as exc:
        logger.exception("Failed to fetch KPIs")
        raise map_app_error_to_http(exc)


@router.get("/platform-breakdown", response_model=PlatformBreakdownResponse)
async def get_platform_breakdown(
    days: int = 0,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PlatformBreakdownResponse:
    try:
        service = SummaryAnalyticsService(db)
        summary = await service.get_summary(days=days, user_id=current_user.id)

        return PlatformBreakdownResponse(
            success=True,
            message="Platform breakdown fetched successfully",
            items=summary.platform_breakdown,
        )
    except AppError as exc:
        logger.exception("Failed to fetch platform breakdown")
        raise map_app_error_to_http(exc)