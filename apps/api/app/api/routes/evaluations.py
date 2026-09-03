from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_write_session
from app.evaluation.api_schemas import (
    EvaluationCaseResultView,
    EvaluationRunDetailView,
    EvaluationRunView,
)
from app.models import EvalScenario, EvaluationCaseResult, EvaluationRun

router = APIRouter()

# Reads via the write/app session, not the read-only one: this endpoint's
# whole purpose is transparency into the hidden `eval` schema's ground
# truth (PRD §28, "verify benchmark measurements") — the same trusted
# access app.evaluation.runner already uses, not something rootlens_readonly
# (the investigation engine's role) should ever see. See ADR-0007.


def _to_run_view(run: EvaluationRun) -> EvaluationRunView:
    return EvaluationRunView(
        run_id=run.id,
        model_name=run.model_name,
        split=run.split,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        aggregate_metrics=run.aggregate_metrics,
    )


def _to_case_view(
    case: EvaluationCaseResult, scenario: EvalScenario | None
) -> EvaluationCaseResultView:
    return EvaluationCaseResultView(
        scenario_id=case.scenario_id,
        template=scenario.template if scenario else None,
        is_unanswerable=scenario.is_unanswerable if scenario else None,
        investigation_id=case.investigation_id,
        predicted_direction=case.predicted_direction,
        predicted_primary_driver=case.predicted_primary_driver,
        predicted_dimensions=case.predicted_dimensions,
        correct_driver=case.correct_driver,
        correct_dimension=case.correct_dimension,
        abstained=case.abstained,
        expected_abstain=case.expected_abstain,
        evidence_citation_valid=case.evidence_citation_valid,
        tool_execution_success=case.tool_execution_success,
        unsupported_claim_count=case.unsupported_claim_count,
        total_claim_count=case.total_claim_count,
        tool_call_count=case.tool_call_count,
        latency_ms=case.latency_ms,
        status=case.status,
        notes=case.notes,
    )


@router.get("/api/evaluations")
def list_evaluations(
    session: Annotated[Session, Depends(get_write_session)],
) -> list[EvaluationRunView]:
    runs = (
        session.execute(select(EvaluationRun).order_by(EvaluationRun.started_at.desc()))
        .scalars()
        .all()
    )
    return [_to_run_view(run) for run in runs]


@router.get("/api/evaluations/{run_id}")
def get_evaluation(
    run_id: str,
    session: Annotated[Session, Depends(get_write_session)],
) -> EvaluationRunDetailView:
    run = session.get(EvaluationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="evaluation run not found")

    case_rows = (
        session.execute(
            select(EvaluationCaseResult)
            .where(EvaluationCaseResult.run_id == run_id)
            .order_by(EvaluationCaseResult.scenario_id)
        )
        .scalars()
        .all()
    )
    scenario_ids = [case.scenario_id for case in case_rows]
    scenarios_by_id = {
        scenario.scenario_id: scenario
        for scenario in session.execute(
            select(EvalScenario).where(EvalScenario.scenario_id.in_(scenario_ids))
        )
        .scalars()
        .all()
    }

    return EvaluationRunDetailView(
        **_to_run_view(run).model_dump(),
        cases=[_to_case_view(case, scenarios_by_id.get(case.scenario_id)) for case in case_rows],
    )
