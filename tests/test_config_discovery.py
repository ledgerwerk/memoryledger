from __future__ import annotations

from pathlib import Path

from .conftest import invoke_ok


def test_config_discovery_from_child(runner, work: Path, monkeypatch) -> None:
    invoke_ok(runner, ["init"])
    child = work / "a" / "b"
    child.mkdir(parents=True)
    monkeypatch.chdir(child)
    assert "config:" in invoke_ok(runner, ["status"]).output
