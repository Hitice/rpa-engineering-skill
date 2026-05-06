"""SQLite-backed :class:`StateStore`.

A single-file SQLite database is enough to make an RPA idempotent across runs:
it persists per-record status, attempt counters and the last error so that the
next execution can skip terminal items and resume the rest.

WAL mode is enabled on file-backed databases so concurrent readers do not
block the writer; writes are serialized through one connection per process.
In-memory databases (``:memory:`` for tests) silently skip the WAL PRAGMA,
which is unsupported there.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from rpa_template.core.state import ItemState, RunStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    key              TEXT PRIMARY KEY,
    status           TEXT NOT NULL,
    attempts         INTEGER NOT NULL DEFAULT 0,
    last_error       TEXT,
    confirmation_id  TEXT,
    correlation_id   TEXT,
    updated_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS items_status_idx ON items (status);
"""


class SqliteStateStore:
    """Thread-safe SQLite implementation of :class:`StateStore`."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            self._path,
            isolation_level=None,  # autocommit; explicit txns via BEGIN
            check_same_thread=False,
        )
        if self._path != ":memory:":
            self._conn.executescript(
                "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;"
            )
        self._conn.executescript(_SCHEMA)

    @classmethod
    @contextmanager
    def open(cls, path: str | Path) -> Iterator[SqliteStateStore]:
        store = cls(path)
        try:
            yield store
        finally:
            store.close()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def get(self, key: str) -> ItemState | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT key, status, attempts, last_error, confirmation_id, "
                "correlation_id, updated_at FROM items WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return ItemState(
            key=row[0],
            status=RunStatus(row[1]),
            attempts=int(row[2]),
            last_error=row[3],
            confirmation_id=row[4],
            correlation_id=row[5],
            updated_at=datetime.fromisoformat(row[6]),
        )

    def upsert(self, state: ItemState) -> None:
        timestamp = (state.updated_at or datetime.now(UTC)).isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT INTO items (key, status, attempts, last_error, "
                "confirmation_id, correlation_id, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET "
                "  status = excluded.status, "
                "  attempts = excluded.attempts, "
                "  last_error = excluded.last_error, "
                "  confirmation_id = excluded.confirmation_id, "
                "  correlation_id = excluded.correlation_id, "
                "  updated_at = excluded.updated_at",
                (
                    state.key,
                    state.status.value,
                    state.attempts,
                    state.last_error,
                    state.confirmation_id,
                    state.correlation_id,
                    timestamp,
                ),
            )
