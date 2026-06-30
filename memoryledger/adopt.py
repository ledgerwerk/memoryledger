from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from ledgercore.atomic import atomic_write_text

from .errors import MemoryledgerError
from .models import GENERATED_MARKER
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

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "content": self.content,
            "kind": self.kind,
            "origin": self.origin,
            "source_hash": self.source_hash,
        }


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def parse_markdown(path: Path, root: Path) -> tuple[str, list[AdoptionProposal]]:
    text = path.read_text()
    if GENERATED_MARKER in text:
        raise MemoryledgerError("ALREADY_GENERATED", "target is already generated")
    digest = source_hash(text)
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    proposals: list[AdoptionProposal] = []
    heading = "Imported agent document"
    body: list[str] = []
    index = 0

    def flush() -> None:
        nonlocal index, body
        content = "\n".join(body).strip()
        if not content:
            body = []
            return
        index += 1
        proposals.append(
            AdoptionProposal(
                heading,
                content,
                "document",
                f"adopt:{rel}:{index}",
                digest,
            )
        )
        body = []

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            heading = line[3:].strip() or "Imported section"
        elif not line.startswith("# "):
            body.append(line)
    flush()
    if not proposals:
        raise MemoryledgerError("EMPTY_CONTENT", "manual target has no importable content")
    return digest, proposals


def adopt(
    store: Store,
    target: Path,
    *,
    backup: bool,
    accept: bool,
    reason: str,
) -> tuple[list[str], Path]:
    if not backup:
        raise MemoryledgerError("ADOPTION_BACKUP_REQUIRED", "adoption requires --backup")
    initial_hash, proposals = parse_markdown(target, store.config.root)
    existing = {memory.origin: memory for memory in store.all_memories()}
    for proposal in proposals:
        old = existing.get(proposal.origin)
        if old and old.origin_hash == proposal.source_hash:
            continue
        store.validate_new(
            proposal.kind,
            proposal.title,
            proposal.content,
            f"Adopted from {target.relative_to(store.config.root)}.",
            "repo",
            "",
            "root_agents",
            "adopt",
            origin=proposal.origin,
            origin_hash=proposal.source_hash,
        )
    ids: list[str] = []
    for proposal in proposals:
        old = existing.get(proposal.origin)
        if old and old.origin_hash == proposal.source_hash:
            ids.append(old.id)
            continue
        memory = store.create(
            proposal.kind,
            proposal.title,
            proposal.content,
            f"Adopted from {target.relative_to(store.config.root)}.",
            "repo",
            "",
            "root_agents",
            "adopt",
            origin=proposal.origin,
            origin_hash=proposal.source_hash,
        )
        ids.append(memory.id)
        if accept:
            transition(store, memory.id, "accepted", reason)
    result = render_all(store.config)
    if source_hash(target.read_text()) != initial_hash:
        raise MemoryledgerError("ADOPTION_SOURCE_CHANGED", "manual target changed")
    backup_path = _backup_path(target)
    shutil.copy2(target, backup_path)
    try:
        atomic_write_text(target, result.root_text)
    except Exception:
        if source_hash(backup_path.read_text()) == initial_hash:
            shutil.copy2(backup_path, target)
        raise
    return ids, backup_path


def _backup_path(target: Path) -> Path:
    number = 1
    while True:
        candidate = target.with_name(f"{target.name}.memoryledger-adopt-{number}.bak")
        if not candidate.exists():
            return candidate
        number += 1
