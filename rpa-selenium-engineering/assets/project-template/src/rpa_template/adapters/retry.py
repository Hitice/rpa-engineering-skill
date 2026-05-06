"""Tenacity-based retry policy for transient errors at the adapter layer.

This is the *intra-call* retry budget. Cross-run resilience is handled by the
:class:`StateStore`, which records attempt counts and promotes exhausted items
to the dead-letter status.
"""

from __future__ import annotations

from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from rpa_template.exceptions import ElementTimeoutError, IntegrationError

_TRANSIENT: tuple[type[Exception], ...] = (IntegrationError, ElementTimeoutError)


def transient_retrier(
    *,
    attempts: int,
    initial_delay_s: float,
    max_delay_s: float,
) -> Retrying:
    """Build a reusable :class:`Retrying` policy.

    Retries only on ``IntegrationError`` and ``ElementTimeoutError``; every
    other exception (auth, business rule, configuration) propagates immediately.
    """
    return Retrying(
        retry=retry_if_exception_type(_TRANSIENT),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=initial_delay_s, max=max_delay_s),
        reraise=True,
    )
