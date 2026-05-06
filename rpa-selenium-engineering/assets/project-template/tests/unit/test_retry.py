"""Tests for the transient retry policy."""

from __future__ import annotations

import pytest

from rpa_template.adapters.retry import transient_retrier
from rpa_template.exceptions import (
    AuthenticationError,
    ElementTimeoutError,
    IntegrationError,
)


def test_retries_only_typed_transients_and_eventually_succeeds() -> None:
    calls: list[int] = []

    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise ElementTimeoutError("timeout")
        return "ok"

    retrier = transient_retrier(attempts=5, initial_delay_s=0.001, max_delay_s=0.002)
    assert retrier(flaky) == "ok"
    assert len(calls) == 3


def test_does_not_retry_on_non_transient() -> None:
    calls: list[int] = []

    def fail() -> None:
        calls.append(1)
        raise AuthenticationError("nope")

    retrier = transient_retrier(attempts=5, initial_delay_s=0.001, max_delay_s=0.002)
    with pytest.raises(AuthenticationError):
        retrier(fail)
    assert len(calls) == 1


def test_exhausts_budget_and_reraises() -> None:
    calls: list[int] = []

    def always_fail() -> None:
        calls.append(1)
        raise IntegrationError("upstream 500")

    retrier = transient_retrier(attempts=3, initial_delay_s=0.001, max_delay_s=0.002)
    with pytest.raises(IntegrationError):
        retrier(always_fail)
    assert len(calls) == 3


def test_on_retry_hook_receives_attempt_error_and_delay() -> None:
    seen: list[tuple[int, str, str, float]] = []

    def hook(attempt: int, etype: str, emsg: str, delay: float) -> None:
        seen.append((attempt, etype, emsg, delay))

    calls: list[int] = []

    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise IntegrationError(f"boom {len(calls)}")
        return "ok"

    retrier = transient_retrier(
        attempts=5,
        initial_delay_s=0.001,
        max_delay_s=0.002,
        on_retry=hook,
    )
    assert retrier(flaky) == "ok"
    assert len(seen) == 2
    assert [s[0] for s in seen] == [1, 2]
    assert all(s[1] == "IntegrationError" for s in seen)
    assert all(s[3] >= 0.0 for s in seen)
