"""In-memory daily YouTube API quota tracker.

YouTube Data API v3 free tier: 10,000 units/day, resets at midnight Pacific.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.quota_usage import QuotaUsage

# Approximate Pacific timezone (PDT = UTC-7)
_PACIFIC = timezone(timedelta(hours=-7))


def _today() -> str:
    return datetime.now(_PACIFIC).strftime("%Y-%m-%d")


# Module-level singleton state
_lock = asyncio.Lock()
_used: int | None = None
_current_day: str | None = None

DAILY_LIMIT = 10_000
WARNING_THRESHOLD = 0.65   # 65%
CRITICAL_THRESHOLD = 0.90  # 90%


class QuotaTracker:
    """Thin class wrapping module-level singleton state backed by DB."""

    async def _init_state(self) -> None:
        global _used, _current_day
        today = _today()
        # Fast path
        if _used is not None and _current_day == today:
            return

        async with _lock:
            if _used is not None and _current_day == today:
                return
            async with AsyncSessionLocal() as session:
                stmt = select(QuotaUsage).where(QuotaUsage.date == today)
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                if row:
                    _used = row.units_used
                else:
                    _used = 0
                _current_day = today

    async def record(self, units: int) -> None:
        global _used
        await self._init_state()
        async with _lock:
            _used += units
            async with AsyncSessionLocal() as session:
                today = _today()
                stmt = select(QuotaUsage).where(QuotaUsage.date == today).with_for_update()
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                if row:
                    row.units_used += units
                else:
                    row = QuotaUsage(date=today, units_used=units)
                    session.add(row)
                await session.commit()

    async def get_usage(self) -> dict:
        await self._init_state()
        used_val = _used or 0
        percent = ((used_val * 1000) // DAILY_LIMIT) / 10.0
        return {
            "used": used_val,
            "limit": DAILY_LIMIT,
            "percent": percent,
            "warning": percent >= WARNING_THRESHOLD * 100,
            "critical": percent >= CRITICAL_THRESHOLD * 100,
        }

    async def can_search(self) -> bool:
        """True if quota allows expensive search operations (100 units)."""
        usage = await self.get_usage()
        return not usage["critical"]

    async def can_browse(self) -> bool:
        """True if quota allows trending browse (2 units)."""
        usage = await self.get_usage()
        return not usage["critical"]
