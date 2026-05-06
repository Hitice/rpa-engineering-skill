"""Domain-level exceptions used across core, contracts and adapters."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for any error that crosses a layer boundary."""


class ConfigurationError(DomainError):
    """Invalid or missing configuration."""


class AuthenticationError(DomainError):
    """Login or session credentials rejected."""


class AuthorizationError(DomainError):
    """Authenticated but not allowed to perform the action."""


class ElementTimeoutError(DomainError):
    """Waiting for a UI condition exceeded the configured budget."""


class IntegrationError(DomainError):
    """External system failure: network, 5xx, malformed response."""


class BusinessRuleViolation(DomainError):
    """A domain invariant was violated."""


class IdempotencyConflict(DomainError):
    """Conflicting state detected and reconciliation is unsafe."""
