from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_readonly_session
from app.main import app
from app.models import Investigation, InvestigationEvent

_BASE_KWARGS = {
    "metric": "product_revenue",
    "metric_definition_version": "product_revenue:v1",
    "current_period_start": "2018-01-01",
    "current_period_end": "2018-01-31",
    "comparison_period_start": "2017-12-01",
    "comparison_period_end": "2017-12-31",
}


def _seed_investigation(
    session: Session, investigation_id: str, status: str, created_at: datetime, updated_at: datetime
) -> None:
    session.add(
        Investigation(
            investigation_id=investigation_id,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            **_BASE_KWARGS,
        )
    )


def _get_runtime_metrics(client: TestClient) -> dict:
    response = client.get("/api/metrics/runtime")
    assert response.status_code == 200
    return response.json()


def test_runtime_metrics_reflects_newly_seeded_investigations_and_events(
    db_session: Session,
) -> None:
    # db_session is a real connection to the shared integration test DB,
    # which (because of test_full_investigation_completes_with_at_least...'s
    # own real-commit design, see its docstring) can already hold rows
    # committed by earlier test runs. Asserting deltas rather than
    # absolute totals keeps this test correct regardless of that history.
    app.dependency_overrides[get_readonly_session] = lambda: db_session
    client = TestClient(app)
    try:
        before = _get_runtime_metrics(client)

        _seed_investigation(
            db_session,
            "inv-done",
            "completed",
            datetime(2026, 1, 1, 0, 0, 0),
            datetime(2026, 1, 1, 0, 0, 10),
        )
        _seed_investigation(
            db_session,
            "inv-rejected",
            "failed",
            datetime(2026, 1, 1, 0, 0, 0),
            datetime(2026, 1, 1, 0, 0, 30),
        )
        db_session.flush()
        db_session.add_all(
            [
                InvestigationEvent(
                    investigation_id="inv-done", event_type="decomposition_plan", payload={}
                ),
                InvestigationEvent(
                    investigation_id="inv-rejected",
                    event_type="ad_hoc_query_rejected",
                    payload={},
                ),
            ]
        )
        db_session.flush()

        after = _get_runtime_metrics(client)
    finally:
        app.dependency_overrides.clear()

    assert after["total_investigations"] == before["total_investigations"] + 2
    assert after["by_status"]["completed"] == before["by_status"].get("completed", 0) + 1
    assert after["by_status"]["failed"] == before["by_status"].get("failed", 0) + 1
    assert after["guardrail_rejections"] == before["guardrail_rejections"] + 1
    assert after["llm_call_count"] == before["llm_call_count"] + 1
