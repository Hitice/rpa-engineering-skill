"""Behavioral contract tests for :class:`StateStore` implementations.

Every implementation registered as ``store_factory`` must satisfy the same
invariants. Adding a new backend (e.g., Postgres) means adding it to the
parametrize list — no changes to ``core/`` or ``flows/`` are needed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from rpa_template.adapters.sqlite_state_store import SqliteStateStore
from rpa_template.contracts.state_store import NullStateStore, StateStore
from rpa_template.core.state import ItemState, RunStatus


@contextmanager
def _sqlite_factory() -> Iterator[StateStore]:
    store = SqliteStateStore(":memory:")
    try:
        yield store
    finally:
        store.close()


@contextmanager
def _null_factory() -> Iterator[StateStore]:
    yield NullStateStore()


StoreFactory = Callable[[], Iterator[StateStore]]


@pytest.fixture(
    params=[
        pytest.param(_sqlite_factory, id="sqlite-memory"),
        pytest.param(_null_factory, id="null"),
    ]
)
def store(request: pytest.FixtureRequest) -> Iterator[StateStore]:
    factory: StoreFactory = request.param
    with factory() as instance:
        yield instance


def _is_null(store: StateStore) -> bool:
    return isinstance(store, NullStateStore)


def test_get_returns_none_for_unknown_keys(store: StateStore) -> None:
    assert store.get("unknown") is None


def test_runtime_checkable_protocol_compliance(store: StateStore) -> None:
    assert isinstance(store, StateStore)


def test_upsert_round_trip_or_explicit_noop(store: StateStore) -> None:
    state = ItemState(
        key="K",
        status=RunStatus.SUCCESS,
        attempts=1,
        confirmation_id="C-1",
    )
    store.upsert(state)
    loaded = store.get("K")
    if _is_null(store):
        assert loaded is None, "NullStateStore must remain a no-op"
    else:
        assert loaded is not None
        assert loaded.status == RunStatus.SUCCESS
        assert loaded.attempts == 1
        assert loaded.confirmation_id == "C-1"


def test_upsert_replaces_previous_state(store: StateStore) -> None:
    if _is_null(store):
        pytest.skip("NullStateStore has no observable mutation")
    store.upsert(ItemState(key="K", status=RunStatus.FAILED, attempts=1))
    store.upsert(ItemState(key="K", status=RunStatus.DEAD_LETTER, attempts=3))
    loaded = store.get("K")
    assert loaded is not None
    assert loaded.status == RunStatus.DEAD_LETTER
    assert loaded.attempts == 3


def test_upsert_does_not_affect_other_keys(store: StateStore) -> None:
    if _is_null(store):
        pytest.skip("NullStateStore has no observable mutation")
    store.upsert(ItemState(key="A", status=RunStatus.SUCCESS, attempts=1))
    store.upsert(ItemState(key="B", status=RunStatus.FAILED, attempts=2))
    a = store.get("A")
    b = store.get("B")
    assert a is not None and a.status == RunStatus.SUCCESS
    assert b is not None and b.status == RunStatus.FAILED
