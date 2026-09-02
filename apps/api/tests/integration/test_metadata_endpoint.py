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


def test_date_range_returns_min_and_max_purchase_dates(loaded_db: Session) -> None:
    from app.db.session import get_readonly_session
    from app.main import app

    app.dependency_overrides[get_readonly_session] = lambda: loaded_db
    try:
        client = TestClient(app)
        response = client.get("/api/metadata/date-range")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["min_date"] == "2017-12-05"
    assert body["max_date"] == "2018-01-20"
