from datetime import datetime
from types import SimpleNamespace

from app.api.routes.metrics import _aggregate_runtime_metrics


def _investigation(status: str, created_at: datetime, updated_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(status=status, created_at=created_at, updated_at=updated_at)


def test_aggregates_status_counts_and_terminal_latency() -> None:
    investigations = [
        _investigation("completed", datetime(2026, 1, 1, 0, 0, 0), datetime(2026, 1, 1, 0, 0, 10)),
        _investigation("failed", datetime(2026, 1, 1, 0, 0, 0), datetime(2026, 1, 1, 0, 0, 30)),
        _investigation("running", datetime(2026, 1, 1, 0, 0, 0), datetime(2026, 1, 1, 0, 0, 0)),
    ]
    event_types = ["decomposition_plan", "report_generated", "ad_hoc_query_rejected"]

    result = _aggregate_runtime_metrics(investigations, event_types)

    assert result["total_investigations"] == 3
    assert result["by_status"] == {"completed": 1, "failed": 1, "running": 1}
    # "running" is not terminal, so only the 10s and 30s investigations count
    assert result["average_latency_ms"] == 20000.0
    assert result["guardrail_rejections"] == 1
    assert result["llm_call_count"] == 2


def test_average_latency_is_none_with_no_terminal_investigations() -> None:
    investigations = [_investigation("running", datetime(2026, 1, 1), datetime(2026, 1, 1))]

    result = _aggregate_runtime_metrics(investigations, [])

    assert result["average_latency_ms"] is None


def test_empty_input_produces_zeroed_metrics() -> None:
    result = _aggregate_runtime_metrics([], [])

    assert result == {
        "total_investigations": 0,
        "by_status": {},
        "average_latency_ms": None,
        "guardrail_rejections": 0,
        "llm_call_count": 0,
    }
