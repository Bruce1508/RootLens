import time

import pytest

from app.investigations import engine
from app.models import Hypothesis, Investigation


def _investigation(**overrides: object) -> Investigation:
    inv = Investigation(
        investigation_id="inv-1",
        metric="product_revenue",
        metric_definition_version="product_revenue:v1",
        status="running",
        step_count=0,
        query_count=0,
    )
    for key, value in overrides.items():
        setattr(inv, key, value)
    return inv


def _hypothesis() -> Hypothesis:
    return Hypothesis(
        id="hyp-1",
        investigation_id="inv-1",
        statement="test",
        status="testing",
        confidence=None,
        supporting_evidence_ids=[],
        contradicting_evidence_ids=[],
    )


class _FakeToolResult:
    def __init__(self, rows: list[dict], evidence_id: str = "ev-1") -> None:
        self.rows = rows
        self.evidence_id = evidence_id


def test_advance_increments_step_and_query_counts() -> None:
    inv = _investigation()
    engine._advance(inv, time.monotonic(), is_query=True)
    assert inv.step_count == 1
    assert inv.query_count == 1

    engine._advance(inv, time.monotonic(), is_query=False)
    assert inv.step_count == 2
    assert inv.query_count == 1


def test_advance_raises_when_step_budget_exceeded() -> None:
    inv = _investigation(step_count=engine._MAX_STEPS)
    with pytest.raises(engine._StoppingConditionExceeded) as exc_info:
        engine._advance(inv, time.monotonic(), is_query=False)
    assert exc_info.value.terminal_status == "partial"


def test_advance_raises_when_query_budget_exceeded() -> None:
    inv = _investigation(query_count=engine._MAX_QUERIES)
    with pytest.raises(engine._StoppingConditionExceeded) as exc_info:
        engine._advance(inv, time.monotonic(), is_query=True)
    assert exc_info.value.terminal_status == "partial"


def test_advance_raises_timed_out_when_wall_clock_budget_exceeded() -> None:
    inv = _investigation()
    started_in_the_past = time.monotonic() - (engine._WALL_CLOCK_TIMEOUT_SECONDS + 1)
    with pytest.raises(engine._StoppingConditionExceeded) as exc_info:
        engine._advance(inv, started_in_the_past, is_query=False)
    assert exc_info.value.terminal_status == "timed_out"


def test_format_percent_handles_none() -> None:
    assert engine._format_percent(None) == "undefined (comparison period value was zero)"


def test_format_percent_formats_fraction_as_percentage_string() -> None:
    assert engine._format_percent(-0.253) == "-25.3"


def test_resolve_hypothesis_marks_supported_high_confidence_above_high_threshold() -> None:
    hyp = _hypothesis()
    result = _FakeToolResult([{"share_of_total_change": 0.8}])

    engine._resolve_hypothesis(hyp, result)  # type: ignore[arg-type]

    assert hyp.status == "supported"
    assert hyp.confidence == "high"
    assert hyp.supporting_evidence_ids == ["ev-1"]


def test_resolve_hypothesis_marks_supported_medium_confidence_between_thresholds() -> None:
    hyp = _hypothesis()
    result = _FakeToolResult([{"share_of_total_change": 0.6}])

    engine._resolve_hypothesis(hyp, result)  # type: ignore[arg-type]

    assert hyp.status == "supported"
    assert hyp.confidence == "medium"


def test_resolve_hypothesis_marks_inconclusive_below_supported_threshold() -> None:
    hyp = _hypothesis()
    result = _FakeToolResult([{"share_of_total_change": 0.2}])

    engine._resolve_hypothesis(hyp, result)  # type: ignore[arg-type]

    assert hyp.status == "inconclusive"
    assert hyp.confidence == "low"
    assert hyp.supporting_evidence_ids == []


def test_resolve_hypothesis_marks_inconclusive_when_no_rows() -> None:
    hyp = _hypothesis()
    result = _FakeToolResult([])

    engine._resolve_hypothesis(hyp, result)  # type: ignore[arg-type]

    assert hyp.status == "inconclusive"
    assert hyp.confidence == "low"
