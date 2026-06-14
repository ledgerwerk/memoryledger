"""Test accept and reject: status change + event append."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from memoryledger.model import MemoryStatus, MemoryType
from memoryledger.store import init_store

FIXED_NOW = datetime(2026, 6, 13, 10, 0, tzinfo=timezone(timedelta(hours=2)))


def _make_store_with_memory(tmp_path: Path):
    store = init_store(tmp_path, now=FIXED_NOW)
    mem = store.capture_memory(
        memory_type=MemoryType.procedural,
        title="Test memory",
        body="Some body.",
    )
    return store, mem


def test_accept_changes_status_and_appends_event(tmp_path: Path) -> None:
    """accept changes status to accepted (and updated_at) + appends memory.accepted."""
    store, mem = _make_store_with_memory(tmp_path)
    result = store.set_status(
        mem.id,
        MemoryStatus.accepted,
        event_type="memory.accepted",
        actor="user",
    )
    assert result.status == MemoryStatus.accepted
    # Reload from disk.
    reloaded = store.load_memory(mem.id)
    assert reloaded.status == MemoryStatus.accepted

    events = store.read_events()
    types = [e["type"] for e in events]
    assert "memory.accepted" in types
    accepted_event = [e for e in events if e["type"] == "memory.accepted"][0]
    assert accepted_event["memory_id"] == mem.id
    assert accepted_event["actor"] == "user"


def test_reject_changes_status_and_appends_event(tmp_path: Path) -> None:
    """reject changes status to rejected + appends memory.rejected."""
    store, mem = _make_store_with_memory(tmp_path)
    result = store.set_status(
        mem.id,
        MemoryStatus.rejected,
        event_type="memory.rejected",
        actor="user",
    )
    assert result.status == MemoryStatus.rejected
    reloaded = store.load_memory(mem.id)
    assert reloaded.status == MemoryStatus.rejected

    events = store.read_events()
    types = [e["type"] for e in events]
    assert "memory.rejected" in types
    rejected_event = [e for e in events if e["type"] == "memory.rejected"][0]
    assert rejected_event["memory_id"] == mem.id
