"""Persistent state contract.

Implementations live in :mod:`rpa_template.adapters`. Keeping the contract here
lets ``core`` depend on the abstraction without ever importing SQLite, the
filesystem or any other infrastructure.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rpa_template.core.state import ItemState


@runtime_checkable
class StateStore(Protocol):
    def get(self, key: str) -> ItemState | None:
        """Return the persisted state for ``key`` or ``None`` if unknown."""

    def upsert(self, state: ItemState) -> None:
        """Insert or replace the state for ``state.key`` atomically."""
