import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ingestion.normalize import (
    normalize_decimal,
    normalize_int,
    normalize_str,
    normalize_timestamp,
)
from app.models import (
    Customer,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductCategoryTranslation,
    Review,
    Seller,
)


@dataclass
class LoadResult:
    inserted_count: int
    rejected_count: int


def _upsert(session: Session, model: type, rows: list[dict], conflict_columns: list[str]) -> None:
    if not rows:
        return
    stmt = pg_insert(model).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=conflict_columns)
    session.execute(stmt)


def load_customers(session: Session, csv_path: Path) -> LoadResult:
    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            rows.append(
                {
                    "customer_id": normalize_str(record["customer_id"]),
                    "customer_unique_id": normalize_str(record["customer_unique_id"]),
                    "customer_zip_code_prefix": normalize_str(record["customer_zip_code_prefix"]),
                    "customer_city": normalize_str(record["customer_city"]),
                    "customer_state": normalize_str(record["customer_state"]),
                }
            )

    _upsert(session, Customer, rows, conflict_columns=["customer_id"])
    return LoadResult(inserted_count=len(rows), rejected_count=0)


def load_orders(session: Session, csv_path: Path) -> LoadResult:
    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            rows.append(
                {
                    "order_id": normalize_str(record["order_id"]),
                    "customer_id": normalize_str(record["customer_id"]),
                    "order_status": normalize_str(record["order_status"]),
                    "order_purchase_timestamp": normalize_timestamp(
                        record["order_purchase_timestamp"]
                    ),
                    "order_approved_at": normalize_timestamp(record["order_approved_at"]),
                    "order_delivered_carrier_date": normalize_timestamp(
                        record["order_delivered_carrier_date"]
                    ),
                    "order_delivered_customer_date": normalize_timestamp(
                        record["order_delivered_customer_date"]
                    ),
                    "order_estimated_delivery_date": normalize_timestamp(
                        record["order_estimated_delivery_date"]
                    ),
                }
            )

    _upsert(session, Order, rows, conflict_columns=["order_id"])
    return LoadResult(inserted_count=len(rows), rejected_count=0)


def load_category_translations(session: Session, csv_path: Path) -> LoadResult:
    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            rows.append(
                {
                    "product_category_name": normalize_str(record["product_category_name"]),
                    "product_category_name_english": normalize_str(
                        record["product_category_name_english"]
                    ),
                }
            )

    _upsert(session, ProductCategoryTranslation, rows, conflict_columns=["product_category_name"])
    return LoadResult(inserted_count=len(rows), rejected_count=0)


def load_sellers(session: Session, csv_path: Path) -> LoadResult:
    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            rows.append(
                {
                    "seller_id": normalize_str(record["seller_id"]),
                    "seller_zip_code_prefix": normalize_str(record["seller_zip_code_prefix"]),
                    "seller_city": normalize_str(record["seller_city"]),
                    "seller_state": normalize_str(record["seller_state"]),
                }
            )

    _upsert(session, Seller, rows, conflict_columns=["seller_id"])
    return LoadResult(inserted_count=len(rows), rejected_count=0)


def load_products(session: Session, csv_path: Path) -> LoadResult:
    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            rows.append(
                {
                    "product_id": normalize_str(record["product_id"]),
                    "product_category_name": normalize_str(record["product_category_name"]),
                    "product_weight_g": normalize_int(record["product_weight_g"]),
                    "product_length_cm": normalize_int(record["product_length_cm"]),
                    "product_height_cm": normalize_int(record["product_height_cm"]),
                    "product_width_cm": normalize_int(record["product_width_cm"]),
                }
            )

    _upsert(session, Product, rows, conflict_columns=["product_id"])
    return LoadResult(inserted_count=len(rows), rejected_count=0)


def load_order_items(session: Session, csv_path: Path) -> LoadResult:
    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            rows.append(
                {
                    "order_id": normalize_str(record["order_id"]),
                    "order_item_id": normalize_int(record["order_item_id"]),
                    "product_id": normalize_str(record["product_id"]),
                    "seller_id": normalize_str(record["seller_id"]),
                    "shipping_limit_date": normalize_timestamp(record["shipping_limit_date"]),
                    "price": normalize_decimal(record["price"]),
                    "freight_value": normalize_decimal(record["freight_value"]),
                }
            )

    _upsert(session, OrderItem, rows, conflict_columns=["order_id", "order_item_id"])
    return LoadResult(inserted_count=len(rows), rejected_count=0)


def load_payments(session: Session, csv_path: Path) -> LoadResult:
    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            rows.append(
                {
                    "order_id": normalize_str(record["order_id"]),
                    "payment_sequential": normalize_int(record["payment_sequential"]),
                    "payment_type": normalize_str(record["payment_type"]),
                    "payment_installments": normalize_int(record["payment_installments"]),
                    "payment_value": normalize_decimal(record["payment_value"]),
                }
            )

    _upsert(session, Payment, rows, conflict_columns=["order_id", "payment_sequential"])
    return LoadResult(inserted_count=len(rows), rejected_count=0)


def load_reviews(session: Session, csv_path: Path) -> LoadResult:
    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for record in csv.DictReader(f):
            rows.append(
                {
                    "review_id": normalize_str(record["review_id"]),
                    "order_id": normalize_str(record["order_id"]),
                    "review_score": normalize_int(record["review_score"]),
                    "review_creation_date": normalize_timestamp(record["review_creation_date"]),
                    "review_answer_timestamp": normalize_timestamp(
                        record["review_answer_timestamp"]
                    ),
                }
            )

    _upsert(session, Review, rows, conflict_columns=["review_id"])
    return LoadResult(inserted_count=len(rows), rejected_count=0)
