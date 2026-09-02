import argparse
import sys
from pathlib import Path

from sqlalchemy import text

from app.core.config import Settings
from app.db.session import WriteSessionLocal
from app.ingestion.loaders import (
    load_category_translations,
    load_customers,
    load_order_items,
    load_orders,
    load_payments,
    load_products,
    load_reviews,
    load_sellers,
)
from app.ingestion.manifest import (
    REQUIRED_FILES,
    IngestionValidationError,
    validate_source_directory,
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

# Load order respects foreign keys: dimension/lookup tables first, then
# tables that reference them.
_LOAD_STEPS = [
    ("category_translations", load_category_translations),
    ("customers", load_customers),
    ("sellers", load_sellers),
    ("products", load_products),
    ("orders", load_orders),
    ("order_items", load_order_items),
    ("payments", load_payments),
    ("reviews", load_reviews),
]

# Reverse FK order for --reset (children before parents).
_RESET_ORDER = [
    Review,
    Payment,
    OrderItem,
    Order,
    Product,
    Seller,
    Customer,
    ProductCategoryTranslation,
]


def _reset_tables() -> None:
    with WriteSessionLocal() as session:
        for model in _RESET_ORDER:
            session.execute(text(f'TRUNCATE TABLE "{model.__tablename__}" CASCADE'))
        session.commit()


def run_import(source_dir: Path, reset: bool) -> int:
    if reset and Settings().environment != "development":
        print(
            "Refusing --reset: ENVIRONMENT is not 'development'. "
            "This flag truncates business tables and is dev-only (see ADR: ingestion "
            "idempotency).",
            file=sys.stderr,
        )
        return 1

    try:
        validate_source_directory(source_dir)
    except IngestionValidationError as e:
        print("Ingestion validation failed:", file=sys.stderr)
        for problem in e.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    if reset:
        _reset_tables()

    total_inserted = 0
    with WriteSessionLocal() as session:
        for key, loader in _LOAD_STEPS:
            filename = str(REQUIRED_FILES[key]["filename"])
            result = loader(session, source_dir / filename)
            print(f"{key}: inserted={result.inserted_count} rejected={result.rejected_count}")
            total_inserted += result.inserted_count
        session.commit()

    print(f"Done. Total rows inserted: {total_inserted}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.ingestion.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import Olist CSVs into Postgres")
    import_parser.add_argument("--source", required=True, help="Directory containing Olist CSVs")
    import_parser.add_argument(
        "--reset",
        action="store_true",
        help="Truncate business tables before importing (development only)",
    )

    args = parser.parse_args()

    if args.command == "import":
        exit_code = run_import(Path(args.source), reset=args.reset)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
