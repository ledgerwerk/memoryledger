"""Linked docs directory migration handler.

Migrates linked agent documents directory configuration.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

LINKED_DOCS_DIR = "linked-docs-dir"


class LinkedDocsDirMigration:
    """Migration handler for linked docs directory changes."""

    name = LINKED_DOCS_DIR
    summary = "Migrate linked agent documents directory configuration."

    def status(self, root: Path) -> Mapping[str, object]:
        """Check linked docs directory status."""
        return {
            "name": self.name,
            "available": True,
            "applied": True,  # No pending migration by default
        }

    def plan(self, root: Path, *, output: Path | None = None) -> Mapping[str, object]:
        """Generate a read-only linked docs dir plan."""
        from ..errors import MemoryledgerError

        raise MemoryledgerError(
            "FEATURE_UNAVAILABLE",
            "linked-docs-dir plan is not yet implemented.",
        )

    def apply(
        self,
        root: Path,
        *,
        plan_file: Path | None = None,
        dry_run: bool = False,
    ) -> Mapping[str, object]:
        """Apply linked docs dir migration."""
        from ..errors import MemoryledgerError

        raise MemoryledgerError(
            "FEATURE_UNAVAILABLE",
            "linked-docs-dir apply is not yet implemented.",
        )

    def recover(
        self,
        root: Path,
        *,
        journal: Path,
        policy: str = "auto",
    ) -> Mapping[str, object]:
        """Recover from a linked docs dir migration."""
        from ..errors import MemoryledgerError

        raise MemoryledgerError(
            "FEATURE_UNAVAILABLE",
            "linked-docs-dir recovery is not yet implemented.",
        )

    def cleanup(
        self,
        root: Path,
        *,
        dry_run: bool = False,
        confirm: bool = False,
    ) -> Mapping[str, object]:
        """Clean up after linked docs dir migration."""
        return {"name": self.name, "cleanup": "no-op", "dry_run": dry_run}


# Singleton instance
linked_docs_dir_migration = LinkedDocsDirMigration()
