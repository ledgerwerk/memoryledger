from __future__ import annotations

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
from .models import Config, Memory, RenderConfig

CONFIG_NAMES = ("memoryledger.toml", ".memoryledger.toml")


def _dump_yaml(data: dict[str, object]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text())
    return data if isinstance(data, dict) else {}


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
    data = tomllib.loads(path.read_text())
    render_data = data.get("render", {})
    render = RenderConfig(
        **{
            k: v
            for k, v in render_data.items()
            if k in RenderConfig.__dataclass_fields__
        }
    )
    return Config(
        root=path.parent,
        config_path=path,
        ledger_code=data.get("ledger", {}).get("code", "ml"),
        ledger_name=data.get("ledger", {}).get("name", "memoryledger"),
        project_name=data.get("project", {}).get("name", "my-project"),
        project_uuid=data.get("project", {}).get("uuid", ""),
        memoryledger_dir=data.get("storage", {}).get(
            "memoryledger_dir", ".memoryledger"
        ),
        render=render,
        allow_run_html=bool(data.get("intake", {}).get("allow_run_html", True)),
        allow_current_run=bool(data.get("intake", {}).get("allow_current_run", True)),
        default_review_status=data.get("intake", {}).get(
            "default_review_status", "candidate"
        ),
    )


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
            items.append(Memory.from_dict(_load_yaml(path)))
        return items

    def get(self, memory_id: str) -> Memory:
        path = self.memory_dir(memory_id) / "memory.yaml"
        if not path.exists():
            raise MemoryledgerError("NOT_FOUND", f"Memory not found: {memory_id}")
        return Memory.from_dict(_load_yaml(path))

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
    ) -> Memory:
        now = utc_now_iso()
        memory = Memory(
            self.next_id(),
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
        )
        self.write(memory, content, evidence, "created")
        return memory

    def write(self, memory: Memory, content: str, evidence: str, reason: str) -> None:
        mdir = self.memory_dir(memory.id)
        (mdir / "versions").mkdir(parents=True, exist_ok=True)
        atomic_write_text(mdir / "memory.yaml", _dump_yaml(memory.to_dict()))
        atomic_write_text(mdir / "content.md", content.rstrip() + "\n")
        atomic_write_text(
            mdir / "evidence.md", evidence.rstrip() + "\n" if evidence else ""
        )
        version = f"v{memory.version:04d}"
        atomic_write_text(
            mdir / "versions" / f"{version}.yaml",
            _dump_yaml({"memory": memory.to_dict(), "reason": reason}),
        )
        atomic_write_text(mdir / "versions" / f"{version}.md", content.rstrip() + "\n")

    def update_status(self, memory_id: str, status: str, reason: str) -> Memory:
        old = self.get(memory_id)
        new = replace(
            old, status=status, updated_at=utc_now_iso(), version=old.version + 1
        )
        self.write(
            new,
            self.read_content(memory_id),
            self.read_evidence(memory_id) + f"\nReview reason: {reason}\n",
            reason,
        )
        return new

    def update_content(
        self, memory_id: str, content: str, reason: str, append: bool = False
    ) -> Memory:
        old = self.get(memory_id)
        body = (
            self.read_content(memory_id).rstrip() + "\n" + content.rstrip() + "\n"
            if append
            else content.rstrip() + "\n"
        )
        new = replace(old, updated_at=utc_now_iso(), version=old.version + 1)
        self.write(new, body, self.read_evidence(memory_id), reason)
        return new

    def next_import_id(self) -> str:
        meta = self.storage_meta()
        number = int(meta.get("next_import_number", 1))
        meta["next_import_number"] = number + 1
        self.write_storage_meta(meta)
        return f"import-{number:04d}"
