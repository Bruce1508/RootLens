from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    order_id: Mapped[str] = mapped_column(
        String, ForeignKey("orders.order_id"), primary_key=True, index=True
    )
    payment_sequential: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_type: Mapped[str] = mapped_column(String)
    payment_installments: Mapped[int] = mapped_column(Integer)
    payment_value: Mapped[Decimal] = mapped_column(Numeric(10, 2))
