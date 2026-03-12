from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repos.analytics.read import AnalyticsReadRepo
from app.schemas.analytics import AnalyticsSummary, PlatformBreakdownItem


class SummaryAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnalyticsReadRepo(db)

    async def get_summary(
        self, *, days: int = 0, user_id: str | None = None,
    ) -> AnalyticsSummary:
        published_after = None
        if days > 0:
            published_after = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)

        total_creators = await self.repo.get_total_creators(user_id=user_id)
        total_content_items = await self.repo.get_total_content_items(
            published_after=published_after,
            user_id=user_id,
        )
        total_metric_snapshots = await self.repo.get_total_metric_snapshots()
        avg_engagement_rate = await self.repo.get_avg_engagement_rate(
            published_after=published_after,
            user_id=user_id,
        )
        total_views = await self.repo.get_total_views(
            published_after=published_after,
            user_id=user_id,
        )
        top_creator_name = await self.repo.get_top_creator_name(
            published_after=published_after,
            user_id=user_id,
        )
        top_content_title = await self.repo.get_top_content_title(
            published_after=published_after,
            user_id=user_id,
        )
        platform_breakdown_rows = await self.repo.get_platform_breakdown(
            published_after=published_after,
            user_id=user_id,
        )

        platform_breakdown = [
            PlatformBreakdownItem(
                platform=row["platform"],
                creator_count=int(row["creator_count"] or 0),
                content_count=int(row["content_count"] or 0),
                avg_engagement_rate=(
                    float(row["avg_engagement_rate"])
                    if row["avg_engagement_rate"] is not None
                    else None
                ),
                total_views=(
                    int(row["total_views"])
                    if row["total_views"] is not None
                    else None
                ),
            )
            for row in platform_breakdown_rows
        ]

        return AnalyticsSummary(
            total_creators=total_creators,
            total_content_items=total_content_items,
            total_metric_snapshots=total_metric_snapshots,
            avg_engagement_rate=avg_engagement_rate,
            total_views=total_views,
            top_creator_name=top_creator_name,
            top_content_title=top_content_title,
            platform_breakdown=platform_breakdown,
        )