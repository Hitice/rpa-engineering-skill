"""Pure orchestration over :class:`BrowserPort` with optional persistence.

This module never imports Selenium, SQLite or any IO library. It depends only
on contracts, so it is fully testable with fakes.

Cross-run behavior, when a :class:`StateStore` is provided:

* Items already in a terminal state (``SUCCESS`` or ``DEAD_LETTER``) are
  skipped without touching the browser.
* Each new attempt increments the persisted ``attempts`` counter.
* Errors are persisted as ``FAILED`` until ``attempts >= max_attempts``, after
  which the item is promoted to ``DEAD_LETTER`` and stops being retried.
* In ``dry_run`` mode no state mutations are written.
"""

from __future__ import annotations

import time
from collections.abc import Iterable

from rpa_template.contracts.browser import BrowserPort
from rpa_template.contracts.logger import StructuredLogger
from rpa_template.contracts.state_store import StateStore
from rpa_template.core.entities import Record, RecordOutcome
from rpa_template.core.state import TERMINAL_STATUSES, ItemState, RunStatus
from rpa_template.exceptions import DomainError


class RecordProcessor:
    """Process a batch of records idempotently with structured telemetry."""

    STEP_NAME = "process_record"

    def __init__(
        self,
        browser: BrowserPort,
        logger: StructuredLogger,
        *,
        state_store: StateStore | None = None,
        dry_run: bool = False,
        max_attempts: int = 3,
        correlation_id: str | None = None,
    ) -> None:
        self._browser = browser
        self._logger = logger
        self._state = state_store
        self._dry_run = dry_run
        self._max_attempts = max(1, max_attempts)
        self._correlation_id = correlation_id

    def process(self, records: Iterable[Record]) -> list[RecordOutcome]:
        outcomes: list[RecordOutcome] = []
        totals: dict[str, int] = {}
        run_start = time.monotonic()

        self._browser.start_session()
        try:
            for record in records:
                outcome = self._process_one(record)
                outcomes.append(outcome)
                totals[outcome.status] = totals.get(outcome.status, 0) + 1
        finally:
            self._browser.end_session()

        elapsed_ms = (time.monotonic() - run_start) * 1000
        self._logger.summary(totals=totals, elapsed_ms=elapsed_ms)
        return outcomes

    def _process_one(self, record: Record) -> RecordOutcome:
        prior = self._state.get(record.key) if self._state is not None else None

        if prior is not None and prior.status in TERMINAL_STATUSES:
            outcome = RecordOutcome(
                key=record.key,
                status="skipped",
                confirmation_id=prior.confirmation_id,
            )
            self._emit_log(outcome, duration_ms=0.0, attempt=prior.attempts)
            return outcome

        attempts = (prior.attempts if prior is not None else 0) + 1
        step_start = time.monotonic()
        try:
            if self._browser.record_exists(record.key):
                outcome = RecordOutcome(key=record.key, status="skipped")
            elif self._dry_run:
                outcome = RecordOutcome(key=record.key, status="would_apply")
            else:
                confirmation = self._browser.submit(record)
                outcome = RecordOutcome(
                    key=record.key,
                    status="success",
                    confirmation_id=confirmation,
                )
        except DomainError as err:
            outcome = RecordOutcome(
                key=record.key,
                status="error",
                error_type=type(err).__name__,
                error_message=str(err),
            )

        duration_ms = (time.monotonic() - step_start) * 1000
        if not self._dry_run:
            self._persist(outcome, attempts)
        self._emit_log(outcome, duration_ms=duration_ms, attempt=attempts)
        return outcome

    def _persist(self, outcome: RecordOutcome, attempts: int) -> None:
        if self._state is None:
            return

        status = self._terminal_status_for(outcome, attempts)
        if status is None:
            return

        self._state.upsert(
            ItemState(
                key=outcome.key,
                status=status,
                attempts=attempts,
                last_error=outcome.error_message,
                confirmation_id=outcome.confirmation_id,
                correlation_id=self._correlation_id,
            )
        )

    def _terminal_status_for(
        self, outcome: RecordOutcome, attempts: int
    ) -> RunStatus | None:
        if outcome.status == "success":
            return RunStatus.SUCCESS
        if outcome.status == "skipped":
            return RunStatus.SKIPPED
        if outcome.status == "error":
            return (
                RunStatus.DEAD_LETTER
                if attempts >= self._max_attempts
                else RunStatus.FAILED
            )
        return None  # would_apply: never persisted

    def _emit_log(
        self,
        outcome: RecordOutcome,
        *,
        duration_ms: float,
        attempt: int,
    ) -> None:
        self._logger.step(
            step=self.STEP_NAME,
            status=outcome.status,
            duration_ms=duration_ms,
            attempt=attempt,
            input_summary={"key": outcome.key},
            output_summary=(
                {"confirmation_id": outcome.confirmation_id}
                if outcome.confirmation_id is not None
                else None
            ),
            error_type=outcome.error_type,
            error_message=outcome.error_message,
        )
