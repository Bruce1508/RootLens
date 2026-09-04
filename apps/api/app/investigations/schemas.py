from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.analytics.schemas import DateRange
from app.investigations.report_schemas import InvestigationReport

InvestigationStatus = Literal["running", "completed", "partial", "failed", "timed_out", "cancelled"]
HypothesisStatus = Literal["untested", "testing", "supported", "rejected", "inconclusive"]
Confidence = Literal["low", "medium", "high"]


class InvestigationCreateRequest(BaseModel):
    metric: str
    current_period: DateRange
    comparison_period: DateRange
    question: str | None = None


class HypothesisView(BaseModel):
    id: str
    statement: str
    status: HypothesisStatus
    confidence: Confidence | None
    supporting_evidence_ids: list[str]
    contradicting_evidence_ids: list[str]


class InvestigationView(BaseModel):
    investigation_id: str
    metric: str
    metric_definition_version: str
    current_period: DateRange
    comparison_period: DateRange
    question: str | None
    status: InvestigationStatus
    step_count: int
    query_count: int
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime
    report: InvestigationReport | None = None


class InvestigationEventView(BaseModel):
    id: int
    event_type: str
    payload: dict
    created_at: datetime


class EvidenceView(BaseModel):
    evidence_id: str
    tool_name: str
    params: dict
    sql: str
    columns: list[str]
    rows: list[dict]
    row_count: int
    execution_ms: float
    warnings: list[str]
    created_at: datetime
