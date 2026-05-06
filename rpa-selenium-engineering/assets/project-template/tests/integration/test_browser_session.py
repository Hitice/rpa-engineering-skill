"""Integration test for the Selenium adapter.

Skipped unless the required environment variables are set, so the suite stays
green on machines without a browser. This is the place to validate that
``Selenium Manager`` resolves the driver and that the login Page Object reaches
the dashboard.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

REQUIRED_ENV = ("RPA_TARGET_URL", "RPA_USERNAME", "RPA_PASSWORD")


@pytest.fixture
def settings():
    if any(os.getenv(name) is None for name in REQUIRED_ENV):
        pytest.skip(f"Set {', '.join(REQUIRED_ENV)} to run integration tests")
    from rpa_template.config import load_settings

    return load_settings()


def test_session_starts_and_ends_without_errors(settings) -> None:
    from rpa_template.adapters.selenium_browser import SeleniumBrowserAdapter

    adapter = SeleniumBrowserAdapter(settings)
    adapter.start_session()
    try:
        assert adapter.driver is not None
    finally:
        adapter.end_session()
