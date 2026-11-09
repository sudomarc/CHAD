from __future__ import annotations

import threading
from collections.abc import Callable

from chad.llm.client import LLMError


class CancellationError(LLMError):
    pass


class CancellationToken:
    """Thread-safe cooperative cancellation token for model requests and agent runs."""

    def __init__(self) -> None:
        self._is_cancelled = False
        self._reason: str | None = None
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[str], None]] = []

    @property
    def is_cancelled(self) -> bool:
        with self._lock:
            return self._is_cancelled

    @property
    def reason(self) -> str | None:
        with self._lock:
            return self._reason

    def cancel(self, reason: str = "Request cancelled") -> None:
        callbacks_to_run: list[Callable[[str], None]] = []
        with self._lock:
            if self._is_cancelled:
                return
            self._is_cancelled = True
            self._reason = reason
            callbacks_to_run = list(self._callbacks)

        for callback in callbacks_to_run:
            try:
                callback(reason)
            except Exception:
                pass

    def register_callback(self, callback: Callable[[str], None]) -> None:
        run_immediately = False
        reason: str | None = None
        with self._lock:
            if self._is_cancelled:
                run_immediately = True
                reason = self._reason or "Request cancelled"
            else:
                self._callbacks.append(callback)

        if run_immediately and reason is not None:
            try:
                callback(reason)
            except Exception:
                pass

    def throw_if_cancelled(self) -> None:
        with self._lock:
            if self._is_cancelled:
                msg = self._reason or "Request cancelled"
                raise CancellationError(msg)
