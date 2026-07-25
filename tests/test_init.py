from __future__ import annotations

from pathlib import Path

from .conftest import invoke_ok


def test_init_creates_config_and_storage(runner, work: Path) -> None:
    invoke_ok(runner, ["init"])
    assert (work / ".ledger/ledger.toml").exists()
    assert (work / ".ledger/memoryledger/config.toml").exists()
    assert (work / ".ledger/memoryledger/data/storage.yaml").exists()
    assert not (work / "memoryledger.toml").exists()


def test_hidden_init(runner, work: Path) -> None:
    result = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app,
        ["init", "--hidden-config"],
    )
    assert result.exit_code == 1
    assert not (work / ".memoryledger.toml").exists()
