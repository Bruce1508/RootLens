from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String, primary_key=True)
    product_category_name: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("product_category_translations.product_category_name"),
        nullable=True,
        index=True,
    )
    product_weight_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_length_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_width_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
