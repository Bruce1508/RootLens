from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[str] = mapped_column(String, primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        String, ForeignKey("investigations.investigation_id"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String)
    params: Mapped[dict] = mapped_column(JSONB)
    sql: Mapped[str] = mapped_column(String)
    columns: Mapped[list[str]] = mapped_column(JSONB)
    rows: Mapped[list[dict]] = mapped_column(JSONB)
    row_count: Mapped[int] = mapped_column(Integer)
    execution_ms: Mapped[float] = mapped_column(Float)
    warnings: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
