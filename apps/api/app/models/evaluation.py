from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_EVAL_SCHEMA = "eval"


class EvalScenario(Base):
    """Hidden benchmark input spec (FR-13). Lives in the `eval` Postgres
    schema, which rootlens_readonly has no grant on (ADR-0004's default
    privileges only cover `public`) — see ADR-0007."""

    __tablename__ = "eval_scenarios"
    __table_args__ = {"schema": _EVAL_SCHEMA}

    scenario_id: Mapped[str] = mapped_column(String, primary_key=True)
    template: Mapped[str] = mapped_column(String, index=True)
    metric: Mapped[str] = mapped_column(String)
    current_period_start: Mapped[date] = mapped_column(Date)
    current_period_end: Mapped[date] = mapped_column(Date)
    comparison_period_start: Mapped[date] = mapped_column(Date)
    comparison_period_end: Mapped[date] = mapped_column(Date)
    split: Mapped[str] = mapped_column(String, index=True)
    seed: Mapped[int] = mapped_column(Integer)
    is_unanswerable: Mapped[bool] = mapped_column(Boolean, default=False)
    question: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EvalGroundTruth(Base):
    """Hidden expected answer for a scenario (FR-13). Same `eval` schema as
    EvalScenario — together they're the answer key kept away from the
    investigation engine's data access, per PRD §14."""

    __tablename__ = "eval_ground_truth"
    __table_args__ = {"schema": _EVAL_SCHEMA}

    scenario_id: Mapped[str] = mapped_column(
        String, ForeignKey(f"{_EVAL_SCHEMA}.eval_scenarios.scenario_id"), primary_key=True
    )
    # Both nullable: unanswerable scenarios (is_unanswerable=True on the
    # matching EvalScenario) have no meaningful direction/driver — they're
    # scored only on abstention accuracy, not root-cause/dimension accuracy.
    direction: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_driver: Mapped[str | None] = mapped_column(String, nullable=True)
    dimensions: Mapped[dict] = mapped_column(JSONB, default=dict)
    severity: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EvaluationRun(Base):
    """A single FR-14 benchmark execution. Public schema — these are the
    reported results, not the hidden answer key."""

    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    model_name: Mapped[str] = mapped_column(String)
    prompt_versions: Mapped[dict] = mapped_column(JSONB, default=dict)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    split: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    aggregate_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class EvaluationCaseResult(Base):
    """One scenario's outcome within an EvaluationRun (FR-14)."""

    __tablename__ = "evaluation_case_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("evaluation_runs.id"), index=True)
    scenario_id: Mapped[str] = mapped_column(String, index=True)
    investigation_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("investigations.investigation_id"), nullable=True
    )
    predicted_direction: Mapped[str | None] = mapped_column(String, nullable=True)
    predicted_primary_driver: Mapped[str | None] = mapped_column(String, nullable=True)
    predicted_dimensions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correct_driver: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    correct_dimension: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    abstained: Mapped[bool] = mapped_column(Boolean, default=False)
    expected_abstain: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_citation_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    tool_execution_success: Mapped[bool] = mapped_column(Boolean, default=True)
    unsupported_claim_count: Mapped[int] = mapped_column(Integer, default=0)
    total_claim_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, index=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
