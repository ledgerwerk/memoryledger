from __future__ import annotations

import os
import shutil
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]
import ledgercore
import yaml
from ledgercore.atomic import atomic_write_text

from .errors import MemoryledgerError
from .guardrails import confined_path, validate_memory, validate_scope_path
from .models import (
    GENERATED_MARKER,
    Config,
    EvidenceRef,
    Memory,
    RenderConfig,
    TemplatePolicy,
)

CONFIG_NAMES = ("memoryledger.toml", ".memoryledger.toml")


def _dump_yaml(data: dict[str, object]) -> str:
    # Keep one public adapter so storage and migration use Ledgercore's YAML
    # serialization rules without changing the record-facing API.
    import tempfile

    with tempfile.NamedTemporaryFile() as handle:
        path = Path(handle.name)
    try:
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    finally:
        path.unlink(missing_ok=True)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    try:
        raw, body = ledgercore.split_front_matter_text(text)
    except Exception as exc:
        raise MemoryledgerError("INVALID_MEMORY_FILE", str(exc)) from exc
    return raw, body.lstrip("\n")


def _frontmatter_text(memory: Memory, content: str) -> str:
    data = memory.to_dict()
    refs = data.pop("evidence_refs", [])
    if refs:
        data["evidence"] = refs
    return ledgercore.render_front_matter_text(
        data, f"\n{content.rstrip()}\n", key_order=list(data)
    )


def _load_evidence_refs(path: Path) -> list[EvidenceRef]:
    raw = yaml.safe_load(path.read_text()) if path.exists() else {}
    if isinstance(raw, dict):
        items = raw.get("evidence", [])
    elif isinstance(raw, list):
        items = raw
    else:
        items = []
    return [EvidenceRef.from_dict(item) for item in items if isinstance(item, dict)]


def _load_memory(path: Path) -> Memory:
    if path.is_file() and path.suffix == ".md":
        data, _body = _split_frontmatter(path.read_text())
        return Memory.from_dict(data)
    data = _load_yaml(path / "memory.yaml")
    if "evidence_refs" not in data:
        refs = _load_evidence_refs(path / "evidence.yaml")
        if refs:
            data = {**data, "evidence_refs": [ref.to_dict() for ref in refs]}
    return Memory.from_dict(data)


def _load_toml(path: Path) -> dict[str, Any]:
    data = tomllib.loads(path.read_text())
    return data if isinstance(data, dict) else {}


def _global_config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "ledger" / "memoryledger.toml"


def _merged_section(
    global_data: dict[str, Any], project_data: dict[str, Any], key: str
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    raw_global = global_data.get(key, {})
    if isinstance(raw_global, dict):
        merged.update(raw_global)
    raw_project = project_data.get(key, {})
    if isinstance(raw_project, dict):
        merged.update(raw_project)
    return merged


def _parse_template_policy(data: dict[str, Any]) -> TemplatePolicy:
    raw = data.get("template_policy", {})
    if not isinstance(raw, dict):
        return TemplatePolicy()
    enabled_raw = raw.get("enabled", False)
    ids: list[str] = []
    enabled = False
    if isinstance(enabled_raw, list):
        ids.extend(str(value) for value in enabled_raw)
        enabled = bool(ids)
    else:
        enabled = bool(enabled_raw)
    raw_ids = raw.get("ids", [])
    if isinstance(raw_ids, list):
        for value in raw_ids:
            item = str(value)
            if item not in ids:
                ids.append(item)
    return TemplatePolicy(
        enabled=enabled or bool(ids),
        ids=ids,
        auto_accept=bool(raw.get("auto_accept", False)),
    )


def default_config_text(project_name: str, memoryledger_dir: str) -> str:
    project_uuid = str(uuid.uuid4())
    return f'''[ledger]
code = "ml"
name = "memoryledger"
version = 0

[project]
name = "{project_name}"
uuid = "{project_uuid}"

[storage]
memoryledger_dir = "{memoryledger_dir}"

[render]
root_agents_path = "AGENTS.md"
linked_docs_dir = "agent_docs"
nested_agents_enabled = false
linked_docs_enabled = true
max_root_agents_chars = 12000
max_linked_doc_chars = 50000
include_local = false
include_rejected = false
sort_order = ["rule", "procedure", "semantic", "learning", "episode", "document"]

[intake]
allow_run_html = true
allow_current_run = true
default_review_status = "candidate"
'''


def find_config(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        for name in CONFIG_NAMES:
            path = directory / name
            if path.exists():
                return path
    return None


def load_config(start: Path | None = None) -> Config:
    from .project import resolve_workspace, workspace_as_compat_config

    try:
        workspace = resolve_workspace(start)
    except MemoryledgerError as exc:
        if exc.code not in {"NO_CONFIG", "INVALID_LEDGER_LAYOUT", "MIGRATION_REQUIRED"}:
            raise
    else:
        if workspace.paths.layout_source == "canonical":
            return workspace_as_compat_config(workspace)
    path = find_config(start)
    if path is None:
        raise MemoryledgerError("NO_CONFIG", "Run `memoryledger init` first.")
    project_data = _load_toml(path)
    global_path = _global_config_path()
    global_data = _load_toml(global_path) if global_path.exists() else {}
    render_data = _merged_section(global_data, project_data, "render")
    ledger_data = _merged_section(global_data, project_data, "ledger")
    project_section = _merged_section(global_data, project_data, "project")
    storage_data = _merged_section(global_data, project_data, "storage")
    intake_data = _merged_section(global_data, project_data, "intake")
    render = RenderConfig(
        **{
            k: v
            for k, v in render_data.items()
            if k in RenderConfig.__dataclass_fields__
        }
    )
    config = Config(
        root=path.parent,
        config_path=path,
        ledger_code=str(ledger_data.get("code", "ml")),
        ledger_name=str(ledger_data.get("name", "memoryledger")),
        project_name=str(project_section.get("name", "my-project")),
        project_uuid=str(project_section.get("uuid", "")),
        memoryledger_dir=str(storage_data.get("memoryledger_dir", ".memoryledger")),
        render=render,
        allow_run_html=bool(intake_data.get("allow_run_html", True)),
        allow_current_run=bool(intake_data.get("allow_current_run", True)),
        default_review_status=str(
            intake_data.get("default_review_status", "candidate")
        ),
        template_policy=_parse_template_policy(
            {
                "template_policy": {
                    **(
                        global_data.get("template_policy", {})
                        if isinstance(global_data.get("template_policy", {}), dict)
                        else {}
                    ),
                    **(
                        project_data.get("template_policy", {})
                        if isinstance(project_data.get("template_policy", {}), dict)
                        else {}
                    ),
                }
            }
        ),
    )
    confined_path(config.root, config.memoryledger_dir, label="memoryledger_dir")
    confined_path(
        config.root,
        config.render.root_agents_path,
        code="INVALID_OUTPUT_PATH",
        label="root_agents_path",
    )
    confined_path(
        config.root,
        config.render.linked_docs_dir,
        code="INVALID_OUTPUT_PATH",
        label="linked_docs_dir",
    )
    if config.render.evidence_index_path:
        confined_path(
            config.root,
            config.render.evidence_index_path,
            code="INVALID_OUTPUT_PATH",
            label="evidence_index_path",
        )
    return config


def init_workspace(
    project_name: str | None, memoryledger_dir: str, hidden_config: bool
) -> Config:
    if memoryledger_dir != ".memoryledger" or hidden_config:
        raise MemoryledgerError(
            "LEGACY_INIT_UNSUPPORTED",
            "schema-3 initialization does not accept legacy config or storage options",
        )
    from .project import init_canonical_workspace, workspace_as_compat_config

    return workspace_as_compat_config(init_canonical_workspace(project_name))


def ensure_storage(config: Config) -> None:
    for rel in ["memories", "imports", "rendered/docs", "rendered/nested"]:
        (config.storage_dir / rel).mkdir(parents=True, exist_ok=True)
    storage = config.storage_dir / "storage.yaml"
    if not storage.exists():
        atomic_write_text(
            storage, _dump_yaml({"next_memory_number": 1, "next_import_number": 1})
        )


class Store:
    def __init__(self, config: Config) -> None:
        self.config = config

    def ensure_initialized(self) -> None:
        """Create legacy durable state explicitly before a mutation."""

        if (
            self.config.config_path.name == "config.toml"
            and self.config.config_path.parent.parent.name == ".ledger"
        ):
            legacy_config = self.config.root / "memoryledger.toml"
            legacy_data = self.config.root / ".memoryledger"
            journals = self.config.root / ".ledger" / "migrations"
            complete = False
            for journal in (
                journals.glob("memoryledger-*.toml") if journals.exists() else []
            ):
                if 'phase = "complete"' in journal.read_text(encoding="utf-8"):
                    complete = True
                    break
            if legacy_config.exists() and legacy_data.exists() and not complete:
                raise MemoryledgerError(
                    "STORAGE_LAYOUT_AMBIGUOUS",
                    "legacy and canonical Memoryledger state coexist without a completed migration journal",
                )
        ensure_storage(self.config)

    def storage_meta(self) -> dict[str, Any]:
        return _load_yaml(self.config.storage_dir / "storage.yaml")

    def write_storage_meta(self, data: dict[str, object]) -> None:
        self.config.storage_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.config.storage_dir / "storage.yaml", _dump_yaml(data))

    def ledger_version(self) -> int:
        data = _load_toml(self.config.config_path)
        ledger = data.get("ledger", {})
        return int(ledger.get("version", 0)) if isinstance(ledger, dict) else 0

    def bump_ledger_version(self) -> int:
        old = self.ledger_version()
        new = old + 1
        self.set_ledger_version(new)
        return new

    def set_ledger_version(self, new: int) -> None:
        text = self.config.config_path.read_text()
        if "[ledger]" not in text:
            text = f"[ledger]\nversion = {new}\n\n" + text
        elif "version =" in text.split("[ledger]", 1)[1].split("\n[", 1)[0]:
            lines = text.splitlines()
            in_ledger = False
            for i, line in enumerate(lines):
                if line.strip() == "[ledger]":
                    in_ledger = True
                elif in_ledger and line.startswith("["):
                    break
                elif in_ledger and line.strip().startswith("version"):
                    lines[i] = f"version = {new}"
                    break
            text = "\n".join(lines) + "\n"
        else:
            text = text.replace("[ledger]\n", f"[ledger]\nversion = {new}\n", 1)
        atomic_write_text(self.config.config_path, text)

    def next_id(self) -> str:
        self.ensure_initialized()
        meta = self.storage_meta()
        existing = [memory.id for memory in self.all_memories()]
        candidate = ledgercore.next_prefixed_id("memory", existing, width=4)
        number = max(
            int(meta.get("next_memory_number", 1)), int(candidate.rsplit("-", 1)[1])
        )
        meta["next_memory_number"] = number + 1
        self.write_storage_meta(meta)
        return f"memory-{number:04d}"

    def memory_dir(self, memory_id: str) -> Path:
        return self.config.storage_dir / "memories" / memory_id

    def memory_file(self, memory_id: str) -> Path:
        return self.config.storage_dir / "memories" / f"{memory_id}.md"

    def all_memories(self) -> list[Memory]:
        base = self.config.storage_dir / "memories"
        if not base.exists():
            return []
        items = [_load_memory(path) for path in sorted(base.glob("memory-*.md"))]
        for path in sorted(base.glob("memory-*/memory.yaml")):
            if not self.memory_file(path.parent.name).exists():
                items.append(_load_memory(path.parent))
        return sorted(items, key=lambda item: item.id)

    def get(self, memory_id: str) -> Memory:
        md = self.memory_file(memory_id)
        if md.exists():
            return _load_memory(md)
        path = self.memory_dir(memory_id) / "memory.yaml"
        if not path.exists():
            raise MemoryledgerError("NOT_FOUND", f"Memory not found: {memory_id}")
        return _load_memory(path.parent)

    def read_content(self, memory_id: str) -> str:
        md = self.memory_file(memory_id)
        if md.exists():
            _data, body = _split_frontmatter(md.read_text())
            return body
        return (self.memory_dir(memory_id) / "content.md").read_text()

    def read_evidence(self, memory_id: str) -> str:
        path = self.memory_dir(memory_id) / "evidence.md"
        return path.read_text() if path.exists() else ""

    def create(
        self,
        kind: str,
        title: str,
        content: str,
        evidence: str,
        scope: str,
        scope_path: str,
        render_target: str,
        source: str = "cli",
        *,
        origin: str = "",
        origin_hash: str = "",
        section: str = "",
        evidence_refs: list[EvidenceRef] | None = None,
    ) -> Memory:
        self.ensure_initialized()
        version = self.ledger_version() + 1
        memory = self.validate_new(
            kind,
            title,
            content,
            evidence,
            scope,
            scope_path,
            render_target,
            source,
            origin=origin,
            origin_hash=origin_hash,
            section=section,
            evidence_refs=evidence_refs,
            version=version,
        )
        self.set_ledger_version(version)
        memory = replace(memory, id=self.next_id())
        self.write(memory, content, evidence, "created")
        return memory

    def validate_new(
        self,
        kind: str,
        title: str,
        content: str,
        evidence: str,
        scope: str,
        scope_path: str,
        render_target: str,
        source: str = "cli",
        *,
        origin: str = "",
        origin_hash: str = "",
        section: str = "",
        evidence_refs: list[EvidenceRef] | None = None,
        version: int | None = None,
    ) -> Memory:
        current = version if version is not None else max(1, self.ledger_version())
        memory = Memory(
            "memory-pending",
            kind,
            title,
            "candidate",
            100,
            scope,
            scope_path,
            render_target,
            source,
            current,
            current,
            [],
            origin,
            origin_hash,
            section,
            evidence_refs or [],
        )
        validate_scope_path(self.config.root, scope_path)
        validate_memory(memory, content, evidence, self.config.root)
        return memory

    def write(self, memory: Memory, content: str, evidence: str, reason: str) -> None:
        validate_scope_path(self.config.root, memory.scope_path)
        validate_memory(memory, content, evidence, self.config.root)
        atomic_write_text(
            self.memory_file(memory.id), _frontmatter_text(memory, content)
        )
        legacy = self.memory_dir(memory.id)
        if legacy.exists() and legacy.is_dir():
            shutil.rmtree(legacy)

    def update_status(self, memory_id: str, status: str, reason: str) -> Memory:
        self.ensure_initialized()
        old = self.get(memory_id)
        version = self.bump_ledger_version()
        refs = old.evidence_refs
        if status == "accepted":
            refs = [
                *refs,
                EvidenceRef(
                    kind="user_approval",
                    title="Review approval",
                    uri=f"memory:{memory_id}#review-v{version}",
                    excerpt=reason,
                ),
            ]
        new = replace(old, status=status, evidence_refs=refs, modified_version=version)
        self.write(
            new,
            self.read_content(memory_id),
            self.read_evidence(memory_id) + f"\nReview reason: {reason}\n",
            reason,
        )
        return new

    def update_content(
        self,
        memory_id: str,
        content: str,
        reason: str,
        append: bool = False,
        section: str | None = None,
    ) -> Memory:
        self.ensure_initialized()
        old = self.get(memory_id)
        version = self.bump_ledger_version()
        body = (
            self.read_content(memory_id).rstrip() + "\n" + content.rstrip() + "\n"
            if append
            else content.rstrip() + "\n"
        )
        new = replace(
            old,
            section=old.section if section is None else section,
            modified_version=version,
        )
        self.write(new, body, self.read_evidence(memory_id), reason)
        return new

    def add_evidence(
        self, memory_id: str, evidence: EvidenceRef, reason: str
    ) -> Memory:
        if not reason.strip():
            raise MemoryledgerError(
                "MISSING_REASON", "evidence changes require a reason"
            )
        self.ensure_initialized()
        old = self.get(memory_id)
        version = self.bump_ledger_version()
        new = replace(
            old, evidence_refs=[*old.evidence_refs, evidence], modified_version=version
        )
        self.write(
            new, self.read_content(memory_id), self.read_evidence(memory_id), reason
        )
        return new

    def next_import_id(self) -> str:
        self.ensure_initialized()
        meta = self.storage_meta()
        existing = [
            path.name for path in (self.config.storage_dir / "imports").glob("import-*")
        ]
        candidate = ledgercore.next_prefixed_id("import", existing, width=4)
        number = max(
            int(meta.get("next_import_number", 1)), int(candidate.rsplit("-", 1)[1])
        )
        meta["next_import_number"] = number + 1
        self.write_storage_meta(meta)
        return f"import-{number:04d}"

    def storage_v2_plan(self) -> dict[str, object]:
        base = self.config.storage_dir / "memories"
        legacy = sorted(path.parent for path in base.glob("memory-*/memory.yaml"))
        return {
            "legacy_memories": [path.name for path in legacy],
            "create": [str(base / f"{path.name}.md") for path in legacy],
            "remove": [str(path) for path in legacy],
            "ledger_version": max(
                [
                    self.ledger_version(),
                    *[self.get(path.name).modified_version for path in legacy],
                ],
                default=self.ledger_version(),
            ),
        }

    def migrate_storage_v2(self, backup: bool = False) -> dict[str, object]:
        plan = self.storage_v2_plan()
        changed: list[str] = []
        base = self.config.storage_dir / "memories"
        raw_legacy_ids = plan.get("legacy_memories", [])
        legacy_ids = (
            [str(item) for item in raw_legacy_ids]
            if isinstance(raw_legacy_ids, list)
            else []
        )
        for memory_id in legacy_ids:
            memory = self.get(memory_id)
            content = self.read_content(memory_id)
            target = base / f"{memory_id}.md"
            atomic_write_text(target, _frontmatter_text(memory, content))
            changed.append(str(target))
            legacy = base / str(memory_id)
            if backup:
                shutil.copytree(
                    legacy, base / f"{memory_id}.legacy-backup", dirs_exist_ok=True
                )
            shutil.rmtree(legacy)
            changed.append(str(legacy))
        target_version = int(str(plan["ledger_version"]))
        if target_version > self.ledger_version():
            text = self.config.config_path.read_text()
            if "version =" in text:
                lines = [
                    f"version = {target_version}"
                    if line.strip().startswith("version")
                    else line
                    for line in text.splitlines()
                ]
                atomic_write_text(self.config.config_path, "\n".join(lines) + "\n")
        return {**plan, "changed": changed}


def linked_docs_dir_migration(
    config: Config, from_dir: str, to_dir: str, apply: bool = False
) -> dict[str, object]:
    src = confined_path(config.root, from_dir, code="INVALID_OUTPUT_PATH", label="from")
    dst = confined_path(config.root, to_dir, code="INVALID_OUTPUT_PATH", label="to")
    movable: list[str] = []
    skipped: list[str] = []
    if src.exists():
        for path in sorted(p for p in src.rglob("*") if p.is_file()):
            if GENERATED_MARKER in path.read_text():
                movable.append(path.relative_to(config.root).as_posix())
            else:
                skipped.append(path.relative_to(config.root).as_posix())
    if apply:
        for rel in movable:
            source = config.root / rel
            target = dst / source.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
        text = config.config_path.read_text()
        old = f'linked_docs_dir = "{from_dir}"'
        new = f'linked_docs_dir = "{to_dir}"'
        if old in text:
            atomic_write_text(config.config_path, text.replace(old, new, 1))
    return {
        "from": from_dir,
        "to": to_dir,
        "move": movable,
        "skip": skipped,
        "mutated": apply,
    }
