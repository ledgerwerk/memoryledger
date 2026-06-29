from __future__ import annotations

import re
from html import unescape
from pathlib import Path

from ledgercore.atomic import atomic_write_text

from .storage import Store


def import_text(store: Store, text: str, source: str = "import") -> list[str]:
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
    raw = path.read_text(errors="replace")
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
    )
    import_id = store.next_import_id()
    idir = store.config.storage_dir / "imports" / import_id
    idir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(idir / "raw_excerpt.md", excerpt + "\n")
    return [memory.id]
