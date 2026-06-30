from __future__ import annotations

import json
from pathlib import Path

from .conftest import invoke_ok


def _global(monkeypatch, work: Path, text: str) -> Path:
    xdg = work / "xdg"
    path = xdg / "ledger/memoryledger.toml"
    path.parent.mkdir(parents=True)
    path.write_text(text)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return path


def test_template_listing_without_project(runner, work, monkeypatch) -> None:
    _global(
        monkeypatch,
        work,
        '[[templates]]\nid="base"\nversion="1"\ntitle="Base"\ncontent="Test."\n',
    )
    data = json.loads(invoke_ok(runner, ["templates", "list", "--json"]).output)
    assert data["templates"][0]["id"] == "base"


def test_template_content_file_cannot_escape(runner, work, monkeypatch) -> None:
    _global(
        monkeypatch,
        work,
        '[[templates]]\nid="bad"\nversion="1"\ntitle="Bad"\ncontent_file="../x"\n',
    )
    result = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app,
        ["templates", "show", "bad"],
    )
    assert result.exit_code == 1
    assert "INVALID_TEMPLATE_PATH" in result.output
