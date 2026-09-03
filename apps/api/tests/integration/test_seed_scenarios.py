import uuid
from datetime import date, datetime
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.evaluation import seed
from app.models import Customer, EvalGroundTruth, EvalScenario, Order, OrderItem, Product, Seller


def test_seed_scenarios_is_idempotent_and_writes_both_tables(db_session: Session) -> None:
    # Bypasses the real-data seller lookup — covered separately by
    # test_resolve_top_seller_picks_the_seller_with_the_most_orders below —
    # so this test only needs to exercise the upsert/flush-ordering logic.
    with patch.object(seed, "_resolve_dimensions", side_effect=lambda _session, s: s.dimensions):
        first_count = seed.seed_scenarios(db_session)
        second_count = seed.seed_scenarios(db_session)

    assert first_count == 35
    assert second_count == 35

    scenario_count = db_session.execute(select(EvalScenario)).scalars().all()
    ground_truth_count = db_session.execute(select(EvalGroundTruth)).scalars().all()
    assert len(scenario_count) == 35
    assert len(ground_truth_count) == 35

    cs_01 = db_session.get(EvalScenario, "cs-01")
    assert cs_01 is not None
    assert cs_01.template == "cancellation_spike"

    cs_01_gt = db_session.get(EvalGroundTruth, "cs-01")
    assert cs_01_gt is not None
    assert cs_01_gt.primary_driver == "cancellation"
    assert cs_01_gt.dimensions["customer_state"] == "SP"


def test_resolve_top_seller_picks_the_seller_with_the_most_orders(db_session: Session) -> None:
    product = Product(product_id="prod-1", product_category_name="widgets")
    seller_a = Seller(
        seller_id="seller-a", seller_zip_code_prefix="00000", seller_city="c", seller_state="SP"
    )
    seller_b = Seller(
        seller_id="seller-b", seller_zip_code_prefix="00000", seller_city="c", seller_state="SP"
    )
    customer = Customer(
        customer_id="cust-1",
        customer_unique_id="cust-1-unique",
        customer_zip_code_prefix="00000",
        customer_city="c",
        customer_state="SP",
    )
    db_session.add_all([product, seller_a, seller_b, customer])
    db_session.flush()

    # seller-a gets 3 orders, seller-b gets 1 — top seller should be seller-a.
    order_ids = [str(uuid.uuid4()) for _ in range(4)]
    for order_id in order_ids:
        db_session.add(
            Order(
                order_id=order_id,
                customer_id="cust-1",
                order_status="delivered",
                order_purchase_timestamp=datetime(2018, 1, 10),
                order_estimated_delivery_date=datetime(2018, 1, 20),
            )
        )
    db_session.flush()

    seller_ids = ["seller-a", "seller-a", "seller-a", "seller-b"]
    for order_id, seller_id in zip(order_ids, seller_ids, strict=True):
        db_session.add(
            OrderItem(
                order_id=order_id,
                order_item_id=1,
                product_id="prod-1",
                seller_id=seller_id,
                shipping_limit_date=datetime(2018, 1, 15),
                price=10.0,
                freight_value=1.0,
            )
        )
    db_session.flush()

    top_seller = seed._resolve_top_seller(
        db_session, "widgets", date(2018, 1, 1), date(2018, 1, 31)
    )
    assert top_seller == "seller-a"
