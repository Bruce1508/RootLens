from datetime import datetime

from pydantic import BaseModel


class EvaluationRunView(BaseModel):
    run_id: str
    model_name: str
    split: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    aggregate_metrics: dict | None


class EvaluationCaseResultView(BaseModel):
    scenario_id: str
    template: str | None
    is_unanswerable: bool | None
    investigation_id: str | None
    predicted_direction: str | None
    predicted_primary_driver: str | None
    predicted_dimensions: dict | None
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


class EvaluationRunDetailView(EvaluationRunView):
    cases: list[EvaluationCaseResultView]
