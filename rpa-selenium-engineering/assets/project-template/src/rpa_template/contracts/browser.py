"""Domain-level browser contract.

The contract exposes only intentions; framework-specific types like
:class:`selenium.webdriver.remote.webelement.WebElement` never leak through.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rpa_template.core.entities import Record


@runtime_checkable
class BrowserPort(Protocol):
    def start_session(self) -> None:
        """Open the target system and bring it to a known starting state."""

    def end_session(self) -> None:
        """Release any browser resources. Must be safe to call once."""

    def record_exists(self, key: str) -> bool:
        """Return True if a record with the given natural key already exists."""

    def submit(self, record: Record) -> str:
        """Submit a new record and return the destination's confirmation id."""
