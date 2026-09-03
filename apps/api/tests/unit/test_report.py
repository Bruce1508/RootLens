from app.analytics.schemas import ToolResult
from app.investigations import report
from app.investigations.report_schemas import ReportFinding, ReportNarrative
from app.models import Hypothesis


def _tool_result(evidence_id: str, tool_name: str, rows: list[dict]) -> ToolResult:
    return ToolResult(
        evidence_id=evidence_id,
        tool_name=tool_name,
        params={},
        sql="test",
        columns=list(rows[0].keys()) if rows else [],
        rows=rows,
        row_count=len(rows),
        execution_ms=1.0,
    )


def _hypothesis(status: str) -> Hypothesis:
    return Hypothesis(
        id="hyp-1",
        investigation_id="inv-1",
        statement="test",
        status=status,
        confidence=None,
        supporting_evidence_ids=[],
        contradicting_evidence_ids=[],
    )


def test_build_observed_change_reads_directly_from_revenue_result() -> None:
    revenue_result = _tool_result(
        "ev-revenue",
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

    observed_change = report.build_observed_change("product_revenue", revenue_result)

    assert observed_change.current_value == 750.0
    assert observed_change.comparison_value == 1000.0
    assert observed_change.percent_change == -0.25
    assert observed_change.evidence_ids == ["ev-revenue"]


def test_determine_status_answered_when_hypothesis_supported() -> None:
    contribution_result = _tool_result(
        "ev-c", "calculate_contribution", [{"segment_value": "SP", "share_of_total_change": 0.8}]
    )
    assert report.determine_status(_hypothesis("supported"), contribution_result) == "answered"


def test_determine_status_partial_when_hypothesis_inconclusive_but_data_exists() -> None:
    contribution_result = _tool_result(
        "ev-c", "calculate_contribution", [{"segment_value": "SP", "share_of_total_change": 0.2}]
    )
    assert report.determine_status(_hypothesis("inconclusive"), contribution_result) == "partial"


def test_determine_status_insufficient_evidence_when_no_contribution_rows() -> None:
    contribution_result = _tool_result("ev-c", "calculate_contribution", [])
    assert (
        report.determine_status(_hypothesis("inconclusive"), contribution_result)
        == "insufficient_evidence"
    )


def test_check_narrative_flags_unknown_evidence_id() -> None:
    narrative = ReportNarrative(
        headline="test",
        findings=[
            ReportFinding(
                claim="Revenue fell.",
                claim_type="observed_fact",
                evidence_ids=["ev-not-allowed"],
                confidence="high",
            )
        ],
        limitations=[],
        recommended_next_checks=[],
    )

    problems = report._check_narrative(narrative, {"ev-revenue"}, {})

    assert len(problems) == 1
    assert "unknown evidence_id" in problems[0]


def test_check_narrative_flags_unsupported_number_in_claim() -> None:
    revenue_result = _tool_result(
        "ev-revenue", "compare_periods", [{"current_value": 750.0, "comparison_value": 1000.0}]
    )
    narrative = ReportNarrative(
        headline="test",
        findings=[
            ReportFinding(
                claim="Revenue fell to 99999.",
                claim_type="observed_fact",
                evidence_ids=["ev-revenue"],
                confidence="high",
            )
        ],
        limitations=[],
        recommended_next_checks=[],
    )

    problems = report._check_narrative(narrative, {"ev-revenue"}, {"ev-revenue": revenue_result})

    assert len(problems) == 1
    assert "number not found" in problems[0]


def test_check_narrative_accepts_number_matching_evidence_within_tolerance() -> None:
    revenue_result = _tool_result(
        "ev-revenue", "compare_periods", [{"current_value": 750.0, "comparison_value": 1000.0}]
    )
    narrative = ReportNarrative(
        headline="test",
        findings=[
            ReportFinding(
                claim="Revenue fell to about 750.",
                claim_type="observed_fact",
                evidence_ids=["ev-revenue"],
                confidence="high",
            )
        ],
        limitations=[],
        recommended_next_checks=[],
    )

    problems = report._check_narrative(narrative, {"ev-revenue"}, {"ev-revenue": revenue_result})

    assert problems == []


def test_check_narrative_accepts_interpretation_claims_regardless_of_numbers() -> None:
    narrative = ReportNarrative(
        headline="test",
        findings=[
            ReportFinding(
                claim="This might be seasonal (roughly 12 months apart).",
                claim_type="interpretation",
                evidence_ids=["ev-revenue"],
                confidence="low",
            )
        ],
        limitations=[],
        recommended_next_checks=[],
    )

    problems = report._check_narrative(narrative, {"ev-revenue"}, {})

    assert problems == []


def test_repair_narrative_strips_unknown_ids_and_downgrades_to_interpretation() -> None:
    narrative = ReportNarrative(
        headline="test",
        findings=[
            ReportFinding(
                claim="Revenue fell to 99999.",
                claim_type="observed_fact",
                evidence_ids=["ev-revenue", "ev-not-allowed"],
                confidence="high",
            )
        ],
        limitations=[],
        recommended_next_checks=[],
    )
    revenue_result = _tool_result(
        "ev-revenue", "compare_periods", [{"current_value": 750.0, "comparison_value": 1000.0}]
    )

    repaired = report._repair_narrative(narrative, {"ev-revenue"}, {"ev-revenue": revenue_result})

    finding = repaired.findings[0]
    assert finding.evidence_ids == ["ev-revenue"]
    assert finding.claim_type == "interpretation"


def test_repair_narrative_keeps_observed_fact_when_claim_becomes_supported() -> None:
    narrative = ReportNarrative(
        headline="test",
        findings=[
            ReportFinding(
                claim="Revenue fell to about 750.",
                claim_type="observed_fact",
                evidence_ids=["ev-revenue"],
                confidence="high",
            )
        ],
        limitations=[],
        recommended_next_checks=[],
    )
    revenue_result = _tool_result(
        "ev-revenue", "compare_periods", [{"current_value": 750.0, "comparison_value": 1000.0}]
    )

    repaired = report._repair_narrative(narrative, {"ev-revenue"}, {"ev-revenue": revenue_result})

    assert repaired.findings[0].claim_type == "observed_fact"


class _FakeLLM:
    """Returns bad_narrative on the first call, good_narrative on retry."""

    def __init__(self, bad_narrative: ReportNarrative, good_narrative: ReportNarrative) -> None:
        self._responses = [bad_narrative, good_narrative]

    def generate_structured(self, prompt: str, schema: type, model: str | None = None) -> object:
        return self._responses.pop(0)

    def health_check(self) -> bool:
        return True


def test_generate_report_regenerates_once_when_first_narrative_has_unknown_citation() -> None:
    from app.investigations.report_schemas import ObservedChange

    revenue_result = _tool_result(
        "ev-revenue",
        "compare_periods",
        [{"current_value": 750.0, "comparison_value": 1000.0, "percent_change": -0.25}],
    )
    orders_result = _tool_result(
        "ev-orders", "compare_periods", [{"current_value": 14.0, "comparison_value": 20.0}]
    )
    cancellation_result = _tool_result(
        "ev-cancellation",
        "compare_periods",
        [{"current_value": 0.02, "comparison_value": 0.02}],
    )
    contribution_result = _tool_result(
        "ev-contribution",
        "calculate_contribution",
        [{"segment_value": "SP", "share_of_total_change": 0.8}],
    )

    bad_narrative = ReportNarrative(
        headline="bad",
        findings=[
            ReportFinding(
                claim="Revenue fell.",
                claim_type="observed_fact",
                evidence_ids=["totally-made-up"],
                confidence="high",
            )
        ],
        limitations=[],
        recommended_next_checks=[],
    )
    good_narrative = ReportNarrative(
        headline="good",
        findings=[
            ReportFinding(
                claim="Revenue fell.",
                claim_type="observed_fact",
                evidence_ids=["ev-revenue"],
                confidence="high",
            )
        ],
        limitations=[],
        recommended_next_checks=[],
    )

    class _Investigation:
        metric = "product_revenue"

    result = report.generate_report(
        _FakeLLM(bad_narrative, good_narrative),
        _Investigation(),  # type: ignore[arg-type]
        _hypothesis("supported"),
        revenue_result,
        orders_result,
        cancellation_result,
        contribution_result,
    )

    assert result.headline == "good"
    assert result.findings[0].evidence_ids == ["ev-revenue"]
    assert isinstance(result.observed_change, ObservedChange)
