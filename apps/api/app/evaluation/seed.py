from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import WriteSessionLocal
from app.evaluation.scenarios import SCENARIOS
from app.evaluation.schemas import SELLER_TO_RESOLVE, ScenarioSpec
from app.models import EvalGroundTruth, EvalScenario, Order, OrderItem, Product


def _resolve_top_seller(
    session: Session, category: str, period_start: date, period_end: date
) -> str:
    """The seller with the most distinct orders for `category` during the
    period — used to ground seller-flavored seller_category_decline
    scenarios in a real seller rather than a hand-picked ID (see
    SELLER_TO_RESOLVE)."""
    stmt = (
        select(OrderItem.seller_id, func.count(func.distinct(OrderItem.order_id)).label("cnt"))
        .join(Order, Order.order_id == OrderItem.order_id)
        .join(Product, Product.product_id == OrderItem.product_id)
        .where(
            Product.product_category_name == category,
            Order.order_purchase_timestamp >= period_start,
            Order.order_purchase_timestamp < period_end + timedelta(days=1),
        )
        .group_by(OrderItem.seller_id)
        .order_by(func.count(func.distinct(OrderItem.order_id)).desc())
        .limit(1)
    )
    row = session.execute(stmt).first()
    if row is None:
        raise ValueError(
            f"no sellers found for category={category!r} in "
            f"{period_start}..{period_end} — is the real dataset ingested? (make ingest)"
        )
    return row.seller_id


def _resolve_dimensions(session: Session, scenario: ScenarioSpec) -> dict[str, str]:
    dimensions = dict(scenario.dimensions)
    if dimensions.get("seller") == SELLER_TO_RESOLVE:
        dimensions["seller"] = _resolve_top_seller(
            session,
            dimensions["product_category"],
            scenario.current_period_start,
            scenario.current_period_end,
        )
    return dimensions


def seed_scenarios(session: Session) -> int:
    """Idempotent upsert of app.evaluation.scenarios.SCENARIOS into the
    hidden `eval` schema (ADR-0007). Returns the number of scenarios
    written. Requires the real Olist dataset to already be ingested —
    seller-flavored scenarios resolve a real seller_id from it.

    Two passes with a flush in between, rather than interleaving both
    tables in one pass: eval_ground_truth.scenario_id FKs to
    eval_scenarios.scenario_id, and letting the ORM's implicit flush
    ordering sort out a cross-schema dependency for a brand-new table is
    less reliable than just being explicit about it."""
    resolved_dimensions_by_id: dict[str, dict[str, str]] = {}

    for scenario in SCENARIOS:
        resolved_dimensions_by_id[scenario.scenario_id] = _resolve_dimensions(session, scenario)

        eval_scenario = session.get(EvalScenario, scenario.scenario_id) or EvalScenario(
            scenario_id=scenario.scenario_id
        )
        eval_scenario.template = scenario.template
        eval_scenario.metric = scenario.metric
        eval_scenario.current_period_start = scenario.current_period_start
        eval_scenario.current_period_end = scenario.current_period_end
        eval_scenario.comparison_period_start = scenario.comparison_period_start
        eval_scenario.comparison_period_end = scenario.comparison_period_end
        eval_scenario.split = scenario.split
        eval_scenario.seed = scenario.seed
        eval_scenario.is_unanswerable = scenario.is_unanswerable
        eval_scenario.question = scenario.question
        session.add(eval_scenario)

    session.flush()

    for scenario in SCENARIOS:
        ground_truth = session.get(EvalGroundTruth, scenario.scenario_id) or EvalGroundTruth(
            scenario_id=scenario.scenario_id
        )
        ground_truth.direction = scenario.direction
        ground_truth.primary_driver = scenario.primary_driver
        ground_truth.dimensions = resolved_dimensions_by_id[scenario.scenario_id]
        ground_truth.severity = scenario.severity
        ground_truth.notes = scenario.notes
        session.add(ground_truth)

    session.commit()
    return len(SCENARIOS)


def main() -> None:
    session = WriteSessionLocal()
    try:
        count = seed_scenarios(session)
        print(f"Seeded {count} scenarios into eval.eval_scenarios / eval.eval_ground_truth")
    finally:
        session.close()


if __name__ == "__main__":
    main()
