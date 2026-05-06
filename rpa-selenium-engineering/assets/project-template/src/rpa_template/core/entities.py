"""Pure domain entities. No IO, no Selenium, no framework imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Record:
    """A unit of work to be processed by the RPA."""

    key: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecordOutcome:
    """The result of processing a single :class:`Record`."""

    key: str
    status: str
    confirmation_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None
