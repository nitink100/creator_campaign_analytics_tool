from __future__ import annotations

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserTrackedCreator(Base):
    """Links a user to a creator they track. Scopes creator/content to the user."""

    __tablename__ = "user_tracked_creators"
    __table_args__ = (
        UniqueConstraint("user_id", "creator_profile_id", name="uq_user_tracked_creator"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    creator_profile_id: Mapped[str] = mapped_column(
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # Optional relationships for ORM (avoid circular import in models/__init__)
    # user: Mapped["User"] = relationship("User", back_populates="tracked_creators")
    # creator_profile: Mapped["CreatorProfile"] = relationship("CreatorProfile")
