from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RepositoryError


class BaseRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def flush(self) -> None:
        try:
            await self.db.flush()
        except SQLAlchemyError as exc:
            raise RepositoryError(f"Database flush failed: {exc}") from exc

    async def commit(self) -> None:
        try:
            await self.db.commit()
        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise RepositoryError(f"Database commit failed: {exc}") from exc

    async def refresh(self, instance: object) -> None:
        try:
            await self.db.refresh(instance)
        except SQLAlchemyError as exc:
            raise RepositoryError(f"Database refresh failed: {exc}") from exc