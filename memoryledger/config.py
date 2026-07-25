"""Strict Memoryledger tool configuration and legacy conversion helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from ledgercore.atomic import atomic_write_text

from .errors import MemoryledgerError
from .models import Config, RenderConfig, TemplatePolicy, ToolConfig

CONFIG_VERSION = 2
_TOP_LEVEL = {"config_version", "ledger", "render", "intake", "template_policy"}
_LEDGER_FIELDS = {"code", "version"}
_RENDER_FIELDS = set(RenderConfig.__dataclass_fields__)
_INTAKE_FIELDS = {"allow_run_html", "allow_current_run", "default_review_status"}
_TEMPLATE_FIELDS = {"enabled", "ids", "auto_accept"}


def global_config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "ledger" / "memoryledger.toml"


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MemoryledgerError(
            "INVALID_CONFIG", f"Unable to read {path}: {exc}"
        ) from exc
    return data if isinstance(data, dict) else {}


def _table(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise MemoryledgerError("INVALID_CONFIG", f"[{name}] must be a table")
    return value


def _reject_unknown(data: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise MemoryledgerError(
            "INVALID_CONFIG",
            f"{label} contains unsupported field(s): {', '.join(unknown)}",
        )


def _render(data: dict[str, Any]) -> RenderConfig:
    _reject_unknown(data, _RENDER_FIELDS, "[render]")
    return RenderConfig(
        **{key: value for key, value in data.items() if key in _RENDER_FIELDS}
    )


def _template_policy(data: dict[str, Any]) -> TemplatePolicy:
    _reject_unknown(data, _TEMPLATE_FIELDS, "[template_policy]")
    raw_ids = data.get("ids", [])
    if not isinstance(raw_ids, list):
        raise MemoryledgerError("INVALID_CONFIG", "template_policy.ids must be a list")
    enabled = data.get("enabled", False)
    ids = [str(item) for item in raw_ids]
    if isinstance(enabled, list):
        ids = [str(item) for item in enabled]
        enabled = bool(ids)
    return TemplatePolicy(
        bool(enabled) or bool(ids), ids, bool(data.get("auto_accept", False))
    )


def _merged_section(
    global_data: dict[str, Any], project_data: dict[str, Any], name: str
) -> dict[str, Any]:
    global_section = _table(global_data, name) if name in global_data else {}
    project_section = _table(project_data, name) if name in project_data else {}
    return {**global_section, **project_section}


def load_tool_config(path: Path, *, global_defaults: bool = True) -> ToolConfig:
    """Load and validate a schema-3 project tool config without resolving paths."""

    project_data = _load_toml(path)
    _reject_unknown(project_data, _TOP_LEVEL, "tool config")
    if project_data.get("config_version") != CONFIG_VERSION:
        raise MemoryledgerError(
            "INVALID_CONFIG_VERSION", f"config_version must be {CONFIG_VERSION}"
        )
    global_data: dict[str, Any] = {}
    if global_defaults and global_config_path().is_file():
        global_data = _load_toml(global_config_path())
    ledger = _table(project_data, "ledger")
    _reject_unknown(ledger, _LEDGER_FIELDS, "[ledger]")
    intake = _merged_section(global_data, project_data, "intake")
    _reject_unknown(intake, _INTAKE_FIELDS, "[intake]")
    return ToolConfig(
        CONFIG_VERSION,
        str(ledger.get("code", "ml")),
        int(ledger.get("version", 0)),
        _render(_merged_section(global_data, project_data, "render")),
        bool(intake.get("allow_run_html", True)),
        bool(intake.get("allow_current_run", True)),
        str(intake.get("default_review_status", "candidate")),
        _template_policy(_merged_section(global_data, project_data, "template_policy")),
    )


def tool_config_from_legacy(data: dict[str, Any]) -> ToolConfig:
    """Translate legacy settings while dropping identity and storage paths."""

    ledger = _table(data, "ledger")
    intake = _table(data, "intake")
    return ToolConfig(
        CONFIG_VERSION,
        str(ledger.get("code", "ml")),
        int(ledger.get("version", 0)),
        _render(_table(data, "render")),
        bool(intake.get("allow_run_html", True)),
        bool(intake.get("allow_current_run", True)),
        str(intake.get("default_review_status", "candidate")),
        _template_policy(_table(data, "template_policy")),
    )


def render_tool_config(config: ToolConfig) -> str:
    r = config.render
    lines = [
        "config_version = 2",
        "",
        "[ledger]",
        f'code = "{config.ledger_code}"',
        f"version = {config.ledger_version}",
        "",
        "[render]",
        f'root_agents_path = "{r.root_agents_path}"',
        f'linked_docs_dir = "{r.linked_docs_dir}"',
        f"nested_agents_enabled = {str(r.nested_agents_enabled).lower()}",
        f"linked_docs_enabled = {str(r.linked_docs_enabled).lower()}",
        f"max_root_agents_chars = {r.max_root_agents_chars}",
        f"max_linked_doc_chars = {r.max_linked_doc_chars}",
        f"include_local = {str(r.include_local).lower()}",
        f"include_rejected = {str(r.include_rejected).lower()}",
        f"include_evidence = {str(r.include_evidence).lower()}",
        f'evidence_index_path = "{r.evidence_index_path}"',
        "sort_order = [" + ", ".join(f'"{item}"' for item in r.sort_order) + "]",
        "",
        "[intake]",
        f"allow_run_html = {str(config.allow_run_html).lower()}",
        f"allow_current_run = {str(config.allow_current_run).lower()}",
        f'default_review_status = "{config.default_review_status}"',
        "",
        "[template_policy]",
        f"enabled = {str(config.template_policy.enabled).lower()}",
        "ids = [" + ", ".join(f'"{item}"' for item in config.template_policy.ids) + "]",
        f"auto_accept = {str(config.template_policy.auto_accept).lower()}",
        "",
    ]
    return "\n".join(lines)


def write_tool_config(path: Path, config: ToolConfig) -> None:
    atomic_write_text(path, render_tool_config(config))


def legacy_config_to_tool_config(config: Config) -> ToolConfig:
    return ToolConfig(
        CONFIG_VERSION,
        config.ledger_code,
        0,
        config.render,
        config.allow_run_html,
        config.allow_current_run,
        config.default_review_status,
        config.template_policy,
    )
