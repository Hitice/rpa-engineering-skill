"""Use-case orchestration: lock + state + processor.

The flow is the only place where adapters are constructed and wired together.
It is also the only place that is allowed to talk to the filesystem (the
SQLite database and the lock file). Everything below is a contract.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Iterator
from contextlib import ExitStack, contextmanager

from filelock import FileLock, Timeout

from rpa_template.adapters.selenium_browser import SeleniumBrowserAdapter
from rpa_template.adapters.sqlite_state_store import NullStateStore, SqliteStateStore
from rpa_template.adapters.structured_logger import JsonStructuredLogger
from rpa_template.config import Settings
from rpa_template.contracts.state_store import StateStore
from rpa_template.core.entities import Record, RecordOutcome
from rpa_template.core.services import RecordProcessor
from rpa_template.exceptions import ConfigurationError


@contextmanager
def _process_lock(settings: Settings) -> Iterator[None]:
    if settings.lock_path is None:
        yield
        return
    settings.lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(settings.lock_path), timeout=settings.lock_timeout_s)
    try:
        with lock:
            yield
    except Timeout as err:
        raise ConfigurationError(
            f"Another instance holds the lock at {settings.lock_path}"
        ) from err


@contextmanager
def _state_store(settings: Settings) -> Iterator[StateStore]:
    if settings.state_db_path is None:
        yield NullStateStore()
        return
    settings.state_db_path.parent.mkdir(parents=True, exist_ok=True)
    with SqliteStateStore.open(settings.state_db_path) as store:
        yield store


def run(settings: Settings, records: Iterable[Record]) -> list[RecordOutcome]:
    correlation_id = str(uuid.uuid4())
    logger = JsonStructuredLogger(
        process=settings.process_name,
        correlation_id=correlation_id,
    )

    with ExitStack() as stack:
        stack.enter_context(_process_lock(settings))
        store = stack.enter_context(_state_store(settings))

        browser = SeleniumBrowserAdapter(settings)
        processor = RecordProcessor(
            browser=browser,
            logger=logger,
            state_store=store,
            dry_run=settings.dry_run,
            max_attempts=settings.max_attempts,
            correlation_id=correlation_id,
        )
        return processor.process(records)
