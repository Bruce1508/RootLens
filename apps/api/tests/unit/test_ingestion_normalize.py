from datetime import datetime
from decimal import Decimal


def test_normalize_str_strips_whitespace() -> None:
    from app.ingestion.normalize import normalize_str

    assert normalize_str("  sao paulo  ") == "sao paulo"


def test_normalize_str_treats_empty_as_none() -> None:
    from app.ingestion.normalize import normalize_str

    assert normalize_str("") is None
    assert normalize_str("   ") is None
    assert normalize_str(None) is None


def test_normalize_timestamp_parses_olist_format() -> None:
    from app.ingestion.normalize import normalize_timestamp

    assert normalize_timestamp("2018-01-15 10:30:00") == datetime(2018, 1, 15, 10, 30, 0)


def test_normalize_timestamp_treats_empty_as_none() -> None:
    from app.ingestion.normalize import normalize_timestamp

    assert normalize_timestamp("") is None
    assert normalize_timestamp(None) is None


def test_normalize_decimal_parses_numeric_string() -> None:
    from app.ingestion.normalize import normalize_decimal

    assert normalize_decimal("129.90") == Decimal("129.90")


def test_normalize_decimal_treats_empty_as_none() -> None:
    from app.ingestion.normalize import normalize_decimal

    assert normalize_decimal("") is None
    assert normalize_decimal(None) is None


def test_normalize_int_parses_integer_string() -> None:
    from app.ingestion.normalize import normalize_int

    assert normalize_int("3") == 3


def test_normalize_int_treats_empty_as_none() -> None:
    from app.ingestion.normalize import normalize_int

    assert normalize_int("") is None
    assert normalize_int(None) is None
