"""Unit tests for the pure core. No browser, no IO."""

from __future__ import annotations

from io import StringIO

from rpa_template.adapters.structured_logger import JsonStructuredLogger
from rpa_template.core.entities import Record
from rpa_template.core.services import RecordProcessor
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
        self.started = False
        self.ended = False

    def start_session(self) -> None:
        self.started = True

    def end_session(self) -> None:
        self.ended = True

    def record_exists(self, key: str) -> bool:
        return key in self.existing_keys

    def submit(self, record: Record) -> str:
        if record.key in self.fail_keys:
            raise IntegrationError(f"forced failure for {record.key}")
        self.submitted.append(record)
        return f"conf-{record.key}"


def _logger() -> tuple[StringIO, JsonStructuredLogger]:
    buf = StringIO()
    return buf, JsonStructuredLogger(process="test", correlation_id="cid", stream=buf)


def test_skips_existing_records() -> None:
    browser = FakeBrowser(existing_keys=["a"])
    _, logger = _logger()
    outcomes = RecordProcessor(browser=browser, logger=logger).process([Record(key="a")])
    assert outcomes[0].status == "skipped"
    assert browser.submitted == []
    assert browser.started and browser.ended


def test_dry_run_does_not_submit() -> None:
    browser = FakeBrowser()
    buf, logger = _logger()
    outcomes = RecordProcessor(browser=browser, logger=logger, dry_run=True).process(
        [Record(key="a", payload={"x": "1"})]
    )
    assert outcomes[0].status == "skipped"
    assert browser.submitted == []
    assert '"would_apply": true' in buf.getvalue()


def test_submits_new_records_and_returns_confirmation() -> None:
    browser = FakeBrowser()
    _, logger = _logger()
    outcomes = RecordProcessor(browser=browser, logger=logger).process(
        [Record(key="x", payload={"f": "1"})]
    )
    assert outcomes[0].status == "success"
    assert outcomes[0].confirmation_id == "conf-x"
    assert [r.key for r in browser.submitted] == ["x"]


def test_domain_errors_recorded_not_propagated() -> None:
    browser = FakeBrowser(fail_keys=["bad"])
    _, logger = _logger()
    outcomes = RecordProcessor(browser=browser, logger=logger).process(
        [Record(key="bad"), Record(key="ok")]
    )
    assert outcomes[0].status == "error"
    assert outcomes[0].error_type == "IntegrationError"
    assert outcomes[1].status == "success"


def test_session_ended_even_on_empty_batch() -> None:
    browser = FakeBrowser()
    _, logger = _logger()
    RecordProcessor(browser=browser, logger=logger).process([])
    assert browser.started and browser.ended


def test_logger_emits_run_summary() -> None:
    browser = FakeBrowser()
    buf, logger = _logger()
    RecordProcessor(browser=browser, logger=logger).process([Record(key="a")])
    assert "_run_summary" in buf.getvalue()
