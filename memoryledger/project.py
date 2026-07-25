"""Canonical schema-3 project discovery and read-only workspace resolution."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import ledgercore

from .config import load_tool_config
from .errors import MemoryledgerError
from .legacy import find_legacy_config, load_legacy_data, load_legacy_workspace
from .models import Config, StorageDiscovery, Workspace, WorkspacePaths

TOOL_NAME = "memoryledger"
EXPECTED_MOUNTS = {"data": "project", "artifacts": "cache"}


def _populated(path: Path | None) -> bool:
    return bool(path and path.exists() and any(path.iterdir()))


def _load_canonical(start: Path) -> Any:
    try:
        return ledgercore.load_ledger_project(
            start, legacy_tool_filenames=("memoryledger.toml", ".memoryledger.toml")
        )
    except Exception as exc:
        raise MemoryledgerError("INVALID_LEDGER_LAYOUT", str(exc)) from exc


def resolve_canonical_workspace(start: Path, loaded: Any | None = None) -> Workspace:
    loaded_project = loaded or _load_canonical(start)
    manifest = loaded_project.manifest  # type: ignore[attr-defined]
    registration = manifest.ledgers.get(TOOL_NAME)
    if registration is None:
        raise MemoryledgerError(
            "MIGRATION_REQUIRED",
            "Memoryledger is not registered in the shared manifest",
        )
    actual = {name: mount.storage for name, mount in registration.mounts.items()}
    if actual != EXPECTED_MOUNTS:
        raise MemoryledgerError(
            "INVALID_LEDGER_LAYOUT",
            f"Memoryledger mounts must be {EXPECTED_MOUNTS}, got {actual}",
        )
    try:
        layout = ledgercore.resolve_ledger_layout(
            loaded_project.locator,
            manifest,
            TOOL_NAME,
            local_overrides=loaded_project.local_overrides,
        )  # type: ignore[attr-defined]
        report = ledgercore.validate_ledger_layout_storage(layout)
    except Exception as exc:
        raise MemoryledgerError("INVALID_LEDGER_LAYOUT", str(exc)) from exc
    if not report.valid:
        reasons = [result.reason for result in report.results if not result.valid]
        raise MemoryledgerError(
            "INVALID_STORAGE_BINDING", "; ".join(str(item) for item in reasons)
        )
    if layout.tool_config_path is None:
        raise MemoryledgerError(
            "INVALID_LEDGER_LAYOUT", "canonical tool config path is missing"
        )
    config = load_tool_config(layout.tool_config_path)
    data_mount = layout.mounts["data"]
    artifact_mount = layout.mounts["artifacts"]
    return Workspace(
        config,
        WorkspacePaths(
            layout.project_root,
            layout.manifest_path,
            layout.local_config_path,
            layout.tool_config_path,
            data_mount.path,
            artifact_mount.path,
            layout.config_binding_path,
            data_mount.binding_path,
            artifact_mount.binding_path,
            "canonical",
        ),
        manifest.project_name or layout.project_root.name,
        manifest.project_uuid,
    )


def resolve_workspace(
    start: Path | None = None, *, allow_legacy: bool = True
) -> Workspace:
    root = (start or Path.cwd()).resolve()
    locator = ledgercore.locate_ledger_project(
        root, legacy_tool_filenames=("memoryledger.toml", ".memoryledger.toml")
    )
    if locator is not None and not locator.is_legacy:
        return resolve_canonical_workspace(locator.project_root)
    legacy = find_legacy_config(root)
    if legacy is not None and allow_legacy:
        return load_legacy_workspace(legacy)
    raise MemoryledgerError("NO_CONFIG", "Run `memoryledger init` first.")


def workspace_as_compat_config(workspace: Workspace) -> Config:
    """Expose the old Config shape to unchanged domain code during migration."""

    try:
        relative_data = workspace.paths.data_dir.relative_to(
            workspace.paths.project_root
        )
        memoryledger_dir = relative_data.as_posix()
    except ValueError:
        memoryledger_dir = str(workspace.paths.data_dir)
    return Config(
        root=workspace.paths.project_root,
        config_path=workspace.paths.config_path,
        ledger_code=workspace.config.ledger_code,
        ledger_name=TOOL_NAME,
        project_name=workspace.project_name,
        project_uuid=workspace.project_uuid,
        memoryledger_dir=memoryledger_dir,
        render=workspace.config.render,
        allow_run_html=workspace.config.allow_run_html,
        allow_current_run=workspace.config.allow_current_run,
        default_review_status=workspace.config.default_review_status,
        template_policy=workspace.config.template_policy,
        artifacts_dir=workspace.paths.artifacts_dir,
    )


def init_canonical_workspace(project_name: str | None = None) -> Workspace:
    """Initialize a fresh schema-3 project with activation written last."""

    root = Path.cwd().resolve()
    manifest_path = root / ".ledger" / "ledger.toml"
    if manifest_path.exists():
        loaded = _load_canonical(root)
        return resolve_canonical_workspace(root, loaded)
    project_uuid = str(uuid.uuid4())
    name = project_name or root.name
    from ledgercore.config import LedgerProjectLocator
    from ledgercore.manifest import (
        LedgerProjectManifest,
        LedgerRegistration,
        MountDefinition,
    )

    manifest = LedgerProjectManifest(
        schema_version=3,
        project_uuid=project_uuid,
        project_name=name,
        ledgers={
            TOOL_NAME: LedgerRegistration(
                name=TOOL_NAME,
                mounts={
                    "data": MountDefinition("data", "project"),
                    "artifacts": MountDefinition("artifacts", "cache"),
                },
            )
        },
    )
    locator = LedgerProjectLocator(
        root,
        root / ".ledger",
        manifest_path,
        root / ".ledger" / "ledger.local.toml",
        "canonical",
    )
    layout = ledgercore.resolve_ledger_layout(locator, manifest, TOOL_NAME)
    if layout.tool_config_path is None:
        raise MemoryledgerError(
            "INVALID_LEDGER_LAYOUT", "canonical tool config path is missing"
        )
    from .config import write_tool_config
    from .models import RenderConfig, TemplatePolicy, ToolConfig

    tool_config = ToolConfig(
        2, "ml", 0, RenderConfig(), True, True, "candidate", TemplatePolicy()
    )
    layout.tool_config_path.parent.mkdir(parents=True, exist_ok=True)
    write_tool_config(layout.tool_config_path, tool_config)
    ledgercore.initialize_config_binding(layout)
    data_mount = layout.mounts["data"]
    ledgercore.initialize_storage_binding(data_mount, require_empty=True)
    (data_mount.path / "memories").mkdir(exist_ok=True)
    (data_mount.path / "imports").mkdir(exist_ok=True)
    ledgercore.write_yaml(
        data_mount.path / "storage.yaml",
        {"next_memory_number": 1, "next_import_number": 1},
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    ledgercore.write_ledger_manifest(manifest_path, manifest, preserve_comments=False)
    return resolve_canonical_workspace(root, _load_canonical(root))


def ensure_artifacts(workspace: Workspace) -> Path:
    """Initialize the derived artifacts mount only when a render is written."""

    if workspace.paths.artifacts_dir is None:
        raise MemoryledgerError(
            "INVALID_LEDGER_LAYOUT", "artifacts mount is unavailable"
        )
    if workspace.paths.layout_source == "canonical":
        loaded = _load_canonical(workspace.paths.project_root)
        layout = ledgercore.resolve_ledger_layout(
            loaded.locator,
            loaded.manifest,
            TOOL_NAME,
            local_overrides=loaded.local_overrides,
        )
        ledgercore.initialize_storage_binding(
            layout.mounts["artifacts"], require_empty=False
        )
    else:
        workspace.paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return workspace.paths.artifacts_dir


def discover_storage(start: Path | None = None) -> StorageDiscovery:
    root = (start or Path.cwd()).resolve()
    locator = ledgercore.locate_ledger_project(
        root, legacy_tool_filenames=("memoryledger.toml", ".memoryledger.toml")
    )
    manifest = (
        locator.manifest_path
        if locator is not None and not locator.is_legacy
        else root / ".ledger" / "ledger.toml"
    )
    legacy_config = find_legacy_config(root)
    if not manifest.exists() and legacy_config is None:
        return StorageDiscovery(
            root,
            None,
            False,
            None,
            None,
            False,
            True,
            None,
            None,
            False,
            None,
            "uninitialized",
        )
    if manifest.exists():
        try:
            workspace = resolve_canonical_workspace(root)
            legacy_data = load_legacy_data(legacy_config)[1] if legacy_config else None
            return StorageDiscovery(
                root,
                manifest,
                True,
                workspace.paths.config_path,
                workspace.paths.data_dir,
                _populated(workspace.paths.data_dir),
                True,
                legacy_config,
                legacy_data,
                _populated(legacy_data),
                None,
                "canonical",
            )
        except MemoryledgerError:
            return StorageDiscovery(
                root,
                manifest,
                False,
                None,
                None,
                False,
                False,
                legacy_config,
                None,
                False,
                None,
                "conflict",
            )
    legacy_data = load_legacy_data(legacy_config)[1] if legacy_config else None
    return StorageDiscovery(
        root,
        None,
        False,
        None,
        None,
        False,
        True,
        legacy_config,
        legacy_data,
        _populated(legacy_data),
        None,
        "legacy",
    )
