from app.analytics.schemas import ToolResult
from app.evaluation.scoring import (
    aggregate_metrics,
    score_claims,
    score_direction,
    score_driver_and_dimension,
)


def _tool_result(rows: list[dict]) -> ToolResult:
    return ToolResult(
        evidence_id="ev-1",
        tool_name="compare_periods",
        params={},
        sql="test",
        columns=[],
        rows=rows,
        row_count=len(rows),
        execution_ms=1.0,
    )


def test_score_direction_negative_percent_change_is_decrease() -> None:
    assert score_direction({"percent_change": -0.4}) == "decrease"


def test_score_direction_positive_percent_change_is_increase() -> None:
    assert score_direction({"percent_change": 0.4}) == "increase"


def test_score_direction_none_when_percent_change_missing() -> None:
    assert score_direction(None) is None
    assert score_direction({"percent_change": None}) is None


def test_score_driver_and_dimension_none_when_no_ground_truth_driver() -> None:
    correct_driver, correct_dimension = score_driver_and_dimension(
        "order_volume", {"customer_state": "SP"}, None, {}
    )
    assert correct_driver is None
    assert correct_dimension is None


def test_score_driver_and_dimension_matches_correctly() -> None:
    correct_driver, correct_dimension = score_driver_and_dimension(
        "cancellation",
        {"customer_state": "SP"},
        "cancellation",
        {"customer_state": "SP", "product_category": "beleza_saude"},
    )
    assert correct_driver is True
    assert correct_dimension is True


def test_score_driver_and_dimension_wrong_driver_and_dimension_value() -> None:
    correct_driver, correct_dimension = score_driver_and_dimension(
        "order_volume",
        {"customer_state": "RJ"},
        "cancellation",
        {"customer_state": "SP"},
    )
    assert correct_driver is False
    assert correct_dimension is False


def test_score_claims_counts_unsupported_observed_facts_only() -> None:
    findings = [
        {
            "claim": "Revenue fell to 750.",
            "claim_type": "observed_fact",
            "evidence_ids": ["ev-1"],
            "confidence": "high",
        },
        {
            "claim": "Revenue fell to 99999.",
            "claim_type": "observed_fact",
            "evidence_ids": ["ev-1"],
            "confidence": "high",
        },
        {
            "claim": "This might be seasonal.",
            "claim_type": "interpretation",
            "evidence_ids": [],
            "confidence": "low",
        },
    ]
    evidence_by_id = {"ev-1": _tool_result([{"current_value": 750.0}])}

    unsupported, total = score_claims(findings, evidence_by_id)
    assert total == 2
    assert unsupported == 1


def test_aggregate_metrics_of_empty_list_is_all_zero() -> None:
    result = aggregate_metrics([])
    assert result["scenario_count"] == 0
    assert result["root_cause_accuracy"] == 0.0


def test_aggregate_metrics_computes_expected_rates() -> None:
    cases = [
        {
            "scenario_id": "s1",
            "investigation_id": "i1",
            "predicted_direction": "decrease",
            "predicted_primary_driver": "cancellation",
            "predicted_dimensions": {"customer_state": "SP"},
            "correct_driver": True,
            "correct_dimension": True,
            "abstained": False,
            "expected_abstain": False,
            "evidence_citation_valid": True,
            "tool_execution_success": True,
            "unsupported_claim_count": 0,
            "total_claim_count": 2,
            "tool_call_count": 4,
            "latency_ms": 100.0,
            "status": "pass",
            "notes": None,
        },
        {
            "scenario_id": "s2",
            "investigation_id": "i2",
            "predicted_direction": "decrease",
            "predicted_primary_driver": "order_volume",
            "predicted_dimensions": {"customer_state": "RJ"},
            "correct_driver": False,
            "correct_dimension": False,
            "abstained": False,
            "expected_abstain": False,
            "evidence_citation_valid": True,
            "tool_execution_success": True,
            "unsupported_claim_count": 1,
            "total_claim_count": 2,
            "tool_call_count": 6,
            "latency_ms": 200.0,
            "status": "fail",
            "notes": None,
        },
        {
            "scenario_id": "s3",
            "investigation_id": "i3",
            "predicted_direction": None,
            "predicted_primary_driver": None,
            "predicted_dimensions": None,
            "correct_driver": None,
            "correct_dimension": None,
            "abstained": True,
            "expected_abstain": True,
            "evidence_citation_valid": True,
            "tool_execution_success": True,
            "unsupported_claim_count": 0,
            "total_claim_count": 0,
            "tool_call_count": 3,
            "latency_ms": None,
            "status": "abstained",
            "notes": None,
        },
    ]

    result = aggregate_metrics(cases)

    assert result["scenario_count"] == 3
    assert result["root_cause_accuracy"] == 0.5  # 1/2 scored (unanswerable case excluded)
    assert result["dimension_accuracy"] == 0.5
    assert result["evidence_citation_validity_rate"] == 1.0
    assert result["tool_execution_success_rate"] == 1.0
    assert result["unsupported_claim_rate"] == 1 / 4
    assert result["abstention_accuracy"] == 1.0
    assert result["average_tool_calls"] == (4 + 6 + 3) / 3
    assert result["average_latency_ms"] == (100.0 + 200.0) / 2
    assert result["completion_rate"] == 1.0
