from datetime import datetime
from decimal import Decimal, InvalidOperation

# Olist CSV timestamps are consistently "YYYY-MM-DD HH:MM:SS", no timezone.
# The whole pipeline treats these as naive local time (documented in
# docs/architecture/overview.md) rather than assuming UTC, since the source
# data carries no timezone marker to normalize against.
_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def normalize_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def normalize_timestamp(value: str | None) -> datetime | None:
    stripped = normalize_str(value)
    if stripped is None:
        return None
    return datetime.strptime(stripped, _TIMESTAMP_FORMAT)


def normalize_decimal(value: str | None) -> Decimal | None:
    stripped = normalize_str(value)
    if stripped is None:
        return None
    try:
        return Decimal(stripped)
    except InvalidOperation as e:
        raise ValueError(f"invalid decimal value: {value!r}") from e


def normalize_int(value: str | None) -> int | None:
    stripped = normalize_str(value)
    if stripped is None:
        return None
    return int(stripped)
