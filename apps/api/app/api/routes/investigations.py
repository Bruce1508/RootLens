import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import ReadOnlySessionLocal, get_readonly_session, get_write_session
from app.investigations.report_schemas import InvestigationReport
from app.investigations.schemas import (
    EvidenceView,
    InvestigationCreateRequest,
    InvestigationEventView,
    InvestigationView,
)
from app.investigations.service import create_investigation
from app.models import Evidence, Investigation, InvestigationEvent, Report

router = APIRouter()

_TERMINAL_STATUSES = {"completed", "partial", "failed", "timed_out", "cancelled"}


def _to_view(investigation: Investigation, session: Session) -> InvestigationView:
    report_row = (
        session.execute(
            select(Report)
            .where(Report.investigation_id == investigation.investigation_id)
            .order_by(Report.id.desc())
        )
        .scalars()
        .first()
    )
    report = (
        InvestigationReport(
            status=report_row.status,
            headline=report_row.headline,
            observed_change=report_row.observed_change,
            findings=report_row.findings,
            limitations=report_row.limitations,
            recommended_next_checks=report_row.recommended_next_checks,
        )
        if report_row is not None
        else None
    )

    return InvestigationView(
        investigation_id=investigation.investigation_id,
        metric=investigation.metric,
        metric_definition_version=investigation.metric_definition_version,
        current_period={
            "start": investigation.current_period_start,
            "end": investigation.current_period_end,
        },
        comparison_period={
            "start": investigation.comparison_period_start,
            "end": investigation.comparison_period_end,
        },
        question=investigation.question,
        status=investigation.status,
        step_count=investigation.step_count,
        query_count=investigation.query_count,
        created_at=investigation.created_at,
        updated_at=investigation.updated_at,
        report=report,
    )


@router.post("/api/investigations", status_code=201)
def post_investigation(
    request: InvestigationCreateRequest,
    background_tasks: BackgroundTasks,
    session: Annotated[Session, Depends(get_write_session)],
) -> InvestigationView:
    try:
        investigation = create_investigation(session, background_tasks, request)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return _to_view(investigation, session)


@router.get("/api/investigations")
def list_investigations(
    session: Annotated[Session, Depends(get_readonly_session)],
) -> list[InvestigationView]:
    investigations = (
        session.execute(select(Investigation).order_by(Investigation.created_at.desc()))
        .scalars()
        .all()
    )
    return [_to_view(investigation, session) for investigation in investigations]


@router.get("/api/investigations/{investigation_id}")
def get_investigation(
    investigation_id: str,
    session: Annotated[Session, Depends(get_readonly_session)],
) -> InvestigationView:
    investigation = session.get(Investigation, investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="investigation not found")
    return _to_view(investigation, session)


@router.get("/api/investigations/{investigation_id}/evidence/{evidence_id}")
def get_evidence(
    investigation_id: str,
    evidence_id: str,
    session: Annotated[Session, Depends(get_readonly_session)],
) -> EvidenceView:
    evidence = session.get(Evidence, evidence_id)
    if evidence is None or evidence.investigation_id != investigation_id:
        raise HTTPException(status_code=404, detail="evidence not found")
    return EvidenceView(
        evidence_id=evidence.evidence_id,
        tool_name=evidence.tool_name,
        params=evidence.params,
        sql=evidence.sql,
        columns=evidence.columns,
        rows=evidence.rows,
        row_count=evidence.row_count,
        execution_ms=evidence.execution_ms,
        warnings=evidence.warnings,
        created_at=evidence.created_at,
    )


@router.get("/api/investigations/{investigation_id}/events")
def get_investigation_events(
    investigation_id: str,
    session: Annotated[Session, Depends(get_readonly_session)],
) -> list[InvestigationEventView]:
    events = (
        session.execute(
            select(InvestigationEvent)
            .where(InvestigationEvent.investigation_id == investigation_id)
            .order_by(InvestigationEvent.id)
        )
        .scalars()
        .all()
    )
    return [
        InvestigationEventView(
            id=event.id,
            event_type=event.event_type,
            payload=event.payload,
            created_at=event.created_at,
        )
        for event in events
    ]


async def _event_stream(investigation_id: str) -> AsyncGenerator[str]:
    # Deliberately opens a fresh short-lived session per poll iteration
    # rather than relying on a Depends-injected one: FastAPI tears down
    # route dependencies as soon as the endpoint function returns, which
    # for StreamingResponse happens before this generator body ever runs.
    last_seen_id = 0
    while True:
        session = ReadOnlySessionLocal()
        try:
            investigation = session.get(Investigation, investigation_id)
            if investigation is None:
                yield f"event: error\ndata: {json.dumps({'error': 'investigation not found'})}\n\n"
                return

            new_events = (
                session.execute(
                    select(InvestigationEvent)
                    .where(
                        InvestigationEvent.investigation_id == investigation_id,
                        InvestigationEvent.id > last_seen_id,
                    )
                    .order_by(InvestigationEvent.id)
                )
                .scalars()
                .all()
            )

            for event in new_events:
                last_seen_id = event.id
                yield "data: {}\n\n".format(
                    json.dumps(
                        {
                            "id": event.id,
                            "event_type": event.event_type,
                            "payload": event.payload,
                            "created_at": event.created_at.isoformat(),
                        }
                    )
                )

            is_terminal = investigation.status in _TERMINAL_STATUSES
            final_status = investigation.status
        finally:
            session.close()

        if is_terminal:
            yield f"event: done\ndata: {json.dumps({'status': final_status})}\n\n"
            return

        await asyncio.sleep(0.5)


@router.get("/api/investigations/{investigation_id}/stream")
async def stream_investigation(investigation_id: str) -> StreamingResponse:
    return StreamingResponse(_event_stream(investigation_id), media_type="text/event-stream")
