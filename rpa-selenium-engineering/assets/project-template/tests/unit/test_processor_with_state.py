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
        buf, logger = _logger()
        processor = RecordProcessor(
            browser=browser, logger=logger, state_store=store, dry_run=True
        )
        outcomes = processor.process([Record(key="K4")])
        assert outcomes[0].status == "skipped"
        assert store.get("K4") is None
        assert '"would_apply": true' in buf.getvalue()
    finally:
        store.close()


def test_works_without_state_store() -> None:
    browser = FakeBrowser()
    _, logger = _logger()
    processor = RecordProcessor(browser=browser, logger=logger)
    outcomes = processor.process([Record(key="K5")])
    assert outcomes[0].status == "success"


def test_skipped_is_non_terminal_and_revalidates_against_destination() -> None:
    """SKIPPED is intentionally non-terminal: a previous run observed the
    record at the destination, but the destination is the source of truth and
    may be eventually consistent. Each run re-checks via ``record_exists``.
    Only ``SUCCESS`` (we wrote it) and ``DEAD_LETTER`` (retries exhausted) are
    terminal.
    """
    store = SqliteStateStore(":memory:")
    try:
        first_browser = FakeBrowser(existing_keys=["K"])
        _, first_logger = _logger()
        RecordProcessor(
            browser=first_browser, logger=first_logger, state_store=store
        ).process([Record(key="K")])
        first_state = store.get("K")
        assert first_state is not None
        assert first_state.status == RunStatus.SKIPPED
        assert first_browser.exists_calls == ["K"]

        second_browser = FakeBrowser(existing_keys=[])
        _, second_logger = _logger()
        outcomes = RecordProcessor(
            browser=second_browser, logger=second_logger, state_store=store
        ).process([Record(key="K")])
        assert second_browser.exists_calls == ["K"], "must re-validate, not short-circuit"
        assert outcomes[0].status == "success"
        assert [r.key for r in second_browser.submitted] == ["K"]
        final_state = store.get("K")
        assert final_state is not None
        assert final_state.status == RunStatus.SUCCESS
    finally:
        store.close()
