import asyncio
from sqlalchemy import select, delete, func
from app.db.session import AsyncSessionLocal
from app.models.campaign import CampaignMember

async def cleanup_duplicates():
    print("🧹 Cleaning up duplicate campaign members...")
    async with AsyncSessionLocal() as db:
        # Finding duplicates
        stmt = select(
            CampaignMember.campaign_id, 
            CampaignMember.creator_profile_id, 
            func.min(CampaignMember.id).label("min_id"),
            func.count(CampaignMember.id).label("count")
        ).group_by(
            CampaignMember.campaign_id, 
            CampaignMember.creator_profile_id
        ).having(func.count(CampaignMember.id) > 1)
        
        result = await db.execute(stmt)
        duplicates = result.all()
        
        if not duplicates:
            print("✨ No duplicates found.")
            return

        for row in duplicates:
            print(f"Found {row.count} entries for campaign {row.campaign_id}, creator {row.creator_profile_id}. Keeping ID {row.min_id}.")
            
            # Delete all except the one with min_id
            del_stmt = delete(CampaignMember).where(
                CampaignMember.campaign_id == row.campaign_id,
                CampaignMember.creator_profile_id == row.creator_profile_id,
                CampaignMember.id != row.min_id
            )
            await db.execute(del_stmt)
        
        await db.commit()
        print("✅ Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
