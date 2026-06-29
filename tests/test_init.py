from __future__ import annotations

from pathlib import Path

from .conftest import invoke_ok


def test_init_creates_config_and_storage(runner, work: Path) -> None:
    invoke_ok(runner, ["init"])
    assert (work / "memoryledger.toml").exists()
    assert (work / ".memoryledger" / "storage.yaml").exists()


def test_hidden_init(runner, work: Path) -> None:
    invoke_ok(runner, ["init", "--hidden-config"])
    assert (work / ".memoryledger.toml").exists()
