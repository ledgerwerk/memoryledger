from __future__ import annotations

import hashlib
import re
from html import unescape
from pathlib import Path

from ledgercore.atomic import atomic_write_text

from .models import EvidenceRef
from .run_import import decode_session
from .storage import Store


def import_text(store: Store, text: str, source: str = "import") -> list[str]:
    """Import safe text as candidate memories with source provenance."""
    body = text.strip()
    title = next(
        (line.strip("# ") for line in body.splitlines() if line.strip()),
        "Imported memory",
    )[:80]
    memory = store.create(
        "learning",
        title,
        body,
        "Imported from text.",
        "global",
        "",
        "root_agents",
        source,
    )
    return [memory.id]


def import_run_html(store: Store, path: Path) -> list[str]:
    """Import safe excerpts from a run HTML file as candidates."""
    raw = path.read_text(errors="replace")
    proposals = decode_session(raw)
    if proposals is not None:
        import_key = hashlib.sha256(raw.encode()).hexdigest()[:16]
        existing = {memory.origin: memory for memory in store.all_memories()}
        for proposal in proposals:
            origin = f"run:{import_key}:{proposal.entry_id}"
            if origin in existing:
                continue
            store.validate_new(
                proposal.kind,
                proposal.title,
                proposal.text,
                "Imported from allowlisted structured session data.",
                "global",
                "",
                proposal.render_target,
                "run_html",
                origin=origin,
                origin_hash=hashlib.sha256(proposal.text.encode()).hexdigest(),
                evidence_refs=[
                    EvidenceRef(
                        kind="run",
                        title="Structured run entry",
                        uri=f"run:{proposal.session_id or import_key}#{proposal.entry_id}",
                        timestamp=proposal.timestamp,
                    )
                ],
            )
        ids: list[str] = []
        for proposal in proposals:
            origin = f"run:{import_key}:{proposal.entry_id}"
            if origin in existing:
                ids.append(existing[origin].id)
                continue
            memory = store.create(
                proposal.kind,
                proposal.title,
                proposal.text,
                "Imported from allowlisted structured session data.",
                "global",
                "",
                proposal.render_target,
                "run_html",
                origin=origin,
                origin_hash=hashlib.sha256(proposal.text.encode()).hexdigest(),
                evidence_refs=[
                    EvidenceRef(
                        kind="run",
                        title="Structured run entry",
                        uri=f"run:{proposal.session_id or import_key}#{proposal.entry_id}",
                        timestamp=proposal.timestamp,
                    )
                ],
            )
            ids.append(memory.id)
        return ids
    text = re.sub(r"<[^>]+>", " ", raw)
    text = unescape(re.sub(r"\s+", " ", text)).strip()
    excerpt = text[:2000]
    memory = store.create(
        "episode",
        "Imported run memory",
        excerpt,
        f"Imported from {path.name}.",
        "global",
        "",
        "linked_doc",
        "run_html",
        origin=f"run-legacy:{hashlib.sha256(raw.encode()).hexdigest()}",
        origin_hash=hashlib.sha256(excerpt.encode()).hexdigest(),
    )
    import_id = store.next_import_id()
    idir = store.config.storage_dir / "imports" / import_id
    idir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(idir / "raw_excerpt.md", excerpt + "\n")
    return [memory.id]
