from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.datetime_utils import utc_now

if TYPE_CHECKING:
    from app.models.creator_profile import CreatorProfile


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, paused, completed
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    members: Mapped[list[CampaignMember]] = relationship("CampaignMember", back_populates="campaign", cascade="all, delete-orphan")


class CampaignMember(Base):
    __tablename__ = "campaign_members"
    __table_args__ = (
        UniqueConstraint("campaign_id", "creator_profile_id", name="uq_campaign_member"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), nullable=False)
    creator_profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("creator_profiles.id"), nullable=False)
    
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="members")
    creator: Mapped[CreatorProfile] = relationship("CreatorProfile")
