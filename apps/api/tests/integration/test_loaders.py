from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, Order

_FIXTURE_CUSTOMERS_CSV = """customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state
cust-1,unique-1,01001,sao paulo,SP
cust-2,unique-2,20000,rio de janeiro,RJ
"""

_FIXTURE_ORDERS_CSV = """order_id,customer_id,order_status,order_purchase_timestamp,order_approved_at,order_delivered_carrier_date,order_delivered_customer_date,order_estimated_delivery_date
order-1,cust-1,delivered,2018-01-05 10:00:00,2018-01-05 11:00:00,2018-01-06 08:00:00,2018-01-10 15:00:00,2018-01-12 00:00:00
order-2,cust-2,canceled,2018-01-06 09:00:00,,,,2018-01-15 00:00:00
"""


def test_load_customers_inserts_normalized_rows(db_session: Session, tmp_path: Path) -> None:
    from app.ingestion.loaders import load_customers

    csv_path = tmp_path / "olist_customers_dataset.csv"
    csv_path.write_text(_FIXTURE_CUSTOMERS_CSV)

    result = load_customers(db_session, csv_path)

    assert result.inserted_count == 2
    assert result.rejected_count == 0

    rows = db_session.execute(select(Customer).order_by(Customer.customer_id)).scalars().all()
    assert [c.customer_id for c in rows] == ["cust-1", "cust-2"]
    assert rows[0].customer_state == "SP"


def test_load_orders_inserts_and_normalizes_nullable_dates(
    db_session: Session, tmp_path: Path
) -> None:
    from app.ingestion.loaders import load_customers, load_orders

    customers_csv = tmp_path / "olist_customers_dataset.csv"
    customers_csv.write_text(_FIXTURE_CUSTOMERS_CSV)
    load_customers(db_session, customers_csv)

    orders_csv = tmp_path / "olist_orders_dataset.csv"
    orders_csv.write_text(_FIXTURE_ORDERS_CSV)

    result = load_orders(db_session, orders_csv)

    assert result.inserted_count == 2
    assert result.rejected_count == 0

    canceled = db_session.execute(select(Order).where(Order.order_id == "order-2")).scalar_one()
    assert canceled.order_status == "canceled"
    assert canceled.order_approved_at is None
    assert canceled.order_delivered_customer_date is None
