from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String, primary_key=True)
    # No FK to product_category_translations: the real Olist dataset's own
    # translation file is known to omit a handful of category names that
    # do appear in products.csv (e.g. "pc_gamer"). No app code joins
    # through this column via the FK (grep-verified), so the constraint
    # only served to reject real, otherwise-valid rows.
    product_category_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    product_weight_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_length_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_width_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
