from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OrderItem, Payment, Product, ProductCategoryTranslation, Review, Seller

_CATEGORY_CSV = """product_category_name,product_category_name_english
beleza_saude,health_beauty
"""

_SELLERS_CSV = """seller_id,seller_zip_code_prefix,seller_city,seller_state
seller-1,10000,campinas,SP
"""

_PRODUCTS_CSV = """product_id,product_category_name,product_weight_g,product_length_cm,product_height_cm,product_width_cm
prod-1,beleza_saude,500,20,10,15
prod-2,,,,,
"""

_ORDER_ITEMS_CSV = """order_id,order_item_id,product_id,seller_id,shipping_limit_date,price,freight_value
order-1,1,prod-1,seller-1,2018-01-08 00:00:00,129.90,15.50
"""

_PAYMENTS_CSV = """order_id,payment_sequential,payment_type,payment_installments,payment_value
order-1,1,credit_card,3,145.40
"""

_REVIEWS_CSV = """review_id,order_id,review_score,review_creation_date,review_answer_timestamp
review-1,order-1,5,2018-01-11 00:00:00,2018-01-12 09:00:00
"""


def _write(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


def _seed_order_prereqs(db_session: Session, tmp_path: Path) -> None:
    from app.ingestion.loaders import load_customers, load_orders

    load_customers(
        db_session,
        _write(
            tmp_path / "customers.csv",
            "customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state\n"
            "cust-1,unique-1,01001,sao paulo,SP\n",
        ),
    )
    load_orders(
        db_session,
        _write(
            tmp_path / "orders.csv",
            "order_id,customer_id,order_status,order_purchase_timestamp,order_approved_at,"
            "order_delivered_carrier_date,order_delivered_customer_date,"
            "order_estimated_delivery_date\n"
            "order-1,cust-1,delivered,2018-01-05 10:00:00,2018-01-05 11:00:00,"
            "2018-01-06 08:00:00,2018-01-10 15:00:00,2018-01-12 00:00:00\n",
        ),
    )


def test_load_category_translations(db_session: Session, tmp_path: Path) -> None:
    from app.ingestion.loaders import load_category_translations

    result = load_category_translations(db_session, _write(tmp_path / "cat.csv", _CATEGORY_CSV))

    assert result.inserted_count == 1
    row = db_session.execute(select(ProductCategoryTranslation)).scalar_one()
    assert row.product_category_name_english == "health_beauty"


def test_load_sellers(db_session: Session, tmp_path: Path) -> None:
    from app.ingestion.loaders import load_sellers

    result = load_sellers(db_session, _write(tmp_path / "sellers.csv", _SELLERS_CSV))

    assert result.inserted_count == 1
    row = db_session.execute(select(Seller)).scalar_one()
    assert row.seller_state == "SP"


def test_load_products_with_nullable_category(db_session: Session, tmp_path: Path) -> None:
    from app.ingestion.loaders import load_category_translations, load_products

    load_category_translations(db_session, _write(tmp_path / "cat.csv", _CATEGORY_CSV))
    result = load_products(db_session, _write(tmp_path / "products.csv", _PRODUCTS_CSV))

    assert result.inserted_count == 2
    rows = {p.product_id: p for p in db_session.execute(select(Product)).scalars().all()}
    assert rows["prod-1"].product_category_name == "beleza_saude"
    assert rows["prod-2"].product_category_name is None
    assert rows["prod-2"].product_weight_g is None


def test_load_order_items_payments_reviews(db_session: Session, tmp_path: Path) -> None:
    from app.ingestion.loaders import (
        load_category_translations,
        load_order_items,
        load_payments,
        load_products,
        load_reviews,
        load_sellers,
    )

    _seed_order_prereqs(db_session, tmp_path)
    load_category_translations(db_session, _write(tmp_path / "cat.csv", _CATEGORY_CSV))
    load_sellers(db_session, _write(tmp_path / "sellers.csv", _SELLERS_CSV))
    load_products(db_session, _write(tmp_path / "products.csv", _PRODUCTS_CSV))

    item_result = load_order_items(
        db_session, _write(tmp_path / "order_items.csv", _ORDER_ITEMS_CSV)
    )
    payment_result = load_payments(db_session, _write(tmp_path / "payments.csv", _PAYMENTS_CSV))
    review_result = load_reviews(db_session, _write(tmp_path / "reviews.csv", _REVIEWS_CSV))

    assert item_result.inserted_count == 1
    assert payment_result.inserted_count == 1
    assert review_result.inserted_count == 1

    item = db_session.execute(select(OrderItem)).scalar_one()
    assert item.price == Decimal("129.90")

    payment = db_session.execute(select(Payment)).scalar_one()
    assert payment.payment_value == Decimal("145.40")

    review = db_session.execute(select(Review)).scalar_one()
    assert review.review_score == 5
