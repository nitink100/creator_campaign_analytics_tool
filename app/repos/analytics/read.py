from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.content_item import ContentItem
from app.models.content_metric import ContentMetric
from app.models.creator_profile import CreatorProfile
from app.models.user_tracked_creator import UserTrackedCreator
from app.repos.base_repo import BaseRepo


class AnalyticsReadRepo(BaseRepo):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    def _user_tracked_creator_ids_subquery(self, user_id: str):
        return select(UserTrackedCreator.creator_profile_id).where(
            UserTrackedCreator.user_id == user_id,
        )

    def _latest_metrics_subquery(self):
        """Subquery that selects the most recent captured_at per content item."""
        return (
            select(
                ContentMetric.content_item_id.label("content_item_id"),
                func.max(ContentMetric.captured_at).label("max_captured_at"),
            )
            .where(ContentMetric.deleted_at.is_(None))
            .group_by(ContentMetric.content_item_id)
            .subquery()
        )

    async def get_total_creators(self, user_id: str | None = None) -> int:
        stmt = select(func.count()).select_from(CreatorProfile).where(
            CreatorProfile.deleted_at.is_(None),
        )
        if user_id is not None:
            stmt = stmt.where(
                CreatorProfile.id.in_(self._user_tracked_creator_ids_subquery(user_id)),
            )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    async def get_total_content_items(
        self, *, published_after: datetime | None = None, user_id: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(ContentItem)
            .where(ContentItem.deleted_at.is_(None))
        )
        if published_after is not None:
            stmt = stmt.where(ContentItem.published_at >= published_after)
        if user_id is not None:
            stmt = stmt.where(
                ContentItem.creator_profile_id.in_(
                    self._user_tracked_creator_ids_subquery(user_id),
                ),
            )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    async def get_total_metric_snapshots(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ContentMetric).where(
                ContentMetric.deleted_at.is_(None)
            )
        )
        return int(result.scalar() or 0)

    async def get_avg_engagement_rate(
        self, *, published_after: datetime | None = None, user_id: str | None = None,
    ) -> float | None:
        latest_sub = self._latest_metrics_subquery()
        latest_metric = aliased(ContentMetric)

        stmt = (
            select(func.avg(latest_metric.engagement_rate))
            .select_from(latest_metric)
            .join(
                latest_sub,
                (latest_metric.content_item_id == latest_sub.c.content_item_id)
                & (latest_metric.captured_at == latest_sub.c.max_captured_at),
            )
            .where(
                latest_metric.deleted_at.is_(None),
                latest_metric.engagement_rate.is_not(None),
            )
        )
        if published_after is not None or user_id is not None:
            stmt = stmt.join(ContentItem, ContentItem.id == latest_metric.content_item_id)
        if published_after is not None:
            stmt = stmt.where(ContentItem.published_at >= published_after)
        if user_id is not None:
            stmt = stmt.where(
                ContentItem.creator_profile_id.in_(
                    self._user_tracked_creator_ids_subquery(user_id),
                ),
            )
        result = await self.db.execute(stmt)
        value = result.scalar()
        return float(value) if value is not None else None

    async def get_total_views(
        self, *, published_after: datetime | None = None, user_id: str | None = None,
    ) -> int | None:
        latest_sub = self._latest_metrics_subquery()
        latest_metric = aliased(ContentMetric)

        stmt = (
            select(func.sum(latest_metric.views))
            .select_from(latest_metric)
            .join(
                latest_sub,
                (latest_metric.content_item_id == latest_sub.c.content_item_id)
                & (latest_metric.captured_at == latest_sub.c.max_captured_at),
            )
            .where(
                latest_metric.deleted_at.is_(None),
                latest_metric.views.is_not(None),
            )
        )
        if published_after is not None or user_id is not None:
            stmt = stmt.join(ContentItem, ContentItem.id == latest_metric.content_item_id)
        if published_after is not None:
            stmt = stmt.where(ContentItem.published_at >= published_after)
        if user_id is not None:
            stmt = stmt.where(
                ContentItem.creator_profile_id.in_(
                    self._user_tracked_creator_ids_subquery(user_id),
                ),
            )
        result = await self.db.execute(stmt)
        value = result.scalar()
        return int(value) if value is not None else None

    async def get_top_creator_name(
        self, *, published_after: datetime | None = None, user_id: str | None = None,
    ) -> str | None:
        latest_sub = self._latest_metrics_subquery()
        latest_metric = aliased(ContentMetric)

        content_join_cond = ContentItem.creator_profile_id == CreatorProfile.id
        if published_after is not None:
            content_join_cond = content_join_cond & (ContentItem.published_at >= published_after)

        stmt = (
            select(CreatorProfile.creator_name)
            .select_from(CreatorProfile)
            .outerjoin(ContentItem, content_join_cond)
            .outerjoin(
                latest_sub,
                latest_sub.c.content_item_id == ContentItem.id,
            )
            .outerjoin(
                latest_metric,
                (latest_metric.content_item_id == ContentItem.id)
                & (latest_metric.captured_at == latest_sub.c.max_captured_at),
            )
            .where(CreatorProfile.deleted_at.is_(None))
        )
        if user_id is not None:
            stmt = stmt.where(
                CreatorProfile.id.in_(self._user_tracked_creator_ids_subquery(user_id)),
            )
        stmt = stmt.group_by(CreatorProfile.id, CreatorProfile.creator_name).order_by(
            desc(func.sum(latest_metric.views)),
        ).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_top_content_title(
        self, *, published_after: datetime | None = None, user_id: str | None = None,
    ) -> str | None:
        latest_sub = self._latest_metrics_subquery()
        latest_metric = aliased(ContentMetric)

        stmt = (
            select(ContentItem.title)
            .select_from(ContentItem)
            .join(
                latest_sub,
                latest_sub.c.content_item_id == ContentItem.id,
            )
            .join(
                latest_metric,
                (latest_metric.content_item_id == ContentItem.id)
                & (latest_metric.captured_at == latest_sub.c.max_captured_at),
            )
            .where(
                ContentItem.deleted_at.is_(None),
                latest_metric.deleted_at.is_(None),
                latest_metric.views.is_not(None),
            )
        )
        if published_after is not None:
            stmt = stmt.where(ContentItem.published_at >= published_after)
        if user_id is not None:
            stmt = stmt.where(
                ContentItem.creator_profile_id.in_(
                    self._user_tracked_creator_ids_subquery(user_id),
                ),
            )
        stmt = stmt.order_by(latest_metric.views.desc()).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_platform_breakdown(
        self, *, published_after: datetime | None = None, user_id: str | None = None,
    ) -> list[dict]:
        latest_sub = self._latest_metrics_subquery()
        latest_metric = aliased(ContentMetric)

        content_join_cond = ContentItem.creator_profile_id == CreatorProfile.id
        if published_after is not None:
            content_join_cond = content_join_cond & (ContentItem.published_at >= published_after)

        stmt = (
            select(
                CreatorProfile.platform.label("platform"),
                func.count(func.distinct(CreatorProfile.id)).label("creator_count"),
                func.count(func.distinct(ContentItem.id)).label("content_count"),
                func.avg(latest_metric.engagement_rate).label("avg_engagement_rate"),
                func.sum(latest_metric.views).label("total_views"),
            )
            .select_from(CreatorProfile)
            .outerjoin(ContentItem, content_join_cond)
            .outerjoin(
                latest_sub,
                latest_sub.c.content_item_id == ContentItem.id,
            )
            .outerjoin(
                latest_metric,
                (latest_metric.content_item_id == ContentItem.id)
                & (latest_metric.captured_at == latest_sub.c.max_captured_at),
            )
            .where(CreatorProfile.deleted_at.is_(None))
        )
        if user_id is not None:
            stmt = stmt.where(
                CreatorProfile.id.in_(self._user_tracked_creator_ids_subquery(user_id)),
            )
        stmt = stmt.group_by(CreatorProfile.platform).order_by(CreatorProfile.platform.asc())
        result = await self.db.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_top_content(
        self,
        limit: int,
        *,
        published_after: datetime | None = None,
        creator_name: str | None = None,
        user_id: str | None = None,
    ) -> list[dict]:
        latest_sub = self._latest_metrics_subquery()
        latest_metric = aliased(ContentMetric)

        stmt = (
            select(
                ContentItem.id.label("content_id"),
                ContentItem.title,
                ContentItem.content_url,
                CreatorProfile.creator_name,
                latest_metric.views,
                latest_metric.likes,
                latest_metric.comments,
                latest_metric.engagement_rate,
                ContentItem.published_at,
            )
            .select_from(ContentItem)
            .join(CreatorProfile, CreatorProfile.id == ContentItem.creator_profile_id)
            .join(
                latest_sub,
                latest_sub.c.content_item_id == ContentItem.id,
            )
            .join(
                latest_metric,
                (latest_metric.content_item_id == ContentItem.id)
                & (latest_metric.captured_at == latest_sub.c.max_captured_at),
            )
            .where(
                ContentItem.deleted_at.is_(None),
                latest_metric.deleted_at.is_(None),
                CreatorProfile.deleted_at.is_(None),
            )
        )
        if published_after is not None:
            stmt = stmt.where(ContentItem.published_at >= published_after)
        if creator_name is not None:
            stmt = stmt.where(CreatorProfile.creator_name == creator_name)
        if user_id is not None:
            stmt = stmt.where(
                ContentItem.creator_profile_id.in_(
                    self._user_tracked_creator_ids_subquery(user_id),
                ),
            )
        stmt = stmt.order_by(desc(latest_metric.views)).limit(limit)

        result = await self.db.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_top_creators(
        self,
        limit: int,
        *,
        published_after: datetime | None = None,
        user_id: str | None = None,
    ) -> list[dict]:
        """
        Returns top creators enriched with latest
        aggregated metrics from their content items (scoped to time period and optionally user).
        """
        latest_sub = self._latest_metrics_subquery()
        latest_metric = aliased(ContentMetric)

        content_join_cond = ContentItem.creator_profile_id == CreatorProfile.id
        if published_after is not None:
            content_join_cond = content_join_cond & (ContentItem.published_at >= published_after)

        stmt = (
            select(
                CreatorProfile.id.label("creator_id"),
                CreatorProfile.creator_name,
                CreatorProfile.channel_url,
                CreatorProfile.thumbnail_url,
                CreatorProfile.subscriber_count,
                func.avg(latest_metric.engagement_rate).label("latest_avg_engagement_rate"),
                func.sum(latest_metric.views).label("latest_total_views"),
                func.count(func.distinct(ContentItem.id)).label("total_content_items"),
            )
            .select_from(CreatorProfile)
            .outerjoin(ContentItem, content_join_cond)
            .outerjoin(
                latest_sub,
                latest_sub.c.content_item_id == ContentItem.id,
            )
            .outerjoin(
                latest_metric,
                (latest_metric.content_item_id == ContentItem.id)
                & (latest_metric.captured_at == latest_sub.c.max_captured_at),
            )
            .where(CreatorProfile.deleted_at.is_(None))
        )
        if user_id is not None:
            stmt = stmt.where(
                CreatorProfile.id.in_(self._user_tracked_creator_ids_subquery(user_id)),
            )
        stmt = (
            stmt.group_by(
                CreatorProfile.id,
                CreatorProfile.creator_name,
                CreatorProfile.channel_url,
                CreatorProfile.thumbnail_url,
                CreatorProfile.subscriber_count,
            )
            .order_by(
                desc(
                    (func.sum(latest_metric.views) * 0.00001 * 0.7)
                    + (func.avg(latest_metric.engagement_rate) * 0.3),
                ),
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [dict(row) for row in result.mappings().all()]