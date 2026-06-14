"""Domain errors for memoryledger.

These live in ``memoryledger.errors`` so the CLI boundary can catch
``memoryledger.errors.MemoryLedgerError`` (and optionally
``ledgercore.errors.LedgerCoreError``) and convert them into clean Typer
errors. Domain code raises these instead of returning error sentinels.
"""

from __future__ import annotations


class MemoryLedgerError(Exception):
    """Base class for all memoryledger domain errors."""

    def __init__(
        self, message: str, *, context: dict[str, object] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, object] = dict(context) if context else {}


class ConfigError(MemoryLedgerError):
    """Raised when the project config is missing, unreadable, or invalid."""


class NotFoundError(MemoryLedgerError):
    """Raised when a memory, file, or resource cannot be located."""


class ValidationError(MemoryLedgerError):
    """Raised when input or stored data fails memoryledger validation."""


class AlreadyExistsError(MemoryLedgerError):
    """Raised when an operation would overwrite an existing artifact."""


class StateError(MemoryLedgerError):
    """Raised when ledger state is inconsistent with an attempted operation."""


__all__ = [
    "AlreadyExistsError",
    "ConfigError",
    "MemoryLedgerError",
    "NotFoundError",
    "StateError",
    "ValidationError",
]
