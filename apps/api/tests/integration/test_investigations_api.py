from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import WriteSessionLocal, get_readonly_session, get_write_session
from app.main import app
from app.models import Investigation, InvestigationEvent

_VALID_BODY = {
    "metric": "product_revenue",
    "current_period": {"start": "2018-01-01", "end": "2018-01-31"},
    "comparison_period": {"start": "2017-12-01", "end": "2017-12-31"},
}


def test_post_investigation_returns_201_running_and_schedules_background_work(
    db_session: Session,
) -> None:
    # Background execution is stubbed here — this test only proves the
    # synchronous create/validate/respond path, not the full loop (that's
    # covered by test_investigation_engine.py and the live test below).
    app.dependency_overrides[get_write_session] = lambda: db_session
    app.dependency_overrides[get_readonly_session] = lambda: db_session
    try:
        with patch("app.investigations.service._run_in_background") as fake_run:
            client = TestClient(app)
            response = client.post("/api/investigations", json=_VALID_BODY)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "running"
    assert body["metric"] == "product_revenue"
    assert body["metric_definition_version"] == "product_revenue:v1"
    fake_run.assert_called_once_with(body["investigation_id"])


def test_post_investigation_rejects_overlapping_periods(db_session: Session) -> None:
    app.dependency_overrides[get_write_session] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.post(
            "/api/investigations",
            json={
                "metric": "product_revenue",
                "current_period": {"start": "2017-12-01", "end": "2017-12-31"},
                "comparison_period": {"start": "2017-12-01", "end": "2017-12-31"},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_post_investigation_rejects_unknown_metric(db_session: Session) -> None:
    app.dependency_overrides[get_write_session] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.post(
            "/api/investigations",
            json={**_VALID_BODY, "metric": "not_a_real_metric"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_get_investigation_returns_404_for_unknown_id(db_session: Session) -> None:
    app.dependency_overrides[get_readonly_session] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.get("/api/investigations/does-not-exist")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_cancel_investigation_sets_flag_on_a_running_investigation(db_session: Session) -> None:
    with patch("app.investigations.service._run_in_background"):
        app.dependency_overrides[get_write_session] = lambda: db_session
        app.dependency_overrides[get_readonly_session] = lambda: db_session
        try:
            client = TestClient(app)
            create_response = client.post("/api/investigations", json=_VALID_BODY)
            investigation_id = create_response.json()["investigation_id"]

            response = client.post(f"/api/investigations/{investigation_id}/cancel")
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["cancel_requested"] is True

    investigation = db_session.get(Investigation, investigation_id)
    assert investigation.cancel_requested is True


def test_cancel_investigation_is_a_no_op_on_an_already_terminal_investigation(
    db_session: Session,
) -> None:
    investigation = Investigation(
        investigation_id="inv-terminal",
        metric="product_revenue",
        metric_definition_version="product_revenue:v1",
        current_period_start="2018-01-01",
        current_period_end="2018-01-31",
        comparison_period_start="2017-12-01",
        comparison_period_end="2017-12-31",
        status="completed",
    )
    db_session.add(investigation)
    db_session.commit()

    app.dependency_overrides[get_write_session] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.post("/api/investigations/inv-terminal/cancel")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["cancel_requested"] is False


def test_cancel_investigation_returns_404_for_unknown_id(db_session: Session) -> None:
    app.dependency_overrides[get_write_session] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.post("/api/investigations/does-not-exist/cancel")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def _ollama_is_reachable() -> bool:
    try:
        httpx.get("http://localhost:11434/api/tags", timeout=1.0)
        return True
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(not _ollama_is_reachable(), reason="local Ollama daemon is not running")
def test_full_investigation_completes_with_at_least_three_evidence_steps() -> None:
    """Proves Milestone 3's exit criterion for real: one revenue
    investigation completes end to end and uses at least three
    evidence-producing analytical steps.

    No dependency overrides on the POST call — it goes through the app's
    real get_write_session, which (because this whole pytest run is
    invoked with DATABASE_URL pointed at rootlens_test) correctly targets
    the test database. _run_in_background is deliberately left unstubbed:
    it opens its own fresh WriteSessionLocal against that same real
    engine, so this genuinely proves the background loop and a real local
    Ollama call, not a simulation.

    Verification reads through WriteSessionLocal directly rather than the
    GET endpoints: there is no working test-DB credential configured for
    the readonly role anywhere in this project (tests/conftest.py's
    DATABASE_URL_READONLY fallback exists only to satisfy Settings() at
    collection time, not to actually connect) — every other integration
    test sidesteps this by overriding get_readonly_session with the
    transactional db_session fixture, but that fixture's session is bound
    to a SAVEPOINT on an already-open connection and is therefore
    invisible to _run_in_background's separate connection, so it can't be
    used to observe this particular test's own background writes.
    """
    client = TestClient(app)

    post_response = client.post("/api/investigations", json=_VALID_BODY)
    assert post_response.status_code == 201
    investigation_id = post_response.json()["investigation_id"]

    verify_session = WriteSessionLocal()
    try:
        investigation = verify_session.get(Investigation, investigation_id)
        assert investigation is not None
        assert investigation.status in ("completed", "partial", "timed_out")

        events = (
            verify_session.execute(
                select(InvestigationEvent).where(
                    InvestigationEvent.investigation_id == investigation_id
                )
            )
            .scalars()
            .all()
        )
        tool_call_events = [e for e in events if e.event_type == "tool_call"]
        assert len(tool_call_events) >= 3
    finally:
        verify_session.close()
