"""JSON line structured logger implementation."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any, TextIO


class JsonStructuredLogger:
    """Writes one JSON object per line.

    The destination stream is injected, which keeps the adapter testable
    (a :class:`io.StringIO` works) and decouples it from any specific sink.
    """

    def __init__(
        self,
        *,
        process: str,
        correlation_id: str,
        stream: TextIO | None = None,
    ) -> None:
        self._process = process
        self._correlation_id = correlation_id
        self._stream = stream if stream is not None else sys.stdout

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
                "input_summary": input_summary or {},
                "output_summary": output_summary or {},
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
