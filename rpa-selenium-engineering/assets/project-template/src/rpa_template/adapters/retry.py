"""Tenacity-based retry policy for transient errors at the adapter layer.

This is the *intra-call* retry budget. Cross-run resilience is handled by the
:class:`StateStore`, which records attempt counts and promotes exhausted items
to the dead-letter status.

The policy retries only typed transient errors, applies exponential backoff
with full jitter (so concurrent jobs do not synchronize on the same delay) and
fires a ``before_sleep`` hook on every retry. The hook receives the attempt
number, the exception type and the delay applied, which is exactly what
``architecture.md`` requires for retry telemetry.
"""

from __future__ import annotations

from collections.abc import Callable

from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from rpa_template.exceptions import ElementTimeoutError, IntegrationError

_TRANSIENT: tuple[type[Exception], ...] = (IntegrationError, ElementTimeoutError)

RetryHook = Callable[[int, str, str, float], None]
"""``(attempt_number, error_type, error_message, delay_s)`` — invoked before every retry sleep."""


def _build_before_sleep(hook: RetryHook | None) -> Callable[[RetryCallState], None] | None:
    if hook is None:
        return None

    def _before_sleep(state: RetryCallState) -> None:
        outcome = state.outcome
        next_action = state.next_action
        if outcome is None or next_action is None:
            return
        exc = outcome.exception()
        hook(
            state.attempt_number,
            type(exc).__name__ if exc is not None else "UnknownError",
            str(exc) if exc is not None else "",
            float(next_action.sleep),
        )

    return _before_sleep


def transient_retrier(
    *,
    attempts: int,
    initial_delay_s: float,
    max_delay_s: float,
    on_retry: RetryHook | None = None,
) -> Retrying:
    """Build a reusable :class:`Retrying` policy.

    Retries only on ``IntegrationError`` and ``ElementTimeoutError``; every
    other exception (auth, business rule, configuration) propagates immediately.
    The first wait is bounded below by ``initial_delay_s`` and above by
    ``max_delay_s``, with random jitter added on top to break herd effects.
    """
    return Retrying(
        retry=retry_if_exception_type(_TRANSIENT),
        stop=stop_after_attempt(attempts),
        wait=(
            wait_exponential(multiplier=1, min=initial_delay_s, max=max_delay_s)
            + wait_random(0, initial_delay_s)
        ),
        before_sleep=_build_before_sleep(on_retry),
        reraise=True,
    )
