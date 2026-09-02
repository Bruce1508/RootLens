from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductCategoryTranslation(Base):
    __tablename__ = "product_category_translations"

    product_category_name: Mapped[str] = mapped_column(String, primary_key=True)
    product_category_name_english: Mapped[str] = mapped_column(String)
