"""JSON line structured logger with declarative key-based redaction.

The redaction rule is intentionally narrow: any dict key whose lowercased
form contains one of ``redact_keys`` (case-insensitive substring) has its
value replaced by ``"***"``. Free-text fields like ``error_message`` are not
inspected; redact at the source whenever possible.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, TextIO

REDACTED = "***"


class JsonStructuredLogger:
    """Writes one JSON object per line.

    Streams are injected so the adapter is testable with :class:`io.StringIO`
    and is decoupled from any specific sink.
    """

    def __init__(
        self,
        *,
        process: str,
        correlation_id: str,
        stream: TextIO | None = None,
        redact_keys: Iterable[str] | None = None,
    ) -> None:
        self._process = process
        self._correlation_id = correlation_id
        self._stream = stream if stream is not None else sys.stdout
        self._redact_keys: tuple[str, ...] = tuple(
            key.lower() for key in (redact_keys or ()) if key
        )

    def _should_redact(self, key: str) -> bool:
        if not self._redact_keys:
            return False
        lowered = key.lower()
        return any(token in lowered for token in self._redact_keys)

    def _redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: REDACTED if self._should_redact(str(k)) else self._redact(v)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._redact(item) for item in value)
        return value

    def _emit(self, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "process": self._process,
            "correlation_id": self._correlation_id,
            **payload,
        }
        self._stream.write(json.dumps(record, default=str) + "\n")
        self._stream.flush()

    def step(
        self,
        *,
        step: str,
        status: str,
        duration_ms: float,
        attempt: int = 1,
        input_summary: dict[str, Any] | None = None,
        output_summary: dict[str, Any] | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self._emit(
            {
                "step": step,
                "status": status,
                "duration_ms": round(duration_ms, 3),
                "attempt": attempt,
                "input_summary": self._redact(input_summary or {}),
                "output_summary": self._redact(output_summary or {}),
                "error_type": error_type,
                "error_message": error_message,
            }
        )

    def summary(self, totals: dict[str, int], elapsed_ms: float) -> None:
        self._emit(
            {
                "step": "_run_summary",
                "status": "success",
                "duration_ms": round(elapsed_ms, 3),
                "totals": totals,
            }
        )
