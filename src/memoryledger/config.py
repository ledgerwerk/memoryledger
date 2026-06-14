"""Project discovery and config loading for memoryledger.

Discovery contract: ``memoryledger`` discovers ONLY ``.memoryledger.toml`` by
walking upward from the current working directory. It must not reuse another
ledger's config (``.taskledger.toml``, ``.archledger.toml``, etc.).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from memoryledger.errors import ConfigError
from memoryledger.model import VALID_SCOPES

CONFIG_FILENAME = ".memoryledger.toml"
CONFIG_FILENAMES: tuple[str, ...] = (CONFIG_FILENAME,)


class ExportTarget(str, Enum):
    """Supported export targets for the MVP."""

    agents_md = "agents-md"


# ---------------------------------------------------------------------------
# Config sub-models (mirror the default .memoryledger.toml in the brief)
# ---------------------------------------------------------------------------


class LedgerSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = "memoryledger"
    version: int = 1
    state_dir: str = ".memoryledger"


class ProjectSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = "ledger-family"
    display_name: str = "Ledger family"


class ScopesSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project: bool = True
    local: bool = True
    role: bool = True
    organization: bool = False


class RetrievalSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    default_limit: int = 12
    max_context_lines: int = 200
    include_local_by_default: bool = False


class ExportsSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    default_target: ExportTarget = ExportTarget.agents_md
    default_path: str = ".memoryledger/exports/AGENTS.memory.md"


class PolicySection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    require_approval_for_rules: bool = True
    require_approval_for_project_memory: bool = True
    allow_auto_capture_to_inbox: bool = True


class MemoryLedgerConfig(BaseModel):
    """Typed view of a parsed ``.memoryledger.toml``."""

    model_config = ConfigDict(extra="ignore")

    ledger: LedgerSection = Field(default_factory=LedgerSection)
    project: ProjectSection = Field(default_factory=ProjectSection)
    scopes: ScopesSection = Field(default_factory=ScopesSection)
    retrieval: RetrievalSection = Field(default_factory=RetrievalSection)
    exports: ExportsSection = Field(default_factory=ExportsSection)
    policy: PolicySection = Field(default_factory=PolicySection)
    config_path: Path | None = None

    @property
    def state_dir_path(self) -> Path:
        """Absolute path to the ``.memoryledger/`` state directory."""
        if self.config_path is None:
            return Path(self.ledger.state_dir)
        from ledgercore.paths import resolve_config_relative_path

        return resolve_config_relative_path(
            self.config_path, self.ledger.state_dir, field_name="state_dir"
        )

    @property
    def workspace_root(self) -> Path:
        """Directory containing the config file (project root)."""
        if self.config_path is None:
            return Path.cwd()
        return self.config_path.parent


class MemoryLedgerProject(BaseModel):
    """A discovered project: root + parsed config + absolute paths."""

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    workspace_root: Path
    config_path: Path
    config: MemoryLedgerConfig
    state_dir: Path
    export_path: Path

    @property
    def ledger_path(self) -> Path:
        return self.state_dir / "ledger.jsonl"

    @property
    def state_file(self) -> Path:
        return self.state_dir / "state.json"

    @property
    def memories_dir(self) -> Path:
        return self.state_dir / "memories"


# ---------------------------------------------------------------------------
# Default config text (must match the brief byte-for-byte in structure)
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_TEXT = """\
[ledger]
name = "memoryledger"
version = 1
state_dir = ".memoryledger"

[project]
id = "ledger-family"
display_name = "Ledger family"

[scopes]
project = true
local = true
role = true

[retrieval]
default_limit = 12
max_context_lines = 200
include_local_by_default = false

[exports]
default_target = "agents-md"
default_path = ".memoryledger/exports/AGENTS.memory.md"

[policy]
require_approval_for_rules = true
require_approval_for_project_memory = true
allow_auto_capture_to_inbox = true
"""


def default_config_text() -> str:
    """Return the canonical default ``.memoryledger.toml`` text."""
    return DEFAULT_CONFIG_TEXT


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _load_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file using stdlib tomllib (3.11+) or tomli fallback."""
    try:
        import tomllib  # type: ignore[import-not-found]

        with path.open("rb") as fh:
            result = tomllib.load(fh)
    except ModuleNotFoundError:  # pragma: no cover - exercised on 3.10 only
        import tomli as tomli  # type: ignore[import-not-found]

        with path.open("rb") as fh:
            result = tomli.load(fh)
    return dict(result)


def load_config(config_path: Path) -> MemoryLedgerConfig:
    """Load and validate a ``.memoryledger.toml`` file.

    Raises :class:`ConfigError` on read/parse/validation failure.
    """
    try:
        raw = _load_toml(config_path)
    except FileNotFoundError as exc:
        raise ConfigError(
            f"Config file not found: {config_path}", context={"path": str(config_path)}
        ) from exc
    except Exception as exc:  # malformed TOML, OSError, etc.
        raise ConfigError(
            f"Failed to parse config {config_path}: {exc}",
            context={"path": str(config_path)},
        ) from exc

    try:
        cfg = MemoryLedgerConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigError(
            f"Invalid config {config_path}: {exc}", context={"path": str(config_path)}
        ) from exc
    cfg.config_path = config_path
    return cfg


def find_project(
    start: Path | None = None, *, now: datetime | None = None
) -> MemoryLedgerProject:
    """Discover the memoryledger project by walking upward for the config file.

    Walks upward from ``start`` (default ``Path.cwd()``) looking only for
    ``.memoryledger.toml``. Other ledgers' config files are ignored.

    Raises :class:`ConfigError` if no config is found.
    """
    from ledgercore.paths import locate_config

    start_path = Path(start) if start is not None else Path.cwd()
    locator = locate_config(start_path, CONFIG_FILENAMES)
    if locator is None:
        raise ConfigError(
            f"No {CONFIG_FILENAME} found walking upward from {start_path}. "
            "Run 'memoryledger init' first. "
            "(Other ledger config files like .taskledger.toml are intentionally ignored.)",
            context={"start": str(start_path)},
        )

    config_path = locator.config_path
    workspace_root = locator.workspace_root
    config = load_config(config_path)
    state_dir = config.state_dir_path
    export_path = _resolve_export_path(config, workspace_root)
    return MemoryLedgerProject(
        workspace_root=workspace_root,
        config_path=config_path,
        config=config,
        state_dir=state_dir,
        export_path=export_path,
    )


def _resolve_export_path(config: MemoryLedgerConfig, workspace_root: Path) -> Path:
    """Resolve the configured default export path relative to the project root."""
    from ledgercore.paths import resolve_config_relative_path

    rel = config.exports.default_path
    # resolve_config_relative_path resolves relative to the config file dir.
    resolved = resolve_config_relative_path(
        config.config_path or workspace_root / CONFIG_FILENAME,
        rel,
        field_name="default_path",
    )
    return resolved


def validate_scope(scope: str) -> str:
    """Return the scope if recognized, else raise ConfigError."""
    if scope not in VALID_SCOPES:
        raise ConfigError(
            f"Unknown scope {scope!r}; expected one of {VALID_SCOPES}",
            context={"scope": scope},
        )
    return scope


__all__ = [
    "CONFIG_FILENAME",
    "CONFIG_FILENAMES",
    "DEFAULT_CONFIG_TEXT",
    "ExportsSection",
    "ExportTarget",
    "LedgerSection",
    "MemoryLedgerConfig",
    "MemoryLedgerProject",
    "PolicySection",
    "ProjectSection",
    "RetrievalSection",
    "ScopesSection",
    "default_config_text",
    "find_project",
    "load_config",
    "validate_scope",
]
