"""Test context: bounded Markdown bundle rendering."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from memoryledger.model import MemoryStatus, MemoryType
from memoryledger.retrieval import render_context_from_query
from memoryledger.store import init_store

FIXED_NOW = datetime(2026, 6, 13, 10, 0, tzinfo=timezone(timedelta(hours=2)))


def _seed_accepted_memories(tmp_path: Path):
    store = init_store(tmp_path, now=FIXED_NOW)
    mem1 = store.capture_memory(
        memory_type=MemoryType.procedural,
        title="Testing command",
        body="Run `uv run pytest` after modifying Python logic.",
    )
    mem2 = store.capture_memory(
        memory_type=MemoryType.semantic,
        title="Ledger config discovery",
        body="Each ledger discovers its own .memoryledger.toml by walking upward from cwd.",
    )
    store.set_status(
        mem1.id, MemoryStatus.accepted, event_type="memory.accepted", actor="user"
    )
    store.set_status(
        mem2.id, MemoryStatus.accepted, event_type="memory.accepted", actor="user"
    )
    return store


def test_context_renders_bounded_markdown_bundle(tmp_path: Path) -> None:
    """context renders a bounded Markdown bundle with numbered headings."""
    store = _seed_accepted_memories(tmp_path)
    cfg = store.config.retrieval
    text = render_context_from_query(
        list(store.iter_memories()),
        "pytest",
        retrieval=cfg,
    )
    assert "# Retrieved project memory" in text
    assert "## 1. Testing command" in text
    assert "Run `uv run pytest`" in text


def test_context_excludes_local_by_default(tmp_path: Path) -> None:
    """context excludes local memories unless configured/flagged."""
    store = init_store(tmp_path, now=FIXED_NOW)
    store.capture_memory(
        memory_type=MemoryType.local,
        title="Local secret",
        body="Hidden local note.",
    )
    accepted = store.capture_memory(
        memory_type=MemoryType.semantic,
        title="Public fact",
        body="Public note.",
    )
    store.set_status(
        accepted.id, MemoryStatus.accepted, event_type="memory.accepted", actor="user"
    )
    cfg = store.config.retrieval
    text = render_context_from_query(
        list(store.iter_memories()),
        "note",
        retrieval=cfg,
    )
    assert "Public fact" in text
    assert "Local secret" not in text


def test_context_honors_max_context_lines(tmp_path: Path) -> None:
    """context truncates output to max_context_lines."""
    store = init_store(tmp_path, now=FIXED_NOW)
    # Create a long body.
    long_body = "\n".join(
        f"Line {i} of content for testing truncation." for i in range(500)
    )
    mem = store.capture_memory(
        memory_type=MemoryType.semantic,
        title="Long memory",
        body=long_body,
    )
    store.set_status(
        mem.id, MemoryStatus.accepted, event_type="memory.accepted", actor="user"
    )
    # Override limit to something small for testing.
    from memoryledger.config import RetrievalSection

    tight = RetrievalSection(default_limit=1, max_context_lines=10)
    text = render_context_from_query(
        list(store.iter_memories()), "content", retrieval=tight
    )
    actual_lines = text.splitlines()
    assert len(actual_lines) <= 10, f"got {len(actual_lines)} lines, expected <= 10"


def test_context_empty_when_no_matches(tmp_path: Path) -> None:
    """context renders a 'no matching' message when nothing matches."""
    store = _seed_accepted_memories(tmp_path)
    cfg = store.config.retrieval
    text = render_context_from_query(
        list(store.iter_memories()),
        "zzzznonexistentzzzz",
        retrieval=cfg,
    )
    assert "No matching accepted memory" in text
