import json
import logging

from app.core.logging import JsonFormatter


def _format(record: logging.LogRecord) -> dict:
    formatter = JsonFormatter()
    return json.loads(formatter.format(record))


def _make_record(msg: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="rootlens",
        level=logging.INFO,
        pathname="x.py",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_format_includes_level_logger_and_message() -> None:
    record = _make_record("investigation started")

    payload = _format(record)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "rootlens"
    assert payload["message"] == "investigation started"
    assert "timestamp" in payload


def test_format_includes_extra_fields() -> None:
    record = _make_record("investigation completed", investigation_id="abc-123", latency_ms=4200)

    payload = _format(record)

    assert payload["investigation_id"] == "abc-123"
    assert payload["latency_ms"] == 4200


def test_format_does_not_leak_internal_record_attributes() -> None:
    record = _make_record("hello")

    payload = _format(record)

    assert "pathname" not in payload
    assert "lineno" not in payload
    assert "args" not in payload
