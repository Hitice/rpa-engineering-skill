"""Tests for :class:`RecordProcessor` integrated with a state store."""

from __future__ import annotations

from io import StringIO

from rpa_template.adapters.sqlite_state_store import SqliteStateStore
from rpa_template.adapters.structured_logger import JsonStructuredLogger
from rpa_template.core.entities import Record
from rpa_template.core.services import RecordProcessor
from rpa_template.core.state import ItemState, RunStatus
from rpa_template.exceptions import IntegrationError


class FakeBrowser:
    def __init__(
        self,
        *,
        existing_keys: list[str] | None = None,
        fail_keys: list[str] | None = None,
    ) -> None:
        self.existing_keys = set(existing_keys or [])
        self.fail_keys = set(fail_keys or [])
        self.submitted: list[Record] = []
        self.exists_calls: list[str] = []

    def start_session(self) -> None:
        return None

    def end_session(self) -> None:
        return None

    def record_exists(self, key: str) -> bool:
        self.exists_calls.append(key)
        return key in self.existing_keys

    def submit(self, record: Record) -> str:
        if record.key in self.fail_keys:
            raise IntegrationError(f"forced for {record.key}")
        self.submitted.append(record)
        return f"conf-{record.key}"


def _logger() -> tuple[StringIO, JsonStructuredLogger]:
    buf = StringIO()
    return buf, JsonStructuredLogger(process="test", correlation_id="cid", stream=buf)


def test_terminal_success_in_state_skips_browser() -> None:
    store = SqliteStateStore(":memory:")
    try:
        store.upsert(
            ItemState(key="K1", status=RunStatus.SUCCESS, attempts=1, confirmation_id="prev")
        )
        browser = FakeBrowser()
        _, logger = _logger()
        processor = RecordProcessor(browser=browser, logger=logger, state_store=store)
        outcomes = processor.process([Record(key="K1")])
        assert outcomes[0].status == "skipped"
        assert outcomes[0].confirmation_id == "prev"
        assert browser.exists_calls == []
        assert browser.submitted == []
    finally:
        store.close()


def test_terminal_dead_letter_in_state_is_skipped() -> None:
    store = SqliteStateStore(":memory:")
    try:
        store.upsert(ItemState(key="K2", status=RunStatus.DEAD_LETTER, attempts=3))
        browser = FakeBrowser()
        _, logger = _logger()
        processor = RecordProcessor(browser=browser, logger=logger, state_store=store)
        outcomes = processor.process([Record(key="K2")])
        assert outcomes[0].status == "skipped"
        assert browser.exists_calls == []
    finally:
        store.close()


def test_success_persists_state_as_success() -> None:
    store = SqliteStateStore(":memory:")
    try:
        browser = FakeBrowser()
        _, logger = _logger()
        processor = RecordProcessor(browser=browser, logger=logger, state_store=store)
        processor.process([Record(key="K3")])
        loaded = store.get("K3")
        assert loaded is not None
        assert loaded.status == RunStatus.SUCCESS
        assert loaded.attempts == 1
        assert loaded.confirmation_id == "conf-K3"
    finally:
        store.close()


def test_error_persists_failed_then_promotes_to_dead_letter() -> None:
    store = SqliteStateStore(":memory:")
    try:
        browser = FakeBrowser(fail_keys=["bad"])
        _, logger = _logger()
        processor = RecordProcessor(
            browser=browser, logger=logger, state_store=store, max_attempts=2
        )
        processor.process([Record(key="bad")])
        loaded = store.get("bad")
        assert loaded is not None
        assert loaded.status == RunStatus.FAILED
        assert loaded.attempts == 1

        processor.process([Record(key="bad")])
        loaded = store.get("bad")
        assert loaded is not None
        assert loaded.status == RunStatus.DEAD_LETTER
        assert loaded.attempts == 2

        browser.fail_keys.clear()
        outcomes = processor.process([Record(key="bad")])
        assert outcomes[0].status == "skipped"
        assert browser.submitted == []
    finally:
        store.close()


def test_dry_run_does_not_persist() -> None:
    store = SqliteStateStore(":memory:")
    try:
        browser = FakeBrowser()
        _, logger = _logger()
        processor = RecordProcessor(
            browser=browser, logger=logger, state_store=store, dry_run=True
        )
        outcomes = processor.process([Record(key="K4")])
        assert outcomes[0].status == "would_apply"
        assert store.get("K4") is None
    finally:
        store.close()


def test_works_without_state_store() -> None:
    browser = FakeBrowser()
    _, logger = _logger()
    processor = RecordProcessor(browser=browser, logger=logger)
    outcomes = processor.process([Record(key="K5")])
    assert outcomes[0].status == "success"
