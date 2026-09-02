from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(String, ForeignKey("orders.order_id"), index=True)
    review_score: Mapped[int] = mapped_column(Integer)
    review_creation_date: Mapped[datetime] = mapped_column(DateTime)
    review_answer_timestamp: Mapped[datetime] = mapped_column(DateTime)
