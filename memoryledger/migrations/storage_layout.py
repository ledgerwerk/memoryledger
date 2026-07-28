"""Storage-layout migration handler.

Converts legacy Memoryledger storage to canonical Ledgercore schema-3 layout.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


STORAGE_LAYOUT = "storage-layout"


class StorageLayoutMigration:
    """Migration handler for storage-layout conversion."""

    name = STORAGE_LAYOUT
    summary = "Convert legacy memoryledger storage to canonical .ledger/ layout."

    def status(self, root: Path) -> Mapping[str, object]:
        """Check if storage-layout migration is needed."""
        legacy_config = root / "memoryledger.toml"
        legacy_dot_config = root / ".memoryledger.toml"
        legacy_data = root / ".memoryledger"
        canonical_manifest = root / ".ledger" / "ledger.toml"

        has_legacy = legacy_config.exists() or legacy_dot_config.exists() or legacy_data.exists()
        has_canonical = canonical_manifest.exists()

        if has_canonical and not has_legacy:
            applied = True
        elif has_legacy:
            applied = False
        else:
            applied = False

        return {
            "name": self.name,
            "available": True,
            "applied": applied,
            "has_legacy": has_legacy,
            "has_canonical": has_canonical,
        }

    def plan(self, root: Path, *, output: Path | None = None) -> Mapping[str, object]:
        """Generate a read-only migration plan."""
        from ..migration import build_plan, write_plan

        plan_obj = build_plan()
        plan_file = write_plan(plan_obj, output) if output else None
        return {
            "migration_id": plan_obj.migration_id,
            "plan_file": str(plan_file) if plan_file else None,
            "details": plan_obj.to_dict(),
        }

    def apply(
        self,
        root: Path,
        *,
        plan_file: Path | None = None,
        dry_run: bool = False,
    ) -> Mapping[str, object]:
        """Apply storage-layout migration."""
        # For now, return feature_unavailable until WP5
        from ..errors import MemoryledgerError
        raise MemoryledgerError(
            "FEATURE_UNAVAILABLE",
            "storage-layout apply is not yet fully implemented with schema-3 support.",
        )

    def recover(
        self,
        root: Path,
        *,
        journal: Path,
        policy: str = "auto",
    ) -> Mapping[str, object]:
        """Recover from a storage-layout migration journal."""
        from ..migration import build_plan, recover_plan

        plan_obj = build_plan()
        return recover_plan(plan_obj)

    def cleanup(
        self,
        root: Path,
        *,
        dry_run: bool = False,
        confirm: bool = False,
    ) -> Mapping[str, object]:
        """Clean up legacy paths after successful migration."""
        from ..migration import build_plan, cleanup_legacy

        plan_obj = build_plan()
        return cleanup_legacy(plan_obj, confirm=confirm and not dry_run)


# Singleton instance
storage_layout_migration = StorageLayoutMigration()
