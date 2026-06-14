"""Test search: deterministic ordering, scoring, exclusion rules."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from memoryledger.model import MemoryStatus, MemoryType
from memoryledger.retrieval import score_memory, search, tokenize
from memoryledger.store import init_store

FIXED_NOW = datetime(2026, 6, 13, 10, 0, tzinfo=timezone(timedelta(hours=2)))


def _seed_memories(tmp_path: Path):
    """Seed a project with several memories of varying types/statuses."""
    store = init_store(tmp_path, now=FIXED_NOW)
    mem1 = store.capture_memory(
        memory_type=MemoryType.procedural,
        title="Testing command",
        body="Run `uv run pytest` after modifying Python logic.",
    )
    mem2 = store.capture_memory(
        memory_type=MemoryType.semantic,
        title="Ledger config discovery",
        body="Each ledger discovers its own .memoryledger.toml by walking upward.",
    )
    mem3 = store.capture_memory(
        memory_type=MemoryType.rule,
        title="Coding style",
        body="Use ruff for linting.",
        tags=["style", "linting"],
    )
    # mem4 is local — hidden by default.
    store.capture_memory(
        memory_type=MemoryType.local,
        title="Local note",
        body="Local machine secret note.",
    )
    # mem5 starts rejected — hidden by default.
    mem5 = store.capture_memory(
        memory_type=MemoryType.learning,
        title="Old lesson",
        body="Old debugging lesson.",
    )
    store.set_status(
        mem5.id, MemoryStatus.rejected, event_type="memory.rejected", actor="user"
    )
    # Accept mem1, mem2, mem3.
    store.set_status(
        mem1.id, MemoryStatus.accepted, event_type="memory.accepted", actor="user"
    )
    store.set_status(
        mem2.id, MemoryStatus.accepted, event_type="memory.accepted", actor="user"
    )
    store.set_status(
        mem3.id, MemoryStatus.accepted, event_type="memory.accepted", actor="user"
    )
    return store


def test_search_returns_deterministic_matches(tmp_path: Path) -> None:
    """search returns title/tag/body matches in deterministic score order."""
    store = _seed_memories(tmp_path)
    memories = list(store.iter_memories())
    results = search(memories, "pytest")
    assert len(results) >= 1
    # The procedural "Testing command" should be top: title match (5) + body match (1)
    # + accepted boost (10) + procedural type boost (3) = 19.
    top = results[0]
    assert "Testing command" in top.memory.title
    assert top.score > 0


def test_search_excludes_rejected_by_default(tmp_path: Path) -> None:
    """search excludes rejected memories by default."""
    store = _seed_memories(tmp_path)
    memories = list(store.iter_memories())
    results = search(memories, "lesson")
    [r.memory.id for r in results]
    # "Old lesson" is rejected — should not appear.
    for r in results:
        assert r.memory.status != MemoryStatus.rejected


def test_search_excludes_local_by_default(tmp_path: Path) -> None:
    """search excludes local memories unless --include-local is set."""
    store = _seed_memories(tmp_path)
    memories = list(store.iter_memories())
    results = search(memories, "secret")
    # Local memories hidden.
    for r in results:
        assert r.memory.type != MemoryType.local

    # With include_local (also include_candidates since local mem is candidate).
    results_local = search(
        memories, "secret", include_local=True, include_candidates=True
    )
    local_found = any(r.memory.type == MemoryType.local for r in results_local)
    assert local_found, "local memory should appear with include_local=True"


def test_search_candidates_excluded_by_default(tmp_path: Path) -> None:
    """search excludes candidates by default (accepted only)."""
    store = _seed_memories(tmp_path)
    # Capture an extra candidate (never accepted).
    store.capture_memory(
        memory_type=MemoryType.semantic,
        title="Candidate memory",
        body="Still a candidate.",
    )
    memories = list(store.iter_memories())
    results = search(memories, "candidate", include_candidates=False)
    for r in results:
        assert r.memory.status == MemoryStatus.accepted

    results_incl = search(memories, "candidate", include_candidates=True)
    cand = [r for r in results_incl if r.memory.status == MemoryStatus.candidate]
    assert len(cand) >= 1


def test_search_score_formula(tmp_path: Path) -> None:
    """score = 5*title + 3*tag + 1*body + status_boost + type_boost."""
    store = init_store(tmp_path, now=FIXED_NOW)
    mem = store.capture_memory(
        memory_type=MemoryType.rule,
        title="pytest style guide",
        body="Run pytest with verbose output.",
        tags=["pytest", "testing"],
    )
    store.set_status(
        mem.id, MemoryStatus.accepted, event_type="memory.accepted", actor="user"
    )
    mem = store.load_memory(mem.id)

    tokens = tokenize("pytest")
    scored = score_memory(mem, tokens)
    # title has "pytest": 5*1, tags has "pytest": 3*1, body has "pytest": 1*1
    # status=accepted: 10, type=rule: 4 => total 23.
    assert scored.title_matches == 1
    assert scored.tag_matches == 1
    assert scored.body_matches == 1
    assert scored.score == 5 + 3 + 1 + 10 + 4
