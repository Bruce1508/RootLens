from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    order_id: Mapped[str] = mapped_column(
        String, ForeignKey("orders.order_id"), primary_key=True, index=True
    )
    order_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[str] = mapped_column(String, ForeignKey("products.product_id"), index=True)
    seller_id: Mapped[str] = mapped_column(String, ForeignKey("sellers.seller_id"), index=True)
    shipping_limit_date: Mapped[datetime] = mapped_column(DateTime)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    freight_value: Mapped[Decimal] = mapped_column(Numeric(10, 2))
