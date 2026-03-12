from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db_session
from app.models.user import User
from app.repos.campaign.write import CampaignReadRepo, CampaignWriteRepo
from app.schemas.campaign import CampaignAddMember, CampaignCreate, CampaignRead

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    repo = CampaignWriteRepo(db)
    campaign = await repo.create_campaign(
        name=payload.name,
        user_id=current_user.id,
        description=payload.description,
        budget=payload.budget,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    await db.commit()
    read_repo = CampaignReadRepo(db)
    campaign_full = await read_repo.get_by_id(campaign.id, user_id=current_user.id)
    return campaign_full


@router.get("", response_model=list[CampaignRead])
async def list_campaigns(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    repo = CampaignReadRepo(db)
    return await repo.get_all(user_id=current_user.id)


@router.get("/{campaign_id}", response_model=CampaignRead)
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    repo = CampaignReadRepo(db)
    campaign = await repo.get_by_id(campaign_id, user_id=current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.post("/{campaign_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    campaign_id: str,
    payload: CampaignAddMember,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    read_repo = CampaignReadRepo(db)
    campaign = await read_repo.get_by_id(campaign_id, user_id=current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    from app.repos.creator.read import CreatorReadRepo
    creator_repo = CreatorReadRepo(db)
    tracked_ids = await creator_repo.get_tracked_creator_profile_ids(current_user.id)
    if payload.creator_profile_id not in tracked_ids:
        raise HTTPException(
            status_code=400,
            detail="Creator not in your tracked list. Track the creator first.",
        )
    repo = CampaignWriteRepo(db)
    await repo.add_member(campaign_id, payload.creator_profile_id)
    await db.commit()
    return {"success": True, "message": "Member added to campaign"}

@router.delete("/{campaign_id}/members/{creator_profile_id}")
async def remove_member(
    campaign_id: str,
    creator_profile_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    read_repo = CampaignReadRepo(db)
    campaign = await read_repo.get_by_id(campaign_id, user_id=current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    repo = CampaignWriteRepo(db)
    deleted = await repo.remove_member(campaign_id, creator_profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Member not found in campaign")
    await db.commit()
    return {"success": True, "message": "Member removed from campaign"}
@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    read_repo = CampaignReadRepo(db)
    campaign = await read_repo.get_by_id(campaign_id, user_id=current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    repo = CampaignWriteRepo(db)
    success = await repo.delete_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await db.commit()
    return {"success": True, "message": "Campaign deleted successfully"}
