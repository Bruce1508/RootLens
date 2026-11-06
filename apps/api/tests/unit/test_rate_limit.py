import pytest
from fastapi import HTTPException

from app.core.rate_limit import InMemoryRateLimiter


def test_allows_requests_up_to_the_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60.0, time_func=lambda: 0.0)

    limiter.check()
    limiter.check()
    limiter.check()


def test_rejects_the_request_over_the_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60.0, time_func=lambda: 0.0)
    limiter.check()
    limiter.check()

    with pytest.raises(HTTPException) as exc_info:
        limiter.check()

    assert exc_info.value.status_code == 429


def test_allows_again_once_the_window_has_elapsed() -> None:
    now = [0.0]
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=10.0, time_func=lambda: now[0])

    limiter.check()
    with pytest.raises(HTTPException):
        limiter.check()

    now[0] = 10.1
    limiter.check()  # the first timestamp has aged out of the window


def test_reset_clears_recorded_requests() -> None:
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60.0, time_func=lambda: 0.0)
    limiter.check()

    limiter.reset()

    limiter.check()
