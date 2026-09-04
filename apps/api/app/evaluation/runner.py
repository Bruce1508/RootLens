"""FR-14 evaluation runner: for each scenario in a split, provisions an
isolated schema clone, applies its incident, runs a real investigation
against it, scores the outcome, and tears the clone down. CLI-only for
MVP (PRD §12) — see app.evaluation.cli."""

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.schemas import DateRange
from app.core.config import Settings
from app.db.session import WriteSessionLocal
from app.evaluation.incidents import apply_incident
from app.evaluation.scenario_schema import (
    provision_scenario_schema,
    scenario_schema_name,
    scenario_sessions,
    teardown_scenario_schema,
)
from app.evaluation.scoring import (
    CaseResult,
    aggregate_metrics,
    score_claims,
    score_direction,
    score_driver_and_dimension,
)
from app.investigations.engine import run_investigation
from app.investigations.schemas import InvestigationCreateRequest
from app.investigations.service import build_investigation
from app.llm.ollama_provider import OllamaProvider
from app.llm.provider import LLMProvider
from app.models import (
    EvalGroundTruth,
    EvalScenario,
    EvaluationCaseResult,
    EvaluationRun,
    Evidence,
    Investigation,
    InvestigationEvent,
    Report,
)
from app.prompts.catalog import get_prompt_definition

_RESULTS_DIR = Path(__file__).resolve().parents[4] / "docs" / "evaluation" / "results"


def run_evaluation(split: str, model_name: str | None = None) -> str:
    settings = Settings()
    model = model_name or settings.ollama_model
    llm = OllamaProvider(base_url=settings.ollama_base_url, default_model=model)

    admin_session = WriteSessionLocal()
    try:
        scenarios = (
            admin_session.execute(
                select(EvalScenario)
                .where(EvalScenario.split == split)
                .order_by(EvalScenario.scenario_id)
            )
            .scalars()
            .all()
        )
        if not scenarios:
            raise ValueError(f"no scenarios for split={split!r} — run `make eval-seed` first")

        scenario_ids = [s.scenario_id for s in scenarios]
        ground_truth_by_id = {
            gt.scenario_id: gt
            for gt in admin_session.execute(
                select(EvalGroundTruth).where(EvalGroundTruth.scenario_id.in_(scenario_ids))
            )
            .scalars()
            .all()
        }

        run_id = str(uuid.uuid4())
        run = EvaluationRun(
            id=run_id,
            model_name=model,
            prompt_versions={
                "decomposition_planner": get_prompt_definition("decomposition_planner").version,
                "report_generator": get_prompt_definition("report_generator").version,
            },
            config={"split": split},
            split=split,
            status="running",
        )
        admin_session.add(run)
        admin_session.commit()

        cases: list[CaseResult] = []
        for scenario in scenarios:
            case = _run_one_scenario(llm, scenario, ground_truth_by_id[scenario.scenario_id])
            cases.append(case)
            admin_session.add(EvaluationCaseResult(run_id=run_id, **case))
            admin_session.commit()

        aggregate = aggregate_metrics(cases)
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        run.aggregate_metrics = aggregate
        admin_session.commit()
    finally:
        admin_session.close()

    _export_json(run_id, model, split, aggregate, cases)
    return run_id


def _run_one_scenario(
    llm: LLMProvider, scenario: EvalScenario, ground_truth: EvalGroundTruth
) -> CaseResult:
    schema_name = scenario_schema_name(scenario.scenario_id)

    provisioning_session = WriteSessionLocal()
    try:
        provision_scenario_schema(provisioning_session, schema_name)
    finally:
        provisioning_session.close()

    started = time.perf_counter()
    investigation_id: str | None = None
    notes: str | None = None

    with scenario_sessions(schema_name) as (write_session, readonly_session):
        if not scenario.is_unanswerable:
            apply_incident(
                write_session,
                scenario.template,  # type: ignore[arg-type]
                DateRange(start=scenario.current_period_start, end=scenario.current_period_end),
                ground_truth.dimensions,
                ground_truth.severity,
                scenario.seed,
            )

        try:
            request = InvestigationCreateRequest(
                metric=scenario.metric,
                current_period=DateRange(
                    start=scenario.current_period_start, end=scenario.current_period_end
                ),
                comparison_period=DateRange(
                    start=scenario.comparison_period_start,
                    end=scenario.comparison_period_end,
                ),
                question=scenario.question,
            )
            investigation = build_investigation(write_session, request)
            investigation_id = investigation.investigation_id
            run_investigation(write_session, readonly_session, llm, investigation_id)
        except Exception as exc:  # noqa: BLE001 — one bad scenario must not abort the run
            notes = f"investigation raised: {type(exc).__name__}: {exc}"

        latency_ms = (time.perf_counter() - started) * 1000
        case = _build_case_result(
            write_session, scenario, ground_truth, investigation_id, latency_ms, notes
        )

    teardown_session = WriteSessionLocal()
    try:
        teardown_scenario_schema(teardown_session, schema_name)
    finally:
        teardown_session.close()

    return case


def _build_case_result(
    session: Session,
    scenario: EvalScenario,
    ground_truth: EvalGroundTruth,
    investigation_id: str | None,
    latency_ms: float,
    notes: str | None,
) -> CaseResult:
    if investigation_id is None:
        return CaseResult(
            scenario_id=scenario.scenario_id,
            investigation_id=None,
            predicted_direction=None,
            predicted_primary_driver=None,
            predicted_dimensions=None,
            correct_driver=None,
            correct_dimension=None,
            abstained=False,
            expected_abstain=scenario.is_unanswerable,
            evidence_citation_valid=False,
            tool_execution_success=False,
            unsupported_claim_count=0,
            total_claim_count=0,
            tool_call_count=0,
            latency_ms=latency_ms,
            status="execution_error",
            notes=notes,
        )

    investigation = session.get(Investigation, investigation_id)
    assert investigation is not None

    report_row = (
        session.execute(
            select(Report)
            .where(Report.investigation_id == investigation_id)
            .order_by(Report.id.desc())
        )
        .scalars()
        .first()
    )
    evidence_rows = (
        session.execute(select(Evidence).where(Evidence.investigation_id == investigation_id))
        .scalars()
        .all()
    )
    evidence_by_id: dict[str, Any] = {e.evidence_id: e for e in evidence_rows}

    tool_call_events = (
        session.execute(
            select(InvestigationEvent).where(
                InvestigationEvent.investigation_id == investigation_id,
                InvestigationEvent.event_type == "tool_call",
            )
        )
        .scalars()
        .all()
    )
    decomposition_event = (
        session.execute(
            select(InvestigationEvent).where(
                InvestigationEvent.investigation_id == investigation_id,
                InvestigationEvent.event_type == "decomposition_plan",
            )
        )
        .scalars()
        .first()
    )

    if report_row is None:
        abstained = False
        evidence_citation_valid = False
        unsupported_count, total_count = 0, 0
        predicted_direction = None
    else:
        abstained = report_row.status == "insufficient_evidence"
        finding_evidence_ids = {
            eid for finding in report_row.findings for eid in finding.get("evidence_ids", [])
        }
        evidence_citation_valid = finding_evidence_ids.issubset(evidence_by_id)
        unsupported_count, total_count = score_claims(report_row.findings, evidence_by_id)
        predicted_direction = score_direction(report_row.observed_change)

    predicted_driver = (
        decomposition_event.payload.get("primary_driver_hypothesis")
        if decomposition_event
        else None
    )
    predicted_dimension_name = (
        decomposition_event.payload.get("recommended_next_dimension")
        if decomposition_event
        else None
    )
    contribution_evidence = next(
        (e for e in evidence_rows if e.tool_name == "calculate_contribution"), None
    )
    predicted_dimensions: dict[str, str] | None = None
    if predicted_dimension_name and contribution_evidence and contribution_evidence.rows:
        predicted_dimensions = {
            predicted_dimension_name: contribution_evidence.rows[0]["segment_value"]
        }

    correct_driver, correct_dimension = score_driver_and_dimension(
        predicted_driver,
        predicted_dimensions,
        ground_truth.primary_driver,
        ground_truth.dimensions,
    )

    if investigation.status == "failed":
        status = "execution_error"
    elif abstained:
        status = "abstained"
    elif ground_truth.primary_driver is None:
        status = "fail"  # unanswerable scenario that should have abstained but didn't
    elif correct_driver and correct_dimension:
        status = "pass"
    else:
        status = "fail"

    return CaseResult(
        scenario_id=scenario.scenario_id,
        investigation_id=investigation_id,
        predicted_direction=predicted_direction,
        predicted_primary_driver=predicted_driver,
        predicted_dimensions=predicted_dimensions,
        correct_driver=correct_driver,
        correct_dimension=correct_dimension,
        abstained=abstained,
        expected_abstain=scenario.is_unanswerable,
        evidence_citation_valid=evidence_citation_valid,
        tool_execution_success=investigation.status != "failed",
        unsupported_claim_count=unsupported_count,
        total_claim_count=total_count,
        tool_call_count=len(tool_call_events),
        latency_ms=latency_ms,
        status=status,
        notes=notes,
    )


def _export_json(
    run_id: str,
    model: str,
    split: str,
    aggregate: dict[str, float | int],
    cases: list[CaseResult],
) -> None:
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "model": model,
        "split": split,
        "aggregate_metrics": aggregate,
        "cases": cases,
    }
    (_RESULTS_DIR / f"{run_id}.json").write_text(json.dumps(payload, indent=2, default=str))
