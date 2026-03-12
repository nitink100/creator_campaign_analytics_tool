from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.ingestion_run import IngestionRun
from app.repos.base_repo import BaseRepo


class IngestionRunReadRepo(BaseRepo):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_id(self, run_id: str) -> IngestionRun:
        result = await self.db.execute(
            select(IngestionRun).where(
                IngestionRun.id == run_id,
                IngestionRun.deleted_at.is_(None),
            )
        )
        run = result.scalar_one_or_none()
        if not run:
            raise NotFoundError(f"Ingestion run not found: {run_id}")
        return run

    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[IngestionRun]:
        result = await self.db.execute(
            select(IngestionRun)
            .where(IngestionRun.deleted_at.is_(None))
            .order_by(desc(IngestionRun.started_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())