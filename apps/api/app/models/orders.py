from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String, ForeignKey("customers.customer_id"), index=True
    )
    order_status: Mapped[str] = mapped_column(String, index=True)
    order_purchase_timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    order_approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    order_delivered_carrier_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    order_delivered_customer_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    order_estimated_delivery_date: Mapped[datetime] = mapped_column(DateTime)
