"""Tests for the SQLite state store using an in-memory database."""

from __future__ import annotations

from rpa_template.adapters.sqlite_state_store import NullStateStore, SqliteStateStore
from rpa_template.core.state import ItemState, RunStatus


def _store() -> SqliteStateStore:
    return SqliteStateStore(":memory:")


def test_get_returns_none_for_unknown_keys() -> None:
    store = _store()
    try:
        assert store.get("missing") is None
    finally:
        store.close()


def test_upsert_inserts_and_round_trips() -> None:
    store = _store()
    try:
        store.upsert(
            ItemState(
                key="A1",
                status=RunStatus.SUCCESS,
                attempts=2,
                confirmation_id="C-1",
                correlation_id="run-x",
            )
        )
        loaded = store.get("A1")
        assert loaded is not None
        assert loaded.status == RunStatus.SUCCESS
        assert loaded.attempts == 2
        assert loaded.confirmation_id == "C-1"
        assert loaded.correlation_id == "run-x"
        assert loaded.updated_at is not None
    finally:
        store.close()


def test_upsert_replaces_existing_row() -> None:
    store = _store()
    try:
        store.upsert(
            ItemState(key="A1", status=RunStatus.FAILED, attempts=1, last_error="boom")
        )
        store.upsert(
            ItemState(key="A1", status=RunStatus.DEAD_LETTER, attempts=3, last_error="boom")
        )
        loaded = store.get("A1")
        assert loaded is not None
        assert loaded.status == RunStatus.DEAD_LETTER
        assert loaded.attempts == 3
    finally:
        store.close()


def test_null_store_is_a_noop() -> None:
    store = NullStateStore()
    assert store.get("anything") is None
    store.upsert(ItemState(key="A1", status=RunStatus.SUCCESS))
    assert store.get("A1") is None
