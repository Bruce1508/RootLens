import random

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.analytics.schemas import DateRange
from app.analytics.validation import exclusive_end
from app.evaluation.schemas import Template
from app.models import Customer, Order, OrderItem, Product

_CANCELLED_STATUS = "canceled"
_ALREADY_EXCLUDED_STATUSES = ["canceled", "unavailable"]

# Qualitative severity -> fraction of eligible orders mutated. Chosen so a
# "high" cancellation spike lands well above the real dataset's baseline
# cancellation rate (~0.6%, verified locally) and is unambiguously
# detectable; "low" is still a clear signal, just a smaller one.
SEVERITY_FRACTIONS: dict[str, float] = {"low": 0.08, "medium": 0.18, "high": 0.30}
_DEFAULT_SEVERITY = "medium"


def _severity_fraction(severity: str | None) -> float:
    return SEVERITY_FRACTIONS.get(
        severity or _DEFAULT_SEVERITY, SEVERITY_FRACTIONS[_DEFAULT_SEVERITY]
    )


def _eligible_order_ids(
    session: Session,
    period: DateRange,
    *,
    customer_state: str | None = None,
    product_category: str | None = None,
    seller_id: str | None = None,
) -> list[str]:
    stmt = select(Order.order_id.distinct()).where(
        Order.order_purchase_timestamp >= period.start,
        Order.order_purchase_timestamp < exclusive_end(period),
        Order.order_status.notin_(_ALREADY_EXCLUDED_STATUSES),
    )
    if customer_state is not None:
        stmt = stmt.join(Customer, Customer.customer_id == Order.customer_id).where(
            Customer.customer_state == customer_state
        )
    if product_category is not None or seller_id is not None:
        stmt = stmt.join(OrderItem, OrderItem.order_id == Order.order_id)
        if product_category is not None:
            stmt = stmt.join(Product, Product.product_id == OrderItem.product_id).where(
                Product.product_category_name == product_category
            )
        if seller_id is not None:
            stmt = stmt.where(OrderItem.seller_id == seller_id)
    return [row[0] for row in session.execute(stmt).all()]


def _sample(order_ids: list[str], fraction: float, seed: int) -> list[str]:
    """Deterministic given (order_ids, fraction, seed): sorts first since
    Postgres doesn't guarantee row order without ORDER BY, then shuffles
    with a seeded RNG so the same inputs always mutate the same orders."""
    if not order_ids:
        return []
    shuffled = sorted(order_ids)
    random.Random(seed).shuffle(shuffled)
    sample_size = max(1, round(len(shuffled) * fraction))
    return shuffled[:sample_size]


def apply_cancellation_spike(
    session: Session,
    period: DateRange,
    customer_state: str,
    product_category: str,
    severity: str | None,
    seed: int,
) -> int:
    """Flips a seeded-random fraction of orders matching (state, category)
    within the incident period to 'canceled', in whatever `orders` table
    the session's search_path resolves to (the scenario schema's clone —
    see app.evaluation.scenario_schema). Returns the number mutated."""
    eligible = _eligible_order_ids(
        session, period, customer_state=customer_state, product_category=product_category
    )
    to_cancel = _sample(eligible, _severity_fraction(severity), seed)
    if to_cancel:
        session.execute(
            update(Order)
            .where(Order.order_id.in_(to_cancel))
            .values(order_status=_CANCELLED_STATUS)
        )
        session.commit()
    return len(to_cancel)


def apply_order_volume_decline(
    session: Session,
    period: DateRange,
    customer_state: str,
    severity: str | None,
    seed: int,
) -> int:
    """Deletes a seeded-random fraction of orders in `customer_state`
    within the incident period — a genuine drop in order count, not a
    cancellation. Returns the number removed."""
    eligible = _eligible_order_ids(session, period, customer_state=customer_state)
    to_remove = _sample(eligible, _severity_fraction(severity), seed)
    if to_remove:
        session.execute(delete(Order).where(Order.order_id.in_(to_remove)))
        session.commit()
    return len(to_remove)


def apply_seller_category_decline(
    session: Session,
    period: DateRange,
    product_category: str,
    severity: str | None,
    seed: int,
    seller_id: str | None = None,
) -> int:
    """Deletes a seeded-random fraction of orders touching `product_category`
    within the incident period — narrowed to `seller_id` when given (the
    seller-flavored half of this template; see
    app.evaluation.schemas.SELLER_TO_RESOLVE). Returns the number removed."""
    eligible = _eligible_order_ids(
        session, period, product_category=product_category, seller_id=seller_id
    )
    to_remove = _sample(eligible, _severity_fraction(severity), seed)
    if to_remove:
        session.execute(delete(Order).where(Order.order_id.in_(to_remove)))
        session.commit()
    return len(to_remove)


def apply_incident(
    session: Session,
    template: Template,
    period: DateRange,
    dimensions: dict[str, str],
    severity: str | None,
    seed: int,
) -> int:
    """Dispatches to the right template function by scenario `template`
    name, extracting the dimension values it needs from `dimensions`
    (app.evaluation.seed's resolved ground-truth dict)."""
    if template == "cancellation_spike":
        return apply_cancellation_spike(
            session,
            period,
            dimensions["customer_state"],
            dimensions["product_category"],
            severity,
            seed,
        )
    if template == "order_volume_decline":
        return apply_order_volume_decline(
            session, period, dimensions["customer_state"], severity, seed
        )
    if template == "seller_category_decline":
        return apply_seller_category_decline(
            session,
            period,
            dimensions["product_category"],
            severity,
            seed,
            seller_id=dimensions.get("seller"),
        )
    raise ValueError(f"unknown incident template: {template!r}")
