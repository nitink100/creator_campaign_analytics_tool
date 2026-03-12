from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_metric import ContentMetric
from app.repos.base_repo import BaseRepo
from app.repos.metric.read import MetricReadRepo


class MetricWriteRepo(BaseRepo):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.read_repo = MetricReadRepo(db)

    async def upsert_metric_snapshot(
        self,
        *,
        content_item_id: str,
        captured_at: datetime,
        views: int | None = None,
        likes: int | None = None,
        comments: int | None = None,
        engagement_rate: float | None = None,
        extra_metrics: dict | None = None,
        raw_payload: dict | None = None,
        ingestion_run_id: str | None = None,
    ) -> tuple[ContentMetric, bool]:
        existing = await self.read_repo.get_by_content_and_captured_at(
            content_item_id=content_item_id,
            captured_at=captured_at,
            include_deleted=True,
        )

        if existing:
            existing.deleted_at = None
            existing.views = views
            existing.likes = likes
            existing.comments = comments
            existing.engagement_rate = engagement_rate
            existing.extra_metrics = extra_metrics
            existing.raw_payload = raw_payload
            existing.ingestion_run_id = ingestion_run_id
            await self.flush()
            return existing, False

        metric = ContentMetric(
            content_item_id=content_item_id,
            captured_at=captured_at,
            views=views,
            likes=likes,
            comments=comments,
            engagement_rate=engagement_rate,
            extra_metrics=extra_metrics,
            raw_payload=raw_payload,
            ingestion_run_id=ingestion_run_id,
        )
        self.db.add(metric)
        await self.flush()
        return metric, True
    
    async def bulk_upsert_metric_snapshots(
        self,
        metrics_data: list[dict],
    ) -> int:
        """
        Efficiently upsert multiple metric snapshots using ON CONFLICT (SQLite or Postgres).
        """
        if not metrics_data:
            return 0

        dialect_name = self.db.get_bind().dialect.name
        if dialect_name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert

        stmt = insert(ContentMetric).values(metrics_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["content_item_id", "captured_at"],
            set_={
                "views": stmt.excluded.views,
                "likes": stmt.excluded.likes,
                "comments": stmt.excluded.comments,
                "engagement_rate": stmt.excluded.engagement_rate,
                "extra_metrics": stmt.excluded.extra_metrics,
                "raw_payload": stmt.excluded.raw_payload,
                "ingestion_run_id": stmt.excluded.ingestion_run_id,
                "updated_at": datetime.now(),
                "deleted_at": None,
            },
        )
        result = await self.db.execute(stmt)
        return result.rowcount