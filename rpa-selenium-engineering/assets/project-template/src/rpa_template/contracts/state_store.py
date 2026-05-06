"""Persistent state contract.

Real implementations (SQLite, Postgres, Redis) live in :mod:`rpa_template.adapters`.
The pure-Python no-op fallback :class:`NullStateStore` lives here because it
has no IO dependency and using it must not force importing an adapter module.
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


class NullStateStore:
    """No-op store used when persistence is intentionally disabled.

    Lives next to the :class:`StateStore` Protocol because it carries no IO
    dependency and is the natural default when ``RPA_STATE_DB_PATH`` is unset.
    """

    def get(self, key: str) -> ItemState | None:
        return None

    def upsert(self, state: ItemState) -> None:
        return None
