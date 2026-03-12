from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_metric import ContentMetric
from app.repos.base_repo import BaseRepo


class MetricReadRepo(BaseRepo):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_content_and_captured_at(
        self,
        *,
        content_item_id: str,
        captured_at: datetime,
        include_deleted: bool = True,
    ) -> ContentMetric | None:
        stmt = select(ContentMetric).where(
            ContentMetric.content_item_id == content_item_id,
            ContentMetric.captured_at == captured_at,
        )
        if not include_deleted:
            stmt = stmt.where(ContentMetric.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()