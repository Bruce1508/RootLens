import time
import uuid

from sqlalchemy.orm import Session

from app.analytics.calculate_contribution import calculate_contribution
from app.analytics.compare_periods import compare_periods
from app.analytics.schemas import DateRange, ToolResult
from app.investigations.report import generate_report
from app.investigations.report_schemas import InvestigationReport
from app.llm.provider import LLMProvider
from app.llm.schemas import DecompositionPlan
from app.models import Evidence, Hypothesis, Investigation, InvestigationEvent, Report
from app.prompts.catalog import get_prompt_definition

_MAX_STEPS = 12
_MAX_QUERIES = 15
_WALL_CLOCK_TIMEOUT_SECONDS = 120.0
_ORDERS_METRIC = "orders"
_CANCELLATION_RATE_METRIC = "cancellation_rate"

# §7's example report cites a segment "contributing 61% of the lost
# revenue" as strong enough to call a driver supported; below this share
# the evidence doesn't clearly implicate one segment.
_SUPPORTED_SHARE_THRESHOLD = 0.5
_HIGH_CONFIDENCE_SHARE_THRESHOLD = 0.75


class _StoppingConditionExceeded(Exception):
    def __init__(self, terminal_status: str, message: str) -> None:
        super().__init__(message)
        self.terminal_status = terminal_status


def run_investigation(session: Session, llm: LLMProvider, investigation_id: str) -> None:
    investigation = session.get(Investigation, investigation_id)
    if investigation is None:
        raise ValueError(f"unknown investigation_id: {investigation_id!r}")

    started_at = time.monotonic()
    current_period = DateRange(
        start=investigation.current_period_start, end=investigation.current_period_end
    )
    comparison_period = DateRange(
        start=investigation.comparison_period_start, end=investigation.comparison_period_end
    )

    try:
        revenue_result = compare_periods(
            session, investigation.metric, current_period, comparison_period
        )
        _advance(investigation, started_at, is_query=True)
        _record_event(session, investigation, "tool_call", revenue_result.model_dump())
        _record_evidence(session, investigation, revenue_result)

        orders_result = compare_periods(session, _ORDERS_METRIC, current_period, comparison_period)
        _advance(investigation, started_at, is_query=True)
        _record_event(session, investigation, "tool_call", orders_result.model_dump())
        _record_evidence(session, investigation, orders_result)
        session.commit()

        cancellation_result = compare_periods(
            session, _CANCELLATION_RATE_METRIC, current_period, comparison_period
        )
        _advance(investigation, started_at, is_query=True)
        _record_event(session, investigation, "tool_call", cancellation_result.model_dump())
        _record_evidence(session, investigation, cancellation_result)
        session.commit()

        plan = _decompose(
            llm, investigation.metric, revenue_result, orders_result, cancellation_result
        )
        _advance(investigation, started_at, is_query=False)
        # Recorded as its own structured event — the hypothesis statement
        # below only embeds these as free text, which the evaluation
        # runner's scoring (FR-14 root-cause / dimension accuracy) can't
        # reliably parse back out.
        _record_event(session, investigation, "decomposition_plan", plan.model_dump())

        hypothesis = Hypothesis(
            id=str(uuid.uuid4()),
            investigation_id=investigation.investigation_id,
            statement=(
                f"The change in {investigation.metric} is primarily driven by "
                f"{plan.primary_driver_hypothesis} ({plan.rationale})"
            ),
            status="testing",
            confidence=None,
            supporting_evidence_ids=[],
            contradicting_evidence_ids=[],
        )
        session.add(hypothesis)
        _record_event(session, investigation, "hypothesis_update", _hypothesis_payload(hypothesis))
        session.commit()

        contribution_result = calculate_contribution(
            session,
            investigation.metric,
            plan.recommended_next_dimension,
            current_period,
            comparison_period,
        )
        _advance(investigation, started_at, is_query=True)
        _record_event(session, investigation, "tool_call", contribution_result.model_dump())
        _record_evidence(session, investigation, contribution_result)

        _resolve_hypothesis(hypothesis, contribution_result)
        _record_event(session, investigation, "hypothesis_update", _hypothesis_payload(hypothesis))
        session.commit()

        report = generate_report(
            llm,
            investigation,
            hypothesis,
            revenue_result,
            orders_result,
            cancellation_result,
            contribution_result,
        )
        _record_report(session, investigation, report)
        _record_event(
            session,
            investigation,
            "report_generated",
            {"status": report.status, "headline": report.headline},
        )

        investigation.status = "completed"
    except _StoppingConditionExceeded as exc:
        investigation.status = exc.terminal_status
        _record_event(session, investigation, "status_change", {"reason": str(exc)})
    except Exception as exc:
        investigation.status = "failed"
        _record_event(session, investigation, "status_change", {"error": str(exc)})
        session.commit()
        raise

    session.commit()


def _advance(investigation: Investigation, started_at: float, *, is_query: bool) -> None:
    investigation.step_count += 1
    if is_query:
        investigation.query_count += 1

    elapsed = time.monotonic() - started_at
    if elapsed > _WALL_CLOCK_TIMEOUT_SECONDS:
        raise _StoppingConditionExceeded(
            "timed_out", f"exceeded {_WALL_CLOCK_TIMEOUT_SECONDS}s wall-clock budget"
        )
    if investigation.step_count > _MAX_STEPS:
        raise _StoppingConditionExceeded("partial", f"exceeded {_MAX_STEPS}-step budget")
    if investigation.query_count > _MAX_QUERIES:
        raise _StoppingConditionExceeded("partial", f"exceeded {_MAX_QUERIES}-query budget")


def _record_event(
    session: Session, investigation: Investigation, event_type: str, payload: dict
) -> None:
    session.add(
        InvestigationEvent(
            investigation_id=investigation.investigation_id,
            event_type=event_type,
            payload=payload,
        )
    )


def _record_evidence(session: Session, investigation: Investigation, result: ToolResult) -> None:
    session.add(
        Evidence(
            evidence_id=result.evidence_id,
            investigation_id=investigation.investigation_id,
            tool_name=result.tool_name,
            params=result.params,
            sql=result.sql,
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            execution_ms=result.execution_ms,
            warnings=result.warnings,
        )
    )


def _record_report(
    session: Session, investigation: Investigation, report: InvestigationReport
) -> None:
    session.add(
        Report(
            investigation_id=investigation.investigation_id,
            status=report.status,
            headline=report.headline,
            observed_change=report.observed_change.model_dump(),
            findings=[finding.model_dump() for finding in report.findings],
            limitations=report.limitations,
            recommended_next_checks=report.recommended_next_checks,
        )
    )


def _decompose(
    llm: LLMProvider,
    metric: str,
    revenue_result: ToolResult,
    orders_result: ToolResult,
    cancellation_result: ToolResult,
) -> DecompositionPlan:
    revenue_row = revenue_result.rows[0]
    orders_row = orders_result.rows[0]
    cancellation_row = cancellation_result.rows[0]
    prompt = get_prompt_definition("decomposition_planner").template.format(
        metric=metric,
        comparison_value=revenue_row["comparison_value"],
        current_value=revenue_row["current_value"],
        percent_change=_format_percent(revenue_row["percent_change"]),
        orders_comparison_value=orders_row["comparison_value"],
        orders_current_value=orders_row["current_value"],
        orders_percent_change=_format_percent(orders_row["percent_change"]),
        cancellation_comparison_value=cancellation_row["comparison_value"],
        cancellation_current_value=cancellation_row["current_value"],
        cancellation_percent_change=_format_percent(cancellation_row["percent_change"]),
    )
    return llm.generate_structured(prompt, DecompositionPlan)


def _format_percent(value: float | None) -> str:
    if value is None:
        return "undefined (comparison period value was zero)"
    return f"{value * 100:.1f}"


def _hypothesis_payload(hypothesis: Hypothesis) -> dict:
    return {
        "id": hypothesis.id,
        "statement": hypothesis.statement,
        "status": hypothesis.status,
        "confidence": hypothesis.confidence,
        "supporting_evidence_ids": hypothesis.supporting_evidence_ids,
        "contradicting_evidence_ids": hypothesis.contradicting_evidence_ids,
    }


def _resolve_hypothesis(hypothesis: Hypothesis, contribution_result: ToolResult) -> None:
    top_share = (
        contribution_result.rows[0]["share_of_total_change"] if contribution_result.rows else None
    )

    if top_share is not None and abs(top_share) >= _SUPPORTED_SHARE_THRESHOLD:
        hypothesis.status = "supported"
        hypothesis.confidence = (
            "high" if abs(top_share) >= _HIGH_CONFIDENCE_SHARE_THRESHOLD else "medium"
        )
        hypothesis.supporting_evidence_ids = [contribution_result.evidence_id]
    else:
        hypothesis.status = "inconclusive"
        hypothesis.confidence = "low"
