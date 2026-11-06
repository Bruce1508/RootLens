from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.compare_periods import compare_periods
from app.analytics.schemas import DateRange
from app.db.session import get_readonly_session
from app.investigations.schemas import TERMINAL_INVESTIGATION_STATUSES
from app.models import Investigation, InvestigationEvent

router = APIRouter()

# Milestone 1 supports only deterministic KPIs computed from
# compare_periods. Delivery delay and review score are added once their
# metric definitions exist (§10 metrics not yet in the catalog).
_SUMMARY_METRICS = ["product_revenue", "orders"]

# Phase 4: the events engine.py already records for every LLM call it
# makes (decomposition, the ad-hoc query decision, report generation).
# ad_hoc_query_decision's own retry-after-rejection call isn't a distinct
# event type, so it isn't double counted here.
_LLM_CALL_EVENT_TYPES = ("decomposition_plan", "ad_hoc_query_decision", "report_generated")


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


def _aggregate_runtime_metrics(investigations: list[Investigation], event_types: list[str]) -> dict:
    by_status: dict[str, int] = {}
    terminal_latencies_ms: list[float] = []
    for investigation in investigations:
        by_status[investigation.status] = by_status.get(investigation.status, 0) + 1
        if investigation.status in TERMINAL_INVESTIGATION_STATUSES:
            latency = investigation.updated_at - investigation.created_at
            terminal_latencies_ms.append(latency.total_seconds() * 1000)

    guardrail_rejections = sum(
        1 for event_type in event_types if event_type == "ad_hoc_query_rejected"
    )
    llm_call_count = sum(1 for event_type in event_types if event_type in _LLM_CALL_EVENT_TYPES)

    average_latency_ms = (
        sum(terminal_latencies_ms) / len(terminal_latencies_ms) if terminal_latencies_ms else None
    )
    return {
        "total_investigations": len(investigations),
        "by_status": by_status,
        "average_latency_ms": average_latency_ms,
        "guardrail_rejections": guardrail_rejections,
        "llm_call_count": llm_call_count,
    }


@router.get("/api/metrics/runtime")
def get_runtime_metrics(
    session: Annotated[Session, Depends(get_readonly_session)],
) -> dict:
    investigations = list(session.execute(select(Investigation)).scalars().all())
    event_types = list(session.execute(select(InvestigationEvent.event_type)).scalars().all())
    return _aggregate_runtime_metrics(investigations, event_types)
