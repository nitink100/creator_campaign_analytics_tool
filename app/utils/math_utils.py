from __future__ import annotations

from app.core.constants import ENGAGEMENT_RATE_PRECISION


def safe_int(value: str | int | float | None) -> int | None:
    """Coerce a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_float(value: str | int | float | None) -> float | None:
    """Coerce a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compute_engagement_rate(
    *,
    views: int | None,
    likes: int | None,
    comments: int | None,
) -> float | None:
    """
    engagement_rate = (likes + comments) / views

    Returns None when views is None, zero, or both likes and comments are None.
    """
    if views is None or views == 0:
        return None

    like_count = likes if likes is not None else 0
    comment_count = comments if comments is not None else 0

    if like_count == 0 and comment_count == 0 and likes is None and comments is None:
        return None

    rate = (like_count + comment_count) / views
    return round(rate, ENGAGEMENT_RATE_PRECISION)
