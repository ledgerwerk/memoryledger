from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ledgercore.atomic import atomic_write_text
from ledgercore.time import utc_now_iso

from .guardrails import safe_to_replace, validate_generated_text, validate_scope_path
from .models import GENERATED_MARKER, Config, Memory
from .storage import Store

DOC_MAP = {
    "procedure": ("Procedures", "procedures.md"),
    "semantic": ("Semantic memory", "semantic-memory.md"),
    "episode": ("Episodes", "episodes.md"),
    "document": ("Documents", "documents.md"),
}
ROOT_SECTIONS = {
    "rule": "Rules",
    "procedure": "Procedures",
    "semantic": "Semantic memory",
    "learning": "Learnings",
    "episode": "Episodes",
    "document": "Documents",
}
LONG_THRESHOLD = 500


@dataclass(frozen=True)
class RenderResult:
    root_text: str
    linked_docs: dict[str, str]
    nested_docs: dict[str, str]


def _escape_markdown(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in ("`", "[", "]", "(", ")", "*", "_"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def _active(config: Config, memories: list[Memory]) -> list[Memory]:
    result = []
    for memory in memories:
        if memory.status != "accepted" and not config.render.include_rejected:
            continue
        if memory.kind == "local" and not config.render.include_local:
            continue
        result.append(memory)
    order = {kind: i for i, kind in enumerate(config.render.sort_order)}
    return sorted(result, key=lambda m: (order.get(m.kind, 99), m.priority, m.id))


def _bullet(title: str, content: str) -> str:
    one = " ".join(
        line.strip() for line in content.strip().splitlines() if line.strip()
    )
    if one.startswith("-") or one.startswith("1."):
        return content.strip()
    return f"- {one}"


def _doc_path(config: Config, kind: str) -> str:
    return f"{config.render.linked_docs_dir}/{DOC_MAP[kind][1]}"


def _evidence_comment(config: Config, memory: Memory) -> str:
    if not config.render.include_evidence or not memory.evidence_refs:
        return ""
    if config.render.evidence_index_path:
        return (
            f"\n<!-- memoryledger:evidence {memory.id} "
            f"{config.render.evidence_index_path}#{memory.id} -->"
        )
    return (
        f"\n<!-- memoryledger:evidence {memory.id} "
        + ",".join(ref.kind for ref in memory.evidence_refs)
        + " -->"
    )


def _format_evidence_ref(ref) -> str:
    label = _escape_markdown(ref.title)
    if ref.line_start is not None and ref.line_end is not None:
        if ref.line_start == ref.line_end:
            label += f" (line {ref.line_start})"
        else:
            label += f" (lines {ref.line_start}-{ref.line_end})"
    return f"- {label} (`{_escape_markdown(ref.uri)}`)"


def render_all(config: Config) -> RenderResult:
    store = Store(config)
    memories = _active(config, store.all_memories())
    linked: dict[str, list[tuple[Memory, str]]] = {}
    root: dict[str, list[tuple[Memory, str]]] = {k: [] for k in ROOT_SECTIONS}
    nested: dict[str, list[tuple[Memory, str]]] = {}

    for memory in memories:
        content = store.read_content(memory.id)
        if memory.render_target == "nested_agents":
            nested.setdefault(memory.scope_path, []).append((memory, content))
            continue
        use_link = memory.render_target == "linked_doc" or (
            config.render.linked_docs_enabled
            and memory.kind in DOC_MAP
            and len(content) > LONG_THRESHOLD
        )
        if use_link and memory.kind in DOC_MAP:
            linked.setdefault(memory.kind, []).append((memory, content))
        elif memory.kind in root:
            evidence_comment = _evidence_comment(config, memory)
            if memory.kind == "document":
                root[memory.kind].append(
                    (memory, f"- {memory.title}{evidence_comment}")
                )
            else:
                root[memory.kind].append(
                    (memory, _bullet(memory.title, content) + evidence_comment)
                )

    linked_docs = _render_linked(config, linked)
    if config.render.include_evidence and config.render.evidence_index_path:
        index_lines = [
            "# Evidence index",
            "",
            GENERATED_MARKER,
            "<!-- Source: .memoryledger; regenerate with `memoryledger render` and `memoryledger export`. -->",
            "",
        ]
        for memory in memories:
            if not memory.evidence_refs:
                continue
            index_lines += [
                f'<a id="{memory.id}"></a>',
                "",
                f"## {memory.id} — {memory.title}",
                "",
            ]
            for ref in memory.evidence_refs:
                index_lines.append(_format_evidence_ref(ref))
            index_lines.append("")
        linked_docs[config.render.evidence_index_path] = (
            "\n".join(index_lines).rstrip() + "\n"
        )
    nested_docs = _render_nested(config, nested)
    root_text = _render_root(config, root, linked_docs, nested_docs)
    validate_generated_text(root_text, config.render.max_root_agents_chars)
    for text in linked_docs.values():
        validate_generated_text(text, config.render.max_linked_doc_chars)
    return RenderResult(root_text, linked_docs, nested_docs)


def _render_root(
    config: Config,
    sections: dict[str, list[tuple[Memory, str]]],
    linked_docs: dict[str, str],
    nested_docs: dict[str, str],
) -> str:
    lines = [
        "# AGENTS.md",
        "",
        GENERATED_MARKER,
        "<!-- Source: .memoryledger; regenerate with `memoryledger render` and `memoryledger export`. -->",
        "",
        "## Project memory policy",
        "",
        "This file contains reviewed long-term project memory.",
        "",
    ]
    for kind in config.render.sort_order:
        if kind not in ROOT_SECTIONS or not sections.get(kind):
            continue
        items = sections[kind]
        if any(memory.section for memory, _text in items):
            lines += [f"## {ROOT_SECTIONS[kind]}", ""]
            grouped: dict[str, list[str]] = {}
            for memory, text in items:
                grouped.setdefault(memory.section, []).append(text)
            if grouped.get(""):
                lines += [*grouped.pop(""), ""]
            for section in sorted(grouped, key=str.casefold):
                lines += [f"### {section}", "", *grouped[section], ""]
        else:
            lines += [f"## {ROOT_SECTIONS[kind]}", "", *(t for _m, t in items), ""]
    if linked_docs:
        lines += ["## Linked documents", ""]
        for path in sorted(linked_docs):
            title = Path(path).stem.replace("-", " ").capitalize()
            lines.append(f"- [{title}]({path})")
        lines.append("")
    if nested_docs:
        lines += ["## Nested agent files", ""]
        for path in sorted(nested_docs):
            lines.append(f"- [{path}]({path})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_linked(
    config: Config, linked: dict[str, list[tuple[Memory, str]]]
) -> dict[str, str]:
    docs: dict[str, str] = {}
    for kind, items in linked.items():
        title, _filename = DOC_MAP[kind]
        lines = [
            f"# {title}",
            "",
            GENERATED_MARKER,
            "<!-- Source: .memoryledger; regenerate with `memoryledger render` and `memoryledger export`. -->",
            "",
        ]
        for memory, content in sorted(
            items, key=lambda item: (item[0].priority, item[0].id)
        ):
            lines += [f"## {memory.title}", "", content.strip(), ""]
            if config.render.include_evidence and memory.evidence_refs:
                lines += ["### Evidence", ""]
                for ref in memory.evidence_refs:
                    lines.append(_format_evidence_ref(ref))
                lines.append("")
        docs[_doc_path(config, kind)] = "\n".join(lines).rstrip() + "\n"
    return docs


def _render_nested(
    config: Config, nested: dict[str, list[tuple[Memory, str]]]
) -> dict[str, str]:
    docs: dict[str, str] = {}
    for scope_path, items in nested.items():
        validate_scope_path(config.root, scope_path)
        lines = [
            "# AGENTS.md",
            "",
            GENERATED_MARKER,
            "<!-- Source: .memoryledger; regenerate with `memoryledger render` and `memoryledger export`. -->",
            "",
            "## Directory memory policy",
            "",
            f"This file applies to `{scope_path}` and its subtree.",
            "",
        ]
        by_kind: dict[str, list[tuple[Memory, str]]] = {}
        for memory, content in items:
            by_kind.setdefault(memory.kind, []).append((memory, content))
        for kind in config.render.sort_order:
            if kind not in by_kind:
                continue
            lines += [f"## {ROOT_SECTIONS.get(kind, kind.title())}", ""]
            for memory, content in sorted(
                by_kind[kind], key=lambda item: (item[0].priority, item[0].id)
            ):
                lines.append(_bullet(memory.title, content))
            lines.append("")
        docs[f"{scope_path}/AGENTS.md"] = "\n".join(lines).rstrip() + "\n"
    return docs


def write_rendered(
    config: Config, result: RenderResult, out: Path | None = None
) -> list[Path]:
    written: list[Path] = []
    root_path = out or config.storage_dir / "rendered" / "AGENTS.md"
    root_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(root_path, result.root_text)
    written.append(root_path)
    base = config.storage_dir / "rendered"
    for rel, text in result.linked_docs.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, text)
        written.append(path)
    for rel, text in result.nested_docs.items():
        path = base / "nested" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, text)
        written.append(path)
    return written


def export(
    config: Config,
    result: RenderResult,
    out: Path | None = None,
    backup: bool = False,
    include_nested: bool = False,
) -> list[Path]:
    targets: list[tuple[Path, str]] = [
        (out or config.root / config.render.root_agents_path, result.root_text)
    ]
    targets += [(config.root / rel, text) for rel, text in result.linked_docs.items()]
    if include_nested or config.render.nested_agents_enabled:
        targets += [
            (config.root / rel, text) for rel, text in result.nested_docs.items()
        ]
    written = []
    for path, text in targets:
        safe_to_replace(path)
    for path, text in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        if backup and path.exists():
            shutil.copy2(
                path,
                path.with_suffix(
                    path.suffix + f".{utc_now_iso().replace(':', '')}.bak"
                ),
            )
        atomic_write_text(path, text)
        written.append(path)
    return written
