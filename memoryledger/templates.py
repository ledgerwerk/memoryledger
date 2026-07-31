from __future__ import annotations

import hashlib
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


from .errors import MemoryledgerError
from .guardrails import confined_path, validate_content
from .models import GlobalConfig, Memory, Template
from .storage import Store


def global_config_path() -> Path:
    """Return the user-level template configuration path."""
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "ledger" / "memoryledger.toml"


def canonical_hash(content: str) -> str:
    """Return the stable content hash used for template synchronization."""
    return hashlib.sha256((content.rstrip() + "\n").encode()).hexdigest()


def load_global_config(path: Path | None = None) -> GlobalConfig:
    """Load global templates from TOML without changing project state."""
    config_path = path or global_config_path()
    if not config_path.exists():
        return GlobalConfig(config_path)
    data = tomllib.loads(config_path.read_text())
    raw_templates = data.get("templates", [])
    if isinstance(raw_templates, dict):
        raw_templates = [
            {"id": template_id, **value} for template_id, value in raw_templates.items()
        ]
    templates: list[Template] = []
    seen: set[str] = set()
    for raw in raw_templates:
        if not isinstance(raw, dict):
            raise MemoryledgerError("INVALID_TEMPLATE", "template must be a table")
        template = _parse_template(raw, config_path.parent)
        if template.id in seen:
            raise MemoryledgerError(
                "DUPLICATE_TEMPLATE_ID", f"Duplicate template ID: {template.id}"
            )
        seen.add(template.id)
        templates.append(template)
    return GlobalConfig(config_path, templates)


def _parse_template(raw: dict[str, Any], root: Path) -> Template:
    template = Template(
        id=str(raw.get("id", "")),
        version=str(raw.get("version", "1")),
        kind=str(raw.get("kind", "rule")),
        title=str(raw.get("title", "")),
        content=str(raw.get("content", "")),
        content_file=str(raw.get("content_file", "")),
        scope=str(raw.get("scope", "global")),
        scope_path=str(raw.get("scope_path", "")),
        render_target=str(raw.get("render_target", "root_agents")),
        section=str(raw.get("section", "")),
        source_root=root,
    )
    if not template.id or not template.title:
        raise MemoryledgerError(
            "INVALID_TEMPLATE", "template ID and title are required"
        )
    return template


def template_content(template: Template) -> str:
    """Resolve inline or file-backed template content."""
    if bool(template.content) == bool(template.content_file):
        raise MemoryledgerError(
            "INVALID_TEMPLATE", "provide exactly one of content or content_file"
        )
    content = template.content
    if template.content_file:
        path = confined_path(
            template.source_root,
            template.content_file,
            code="INVALID_TEMPLATE_PATH",
            label="template content_file",
            must_exist=True,
        )
        content = path.read_text()
    validate_content(content)
    return content.rstrip() + "\n"


def find_template(config: GlobalConfig, template_id: str) -> Template:
    """Find a configured template or raise a domain not-found error."""
    for template in config.templates:
        if template.id == template_id:
            return template
    raise MemoryledgerError("TEMPLATE_NOT_FOUND", template_id)


def apply_template(store: Store, template: Template) -> tuple[str, Memory]:
    """Create or update a candidate from a template."""
    content = template_content(template)
    digest = canonical_hash(content)
    origin = f"template:{template.id}"
    matches = [memory for memory in store.all_memories() if memory.origin == origin]
    if not matches:
        memory = store.create(
            template.kind,
            template.title,
            content,
            f"Applied template {template.id} version {template.version}.",
            template.scope,
            template.scope_path,
            template.render_target,
            "template",
            origin=origin,
            origin_hash=digest,
            section=template.section,
        )
        return "created", memory
    memory = matches[0]
    local = store.read_content(memory.id)
    if canonical_hash(local) != memory.origin_hash:
        raise MemoryledgerError(
            "TEMPLATE_CONFLICT", f"Local memory diverged from template: {memory.id}"
        )
    if memory.origin_hash == digest:
        return "unchanged", memory
    version = store.bump_ledger_version()
    updated = replace(
        memory,
        kind=template.kind,
        title=template.title,
        status="candidate",
        scope=template.scope,
        scope_path=template.scope_path,
        render_target=template.render_target,
        section=template.section,
        origin_hash=digest,
        modified_version=version,
    )
    store.write(
        updated,
        content,
        f"Synced template {template.id} version {template.version}.",
        f"template sync {template.version}",
    )
    return "updated", updated


def remove_template(store: Store, template_id: str, reason: str) -> Memory:
    """Archive the memory associated with a template after a reasoned change."""
    matches = [
        memory
        for memory in store.all_memories()
        if memory.origin == f"template:{template_id}"
    ]
    if not matches:
        raise MemoryledgerError("TEMPLATE_NOT_APPLIED", template_id)
    return store.update_status(matches[0].id, "archived", reason)
