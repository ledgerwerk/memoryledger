"""Storage-v2 migration handler.

Converts sidecar-based memory records to single frontmatter Markdown files.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


STORAGE_V2 = "storage-v2"


class StorageV2Migration:
    """Migration handler for storage-v2 tree replacement."""

    name = STORAGE_V2
    summary = "Convert sidecar memory records to single frontmatter Markdown files."

    def status(self, root: Path) -> Mapping[str, object]:
        """Check if storage-v2 migration is needed."""
        # Check if there are any sidecar-based records
        storage_dir = root / ".memoryledger" / "memories"
        if not storage_dir.exists():
            storage_dir = root / ".ledger" / "memoryledger" / "data" / "memories"

        has_sidecars = False
        if storage_dir.exists():
            for mem_dir in storage_dir.iterdir():
                if mem_dir.is_dir() and (mem_dir / "memory.yaml").exists():
                    has_sidecars = True
                    break

        return {
            "name": self.name,
            "available": True,
            "applied": not has_sidecars,
            "has_sidecars": has_sidecars,
        }

    def plan(self, root: Path, *, output: Path | None = None) -> Mapping[str, object]:
        """Generate a read-only storage-v2 plan."""
        from ..storage import Store
        from ..project import resolve_workspace, workspace_as_compat_config

        workspace = resolve_workspace(root)
        config = workspace_as_compat_config(workspace)
        store = Store(config)
        return store.storage_v2_plan()

    def apply(
        self,
        root: Path,
        *,
        plan_file: Path | None = None,
        dry_run: bool = False,
    ) -> Mapping[str, object]:
        """Apply storage-v2 migration."""
        from ..storage import Store
        from ..project import resolve_workspace, workspace_as_compat_config

        workspace = resolve_workspace(root)
        config = workspace_as_compat_config(workspace)
        store = Store(config)
        return store.migrate_storage_v2(backup=True)

    def recover(
        self,
        root: Path,
        *,
        journal: Path,
        policy: str = "auto",
    ) -> Mapping[str, object]:
        """Recover from a storage-v2 migration."""
        from ..errors import MemoryledgerError
        raise MemoryledgerError(
            "FEATURE_UNAVAILABLE",
            "storage-v2 recovery is not yet implemented.",
        )

    def cleanup(
        self,
        root: Path,
        *,
        dry_run: bool = False,
        confirm: bool = False,
    ) -> Mapping[str, object]:
        """Clean up after storage-v2 migration."""
        return {"name": self.name, "cleanup": "no-op", "dry_run": dry_run}


# Singleton instance
storage_v2_migration = StorageV2Migration()
