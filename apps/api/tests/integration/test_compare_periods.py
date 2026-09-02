import json
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

_FIXTURES_DIR = Path(__file__).resolve().parents[4] / "data" / "fixtures"
_EXPECTED = json.loads((_FIXTURES_DIR / "expected_metrics.json").read_text())


@pytest.fixture
def loaded_db(db_session: Session) -> Session:
    from app.ingestion.cli import _LOAD_STEPS
    from app.ingestion.manifest import REQUIRED_FILES

    for key, loader in _LOAD_STEPS:
        filename = str(REQUIRED_FILES[key]["filename"])
        loader(db_session, _FIXTURES_DIR / filename)
    db_session.flush()
    return db_session


def test_compare_periods_product_revenue_matches_fixture(loaded_db: Session) -> None:
    from app.analytics.compare_periods import compare_periods
    from app.analytics.schemas import DateRange

    current = DateRange(start=date(2018, 1, 1), end=date(2018, 1, 31))
    comparison = DateRange(start=date(2017, 12, 1), end=date(2017, 12, 31))

    result = compare_periods(loaded_db, "product_revenue", current, comparison)

    expected = _EXPECTED["product_revenue"]
    assert float(result.rows[0]["current_value"]) == pytest.approx(expected["current"])
    assert float(result.rows[0]["comparison_value"]) == pytest.approx(expected["comparison"])
    assert float(result.rows[0]["percent_change"]) == pytest.approx(
        expected["percent_change"], abs=1e-4
    )
    assert result.row_count == 1
    assert result.tool_name == "compare_periods"
    assert result.evidence_id


def test_compare_periods_orders_matches_fixture(loaded_db: Session) -> None:
    from app.analytics.compare_periods import compare_periods
    from app.analytics.schemas import DateRange

    current = DateRange(start=date(2018, 1, 1), end=date(2018, 1, 31))
    comparison = DateRange(start=date(2017, 12, 1), end=date(2017, 12, 31))

    result = compare_periods(loaded_db, "orders", current, comparison)

    expected = _EXPECTED["orders"]
    assert int(result.rows[0]["current_value"]) == expected["current"]
    assert int(result.rows[0]["comparison_value"]) == expected["comparison"]
