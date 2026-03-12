from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repos.analytics.read import AnalyticsReadRepo
from app.schemas.analytics import TopCreatorItem


class CreatorAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnalyticsReadRepo(db)

    async def get_top_creators(
        self, limit: int, *, days: int = 0, user_id: str | None = None,
    ) -> list[TopCreatorItem]:
        published_after = None
        if days > 0:
            published_after = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)
        rows = await self.repo.get_top_creators(
            limit, published_after=published_after, user_id=user_id,
        )
        # #region agent log
        try:
            import json
            with open("/Users/nitinkanna/Documents/CreatorCampaignAnalyticsTool/.cursor/debug-bfc2c2.log", "a") as f:
                f.write(json.dumps({"hypothesisId": "H2", "location": "creator_analytics_service.py:get_top_creators", "message": "repo returned rows", "data": {"user_id": user_id, "rows_count": len(rows)}, "timestamp": __import__("time").time() * 1000}) + "\n")
        except Exception:
            pass
        # #endregion
        return [TopCreatorItem(**row) for row in rows]