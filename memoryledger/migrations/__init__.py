"""Memoryledger migration handlers registry.

Provides a common protocol for migration handlers and a registry
that maps migration names to their implementations.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class MigrationHandler(Protocol):
    """Protocol for Memoryledger migration handlers."""

    name: str
    summary: str

    def status(self, root: Path) -> Mapping[str, object]:
        """Return migration status for this handler."""
        ...

    def plan(self, root: Path, *, output: Path | None = None) -> Mapping[str, object]:
        """Generate a read-only migration plan."""
        ...

    def apply(
        self,
        root: Path,
        *,
        plan_file: Path | None = None,
        dry_run: bool = False,
    ) -> Mapping[str, object]:
        """Apply a migration plan."""
        ...

    def recover(
        self,
        root: Path,
        *,
        journal: Path,
        policy: str = "auto",
    ) -> Mapping[str, object]:
        """Recover from a migration journal."""
        ...

    def cleanup(
        self,
        root: Path,
        *,
        dry_run: bool = False,
        confirm: bool = False,
    ) -> Mapping[str, object]:
        """Clean up legacy paths after successful migration."""
        ...


class MigrationRegistry:
    """Registry of migration handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, MigrationHandler] = {}

    def register(self, handler: MigrationHandler) -> None:
        """Register a migration handler."""
        if handler.name in self._handlers:
            raise ValueError(f"Duplicate migration handler: {handler.name}")
        self._handlers[handler.name] = handler

    def get(self, name: str) -> MigrationHandler:
        """Get a migration handler by name."""
        if name not in self._handlers:
            valid = ", ".join(sorted(self._handlers.keys()))
            raise ValueError(f"Unknown migration '{name}'. Valid: {valid}")
        return self._handlers[name]

    def list(self) -> list[Mapping[str, object]]:
        """List all registered migrations."""
        return [
            {"name": h.name, "summary": h.summary}
            for h in self._handlers.values()
        ]

    def status(self, root: Path) -> list[Mapping[str, object]]:
        """Get status for all migrations."""
        results = []
        for handler in self._handlers.values():
            try:
                status = handler.status(root)
                results.append(status)
            except Exception as e:
                results.append({
                    "name": handler.name,
                    "available": False,
                    "error": str(e),
                })
        return results


# Global registry instance
REGISTRY = MigrationRegistry()
