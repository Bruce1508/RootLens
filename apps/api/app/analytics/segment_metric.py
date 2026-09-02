import time
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.dimensions import apply_dimension_joins, dimension_column
from app.analytics.schemas import DateRange, ToolResult
from app.analytics.validation import exclusive_end, validate_non_overlapping
from app.metrics.catalog import get_metric_definition
from app.models import Order, OrderItem

_REVENUE_METRIC = "product_revenue"


def segment_values(
    session: Session, metric: str, dimension: str, period: DateRange, limit: int
) -> dict[str, float]:
    if metric != _REVENUE_METRIC:
        raise NotImplementedError(f"segment_metric does not support metric {metric!r} yet")

    excluded_statuses = get_metric_definition(_REVENUE_METRIC).excluded_statuses
    seg_col = dimension_column(dimension)

    stmt = (
        select(seg_col.label("segment_value"), func.sum(OrderItem.price).label("value"))
        .select_from(OrderItem)
        .join(Order, Order.order_id == OrderItem.order_id)
    )
    stmt = apply_dimension_joins(stmt, dimension)
    stmt = stmt.where(
        Order.order_purchase_timestamp >= period.start,
        Order.order_purchase_timestamp < exclusive_end(period),
        Order.order_status.notin_(excluded_statuses),
    ).group_by(seg_col)

    rows = session.execute(stmt).all()
    return {row.segment_value: float(row.value) for row in rows if row.segment_value is not None}


def segment_metric(
    session: Session,
    metric: str,
    dimension: str,
    current_period: DateRange,
    comparison_period: DateRange,
    limit: int = 10,
) -> ToolResult:
    validate_non_overlapping(current_period, comparison_period)

    started = time.perf_counter()
    current_by_segment = segment_values(session, metric, dimension, current_period, limit)
    comparison_by_segment = segment_values(session, metric, dimension, comparison_period, limit)
    elapsed_ms = (time.perf_counter() - started) * 1000

    all_segments = sorted(set(current_by_segment) | set(comparison_by_segment))
    rows = [
        {
            "segment_value": segment,
            "current_value": current_by_segment.get(segment, 0.0),
            "comparison_value": comparison_by_segment.get(segment, 0.0),
        }
        for segment in all_segments
    ][:limit]

    return ToolResult(
        evidence_id=str(uuid.uuid4()),
        tool_name="segment_metric",
        params={
            "metric": metric,
            "dimension": dimension,
            "current_period": {
                "start": str(current_period.start),
                "end": str(current_period.end),
            },
            "comparison_period": {
                "start": str(comparison_period.start),
                "end": str(comparison_period.end),
            },
            "limit": limit,
        },
        sql="see app.analytics.segment_metric (parameterized query, not a raw SQL string)",
        columns=["segment_value", "current_value", "comparison_value"],
        rows=rows,
        row_count=len(rows),
        execution_ms=elapsed_ms,
        warnings=[],
    )
