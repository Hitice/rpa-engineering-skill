"""Structured logger contract."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StructuredLogger(Protocol):
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
        """Emit one structured record per step."""

    def summary(self, totals: dict[str, int], elapsed_ms: float) -> None:
        """Emit a final summary at the end of a run."""
