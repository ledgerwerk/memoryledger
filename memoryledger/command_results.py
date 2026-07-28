"""Typed result dataclasses for major commands.

Use these instead of constructing unrelated dictionaries in command handlers.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StatusResult:
    """Result for the status command."""

    initialized: bool
    configured: bool
    layout: str = ""
    config_path: str | None = None
    storage_path: str | None = None
    memory_count: int = 0
    candidate_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    archived_count: int = 0
    next_action: dict[str, str] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "initialized": self.initialized,
            "configured": self.configured,
            "layout": self.layout,
            "config_path": self.config_path,
            "storage_path": self.storage_path,
            "memory_count": self.memory_count,
            "candidate_count": self.candidate_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "archived_count": self.archived_count,
            "next_action": self.next_action,
        }


@dataclass
class InfoResult:
    """Result for the info command."""

    project_name: str = ""
    project_uuid: str = ""
    root: str = ""
    manifest: str = ""
    local_config: str = ""
    tool_config: str = ""
    layout: str = ""
    mounts: list[dict[str, str]] = field(default_factory=list)
    legacy_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "project_name": self.project_name,
            "project_uuid": self.project_uuid,
            "root": self.root,
            "manifest": self.manifest,
            "local_config": self.local_config,
            "tool_config": self.tool_config,
            "layout": self.layout,
            "mounts": self.mounts,
            "legacy_paths": self.legacy_paths,
        }


@dataclass
class DoctorResult:
    """Result for the doctor command."""

    ok: bool = True
    issues: list[str] = field(default_factory=list)
    layout: str = ""
    check_mode: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "issues": self.issues,
            "layout": self.layout,
        }


@dataclass
class NextActionResult:
    """Result for the next-action command."""

    command: str = ""
    reason: str = ""
    context: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "reason": self.reason,
            "context": self.context,
        }


@dataclass
class MemoryMutationResult:
    """Result for memory mutations."""

    memory_id: str
    status: str = ""
    version: int = 0
    action: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "memory_id": self.memory_id,
            "status": self.status,
            "version": self.version,
            "action": self.action,
        }


@dataclass
class StorageWhereResult:
    """Result for storage where."""

    project_root: str = ""
    manifest: str | None = None
    local_config: str | None = None
    tool_config: str | None = None
    layout_schema: str = ""
    project_uuid: str = ""
    mounts: list[dict[str, object]] = field(default_factory=list)
    legacy_config: str | None = None
    legacy_data: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "project_root": self.project_root,
            "manifest": self.manifest,
            "tool_config": self.tool_config,
            "layout_schema": self.layout_schema,
            "project_uuid": self.project_uuid,
            "mounts": self.mounts,
            "legacy_config": self.legacy_config,
            "legacy_data": self.legacy_data,
        }


@dataclass
class MigrationStatusResult:
    """Result for migrate status."""

    migrations: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"migrations": self.migrations}


@dataclass
class MigrationPlanResult:
    """Result for migrate plan."""

    migration_id: str = ""
    source_paths: list[str] = field(default_factory=list)
    target_paths: list[str] = field(default_factory=list)
    plan_file: str | None = None
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "migration_id": self.migration_id,
            "source_paths": self.source_paths,
            "target_paths": self.target_paths,
            "plan_file": self.plan_file,
            "details": self.details,
        }
