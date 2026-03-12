from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.schemas.creator import CreatorListItem

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    budget: Optional[float] = Field(None, ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class CampaignMemberRead(BaseModel):
    creator: CreatorListItem
    joined_at: datetime

    class Config:
        from_attributes = True

class CampaignRead(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    budget: Optional[float] = None
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    members: list[CampaignMemberRead] = []
    creators: list[CreatorListItem] = []

    class Config:
        from_attributes = True

class CampaignAddMember(BaseModel):
    creator_profile_id: str
