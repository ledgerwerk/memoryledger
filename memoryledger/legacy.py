"""Legacy Memoryledger discovery isolated from canonical project resolution."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from ledgercore.ids import next_prefixed_id, parse_prefixed_number

from .config import tool_config_from_legacy
from .errors import MemoryledgerError
from .models import DerivedState, LegacyInventory, Workspace, WorkspacePaths

LEGACY_CONFIG_NAMES = ("memoryledger.toml", ".memoryledger.toml")


def find_legacy_config(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        for name in LEGACY_CONFIG_NAMES:
            path = directory / name
            if path.is_file():
                return path
    return None


def load_legacy_data(config_path: Path) -> tuple[dict[str, Any], Path]:
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MemoryledgerError(
            "INVALID_CONFIG", f"Unable to read {config_path}: {exc}"
        ) from exc
    storage = data.get("storage", {})
    if not isinstance(storage, dict):
        raise MemoryledgerError("INVALID_CONFIG", "[storage] must be a table")
    relative = str(storage.get("memoryledger_dir", ".memoryledger"))
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise MemoryledgerError(
            "INVALID_STORAGE_PATH", "legacy storage path escapes the project"
        )
    return data, config_path.parent / path


def load_legacy_workspace(config_path: Path) -> Workspace:
    data, data_dir = load_legacy_data(config_path)
    project = data.get("project", {})
    if not isinstance(project, dict):
        raise MemoryledgerError("INVALID_CONFIG", "[project] must be a table")
    project_uuid = str(project.get("uuid", ""))
    if project_uuid:
        try:
            project_uuid = str(uuid.UUID(project_uuid))
        except ValueError as exc:
            raise MemoryledgerError(
                "INVALID_PROJECT_UUID", "legacy project UUID is invalid"
            ) from exc
    project_name = (
        str(project.get("name", config_path.parent.name)) or config_path.parent.name
    )
    return Workspace(
        config=tool_config_from_legacy(data),
        paths=WorkspacePaths(
            config_path.parent,
            None,
            None,
            config_path,
            data_dir,
            data_dir / "rendered",
            None,
            None,
            None,
            "legacy",
        ),
        project_name=project_name,
        project_uuid=project_uuid,
    )


def derive_legacy_state(
    memory_ids: list[str], import_ids: list[str], configured_version: int
) -> DerivedState:
    memory_next = next_prefixed_id("memory", memory_ids, width=4)
    import_next = next_prefixed_id("import", import_ids, width=4)
    return DerivedState(
        max(0, configured_version),
        parse_prefixed_number(memory_next, prefix="memory", width=4),
        parse_prefixed_number(import_next, prefix="import", width=4),
    )


def inventory_legacy_storage(workspace: Workspace) -> LegacyInventory:
    data_dir = workspace.paths.data_dir
    memory_ids = tuple(
        sorted(path.stem for path in (data_dir / "memories").glob("memory-*.md"))
    )
    import_ids = tuple(
        sorted(path.name for path in (data_dir / "imports").glob("import-*"))
    )
    files = (
        tuple(sorted(path for path in data_dir.rglob("*") if path.is_file()))
        if data_dir.exists()
        else ()
    )
    return LegacyInventory(
        workspace.paths.config_path,
        data_dir,
        memory_ids,
        import_ids,
        files,
        derive_legacy_state(
            list(memory_ids), list(import_ids), workspace.config.ledger_version
        ),
    )
