from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.analytics.compare_periods import compare_periods
from app.analytics.schemas import DateRange
from app.db.session import get_readonly_session

router = APIRouter()

# Milestone 1 supports only deterministic KPIs computed from
# compare_periods. Delivery delay and review score are added once their
# metric definitions exist (§10 metrics not yet in the catalog).
_SUMMARY_METRICS = ["product_revenue", "orders"]


@router.get("/api/metrics/summary")
def get_metrics_summary(
    current_start: date,
    current_end: date,
    comparison_start: date,
    comparison_end: date,
    session: Annotated[Session, Depends(get_readonly_session)],
) -> dict[str, dict]:
    try:
        current_period = DateRange(start=current_start, end=current_end)
        comparison_period = DateRange(start=comparison_start, end=comparison_end)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    summary: dict[str, dict] = {}
    try:
        for metric in _SUMMARY_METRICS:
            result = compare_periods(session, metric, current_period, comparison_period)
            summary[metric] = result.rows[0]
    except ValueError as e:
        # validate_non_overlapping (or another analytics-layer precondition)
        # rejected the request. This is a client input error, not a server
        # fault — surfacing it as 422 keeps FastAPI's normal response path,
        # which is what carries the CORSMiddleware headers a browser needs;
        # an unhandled exception instead falls through to Starlette's
        # ServerErrorMiddleware, which sits outside CORSMiddleware and
        # produces a response with no Access-Control-Allow-Origin header —
        # the browser then reports a misleading CORS failure.
        raise HTTPException(status_code=422, detail=str(e)) from e

    return summary
