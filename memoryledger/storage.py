from __future__ import annotations

import os
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]
import yaml
from ledgercore.atomic import atomic_write_text
from ledgercore.time import utc_now_iso

from .errors import MemoryledgerError
from .guardrails import confined_path, validate_memory, validate_scope_path
from .models import Config, EvidenceRef, Memory, RenderConfig, TemplatePolicy

CONFIG_NAMES = ("memoryledger.toml", ".memoryledger.toml")


def _dump_yaml(data: dict[str, object]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text())
    return data if isinstance(data, dict) else {}


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
    auto_accept = bool(raw.get("auto_accept", False))
    return TemplatePolicy(
        enabled=enabled or bool(ids), ids=ids, auto_accept=auto_accept
    )


def default_config_text(project_name: str, memoryledger_dir: str) -> str:
    project_uuid = str(uuid.uuid4())
    return f'''[ledger]
code = "ml"
name = "memoryledger"

[project]
name = "{project_name}"
uuid = "{project_uuid}"

[storage]
memoryledger_dir = "{memoryledger_dir}"

[render]
root_agents_path = "AGENTS.md"
linked_docs_dir = "docs/agents"
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
    root = Path.cwd().resolve()
    config_path = root / (
        ".memoryledger.toml" if hidden_config else "memoryledger.toml"
    )
    if not config_path.exists():
        atomic_write_text(
            config_path,
            default_config_text(project_name or root.name, memoryledger_dir),
        )
    config = load_config(root)
    ensure_storage(config)
    return config


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
        ensure_storage(config)

    def storage_meta(self) -> dict[str, Any]:
        return _load_yaml(self.config.storage_dir / "storage.yaml")

    def write_storage_meta(self, data: dict[str, object]) -> None:
        atomic_write_text(self.config.storage_dir / "storage.yaml", _dump_yaml(data))

    def next_id(self) -> str:
        meta = self.storage_meta()
        number = int(meta.get("next_memory_number", 1))
        meta["next_memory_number"] = number + 1
        self.write_storage_meta(meta)
        return f"memory-{number:04d}"

    def memory_dir(self, memory_id: str) -> Path:
        return self.config.storage_dir / "memories" / memory_id

    def all_memories(self) -> list[Memory]:
        items: list[Memory] = []
        base = self.config.storage_dir / "memories"
        for path in sorted(base.glob("memory-*/memory.yaml")):
            items.append(_load_memory(path.parent))
        return items

    def get(self, memory_id: str) -> Memory:
        path = self.memory_dir(memory_id) / "memory.yaml"
        if not path.exists():
            raise MemoryledgerError("NOT_FOUND", f"Memory not found: {memory_id}")
        return _load_memory(path.parent)

    def read_content(self, memory_id: str) -> str:
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
        )
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
    ) -> Memory:
        now = utc_now_iso()
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
            now,
            now,
            1,
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
        mdir = self.memory_dir(memory.id)
        (mdir / "versions").mkdir(parents=True, exist_ok=True)
        atomic_write_text(mdir / "memory.yaml", _dump_yaml(memory.to_dict()))
        atomic_write_text(mdir / "content.md", content.rstrip() + "\n")
        atomic_write_text(
            mdir / "evidence.md", evidence.rstrip() + "\n" if evidence else ""
        )
        evidence_yaml = mdir / "evidence.yaml"
        if memory.evidence_refs:
            atomic_write_text(
                evidence_yaml,
                _dump_yaml(
                    {"evidence": [ref.to_dict() for ref in memory.evidence_refs]}
                ),
            )
        elif evidence_yaml.exists():
            evidence_yaml.unlink()
        version = f"v{memory.version:04d}"
        atomic_write_text(
            mdir / "versions" / f"{version}.yaml",
            _dump_yaml(
                {"memory": memory.to_dict(), "reason": reason, "evidence": evidence}
            ),
        )
        atomic_write_text(mdir / "versions" / f"{version}.md", content.rstrip() + "\n")

    def update_status(self, memory_id: str, status: str, reason: str) -> Memory:
        old = self.get(memory_id)
        refs = old.evidence_refs
        if status == "accepted":
            refs = [
                *refs,
                EvidenceRef(
                    kind="user_approval",
                    title="Review approval",
                    uri=f"memory:{memory_id}#review-v{old.version + 1:04d}",
                    excerpt=reason,
                    timestamp=utc_now_iso(),
                ),
            ]
        new = replace(
            old,
            status=status,
            evidence_refs=refs,
            updated_at=utc_now_iso(),
            version=old.version + 1,
        )
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
        old = self.get(memory_id)
        body = (
            self.read_content(memory_id).rstrip() + "\n" + content.rstrip() + "\n"
            if append
            else content.rstrip() + "\n"
        )
        new = replace(
            old,
            section=old.section if section is None else section,
            updated_at=utc_now_iso(),
            version=old.version + 1,
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
        old = self.get(memory_id)
        new = replace(
            old,
            evidence_refs=[*old.evidence_refs, evidence],
            updated_at=utc_now_iso(),
            version=old.version + 1,
        )
        self.write(
            new, self.read_content(memory_id), self.read_evidence(memory_id), reason
        )
        return new

    def next_import_id(self) -> str:
        meta = self.storage_meta()
        number = int(meta.get("next_import_number", 1))
        meta["next_import_number"] = number + 1
        self.write_storage_meta(meta)
        return f"import-{number:04d}"
