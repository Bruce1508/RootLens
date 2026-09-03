from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        String, ForeignKey("investigations.investigation_id"), index=True
    )
    statement: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    confidence: Mapped[str | None] = mapped_column(String, nullable=True)
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    contradicting_evidence_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
