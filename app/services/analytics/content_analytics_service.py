from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repos.analytics.read import AnalyticsReadRepo
from app.schemas.analytics import TopContentItem


class ContentAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnalyticsReadRepo(db)

    async def get_top_content(
        self,
        limit: int,
        *,
        days: int = 0,
        creator_name: str | None = None,
        user_id: str | None = None,
    ) -> list[TopContentItem]:
        published_after = None
        if days > 0:
            published_after = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)
        rows = await self.repo.get_top_content(
            limit,
            published_after=published_after,
            creator_name=creator_name,
            user_id=user_id,
        )
        return [TopContentItem(**row) for row in rows]