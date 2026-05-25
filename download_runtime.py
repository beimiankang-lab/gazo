from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import requests

RETRYABLE_STATUSES = {421, 429, 502, 503}
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)


def wait_for_resume(pause_event, stop_event) -> bool:
    while pause_event is not None and not pause_event.is_set():
        if stop_event is not None and stop_event.is_set():
            return False
        time.sleep(0.2)
    return not (stop_event is not None and stop_event.is_set())


def sleep_with_control(seconds: float, pause_event=None, stop_event=None) -> bool:
    remaining = max(0.0, seconds)
    while remaining > 0:
        if stop_event is not None and stop_event.is_set():
            return False
        if pause_event is not None and not pause_event.is_set():
            if not wait_for_resume(pause_event, stop_event):
                return False
        chunk = min(0.2, remaining)
        time.sleep(chunk)
        remaining -= chunk
    return not (stop_event is not None and stop_event.is_set())


def backoff_delay(attempt: int, base_delay: float = 1.0) -> float:
    return min(base_delay * (2 ** max(0, attempt - 1)), 8.0)


def retryable_request(
    send: Callable[[], requests.Response],
    *,
    attempts: int,
    pause_event=None,
    stop_event=None,
    on_retryable: Callable[[dict[str, Any]], None] | None = None,
    base_delay: float = 1.0,
) -> requests.Response | None:
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        if stop_event is not None and stop_event.is_set():
            return None
        if pause_event is not None and not pause_event.is_set():
            if not wait_for_resume(pause_event, stop_event):
                return None

        try:
            response = send()
            if response.status_code in RETRYABLE_STATUSES:
                delay = backoff_delay(attempt, base_delay)
                if on_retryable is not None:
                    on_retryable(
                        {
                            "attempt": attempt,
                            "delay": delay,
                            "status_code": response.status_code,
                            "kind": "status",
                        }
                    )
                response.close()
                if attempt >= attempts:
                    response.raise_for_status()
                if not sleep_with_control(delay, pause_event=pause_event, stop_event=stop_event):
                    return None
                continue

            response.raise_for_status()
            return response
        except RETRYABLE_EXCEPTIONS as exc:
            last_error = exc
            delay = backoff_delay(attempt, base_delay)
            if on_retryable is not None:
                on_retryable(
                    {
                        "attempt": attempt,
                        "delay": delay,
                        "kind": "exception",
                        "error": str(exc),
                    }
                )
            if attempt >= attempts:
                raise
            if not sleep_with_control(delay, pause_event=pause_event, stop_event=stop_event):
                return None
        except Exception:
            raise

    if last_error is not None:
        raise last_error
    return None


@dataclass
class AdaptiveConcurrency:
    initial: int
    floor: int = 2
    threshold: int = 2
    window_seconds: float = 15.0
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _target: int = field(init=False)
    _hits: list[float] = field(default_factory=list, init=False)
    _reduced: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self._target = max(1, self.initial)

    def target(self) -> int:
        with self._lock:
            return self._target

    def note_retryable(self) -> int | None:
        with self._lock:
            now = time.time()
            self._hits = [ts for ts in self._hits if now - ts <= self.window_seconds]
            self._hits.append(now)
            if self._reduced:
                return None
            if len(self._hits) < self.threshold:
                return None
            lowered = min(self._target, max(1, self.floor))
            if lowered >= self._target:
                self._reduced = True
                return None
            self._target = lowered
            self._reduced = True
            return self._target
