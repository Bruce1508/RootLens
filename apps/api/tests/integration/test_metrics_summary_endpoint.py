from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

_FIXTURES_DIR = Path(__file__).resolve().parents[4] / "data" / "fixtures"


@pytest.fixture
def loaded_db(db_session: Session) -> Session:
    from app.ingestion.cli import _LOAD_STEPS
    from app.ingestion.manifest import REQUIRED_FILES

    for key, loader in _LOAD_STEPS:
        filename = str(REQUIRED_FILES[key]["filename"])
        loader(db_session, _FIXTURES_DIR / filename)
    db_session.flush()
    return db_session


def test_metrics_summary_uses_readonly_session_override(loaded_db: Session) -> None:
    from app.db.session import get_readonly_session
    from app.main import app

    app.dependency_overrides[get_readonly_session] = lambda: loaded_db
    try:
        client = TestClient(app)
        response = client.get(
            "/api/metrics/summary",
            params={
                "current_start": "2018-01-01",
                "current_end": "2018-01-31",
                "comparison_start": "2017-12-01",
                "comparison_end": "2017-12-31",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()

    assert body["product_revenue"]["current_value"] == pytest.approx(150.00)
    assert body["product_revenue"]["comparison_value"] == pytest.approx(250.00)
    assert body["orders"]["current_value"] == pytest.approx(2)
    assert body["orders"]["comparison_value"] == pytest.approx(3)


def test_metrics_summary_rejects_invalid_period(loaded_db: Session) -> None:
    from app.db.session import get_readonly_session
    from app.main import app

    app.dependency_overrides[get_readonly_session] = lambda: loaded_db
    try:
        client = TestClient(app)
        response = client.get(
            "/api/metrics/summary",
            params={
                "current_start": "2018-01-31",
                "current_end": "2018-01-01",
                "comparison_start": "2017-12-01",
                "comparison_end": "2017-12-31",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_metrics_summary_rejects_overlapping_periods(loaded_db: Session) -> None:
    from app.db.session import get_readonly_session
    from app.main import app

    app.dependency_overrides[get_readonly_session] = lambda: loaded_db
    try:
        client = TestClient(app)
        response = client.get(
            "/api/metrics/summary",
            params={
                "current_start": "2017-12-01",
                "current_end": "2017-12-31",
                "comparison_start": "2017-12-01",
                "comparison_end": "2017-12-31",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "overlap" in response.json()["detail"]
