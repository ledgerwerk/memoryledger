"""Test capture: candidate creation, front matter, proposed event."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from memoryledger.model import MemoryStatus, MemoryType
from memoryledger.store import init_store

FIXED_NOW = datetime(2026, 6, 13, 10, 0, tzinfo=timezone(timedelta(hours=2)))


def test_capture_creates_candidate_with_valid_front_matter(tmp_path: Path) -> None:
    """capture creates a candidate Markdown file with valid ordered front matter."""
    store = init_store(tmp_path, now=FIXED_NOW)
    mem = store.capture_memory(
        memory_type=MemoryType.procedural,
        title="Ledger discovery rule",
        body="When a ledger tool starts, it must discover its own .memoryledger.toml.",
    )
    assert mem.id.startswith("mem-20260613-")
    assert mem.status == MemoryStatus.candidate

    path = store.memory_path(mem)
    assert path.exists(), f"memory file missing: {path}"
    text = path.read_text(encoding="utf-8")
    # Front matter keys appear in deterministic order.
    assert text.startswith("---\nid: mem-")
    # Required fields present.
    for field in (
        "id",
        "type",
        "scope",
        "status",
        "confidence",
        "created_at",
        "updated_at",
    ):
        assert f"\n{field}:" in text, f"missing field {field} in front matter"
    # Title preserved in body as H1.
    assert "\n# Ledger discovery rule\n" in text


def test_capture_appends_proposed_event(tmp_path: Path) -> None:
    """capture appends a memory.proposed event to the JSONL log."""
    store = init_store(tmp_path, now=FIXED_NOW)
    store.capture_memory(
        memory_type=MemoryType.semantic,
        title="Test fact",
        body="Fact body.",
        tags=["testing"],
    )
    events = store.read_events()
    proposed = [e for e in events if e["type"] == "memory.proposed"]
    assert len(proposed) == 1
    assert proposed[0]["memory_id"].startswith("mem-")
    assert proposed[0]["payload"]["title"] == "Test fact"
    assert proposed[0]["payload"]["memory_type"] == "semantic"


def test_capture_candidate_gating(tmp_path: Path) -> None:
    """Rules and project memories always start as candidate, never accepted."""
    store = init_store(tmp_path, now=FIXED_NOW)
    for mtype in (MemoryType.rule, MemoryType.procedural, MemoryType.semantic):
        mem = store.capture_memory(
            memory_type=mtype,
            title=f"Test {mtype.value}",
            body="body",
        )
        assert mem.status == MemoryStatus.candidate, (
            f"{mtype.value} must start as candidate, got {mem.status}"
        )
