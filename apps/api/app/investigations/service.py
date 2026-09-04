import uuid

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.analytics.validation import validate_non_overlapping
from app.core.config import Settings
from app.db.session import ReadOnlySessionLocal, WriteSessionLocal
from app.investigations.engine import run_investigation
from app.investigations.schemas import InvestigationCreateRequest
from app.llm.ollama_provider import OllamaProvider
from app.metrics.catalog import get_metric_definition
from app.models import Investigation


def build_investigation(session: Session, request: InvestigationCreateRequest) -> Investigation:
    """The synchronous validate-and-create half of create_investigation,
    split out so app.evaluation.runner can create a benchmark scenario's
    investigation row without going through BackgroundTasks/the global
    WriteSessionLocal — it needs the scenario-scoped session from
    app.evaluation.scenario_schema.scenario_sessions instead."""
    validate_non_overlapping(request.current_period, request.comparison_period)
    metric_definition = get_metric_definition(request.metric)  # KeyError if unsupported

    investigation = Investigation(
        investigation_id=str(uuid.uuid4()),
        metric=request.metric,
        metric_definition_version=f"{metric_definition.name}:{metric_definition.version}",
        current_period_start=request.current_period.start,
        current_period_end=request.current_period.end,
        comparison_period_start=request.comparison_period.start,
        comparison_period_end=request.comparison_period.end,
        question=request.question,
        status="running",
    )
    session.add(investigation)
    session.commit()
    session.refresh(investigation)
    return investigation


def create_investigation(
    session: Session, background_tasks: BackgroundTasks, request: InvestigationCreateRequest
) -> Investigation:
    investigation = build_investigation(session, request)
    background_tasks.add_task(_run_in_background, investigation.investigation_id)
    return investigation


def _run_in_background(investigation_id: str) -> None:
    # Not FastAPI-Depends-scoped — BackgroundTasks run after the request's
    # own dependencies have already been torn down, so this opens its own
    # sessions for the loop's full duration: write for state, readonly
    # for every analytics query (Milestone 6 role split, ADR-0004/0007).
    settings = Settings()
    llm = OllamaProvider(base_url=settings.ollama_base_url, default_model=settings.ollama_model)
    write_session = WriteSessionLocal()
    readonly_session = ReadOnlySessionLocal()
    try:
        run_investigation(write_session, readonly_session, llm, investigation_id)
    finally:
        write_session.close()
        readonly_session.close()
