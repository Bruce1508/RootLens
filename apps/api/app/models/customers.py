from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_unique_id: Mapped[str] = mapped_column(String, index=True)
    customer_zip_code_prefix: Mapped[str] = mapped_column(String)
    customer_city: Mapped[str] = mapped_column(String)
    customer_state: Mapped[str] = mapped_column(String(2), index=True)
