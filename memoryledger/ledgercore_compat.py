"""Explicit Ledgercore 0.6.x compatibility boundary.

Re-export only the public APIs Memoryledger needs and provide a runtime
version check for source-tree / editable installs where the package
resolver may not enforce the declared range.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from ledgercore.cli import (
    CLIError,
    CLIWarning,
    CommandInventory,
    CommandMetadata,
    CommonCLIState,
    ErrorEnvelope,
    ExitCode,
    SuccessEnvelope,
    deprecated_command_warning,
    deprecated_executable_warning,
    deprecated_option_warning,
)
from ledgercore.layout import resolve_ledger_layout
from ledgercore.storage_binding import validate_ledger_layout_storage

MIN_LEDGERCORE = (0, 6, 0)
MAX_LEDGERCORE = (0, 7, 0)


def _parse_version_tuple(ver_str: str) -> tuple[int, ...]:
    """Parse a version string like '0.6.1' into a tuple of ints."""
    parts: list[int] = []
    for segment in ver_str.split("."):
        # Strip dev/pre/post suffixes
        num = ""
        for ch in segment:
            if ch.isdigit():
                num += ch
            else:
                break
        if num:
            parts.append(int(num))
    return tuple(parts)


class LedgercoreVersionUnsupported(Exception):
    """Raised when the installed Ledgercore version is outside the supported range."""

    def __init__(
        self, installed: str, minimum: tuple[int, ...], maximum: tuple[int, ...]
    ) -> None:
        self.installed = installed
        self.minimum = minimum
        self.maximum = maximum
        min_str = ".".join(str(x) for x in minimum)
        max_str = ".".join(str(x) for x in maximum)
        super().__init__(
            f"Ledgercore {installed} is not supported. "
            f"Memoryledger requires >={min_str},<{max_str}."
        )


LEDGERCORE_VERSION_UNSUPPORTED = LedgercoreVersionUnsupported


def require_supported_ledgercore() -> None:
    """Check that the installed Ledgercore version is in the supported range.

    The package resolver already enforces this in normal installations;
    this check catches editable/source-tree mistakes.
    """
    try:
        installed_str = version("ledgercore")
    except PackageNotFoundError:
        raise LedgercoreVersionUnsupported(
            "not installed", MIN_LEDGERCORE, MAX_LEDGERCORE
        ) from None
    installed = _parse_version_tuple(installed_str)
    if installed < MIN_LEDGERCORE or installed >= MAX_LEDGERCORE:
        raise LedgercoreVersionUnsupported(
            installed_str, MIN_LEDGERCORE, MAX_LEDGERCORE
        )


__all__ = [
    # CLI contracts
    "CLIError",
    "CLIWarning",
    "CommandInventory",
    "CommandMetadata",
    "CommonCLIState",
    "ErrorEnvelope",
    "ExitCode",
    "SuccessEnvelope",
    "deprecated_command_warning",
    "deprecated_executable_warning",
    "deprecated_option_warning",
    # Manifest/layout
    "resolve_ledger_layout",
    "validate_ledger_layout_storage",
    # Version checking
    "require_supported_ledgercore",
    "LedgercoreVersionUnsupported",
    "LEDGERCORE_VERSION_UNSUPPORTED",
]
