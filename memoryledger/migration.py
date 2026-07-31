"""Deterministic, copy-first migration from legacy Memoryledger storage."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import ledgercore

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from ledgercore.config import LedgerProjectLocator
from ledgercore.manifest import (
    LedgerProjectManifest,
    LedgerRegistration,
    MountDefinition,
)

from .config import render_tool_config, tool_config_from_legacy
from .errors import MemoryledgerError
from .legacy import find_legacy_config, load_legacy_data

MIGRATION_NAME = "memoryledger-legacy-to-schema3"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _record_version(path: Path) -> tuple[str, int]:
    try:
        metadata, _body = ledgercore.read_front_matter_document(path)
    except Exception as exc:
        raise MemoryledgerError("INVALID_MEMORY_FILE", f"{path}: {exc}") from exc
    record_id = str(metadata.get("id", ""))
    if path.stem != record_id:
        raise MemoryledgerError(
            "MEMORY_ID_CONFLICT", f"{path} does not match front matter id {record_id!r}"
        )
    try:
        created = int(str(metadata.get("created_version", metadata.get("version", 0))))
        modified = int(
            str(metadata.get("modified_version", metadata.get("version", created)))
        )
    except (TypeError, ValueError) as exc:
        raise MemoryledgerError(
            "LEDGER_VERSION_INCONSISTENT", f"invalid version in {path}"
        ) from exc
    if created < 0 or modified < 0 or created > modified:
        raise MemoryledgerError(
            "LEDGER_VERSION_INCONSISTENT", f"invalid version ordering in {path}"
        )
    return record_id, modified


@dataclass(frozen=True)
class MigrationPlan:
    """Deterministic copy-first plan for a legacy-to-canonical migration."""

    migration_id: str
    root: Path
    source_config: Path
    source_data: Path
    target_manifest: Path
    target_config: Path
    target_data: Path
    target_artifacts: Path
    project_uuid: str
    project_name: str
    configured_version: int | None
    maximum_record_version: int
    target_version: int
    next_memory_number: int
    next_import_number: int
    files: tuple[dict[str, object], ...]
    warnings: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()

    @property
    def repair_required(self) -> bool:
        return (
            self.configured_version != self.target_version
            or not (self.source_data / "storage.yaml").exists()
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "migration_id": self.migration_id,
            "source": {
                "layout": "legacy",
                "config_path": str(self.source_config),
                "data_path": str(self.source_data),
                "config_sha256": _sha256(self.source_config),
                "inventory_sha256": hashlib.sha256(
                    _canonical(self.files).encode()
                ).hexdigest(),
            },
            "target": {
                "manifest_path": str(self.target_manifest),
                "config_path": str(self.target_config),
                "data_path": str(self.target_data),
                "artifacts_path": str(self.target_artifacts),
            },
            "identity": {
                "legacy_uuid": self.project_uuid,
                "canonical_uuid": None,
                "requires_adoption": False,
            },
            "version": {
                "configured": self.configured_version,
                "maximum_record": self.maximum_record_version,
                "target": self.target_version,
                "repair_required": self.configured_version != self.target_version,
            },
            "counters": {
                "next_memory_number": self.next_memory_number,
                "next_import_number": self.next_import_number,
                "repair_required": not (self.source_data / "storage.yaml").exists(),
            },
            "inventory": {
                "durable_files": len(self.files),
                "bytes": sum(int(str(item["size"])) for item in self.files),
            },
            "warnings": list(self.warnings),
            "conflicts": list(self.conflicts),
        }


def _target_manifest(
    root: Path, source_data: dict[str, Any], *, adopt_project_uuid: bool = False
) -> LedgerProjectManifest:
    manifest_path = root / ".ledger" / "ledger.toml"
    if manifest_path.is_file():
        try:
            manifest = ledgercore.read_ledger_manifest(manifest_path)
        except Exception as exc:
            raise MemoryledgerError("INVALID_LEDGER_LAYOUT", str(exc)) from exc
        project = source_data.get("project", {})
        legacy_uuid = str(project.get("uuid", "")) if isinstance(project, dict) else ""
        if (
            legacy_uuid
            and str(uuid.UUID(legacy_uuid)) != manifest.project_uuid
            and not adopt_project_uuid
        ):
            raise MemoryledgerError(
                "PROJECT_UUID_MISMATCH",
                f"legacy UUID {legacy_uuid} differs from canonical UUID {manifest.project_uuid}",
            )
        registration = manifest.ledgers.get("memoryledger")
        if registration is not None:
            mounts = {
                name: mount.storage for name, mount in registration.mounts.items()
            }
            if mounts != {"data": "project", "artifacts": "cache"}:
                raise MemoryledgerError(
                    "STORAGE_REGISTRATION_CONFLICT",
                    f"unsupported Memoryledger mounts: {mounts}",
                )
        if registration is None:
            return LedgerProjectManifest(
                manifest.schema_version,
                manifest.project_uuid,
                manifest.project_name,
                {
                    **manifest.ledgers,
                    "memoryledger": LedgerRegistration(
                        "memoryledger",
                        {
                            "data": MountDefinition("data", "project"),
                            "artifacts": MountDefinition("artifacts", "cache"),
                        },
                    ),
                },
            )
        return manifest
    project = source_data.get("project", {})
    legacy_uuid = str(project.get("uuid", "")) if isinstance(project, dict) else ""
    if not legacy_uuid:
        raise MemoryledgerError(
            "INVALID_PROJECT_UUID", "legacy project UUID is required for migration"
        )
    try:
        legacy_uuid = str(uuid.UUID(legacy_uuid))
    except ValueError as exc:
        raise MemoryledgerError(
            "INVALID_PROJECT_UUID", "legacy project UUID is invalid"
        ) from exc
    name = (
        str(project.get("name", root.name)) if isinstance(project, dict) else root.name
    )
    return LedgerProjectManifest(
        3,
        legacy_uuid,
        name or root.name,
        {
            "memoryledger": LedgerRegistration(
                "memoryledger",
                {
                    "data": MountDefinition("data", "project"),
                    "artifacts": MountDefinition("artifacts", "cache"),
                },
            )
        },
    )


def _layout_for_manifest(root: Path, manifest: LedgerProjectManifest):
    locator = LedgerProjectLocator(
        root,
        root / ".ledger",
        root / ".ledger" / "ledger.toml",
        root / ".ledger" / "ledger.local.toml",
        "canonical",
    )
    return ledgercore.resolve_ledger_layout(locator, manifest, "memoryledger")


def build_plan(
    start: Path | None = None, *, adopt_project_uuid: bool = False
) -> MigrationPlan:
    """Build and validate a migration plan without activating it."""
    root = (start or Path.cwd()).resolve()
    source_config = find_legacy_config(root)
    if source_config is None:
        raise MemoryledgerError(
            "STORAGE_MIGRATION_REQUIRED", "no legacy Memoryledger config found"
        )
    source_data_raw, source_data = load_legacy_data(source_config)
    manifest = _target_manifest(
        root, source_data_raw, adopt_project_uuid=adopt_project_uuid
    )
    registration = manifest.ledgers.get("memoryledger")
    if registration is None:
        manifest = LedgerProjectManifest(
            manifest.schema_version,
            manifest.project_uuid,
            manifest.project_name,
            {
                **manifest.ledgers,
                "memoryledger": LedgerRegistration(
                    "memoryledger",
                    {
                        "data": MountDefinition("data", "project"),
                        "artifacts": MountDefinition("artifacts", "cache"),
                    },
                ),
            },
        )
    layout = _layout_for_manifest(root, manifest)
    files: list[dict[str, object]] = []
    versions: list[int] = []
    memory_ids: list[str] = []
    import_ids: list[str] = []
    if source_data.exists():
        for path in sorted(source_data.rglob("*")):
            relative = path.relative_to(source_data).as_posix()
            if path.is_symlink() or not path.is_file():
                if path.is_symlink():
                    raise MemoryledgerError(
                        "STORAGE_MIGRATION_CONFLICT",
                        f"symlink is not allowed: {relative}",
                    )
                continue
            category = (
                "derived"
                if relative == "rendered" or relative.startswith("rendered/")
                else "unknown"
            )
            if relative.startswith("memories/memory-") and path.suffix == ".md":
                memory_id, version = _record_version(path)
                memory_ids.append(memory_id)
                versions.append(version)
                category = "memory-record"
            elif relative.startswith("imports/"):
                category = "import"
                if path.parent.name.startswith("import-"):
                    import_ids.append(path.parent.name)
            elif relative == "storage.yaml":
                category = "metadata"
            files.append(
                {
                    "relative_path": relative,
                    "category": category,
                    "size": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    if len(memory_ids) != len(set(memory_ids)):
        raise MemoryledgerError(
            "MEMORY_ID_CONFLICT", "duplicate memory IDs in legacy storage"
        )
    configured: int | None = None
    ledger = source_data_raw.get("ledger", {})
    if isinstance(ledger, dict) and "version" in ledger:
        try:
            configured = int(ledger["version"])
        except (TypeError, ValueError) as exc:
            raise MemoryledgerError(
                "LEDGER_VERSION_INCONSISTENT", "legacy ledger version is invalid"
            ) from exc
    maximum = max(versions, default=0)
    target_version = max(configured or 0, maximum)
    memory_next = ledgercore.next_prefixed_id("memory", memory_ids, width=4)
    import_next = ledgercore.next_prefixed_id("import", import_ids, width=4)
    semantic = {
        "config_sha256": _sha256(source_config),
        "inventory_sha256": hashlib.sha256(_canonical(files).encode()).hexdigest(),
        "manifest": {
            "uuid": manifest.project_uuid,
            "name": manifest.project_name,
            "ledgers": sorted(manifest.ledgers),
        },
        "version": target_version,
    }
    migration_id = (
        "memoryledger-" + hashlib.sha256(_canonical(semantic).encode()).hexdigest()[:16]
    )
    return MigrationPlan(
        migration_id,
        root,
        source_config,
        source_data,
        root / ".ledger" / "ledger.toml",
        layout.tool_config_path,
        layout.mounts["data"].path,
        layout.mounts["artifacts"].path,
        manifest.project_uuid,
        manifest.project_name or root.name,
        configured,
        maximum,
        target_version,
        int(memory_next.rsplit("-", 1)[1]),
        int(import_next.rsplit("-", 1)[1]),
        tuple(files),
    )


def write_plan(plan: MigrationPlan, path: Path | None = None) -> Path:
    """Serialize a migration plan to a deterministic TOML file."""
    target = path or plan.root / ".memoryledger-migration-plan.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(plan.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target


def _journal_path(plan: MigrationPlan) -> Path:
    return plan.root / ".ledger" / "migrations" / f"{plan.migration_id}.toml"


def _journal(plan: MigrationPlan, phase: str) -> None:
    path = _journal_path(plan)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'schema_version = 1\nmigration = "{MIGRATION_NAME}"\nmigration_id = "{plan.migration_id}"\nphase = "{phase}"\n',
        encoding="utf-8",
    )


def apply_plan(
    plan: MigrationPlan, *, adopt_project_uuid: bool = False
) -> dict[str, object]:
    """Apply a validated migration plan with copy-first activation semantics."""
    if plan.conflicts:
        raise MemoryledgerError("STORAGE_MIGRATION_CONFLICT", "; ".join(plan.conflicts))
    stage = plan.root / ".ledger" / "migrations" / plan.migration_id / "stage"
    if (
        plan.target_data.exists()
        and any(plan.target_data.iterdir())
        and not (plan.target_data / ".ledger-project.toml").exists()
    ):
        raise MemoryledgerError(
            "STORAGE_MIGRATION_CONFLICT",
            f"target data is populated and unbound: {plan.target_data}",
        )
    _journal(plan, "locked")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    stage_data = stage / "data"
    stage_data.mkdir()
    for item in plan.files:
        relative = str(item["relative_path"])
        if relative == "storage.yaml" or relative.startswith("rendered/"):
            continue
        source = plan.source_data / relative
        target = stage_data / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if _sha256(target) != str(item["sha256"]):
            raise MemoryledgerError(
                "STORAGE_MIGRATION_FAILED", f"hash mismatch after copy: {relative}"
            )
    ledgercore.write_yaml(
        stage_data / "storage.yaml",
        {
            "next_memory_number": plan.next_memory_number,
            "next_import_number": plan.next_import_number,
        },
    )
    source_config, _source_data = load_legacy_data(plan.source_config)
    tool_config = replace(
        tool_config_from_legacy(source_config), ledger_version=plan.target_version
    )
    plan.target_config.parent.mkdir(parents=True, exist_ok=True)
    plan.target_config.write_text(render_tool_config(tool_config), encoding="utf-8")
    layout = _layout_for_manifest(
        plan.root, _target_manifest(plan.root, load_legacy_data(plan.source_config)[0])
    )
    ledgercore.initialize_config_binding(layout)
    plan.target_data.parent.mkdir(parents=True, exist_ok=True)
    if plan.target_data.exists():
        shutil.rmtree(plan.target_data)
    shutil.copytree(stage_data, plan.target_data)
    ledgercore.initialize_storage_binding(layout.mounts["data"], require_empty=False)
    _journal(plan, "installed")
    manifest = _target_manifest(
        plan.root, load_legacy_data(plan.source_config)[0], adopt_project_uuid=True
    )
    plan.target_manifest.parent.mkdir(parents=True, exist_ok=True)
    ledgercore.write_ledger_manifest(
        plan.target_manifest, manifest, preserve_comments=True
    )
    _journal(plan, "complete")
    return {
        "migration_id": plan.migration_id,
        "phase": "complete",
        "manifest": str(plan.target_manifest),
        "data": str(plan.target_data),
    }


def recover_plan(plan: MigrationPlan) -> dict[str, object]:
    """Recover an incomplete migration from its journal."""
    journal = _journal_path(plan)
    if not journal.is_file():
        raise MemoryledgerError(
            "STORAGE_MIGRATION_INCOMPLETE", f"migration journal not found: {journal}"
        )
    data = tomllib.loads(journal.read_text(encoding="utf-8"))
    return {
        "migration_id": plan.migration_id,
        "phase": data.get("phase"),
        "journal": str(journal),
    }


def cleanup_legacy(
    plan: MigrationPlan, *, confirm: bool = False, discard_rendered: bool = False
) -> dict[str, object]:
    """Plan or perform confirmed cleanup after successful migration."""
    state = recover_plan(plan)
    if state.get("phase") != "complete":
        raise MemoryledgerError(
            "LEGACY_CLEANUP_UNSAFE", "cleanup requires a completed migration journal"
        )
    for item in plan.files:
        relative = str(item["relative_path"])
        source = plan.source_data / relative
        if source.is_file() and _sha256(source) != str(item["sha256"]):
            raise MemoryledgerError(
                "LEGACY_CLEANUP_UNSAFE", f"legacy source changed: {relative}"
            )
    removals = [
        plan.source_config,
        plan.source_data / "storage.yaml",
        plan.source_data / "memories",
        plan.source_data / "imports",
    ]
    if (plan.source_data / "rendered").exists() and not discard_rendered:
        raise MemoryledgerError(
            "LEGACY_CLEANUP_UNSAFE",
            "rendered legacy output requires --discard-rendered",
        )
    if discard_rendered:
        removals.append(plan.source_data / "rendered")
    if confirm:
        for path in removals:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        if plan.source_data.exists() and not any(plan.source_data.iterdir()):
            plan.source_data.rmdir()
    return {
        "phase": "complete",
        "mutated": confirm,
        "remove": [str(path) for path in removals],
    }
