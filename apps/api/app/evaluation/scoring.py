"""FR-14 scoring: turns one investigation's outcome into a per-scenario
case result, and turns a list of case results into the benchmark's
aggregate metrics. Pure/DB-free — app.evaluation.runner is what actually
reads investigations/evidence and builds the case dicts this module scores."""

from typing import Any, TypedDict

from app.investigations.report import _numbers_supported
from app.investigations.report_schemas import ReportFinding


class CaseResult(TypedDict):
    scenario_id: str
    investigation_id: str | None
    predicted_direction: str | None
    predicted_primary_driver: str | None
    predicted_dimensions: dict[str, str] | None
    correct_driver: bool | None
    correct_dimension: bool | None
    abstained: bool
    expected_abstain: bool
    evidence_citation_valid: bool
    tool_execution_success: bool
    unsupported_claim_count: int
    total_claim_count: int
    tool_call_count: int
    latency_ms: float | None
    status: str
    notes: str | None


def score_claims(findings: list[dict[str, Any]], evidence_by_id: dict[str, Any]) -> tuple[int, int]:
    """Returns (unsupported_count, total_count) — re-checks the *final*
    persisted report's observed_fact claims against their cited evidence,
    independent of whatever repair app.investigations.report already did.
    `evidence_by_id` values need only a `.rows` attribute (a stored
    app.models.Evidence row or a ToolResult both qualify)."""
    total = 0
    unsupported = 0
    for finding in findings:
        if finding.get("claim_type") != "observed_fact":
            continue
        total += 1
        report_finding = ReportFinding(**finding)
        if not _numbers_supported(report_finding, evidence_by_id):
            unsupported += 1
    return unsupported, total


def score_direction(observed_change: dict[str, Any] | None) -> str | None:
    if not observed_change or observed_change.get("percent_change") is None:
        return None
    percent_change = observed_change["percent_change"]
    if percent_change < 0:
        return "decrease"
    if percent_change > 0:
        return "increase"
    return None


def score_driver_and_dimension(
    predicted_driver: str | None,
    predicted_dimensions: dict[str, str] | None,
    ground_truth_driver: str | None,
    ground_truth_dimensions: dict[str, str],
) -> tuple[bool | None, bool | None]:
    """None for both when there's no ground-truth driver to compare against
    (unanswerable scenarios) — those are scored on abstention accuracy
    only, per the Milestone 5 plan."""
    if ground_truth_driver is None:
        return None, None

    correct_driver = predicted_driver == ground_truth_driver

    correct_dimension = False
    if predicted_dimensions:
        for dimension_name, predicted_value in predicted_dimensions.items():
            if ground_truth_dimensions.get(dimension_name) == predicted_value:
                correct_dimension = True
                break

    return correct_driver, correct_dimension


def aggregate_metrics(cases: list[CaseResult]) -> dict[str, float | int]:
    """The 8 FR-14 metrics, computed over one evaluation run's cases."""
    if not cases:
        return {
            "root_cause_accuracy": 0.0,
            "dimension_accuracy": 0.0,
            "evidence_citation_validity_rate": 0.0,
            "tool_execution_success_rate": 0.0,
            "unsupported_claim_rate": 0.0,
            "abstention_accuracy": 0.0,
            "average_tool_calls": 0.0,
            "average_latency_ms": 0.0,
            "completion_rate": 0.0,
            "scenario_count": 0,
        }

    scored_driver_cases = [c for c in cases if c["correct_driver"] is not None]
    scored_dimension_cases = [c for c in cases if c["correct_dimension"] is not None]
    latency_cases = [c for c in cases if c["latency_ms"] is not None]

    total_claims = sum(c["total_claim_count"] for c in cases)
    total_unsupported = sum(c["unsupported_claim_count"] for c in cases)

    return {
        "root_cause_accuracy": _rate(c["correct_driver"] for c in scored_driver_cases),
        "dimension_accuracy": _rate(c["correct_dimension"] for c in scored_dimension_cases),
        "evidence_citation_validity_rate": _rate(c["evidence_citation_valid"] for c in cases),
        "tool_execution_success_rate": _rate(c["tool_execution_success"] for c in cases),
        "unsupported_claim_rate": (total_unsupported / total_claims) if total_claims else 0.0,
        "abstention_accuracy": _rate(c["abstained"] == c["expected_abstain"] for c in cases),
        "average_tool_calls": sum(c["tool_call_count"] for c in cases) / len(cases),
        "average_latency_ms": (
            sum(c["latency_ms"] or 0.0 for c in latency_cases) / len(latency_cases)
            if latency_cases
            else 0.0
        ),
        "completion_rate": _rate(c["status"] != "execution_error" for c in cases),
        "scenario_count": len(cases),
    }


def _rate(flags: Any) -> float:
    flags = list(flags)
    if not flags:
        return 0.0
    return sum(1 for f in flags if f) / len(flags)
