"""Test discovery: upward walk for .memoryledger.toml only."""

from __future__ import annotations

from pathlib import Path

import pytest

from memoryledger.config import CONFIG_FILENAME, find_project
from memoryledger.errors import ConfigError
from memoryledger.store import init_store


def test_discovery_from_nested_dir(tmp_path: Path) -> None:
    """Discovery walks upward from nested subdirectories to find config."""
    init_store(tmp_path, now=None)
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    proj = find_project(nested)
    assert proj.config_path == tmp_path / CONFIG_FILENAME
    assert proj.workspace_root == tmp_path


def test_discovery_ignores_taskledger_config(tmp_path: Path) -> None:
    """Discovery fails if only .taskledger.toml exists."""
    (tmp_path / ".taskledger.toml").write_text("[ledger]\nname = 'taskledger'\n")
    nested = tmp_path / "sub"
    nested.mkdir()
    with pytest.raises(ConfigError, match="No .memoryledger.toml found"):
        find_project(nested)


def test_discovery_ignores_archledger_config(tmp_path: Path) -> None:
    """Discovery fails if only .archledger.toml exists."""
    (tmp_path / ".archledger.toml").write_text("[ledger]\nname = 'archledger'\n")
    nested = tmp_path / "sub"
    nested.mkdir()
    with pytest.raises(ConfigError, match="No .memoryledger.toml found"):
        find_project(nested)


def test_discovery_finds_own_config_among_others(tmp_path: Path) -> None:
    """Finds .memoryledger.toml even when other ledger configs coexist."""
    (tmp_path / ".taskledger.toml").write_text("[ledger]\nname = 'taskledger'\n")
    (tmp_path / ".archledger.toml").write_text("[ledger]\nname = 'archledger'\n")
    init_store(tmp_path, now=None)
    nested = tmp_path / "x" / "y"
    nested.mkdir(parents=True)
    proj = find_project(nested)
    assert proj.config_path.name == CONFIG_FILENAME
