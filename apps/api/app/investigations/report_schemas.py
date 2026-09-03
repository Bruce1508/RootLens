from typing import Literal

from pydantic import BaseModel

ReportStatus = Literal["answered", "partial", "insufficient_evidence"]
ClaimType = Literal["observed_fact", "interpretation"]
FindingConfidence = Literal["low", "medium", "high"]


class ObservedChange(BaseModel):
    metric: str
    current_value: float
    comparison_value: float
    percent_change: float | None
    evidence_ids: list[str]


class ReportFinding(BaseModel):
    claim: str
    claim_type: ClaimType
    evidence_ids: list[str]
    confidence: FindingConfidence


class ReportNarrative(BaseModel):
    """What the LLM actually generates — headline and findings text.
    Never the numbers themselves; those come from ObservedChange, built
    deterministically from evidence (PRD §6 principle 4)."""

    headline: str
    findings: list[ReportFinding]
    limitations: list[str]
    recommended_next_checks: list[str]


class InvestigationReport(BaseModel):
    status: ReportStatus
    headline: str
    observed_change: ObservedChange
    findings: list[ReportFinding]
    limitations: list[str]
    recommended_next_checks: list[str]
