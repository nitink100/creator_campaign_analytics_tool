from __future__ import annotations

from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine, ASYNC_DATABASE_URL

# Import all models so SQLAlchemy metadata is fully registered.
from app.models import (  # noqa: F401
    ContentItem,
    ContentMetric,
    CreatorProfile,
    IngestionRun,
    Campaign,
    CampaignMember,
    User,
    UserTrackedCreator,
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add role column to users if missing (e.g. existing DB before admin feature)
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))
        except Exception:
            pass  # column already exists
        # Add user_id to campaigns for user-scoped campaigns
        try:
            await conn.execute(text("ALTER TABLE campaigns ADD COLUMN user_id VARCHAR(36) REFERENCES users(id)"))
        except Exception:
            pass  # column already exists
        # One-time backfill (SQLite or Postgres): link existing is_tracked creators to the single user
        try:
            from sqlalchemy import text as sql_text
            res = await conn.execute(sql_text("SELECT COUNT(*) FROM users"))
            user_count = (await res.fetchone())[0]
            res2 = await conn.execute(sql_text("SELECT COUNT(*) FROM user_tracked_creators"))
            utc_count = (await res2.fetchone())[0]
            if user_count == 1 and utc_count == 0:
                if "sqlite" in ASYNC_DATABASE_URL:
                    await conn.execute(sql_text("""
                        INSERT OR IGNORE INTO user_tracked_creators (user_id, creator_profile_id)
                        SELECT (SELECT id FROM users LIMIT 1), id FROM creator_profiles
                        WHERE deleted_at IS NULL AND is_tracked = 1
                    """))
                else:
                    await conn.execute(sql_text("""
                        INSERT INTO user_tracked_creators (user_id, creator_profile_id)
                        SELECT (SELECT id FROM users LIMIT 1), id FROM creator_profiles
                        WHERE deleted_at IS NULL AND is_tracked = 1
                        ON CONFLICT (user_id, creator_profile_id) DO NOTHING
                    """))
                await conn.execute(sql_text("""
                    UPDATE campaigns SET user_id = (SELECT id FROM users LIMIT 1)
                    WHERE user_id IS NULL AND deleted_at IS NULL
                """))
        except Exception:
            pass