from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.deps.db import get_db_session
from app.db.base import Base
from app.db.session import engine

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = get_logger(__name__)

@router.post("/reset-db")
async def reset_database(
    db: AsyncSession = Depends(get_db_session)
):
    """
    DANGEROUS: Wipes all data from the database and recreates the schema.
    Only for development/testing use.
    """
    try:
        logger.warning("Database reset requested!")
        
        async with engine.begin() as conn:
            # We use run_sync to call the metadata methods
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database reset successful")
        return {"success": True, "message": "Database reset successfully. All data wiped."}
    except Exception as exc:
        logger.exception("Failed to reset database")
        raise HTTPException(status_code=500, detail=f"Database reset failed: {str(exc)}")
