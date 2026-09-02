from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Seller(Base):
    __tablename__ = "sellers"

    seller_id: Mapped[str] = mapped_column(String, primary_key=True)
    seller_zip_code_prefix: Mapped[str] = mapped_column(String)
    seller_city: Mapped[str] = mapped_column(String)
    seller_state: Mapped[str] = mapped_column(String(2), index=True)
