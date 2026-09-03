import uuid
from datetime import date, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.analytics.schemas import DateRange
from app.evaluation.incidents import (
    apply_cancellation_spike,
    apply_incident,
    apply_order_volume_decline,
    apply_seller_category_decline,
)
from app.models import Customer, Order, OrderItem, Product, Seller

_PERIOD = DateRange(start=date(2018, 1, 1), end=date(2018, 1, 31))


def _seed_catalog(session: Session) -> None:
    session.add_all(
        [
            Product(product_id="prod-widgets", product_category_name="widgets"),
            Product(product_id="prod-gadgets", product_category_name="gadgets"),
            Seller(
                seller_id="seller-a",
                seller_zip_code_prefix="0",
                seller_city="c",
                seller_state="SP",
            ),
            Seller(
                seller_id="seller-b",
                seller_zip_code_prefix="0",
                seller_city="c",
                seller_state="SP",
            ),
            Customer(
                customer_id="cust-sp",
                customer_unique_id="cust-sp-u",
                customer_zip_code_prefix="0",
                customer_city="c",
                customer_state="SP",
            ),
            Customer(
                customer_id="cust-rj",
                customer_unique_id="cust-rj-u",
                customer_zip_code_prefix="0",
                customer_city="c",
                customer_state="RJ",
            ),
        ]
    )
    session.flush()


def _make_orders(
    session: Session, *, customer_id: str, category: str, seller_id: str, count: int
) -> list[str]:
    order_ids = [str(uuid.uuid4()) for _ in range(count)]
    for order_id in order_ids:
        session.add(
            Order(
                order_id=order_id,
                customer_id=customer_id,
                order_status="delivered",
                order_purchase_timestamp=datetime(2018, 1, 15),
                order_estimated_delivery_date=datetime(2018, 1, 25),
            )
        )
    session.flush()
    product_id = "prod-widgets" if category == "widgets" else "prod-gadgets"
    for order_id in order_ids:
        session.add(
            OrderItem(
                order_id=order_id,
                order_item_id=1,
                product_id=product_id,
                seller_id=seller_id,
                shipping_limit_date=datetime(2018, 1, 20),
                price=10.0,
                freight_value=1.0,
            )
        )
    session.flush()
    return order_ids


def _clone_orders_into_scenario_schema(session: Session, schema_name: str) -> None:
    """A same-transaction, non-committing stand-in for
    app.evaluation.scenario_schema.provision_scenario_schema — that
    function commits (needed so a *different* pooled connection can see
    the clone in production), which would break this test module's
    rely-on-rollback isolation via the shared db_session fixture. DDL is
    transactional in Postgres, so this still gets cleaned up by the
    fixture's rollback like everything else."""
    session.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    session.execute(text(f'CREATE TABLE "{schema_name}".orders AS TABLE public.orders'))
    session.execute(text(f'SET search_path TO "{schema_name}", public'))


def test_apply_cancellation_spike_only_cancels_matching_state_and_category(
    db_session: Session,
) -> None:
    _seed_catalog(db_session)
    sp_widgets = _make_orders(
        db_session, customer_id="cust-sp", category="widgets", seller_id="seller-a", count=10
    )
    sp_gadgets = _make_orders(
        db_session, customer_id="cust-sp", category="gadgets", seller_id="seller-a", count=10
    )
    rj_widgets = _make_orders(
        db_session, customer_id="cust-rj", category="widgets", seller_id="seller-a", count=10
    )
    _clone_orders_into_scenario_schema(db_session, "scenario_test_cs")

    cancelled_count = apply_cancellation_spike(
        db_session, _PERIOD, "SP", "widgets", severity="high", seed=7
    )
    assert cancelled_count == 3  # 30% of 10, rounded

    statuses = {
        order_id: db_session.get(Order, order_id).order_status
        for order_id in sp_widgets + sp_gadgets + rj_widgets
    }
    assert sum(1 for o in sp_widgets if statuses[o] == "canceled") == cancelled_count
    assert all(statuses[o] == "delivered" for o in sp_gadgets)
    assert all(statuses[o] == "delivered" for o in rj_widgets)

    # The clone was mutated, not the real public.orders it was copied from.
    original_status = db_session.execute(
        text("SELECT order_status FROM public.orders WHERE order_id = :oid"),
        {"oid": sp_widgets[0]},
    ).scalar_one()
    assert original_status == "delivered"


def test_apply_order_volume_decline_only_removes_matching_state(db_session: Session) -> None:
    _seed_catalog(db_session)
    sp_orders = _make_orders(
        db_session, customer_id="cust-sp", category="widgets", seller_id="seller-a", count=10
    )
    rj_orders = _make_orders(
        db_session, customer_id="cust-rj", category="widgets", seller_id="seller-a", count=10
    )
    _clone_orders_into_scenario_schema(db_session, "scenario_test_ov")

    removed_count = apply_order_volume_decline(db_session, _PERIOD, "RJ", severity="medium", seed=3)
    assert removed_count == round(10 * 0.18)

    remaining_rj = (
        db_session.execute(select(Order.order_id).where(Order.order_id.in_(rj_orders)))
        .scalars()
        .all()
    )
    assert len(remaining_rj) == 10 - removed_count

    remaining_sp = (
        db_session.execute(select(Order.order_id).where(Order.order_id.in_(sp_orders)))
        .scalars()
        .all()
    )
    assert len(remaining_sp) == 10


def test_apply_seller_category_decline_narrows_to_seller_when_given(db_session: Session) -> None:
    _seed_catalog(db_session)
    seller_a_orders = _make_orders(
        db_session, customer_id="cust-sp", category="widgets", seller_id="seller-a", count=10
    )
    seller_b_orders = _make_orders(
        db_session, customer_id="cust-sp", category="widgets", seller_id="seller-b", count=10
    )
    _clone_orders_into_scenario_schema(db_session, "scenario_test_scd")

    removed_count = apply_seller_category_decline(
        db_session, _PERIOD, "widgets", severity="low", seed=9, seller_id="seller-a"
    )
    assert removed_count == max(1, round(10 * 0.08))

    remaining_a = (
        db_session.execute(select(Order.order_id).where(Order.order_id.in_(seller_a_orders)))
        .scalars()
        .all()
    )
    remaining_b = (
        db_session.execute(select(Order.order_id).where(Order.order_id.in_(seller_b_orders)))
        .scalars()
        .all()
    )
    assert len(remaining_a) == 10 - removed_count
    assert len(remaining_b) == 10


def test_apply_incident_dispatches_cancellation_spike_by_template_name(
    db_session: Session,
) -> None:
    _seed_catalog(db_session)
    _make_orders(
        db_session, customer_id="cust-sp", category="widgets", seller_id="seller-a", count=10
    )
    _clone_orders_into_scenario_schema(db_session, "scenario_test_dispatch")

    mutated = apply_incident(
        db_session,
        "cancellation_spike",
        _PERIOD,
        {"customer_state": "SP", "product_category": "widgets"},
        "high",
        seed=7,
    )
    assert mutated == 3
