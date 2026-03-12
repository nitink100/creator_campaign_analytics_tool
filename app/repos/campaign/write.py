from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import select, delete, func, desc
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.models.campaign import Campaign, CampaignMember
from app.models.content_item import ContentItem
from app.models.content_metric import ContentMetric
from app.models.creator_profile import CreatorProfile
from app.repos.base_repo import BaseRepo

logger = get_logger(__name__)

class CampaignWriteRepo(BaseRepo):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def create_campaign(
        self,
        name: str,
        user_id: str,
        description: str | None = None,
        budget: float | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Campaign:
        logger.info(
            "Creating campaign | name=%s user_id=%s budget=%s",
            name,
            user_id,
            budget,
        )
        campaign = Campaign(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            budget=budget,
            start_date=start_date,
            end_date=end_date,
        )
        self.db.add(campaign)
        logger.info("Campaign created (pending commit) | id=%s user_id=%s", campaign.id, user_id)
        return campaign

    async def add_member(self, campaign_id: str, creator_profile_id: str) -> CampaignMember:
        # Check for existing
        stmt = select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.creator_profile_id == creator_profile_id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(
                "Campaign member already exists | campaign_id=%s creator_profile_id=%s",
                campaign_id,
                creator_profile_id,
            )
            return existing

        member = CampaignMember(
            campaign_id=campaign_id,
            creator_profile_id=creator_profile_id,
        )
        self.db.add(member)
        logger.info(
            "Added creator to campaign (pending commit) | campaign_id=%s creator_profile_id=%s",
            campaign_id,
            creator_profile_id,
        )
        return member

    async def remove_member(self, campaign_id: str, creator_profile_id: str) -> bool:
        stmt = delete(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.creator_profile_id == creator_profile_id,
        )
        result = await self.db.execute(stmt)
        removed = result.rowcount > 0
        logger.info(
            "Removed campaign member | campaign_id=%s creator_profile_id=%s removed=%s",
            campaign_id,
            creator_profile_id,
            removed,
        )
        return removed

    async def delete_campaign(self, campaign_id: str) -> bool:
        # Soft delete
        from app.utils.datetime_utils import utc_now
        stmt = select(Campaign).where(Campaign.id == campaign_id)
        result = await self.db.execute(stmt)
        campaign = result.scalar_one_or_none()
        if not campaign:
            logger.warning("Delete campaign requested but not found | id=%s", campaign_id)
            return False
        campaign.deleted_at = utc_now()
        logger.info("Campaign soft-deleted (pending commit) | id=%s", campaign_id)
        return True

class CampaignReadRepo(BaseRepo):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_all(self, user_id: str) -> list[Campaign]:
        stmt = (
            select(Campaign)
            .where(
                Campaign.deleted_at.is_(None),
                Campaign.user_id == user_id,
            )
            .options(selectinload(Campaign.members).selectinload(CampaignMember.creator))
        )
        result = await self.db.execute(stmt)
        campaigns = list(result.scalars().all())
        
        for c in campaigns:
            await self._populate_campaign_creator_stats(c)
        return campaigns

    async def get_by_id(self, campaign_id: str, user_id: str | None = None) -> Campaign | None:
        stmt = (
            select(Campaign)
            .where(
                Campaign.id == campaign_id,
                Campaign.deleted_at.is_(None),
            )
            .options(selectinload(Campaign.members).selectinload(CampaignMember.creator))
        )
        if user_id is not None:
            stmt = stmt.where(Campaign.user_id == user_id)
        result = await self.db.execute(stmt)
        campaign = result.scalar_one_or_none()
        if campaign:
            await self._populate_campaign_creator_stats(campaign)
        return campaign

    async def _populate_campaign_creator_stats(self, campaign: Campaign):
        """
        Populate the creator objects in a campaign with calculated engagement stats.
        """
        # Get member IDs first
        stmt = select(CampaignMember).where(CampaignMember.campaign_id == campaign.id)
        res = await self.db.execute(stmt)
        members = list(res.scalars().all())
        
        if not members:
            campaign.members = []
            return

        creator_ids = [m.creator_profile_id for m in members]
        
        # Subquery for latest metrics (same logic as CreatorReadRepo)
        latest_metrics_subquery = (
            select(
                ContentMetric.content_item_id.label("content_item_id"),
                func.max(ContentMetric.captured_at).label("max_captured_at"),
            )
            .where(ContentMetric.deleted_at.is_(None))
            .group_by(ContentMetric.content_item_id)
            .subquery()
        )
        # Fix: SQLite group by can't easily handle this without a proper ID or being careful.
        # Let's use the one from CreatorReadRepo exactly.
        
        latest_metric = aliased(ContentMetric)
        
        # Re-fetch creators with stats
        stmt = (
            select(
                CreatorProfile,
                func.avg(latest_metric.engagement_rate).label("avg_eng"),
                func.sum(latest_metric.views).label("total_views"),
                func.count(func.distinct(ContentItem.id)).label("total_videos"),
            )
            .select_from(CreatorProfile)
            .outerjoin(ContentItem, ContentItem.creator_profile_id == CreatorProfile.id)
            .outerjoin(
                latest_metrics_subquery,
                latest_metrics_subquery.c.content_item_id == ContentItem.id,
            )
            .outerjoin(
                latest_metric,
                (latest_metric.content_item_id == ContentItem.id)
                & (latest_metric.captured_at == latest_metrics_subquery.c.max_captured_at),
            )
            .where(CreatorProfile.id.in_(creator_ids))
            .group_by(CreatorProfile.id)
        )
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        # Map them back to the campaign members
        creator_map = {}
        for creator, avg_eng, total_views, total_videos in rows:
            # Avoid using public attribute names that might conflict with properties
            creator._latest_avg_engagement_rate = avg_eng
            creator._latest_total_views = total_views
            creator._total_content_items = total_videos
            creator_map[creator.id] = creator
            
        # Re-assign members with populated creators
        campaign.members = members
        campaign.creators = [] # Initialize for collection
        for m in campaign.members:
            m.creator = creator_map.get(m.creator_profile_id)
            if m.creator:
                campaign.creators.append(m.creator)
