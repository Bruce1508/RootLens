import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException

from app.core.config import Settings


class InMemoryRateLimiter:
    """Phase 4 minimum-credible-set rate limiting: a fixed-count sliding
    window, in process. Single-instance deployment, so no shared store
    (Redis etc.) is needed — add one if this ever runs as more than one
    process."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        time_func: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._time_func = time_func
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def check(self) -> None:
        now = self._time_func()
        with self._lock:
            while self._timestamps and now - self._timestamps[0] > self._window_seconds:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._max_requests:
                raise HTTPException(status_code=429, detail="rate limit exceeded")
            self._timestamps.append(now)

    def reset(self) -> None:
        with self._lock:
            self._timestamps.clear()


_settings = Settings()
investigation_rate_limiter = InMemoryRateLimiter(
    max_requests=_settings.rate_limit_max_requests,
    window_seconds=_settings.rate_limit_window_seconds,
)


def enforce_investigation_rate_limit() -> None:
    investigation_rate_limiter.check()
