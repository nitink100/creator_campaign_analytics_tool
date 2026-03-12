import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.creator_profile import CreatorProfile

async def find_missing_thumbnails():
    print("🔍 Searching for creators with missing thumbnails...")
    async with AsyncSessionLocal() as db:
        stmt = select(CreatorProfile).where(
            (CreatorProfile.thumbnail_url == None) | (CreatorProfile.thumbnail_url == "")
        )
        result = await db.execute(stmt)
        creators = result.scalars().all()
        
        if not creators:
            print("✨ All creators have thumbnails!")
            return []

        print(f"Found {len(creators)} creators missing thumbnails:")
        for c in creators:
            print(f"- {c.creator_name} ({c.platform_creator_id})")
        
        return [c.platform_creator_id for c in creators]

if __name__ == "__main__":
    asyncio.run(find_missing_thumbnails())
