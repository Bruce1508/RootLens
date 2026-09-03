import time
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.schemas import DateRange, ToolResult
from app.analytics.validation import exclusive_end, validate_non_overlapping
from app.metrics.catalog import get_metric_definition

_REVENUE_METRIC = "product_revenue"
_ORDERS_METRIC = "orders"
_CANCELLATION_RATE_METRIC = "cancellation_rate"


def _period_value(session: Session, metric: str, period: DateRange) -> float:
    from app.models import Order, OrderItem

    excluded_statuses = get_metric_definition(_REVENUE_METRIC).excluded_statuses

    if metric == _REVENUE_METRIC:
        revenue_stmt = (
            select(func.coalesce(func.sum(OrderItem.price), 0))
            .join(Order, Order.order_id == OrderItem.order_id)
            .where(
                Order.order_purchase_timestamp >= period.start,
                Order.order_purchase_timestamp < exclusive_end(period),
                Order.order_status.notin_(excluded_statuses),
            )
        )
        return float(session.execute(revenue_stmt).scalar_one())

    if metric == _ORDERS_METRIC:
        orders_stmt = select(func.count(func.distinct(Order.order_id))).where(
            Order.order_purchase_timestamp >= period.start,
            Order.order_purchase_timestamp < exclusive_end(period),
            Order.order_status.notin_(excluded_statuses),
        )
        return float(session.execute(orders_stmt).scalar_one())

    if metric == _CANCELLATION_RATE_METRIC:
        # Unlike product_revenue/orders, the denominator here is *all* orders
        # in the period — cancelled/unavailable orders are exactly what's
        # being measured, not excluded from it.
        cancellation_stmt = select(
            func.count(func.distinct(Order.order_id)).filter(
                Order.order_status.in_(excluded_statuses)
            ),
            func.count(func.distinct(Order.order_id)),
        ).where(
            Order.order_purchase_timestamp >= period.start,
            Order.order_purchase_timestamp < exclusive_end(period),
        )
        cancelled_count, total_count = session.execute(cancellation_stmt).one()
        if not total_count:
            return 0.0
        return float(cancelled_count) / float(total_count)

    raise NotImplementedError(f"compare_periods does not support metric {metric!r} yet")


def compare_periods(
    session: Session,
    metric: str,
    current_period: DateRange,
    comparison_period: DateRange,
) -> ToolResult:
    validate_non_overlapping(current_period, comparison_period)

    started = time.perf_counter()
    current_value = _period_value(session, metric, current_period)
    comparison_value = _period_value(session, metric, comparison_period)
    elapsed_ms = (time.perf_counter() - started) * 1000

    absolute_change = current_value - comparison_value
    percent_change = (absolute_change / comparison_value) if comparison_value else None

    return ToolResult(
        evidence_id=str(uuid.uuid4()),
        tool_name="compare_periods",
        params={
            "metric": metric,
            "current_period": {
                "start": str(current_period.start),
                "end": str(current_period.end),
            },
            "comparison_period": {
                "start": str(comparison_period.start),
                "end": str(comparison_period.end),
            },
        },
        sql="see app.analytics.compare_periods (parameterized query, not a raw SQL string)",
        columns=["current_value", "comparison_value", "absolute_change", "percent_change"],
        rows=[
            {
                "current_value": current_value,
                "comparison_value": comparison_value,
                "absolute_change": absolute_change,
                "percent_change": percent_change,
            }
        ],
        row_count=1,
        execution_ms=elapsed_ms,
        warnings=[] if comparison_value else ["comparison period value is zero"],
    )
