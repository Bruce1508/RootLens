import time
import uuid

from sqlalchemy.orm import Session

from app.analytics.schemas import DateRange, ToolResult
from app.analytics.segment_metric import segment_values
from app.analytics.validation import validate_non_overlapping


def calculate_contribution(
    session: Session,
    metric: str,
    dimension: str,
    current_period: DateRange,
    comparison_period: DateRange,
    limit: int = 10,
) -> ToolResult:
    """Quantifies each segment's share of the total change in `metric`
    between the two periods — the FR-7 tool an agent uses to identify
    which dimension value (state, category, ...) drove an observed
    change, distinct from segment_metric's raw per-segment values."""
    validate_non_overlapping(current_period, comparison_period)

    started = time.perf_counter()
    current_by_segment = segment_values(session, metric, dimension, current_period, limit=1000)
    comparison_by_segment = segment_values(
        session, metric, dimension, comparison_period, limit=1000
    )
    elapsed_ms = (time.perf_counter() - started) * 1000

    total_change = sum(current_by_segment.values()) - sum(comparison_by_segment.values())

    all_segments = sorted(set(current_by_segment) | set(comparison_by_segment))
    changes = {
        segment: current_by_segment.get(segment, 0.0) - comparison_by_segment.get(segment, 0.0)
        for segment in all_segments
    }

    # Largest-magnitude contributors first — that's the point of this tool.
    ordered_segments = sorted(changes.items(), key=lambda item: abs(item[1]), reverse=True)
    rows = [
        {
            "segment_value": segment,
            "change": change,
            "share_of_total_change": (change / total_change) if total_change else None,
        }
        for segment, change in ordered_segments[:limit]
    ]

    return ToolResult(
        evidence_id=str(uuid.uuid4()),
        tool_name="calculate_contribution",
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
        sql="see app.analytics.calculate_contribution (derived from segment_metric queries)",
        columns=["segment_value", "change", "share_of_total_change"],
        rows=rows,
        row_count=len(rows),
        execution_ms=elapsed_ms,
        warnings=(
            [] if total_change else ["total change is zero; share_of_total_change is undefined"]
        ),
    )
