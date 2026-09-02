from datetime import date

import pytest
from pydantic import ValidationError


def test_date_range_accepts_start_before_end() -> None:
    from app.analytics.schemas import DateRange

    r = DateRange(start=date(2018, 1, 1), end=date(2018, 1, 31))

    assert r.start == date(2018, 1, 1)
    assert r.end == date(2018, 1, 31)


def test_date_range_rejects_start_not_before_end() -> None:
    from app.analytics.schemas import DateRange

    with pytest.raises(ValidationError):
        DateRange(start=date(2018, 1, 31), end=date(2018, 1, 1))


def test_date_range_rejects_equal_start_and_end() -> None:
    from app.analytics.schemas import DateRange

    with pytest.raises(ValidationError):
        DateRange(start=date(2018, 1, 1), end=date(2018, 1, 1))


def test_validate_non_overlapping_accepts_disjoint_periods() -> None:
    from app.analytics.schemas import DateRange
    from app.analytics.validation import validate_non_overlapping

    current = DateRange(start=date(2018, 1, 1), end=date(2018, 1, 31))
    comparison = DateRange(start=date(2017, 12, 1), end=date(2017, 12, 31))

    validate_non_overlapping(current, comparison)  # should not raise


def test_validate_non_overlapping_rejects_overlap() -> None:
    from app.analytics.schemas import DateRange
    from app.analytics.validation import validate_non_overlapping

    current = DateRange(start=date(2018, 1, 1), end=date(2018, 1, 31))
    comparison = DateRange(start=date(2018, 1, 15), end=date(2018, 2, 15))

    with pytest.raises(ValueError, match="overlap"):
        validate_non_overlapping(current, comparison)
