"""Migration registry setup.

Register all migration handlers with the global registry.
"""

from __future__ import annotations

from . import REGISTRY
from .linked_docs_dir import linked_docs_dir_migration
from .storage_layout import storage_layout_migration
from .storage_v2 import storage_v2_migration


def register_all_migrations() -> None:
    """Register all migration handlers."""
    REGISTRY.register(storage_layout_migration)
    REGISTRY.register(storage_v2_migration)
    REGISTRY.register(linked_docs_dir_migration)


# Auto-register on import
register_all_migrations()
