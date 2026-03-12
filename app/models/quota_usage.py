from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuotaUsage(Base):
    __tablename__ = "quota_usage"

    date: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
        comment="YYYY-MM-DD",
    )
    units_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
