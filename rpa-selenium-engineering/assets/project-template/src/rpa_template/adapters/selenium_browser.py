"""Selenium 4 implementation of :class:`BrowserPort`.

Driver binaries are resolved automatically by Selenium Manager, so no driver
path is hardcoded. Synchronization uses :class:`WebDriverWait` with explicit
``expected_conditions``; ``time.sleep`` is forbidden by skill rules.

Transient failures (network blips, slow elements) are retried *inside* a single
``submit`` or ``record_exists`` call via the policy in
:mod:`rpa_template.adapters.retry`. Cross-run idempotency is the responsibility
of the :class:`StateStore`.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from rpa_template.adapters.pages.login_page import LoginPage
from rpa_template.adapters.pages.records_page import RecordsPage
from rpa_template.adapters.retry import transient_retrier
from rpa_template.config import Settings
from rpa_template.contracts.logger import StructuredLogger
from rpa_template.core.entities import Record
from rpa_template.exceptions import (
    AuthenticationError,
    ConfigurationError,
    DomainError,
)


def _build_chrome(*, headless: bool) -> WebDriver:
    from selenium.webdriver.chrome.options import Options as ChromeOptions

    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)


def _build_firefox(*, headless: bool) -> WebDriver:
    from selenium.webdriver.firefox.options import Options as FirefoxOptions

    options = FirefoxOptions()
    if headless:
        options.add_argument("-headless")
    return webdriver.Firefox(options=options)


def _build_edge(*, headless: bool) -> WebDriver:
    from selenium.webdriver.edge.options import Options as EdgeOptions

    options = EdgeOptions()
    if headless:
        options.add_argument("--headless=new")
    return webdriver.Edge(options=options)


_BUILDERS: dict[str, Callable[..., WebDriver]] = {
    "chrome": _build_chrome,
    "firefox": _build_firefox,
    "edge": _build_edge,
}


def _build_driver(browser: str, *, headless: bool) -> WebDriver:
    builder = _BUILDERS.get(browser)
    if builder is None:
        raise ConfigurationError(f"Unsupported browser: {browser!r}")
    return builder(headless=headless)


class SeleniumBrowserAdapter:
    """Implements :class:`BrowserPort` against a real browser session."""

    STEP_NAME = "selenium_retry"

    def __init__(
        self,
        settings: Settings,
        *,
        logger: StructuredLogger | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self._settings = settings
        self._logger = logger
        self._correlation_id = correlation_id
        self._driver: WebDriver | None = None
        self._records: RecordsPage | None = None
        self._retry = transient_retrier(
            attempts=settings.retry_attempts,
            initial_delay_s=settings.retry_initial_delay_s,
            max_delay_s=settings.retry_max_delay_s,
            on_retry=self._log_retry if logger is not None else None,
        )

    def _diagnostics_dir(self) -> Path | None:
        if self._correlation_id is None:
            return None
        target = Path(self._settings.artifacts_dir) / self._correlation_id
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
        return target

    def _dump_diagnostics(self, driver: WebDriver, label: str) -> None:
        """Persist page_source + screenshot for post-mortem; never raises."""
        target = self._diagnostics_dir()
        if target is None:
            return
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        prefix = f"{timestamp}-{label}"
        with suppress(OSError, WebDriverException):
            (target / f"{prefix}.html").write_text(
                driver.page_source, encoding="utf-8"
            )
        with suppress(OSError, WebDriverException, ValueError):
            png_b64 = driver.get_screenshot_as_base64()
            (target / f"{prefix}.png").write_bytes(base64.b64decode(png_b64))

    def _log_retry(
        self,
        attempt_number: int,
        error_type: str,
        error_message: str,
        delay_s: float,
    ) -> None:
        if self._logger is None:
            return
        self._logger.step(
            step=self.STEP_NAME,
            status="error",
            duration_ms=delay_s * 1000.0,
            attempt=attempt_number,
            error_type=error_type,
            error_message=error_message,
            output_summary={"next_delay_s": round(delay_s, 3), "retrying": True},
        )

    @property
    def driver(self) -> WebDriver:
        if self._driver is None:
            raise RuntimeError("Session not started. Call start_session() first.")
        return self._driver

    def start_session(self) -> None:
        driver = _build_driver(self._settings.browser, headless=self._settings.headless)
        try:
            driver.get(str(self._settings.target_url))
            LoginPage(driver, self._settings.default_timeout_s).login(
                self._settings.username.get_secret_value(),
                self._settings.password.get_secret_value(),
            )
        except TimeoutException as err:
            self._dump_diagnostics(driver, "login_timeout")
            driver.quit()
            raise AuthenticationError("Login flow did not reach the dashboard") from err
        except Exception:
            self._dump_diagnostics(driver, "login_unexpected")
            driver.quit()
            raise

        self._driver = driver
        self._records = RecordsPage(
            driver,
            default_timeout_s=self._settings.default_timeout_s,
            submit_timeout_s=self._settings.submit_timeout_s,
        )

    def end_session(self) -> None:
        if self._driver is None:
            return
        try:
            self._driver.quit()
        finally:
            self._driver = None
            self._records = None

    def record_exists(self, key: str) -> bool:
        if self._records is None:
            raise RuntimeError("Session not started.")
        try:
            return bool(self._retry(self._records.has_record, key))
        except DomainError:
            self._dump_diagnostics(self.driver, f"record_exists-{key}")
            raise

    def submit(self, record: Record) -> str:
        if self._records is None:
            raise RuntimeError("Session not started.")
        try:
            return str(self._retry(self._records.submit_record, record))
        except DomainError:
            self._dump_diagnostics(self.driver, f"submit-{record.key}")
            raise
