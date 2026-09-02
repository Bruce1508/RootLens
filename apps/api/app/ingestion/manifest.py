import csv
from pathlib import Path

REQUIRED_FILES: dict[str, dict[str, object]] = {
    "customers": {
        "filename": "olist_customers_dataset.csv",
        "columns": [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ],
    },
    "orders": {
        "filename": "olist_orders_dataset.csv",
        "columns": [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    },
    "order_items": {
        "filename": "olist_order_items_dataset.csv",
        "columns": [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ],
    },
    "payments": {
        "filename": "olist_order_payments_dataset.csv",
        "columns": [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ],
    },
    "reviews": {
        "filename": "olist_order_reviews_dataset.csv",
        "columns": [
            "review_id",
            "order_id",
            "review_score",
            "review_creation_date",
            "review_answer_timestamp",
        ],
    },
    "products": {
        "filename": "olist_products_dataset.csv",
        "columns": [
            "product_id",
            "product_category_name",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ],
    },
    "sellers": {
        "filename": "olist_sellers_dataset.csv",
        "columns": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    },
    "category_translations": {
        "filename": "product_category_name_translation.csv",
        "columns": ["product_category_name", "product_category_name_english"],
    },
}


class IngestionValidationError(Exception):
    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("; ".join(problems))


def validate_source_directory(source_dir: Path) -> None:
    problems: list[str] = []

    for spec in REQUIRED_FILES.values():
        filename = str(spec["filename"])
        file_path = source_dir / filename
        if not file_path.exists():
            problems.append(f"missing required file: {filename}")
            continue

        with file_path.open(newline="", encoding="utf-8") as f:
            header = next(csv.reader(f), [])
        header_set = set(header)
        required_columns = spec["columns"]
        assert isinstance(required_columns, list)
        missing_columns = [c for c in required_columns if c not in header_set]
        if missing_columns:
            problems.append(f"{filename}: missing required columns: {', '.join(missing_columns)}")

    if problems:
        raise IngestionValidationError(problems)
