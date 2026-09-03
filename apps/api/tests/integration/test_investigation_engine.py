import uuid
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.schemas import ToolResult
from app.investigations import engine
from app.llm.schemas import DecompositionPlan
from app.models import Hypothesis, Investigation, InvestigationEvent


def _make_investigation(session: Session) -> Investigation:
    investigation = Investigation(
        investigation_id=str(uuid.uuid4()),
        metric="product_revenue",
        metric_definition_version="product_revenue:v1",
        current_period_start=date(2018, 1, 1),
        current_period_end=date(2018, 1, 31),
        comparison_period_start=date(2017, 12, 1),
        comparison_period_end=date(2017, 12, 31),
        question=None,
        status="running",
    )
    session.add(investigation)
    session.flush()
    return investigation


def _tool_result(tool_name: str, rows: list[dict]) -> ToolResult:
    return ToolResult(
        evidence_id=str(uuid.uuid4()),
        tool_name=tool_name,
        params={},
        sql="test",
        columns=list(rows[0].keys()) if rows else [],
        rows=rows,
        row_count=len(rows),
        execution_ms=1.0,
    )


class _FakeLLM:
    def __init__(self, plan: DecompositionPlan) -> None:
        self._plan = plan

    def generate_structured(self, prompt: str, schema: type, model: str | None = None) -> object:
        return self._plan

    def health_check(self) -> bool:
        return True


_REVENUE_RESULT = _tool_result(
    "compare_periods",
    [
        {
            "current_value": 750.0,
            "comparison_value": 1000.0,
            "absolute_change": -250.0,
            "percent_change": -0.25,
        }
    ],
)
_ORDERS_RESULT = _tool_result(
    "compare_periods",
    [
        {
            "current_value": 14.0,
            "comparison_value": 20.0,
            "absolute_change": -6.0,
            "percent_change": -0.3,
        }
    ],
)
_PLAN = DecompositionPlan(
    metric="product_revenue",
    primary_driver_hypothesis="order_volume",
    rationale="Order count fell sharply while AOV stayed roughly flat.",
    recommended_next_dimension="customer_state",
)


def test_run_investigation_completes_and_supports_hypothesis_on_concentrated_contribution(
    db_session: Session,
) -> None:
    investigation = _make_investigation(db_session)
    contribution_result = _tool_result(
        "calculate_contribution",
        [{"segment_value": "SP", "change": -200.0, "share_of_total_change": 0.8}],
    )

    with (
        patch.object(engine, "compare_periods", side_effect=[_REVENUE_RESULT, _ORDERS_RESULT]),
        patch.object(engine, "calculate_contribution", return_value=contribution_result),
    ):
        engine.run_investigation(db_session, _FakeLLM(_PLAN), investigation.investigation_id)

    db_session.refresh(investigation)
    assert investigation.status == "completed"
    assert investigation.step_count == 4
    assert investigation.query_count == 3

    hypothesis = db_session.execute(
        select(Hypothesis).where(Hypothesis.investigation_id == investigation.investigation_id)
    ).scalar_one()
    assert hypothesis.status == "supported"
    assert hypothesis.confidence == "high"
    assert hypothesis.supporting_evidence_ids == [contribution_result.evidence_id]

    events = (
        db_session.execute(
            select(InvestigationEvent)
            .where(InvestigationEvent.investigation_id == investigation.investigation_id)
            .order_by(InvestigationEvent.id)
        )
        .scalars()
        .all()
    )
    tool_call_events = [e for e in events if e.event_type == "tool_call"]
    assert len(tool_call_events) == 3


def test_run_investigation_marks_hypothesis_inconclusive_when_contribution_not_concentrated(
    db_session: Session,
) -> None:
    investigation = _make_investigation(db_session)
    contribution_result = _tool_result(
        "calculate_contribution",
        [{"segment_value": "SP", "change": -50.0, "share_of_total_change": 0.2}],
    )

    with (
        patch.object(engine, "compare_periods", side_effect=[_REVENUE_RESULT, _ORDERS_RESULT]),
        patch.object(engine, "calculate_contribution", return_value=contribution_result),
    ):
        engine.run_investigation(db_session, _FakeLLM(_PLAN), investigation.investigation_id)

    db_session.refresh(investigation)
    assert investigation.status == "completed"

    hypothesis = db_session.execute(
        select(Hypothesis).where(Hypothesis.investigation_id == investigation.investigation_id)
    ).scalar_one()
    assert hypothesis.status == "inconclusive"
    assert hypothesis.confidence == "low"


def test_run_investigation_raises_for_unknown_investigation_id(db_session: Session) -> None:
    with pytest.raises(ValueError, match="unknown investigation_id"):
        engine.run_investigation(db_session, _FakeLLM(_PLAN), "does-not-exist")
