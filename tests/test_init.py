"""Test init: layout creation, idempotency, no overwrite."""

from __future__ import annotations

from pathlib import Path

from memoryledger.config import CONFIG_FILENAME
from memoryledger.store import (
    LEDGER_FILENAME,
    MEMORIES_DIRNAME,
    REQUIRED_MEMORY_SUBDIRS,
    STATE_DIR_NAME,
    STATE_FILENAME,
    init_store,
)


def test_init_creates_full_layout(tmp_path: Path) -> None:
    """init creates config, state dir, subdirs, ledger.jsonl, state.json."""
    init_store(tmp_path, now=None)
    cfg = tmp_path / CONFIG_FILENAME
    state_dir = tmp_path / STATE_DIR_NAME
    memories = state_dir / MEMORIES_DIRNAME
    ledger = state_dir / LEDGER_FILENAME
    state = state_dir / STATE_FILENAME
    assert cfg.exists(), f"config missing: {cfg}"
    assert state_dir.is_dir(), f"state dir missing: {state_dir}"
    assert memories.is_dir(), f"memories dir missing: {memories}"
    for sub in REQUIRED_MEMORY_SUBDIRS:
        assert (memories / sub).is_dir(), f"missing subdir: {sub}"
    assert ledger.exists(), f"ledger.jsonl missing: {ledger}"
    assert state.exists(), f"state.json missing: {state}"
    assert ledger.read_text() == "", "ledger.jsonl should be empty on init"
    import json

    assert json.loads(state.read_text()) == {}, "state.json should be {} on init"


def test_init_does_not_overwrite_existing_config(tmp_path: Path) -> None:
    """init does not overwrite an existing .memoryledger.toml."""
    custom = tmp_path / CONFIG_FILENAME
    custom.write_text(
        '[ledger]\nname = "custom-ledger"\nversion = 1\nstate_dir = ".memoryledger"\n'
    )
    init_store(tmp_path, now=None)
    assert (
        custom.read_text()
        == '[ledger]\nname = "custom-ledger"\nversion = 1\nstate_dir = ".memoryledger"\n'
    )
