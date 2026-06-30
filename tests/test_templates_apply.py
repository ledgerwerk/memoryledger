from __future__ import annotations

import json
from pathlib import Path

from .conftest import invoke_ok


def _write(work: Path, monkeypatch, content: str, version: str = "1") -> Path:
    xdg = work / "xdg"
    path = xdg / "ledger/memoryledger.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'[[templates]]\nid="base"\nversion="{version}"\ntitle="Base"\n'
        f'kind="rule"\ncontent="{content}"\n'
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return path


def test_apply_idempotent_and_sync_returns_candidate(
    runner, work, monkeypatch
) -> None:
    invoke_ok(runner, ["init"])
    path = _write(work, monkeypatch, "Initial.")
    first = json.loads(
        invoke_ok(runner, ["templates", "apply", "base", "--json"]).output
    )
    assert first == {
        "action": "created",
        "memory_id": "memory-0001",
        "status": "candidate",
    }
    again = json.loads(
        invoke_ok(runner, ["templates", "apply", "base", "--json"]).output
    )
    assert again["action"] == "unchanged"
    path.write_text(
        '[[templates]]\nid="base"\nversion="2"\ntitle="Base"\n'
        'kind="rule"\ncontent="Changed."\n'
    )
    changed = json.loads(
        invoke_ok(runner, ["templates", "sync", "base", "--json"]).output
    )
    assert changed["action"] == "updated"
    assert changed["status"] == "candidate"
