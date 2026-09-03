from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[str] = mapped_column(
        String, ForeignKey("investigations.investigation_id"), index=True
    )
    status: Mapped[str] = mapped_column(String)
    headline: Mapped[str] = mapped_column(String)
    observed_change: Mapped[dict] = mapped_column(JSONB)
    findings: Mapped[list[dict]] = mapped_column(JSONB)
    limitations: Mapped[list[str]] = mapped_column(JSONB)
    recommended_next_checks: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
