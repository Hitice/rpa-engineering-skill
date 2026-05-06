"""Pure entities for cross-run persistent state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RunStatus(StrEnum):
    """Lifecycle states a record can be in across runs."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


TERMINAL_STATUSES: frozenset[RunStatus] = frozenset(
    {RunStatus.SUCCESS, RunStatus.DEAD_LETTER}
)


@dataclass(frozen=True)
class ItemState:
    """Persistent record describing what happened to a given key over time."""

    key: str
    status: RunStatus
    attempts: int = 0
    last_error: str | None = None
    confirmation_id: str | None = None
    correlation_id: str | None = None
    updated_at: datetime | None = None
