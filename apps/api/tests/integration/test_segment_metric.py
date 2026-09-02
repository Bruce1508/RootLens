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


def test_segment_metric_by_customer_state_matches_fixture(loaded_db: Session) -> None:
    from app.analytics.schemas import DateRange
    from app.analytics.segment_metric import segment_metric

    current = DateRange(start=date(2018, 1, 1), end=date(2018, 1, 31))
    comparison = DateRange(start=date(2017, 12, 1), end=date(2017, 12, 31))

    result = segment_metric(loaded_db, "product_revenue", "customer_state", current, comparison)

    expected = _EXPECTED["segment_by_customer_state"]
    by_segment = {row["segment_value"]: row for row in result.rows}

    assert set(by_segment.keys()) == {"SP", "RJ"}
    for state, row in by_segment.items():
        assert float(row["current_value"]) == pytest.approx(expected["current"][state])
        assert float(row["comparison_value"]) == pytest.approx(expected["comparison"][state])
    assert result.tool_name == "segment_metric"


def test_segment_metric_by_product_category_matches_fixture(loaded_db: Session) -> None:
    from app.analytics.schemas import DateRange
    from app.analytics.segment_metric import segment_metric

    current = DateRange(start=date(2018, 1, 1), end=date(2018, 1, 31))
    comparison = DateRange(start=date(2017, 12, 1), end=date(2017, 12, 31))

    result = segment_metric(loaded_db, "product_revenue", "product_category", current, comparison)

    expected = _EXPECTED["segment_by_product_category"]
    by_segment = {row["segment_value"]: row for row in result.rows}

    for category, row in by_segment.items():
        assert float(row["current_value"]) == pytest.approx(expected["current"][category])
        assert float(row["comparison_value"]) == pytest.approx(expected["comparison"][category])


def test_calculate_contribution_by_customer_state_matches_fixture(loaded_db: Session) -> None:
    from app.analytics.calculate_contribution import calculate_contribution
    from app.analytics.schemas import DateRange

    current = DateRange(start=date(2018, 1, 1), end=date(2018, 1, 31))
    comparison = DateRange(start=date(2017, 12, 1), end=date(2017, 12, 31))

    result = calculate_contribution(
        loaded_db, "product_revenue", "customer_state", current, comparison
    )

    expected = _EXPECTED["segment_by_customer_state"]["contribution_to_total_change"]
    by_segment = {row["segment_value"]: row for row in result.rows}

    for state, row in by_segment.items():
        assert float(row["change"]) == pytest.approx(expected[state]["change"])
        assert float(row["share_of_total_change"]) == pytest.approx(
            expected[state]["share_of_total_change"], abs=1e-4
        )
    assert result.tool_name == "calculate_contribution"


def test_calculate_contribution_by_product_category_matches_fixture(
    loaded_db: Session,
) -> None:
    from app.analytics.calculate_contribution import calculate_contribution
    from app.analytics.schemas import DateRange

    current = DateRange(start=date(2018, 1, 1), end=date(2018, 1, 31))
    comparison = DateRange(start=date(2017, 12, 1), end=date(2017, 12, 31))

    result = calculate_contribution(
        loaded_db, "product_revenue", "product_category", current, comparison
    )

    expected = _EXPECTED["segment_by_product_category"]["contribution_to_total_change"]
    by_segment = {row["segment_value"]: row for row in result.rows}

    for category, row in by_segment.items():
        assert float(row["change"]) == pytest.approx(expected[category]["change"])
        assert float(row["share_of_total_change"]) == pytest.approx(
            expected[category]["share_of_total_change"], abs=1e-4
        )
