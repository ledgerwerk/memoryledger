from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from ledgercore.atomic import atomic_write_text

from .errors import MemoryledgerError
from .guardrails import safe_to_replace
from .models import GENERATED_MARKER, EvidenceRef
from .render import render_all
from .review import transition
from .storage import Store


@dataclass(frozen=True)
class AdoptionProposal:
    title: str
    content: str
    kind: str
    origin: str
    source_hash: str
    render_target: str = "linked_doc"

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "content": self.content,
            "kind": self.kind,
            "origin": self.origin,
            "source_hash": self.source_hash,
            "render_target": self.render_target,
        }


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def source_headings(text: str) -> list[str]:
    return [
        line.lstrip("# ").strip()
        for line in text.splitlines()
        if re.match(r"^#{1,6}\s+", line) and line.lstrip("# ").strip()
    ]


def parse_markdown(path: Path, root: Path) -> tuple[str, list[AdoptionProposal]]:
    text = path.read_text()
    if GENERATED_MARKER in text:
        raise MemoryledgerError("ALREADY_GENERATED", "target is already generated")
    digest = source_hash(text)
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    title = (
        source_headings(text)[0]
        if source_headings(text)
        else "Original repository guidelines"
    )
    proposals = [
        AdoptionProposal(
            f"Full migrated source: {title}",
            text.rstrip() + "\n",
            "document",
            f"adopt:{rel}:full-source",
            digest,
            "linked_doc",
        )
    ]
    return digest, proposals


def adoption_plan(path: Path, root: Path) -> dict[str, object]:
    text = path.read_text()
    digest, proposals = parse_markdown(path, root)
    root_lines = [line for line in text.splitlines() if line.startswith("#")]
    return {
        "target": str(path),
        "source_hash": digest,
        "headings": source_headings(text),
        "line_count": len(text.splitlines()),
        "word_count": len(text.split()),
        "proposals": [
            p.to_dict() | {"likely_placement": "linked_doc"} for p in proposals
        ],
        "root_expected_to_shrink": bool(root_lines or len(text) > 500),
        "mutated": False,
    }


def adopt(
    store: Store, target: Path, *, backup: bool, accept: bool, reason: str
) -> tuple[list[str], Path]:
    if not backup:
        raise MemoryledgerError(
            "ADOPTION_BACKUP_REQUIRED", "adoption requires --backup"
        )
    initial_hash, proposals = parse_markdown(target, store.config.root)
    existing = {memory.origin: memory for memory in store.all_memories()}
    rel = target.relative_to(store.config.root).as_posix()
    for proposal in proposals:
        old = existing.get(proposal.origin)
        if old and old.origin_hash == proposal.source_hash:
            continue
        store.validate_new(
            proposal.kind,
            proposal.title,
            proposal.content,
            f"Adopted full source from {rel}.",
            "repo",
            "",
            proposal.render_target,
            "adopt",
            origin=proposal.origin,
            origin_hash=proposal.source_hash,
        )
    ids: list[str] = []
    evidence = EvidenceRef(
        kind="file",
        title="Original manual agent file",
        uri=rel,
        content_hash=initial_hash,
    )
    for proposal in proposals:
        old = existing.get(proposal.origin)
        if old and old.origin_hash == proposal.source_hash:
            ids.append(old.id)
            continue
        memory = store.create(
            proposal.kind,
            proposal.title,
            proposal.content,
            f"Adopted full source from {rel}.",
            "repo",
            "",
            proposal.render_target,
            "adopt",
            origin=proposal.origin,
            origin_hash=proposal.source_hash,
            evidence_refs=[evidence],
        )
        ids.append(memory.id)
        if accept:
            transition(store, memory.id, "accepted", reason)
    result = render_all(store.config)
    if source_hash(target.read_text()) != initial_hash:
        raise MemoryledgerError("ADOPTION_SOURCE_CHANGED", "manual target changed")
    extra_targets = [
        (store.config.root / rel, text) for rel, text in result.linked_docs.items()
    ]
    if store.config.render.nested_agents_enabled:
        extra_targets.extend(
            (store.config.root / rel, text) for rel, text in result.nested_docs.items()
        )
    for path, _text in extra_targets:
        safe_to_replace(path)
    backup_path = _backup_path(target)
    shutil.copy2(target, backup_path)
    try:
        atomic_write_text(target, result.root_text)
        for path, text in extra_targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(path, text)
    except Exception:
        if source_hash(backup_path.read_text()) == initial_hash:
            shutil.copy2(backup_path, target)
        raise
    return ids, backup_path


def verify_adoption(store: Store, source: Path) -> dict[str, object]:
    text = source.read_text()
    digest = source_hash(text)
    memories = [
        m
        for m in store.all_memories()
        if m.origin_hash == digest and m.kind == "document"
    ]
    represented = any(
        any(ref.content_hash == digest for ref in m.evidence_refs)
        or m.origin_hash == digest
        for m in memories
    )
    result = render_all(store.config)
    generated = {
        store.config.render.root_agents_path: result.root_text,
        **result.linked_docs,
        **result.nested_docs,
    }
    full_reachable = False
    root = result.root_text
    for rel, doc in result.linked_docs.items():
        if rel in root and text.strip() in doc:
            full_reachable = True
            break
    headings = source_headings(text)
    all_generated = "\n".join(generated.values())
    missing_headings = [h for h in headings if h not in all_generated]
    ok = represented and full_reachable
    return {
        "ok": ok,
        "source_hash": digest,
        "represented": represented,
        "full_document_reachable": full_reachable,
        "headings": headings,
        "missing_headings": missing_headings,
    }


def _backup_path(target: Path) -> Path:
    number = 1
    while True:
        candidate = target.with_name(f"{target.name}.memoryledger-adopt-{number}.bak")
        if not candidate.exists():
            return candidate
        number += 1
