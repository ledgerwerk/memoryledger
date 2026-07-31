from __future__ import annotations

import json

from typer.main import get_command

from memoryledger.cli import app
from memoryledger.command_catalog import CATALOG


def _registered_paths() -> tuple[set[str], set[str]]:
    root = get_command(app)
    visible: set[str] = set()
    all_paths: set[str] = set()

    def walk(command, prefix: tuple[str, ...] = (), hidden_parent: bool = False) -> None:
        hidden = hidden_parent or bool(getattr(command, "hidden", False))
        children = getattr(command, "commands", None)
        if children is not None:
            for name, child in children.items():
                walk(child, prefix + (name,), hidden)
            return
        path = " ".join(prefix)
        all_paths.add(path)
        if not hidden:
            visible.add(path)

    walk(root)
    return visible, all_paths


def test_catalog_matches_visible_and_registered_commands() -> None:
    visible, registered = _registered_paths()
    entries = list(CATALOG.entries)
    paths = [entry.path for entry in entries]

    assert len(paths) == len(set(paths))
    assert visible <= set(paths)
    assert set(paths) <= registered
    assert all(entry.summary.strip() for entry in entries)
    assert all(not entry.deprecated or entry.replacement for entry in entries)

    canonical = {entry.path for entry in entries if not entry.deprecated}
    aliases = {
        alias
        for entry in entries
        for alias in entry.aliases
    }
    assert not canonical & aliases
    assert not aliases & set(paths)


def test_every_visible_command_has_non_empty_help() -> None:
    root = get_command(app)

    def walk(command, hidden_parent: bool = False):
        hidden = hidden_parent or bool(getattr(command, "hidden", False))
        children = getattr(command, "commands", None)
        if children is not None:
            for child in children.values():
                yield from walk(child, hidden)
        elif not hidden:
            yield command

    assert all((command.help or "").strip() for command in walk(root))


def test_commands_json_uses_ledgerwerk_envelope_and_catalog_entries(runner) -> None:
    result = runner.invoke(app, ["--json", "commands"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "ledgerwerk.cli.v1"
    assert payload["ok"] is True
    documented = payload["result"]["commands"]
    assert [item["path"] for item in documented] == [entry.path for entry in CATALOG.entries]
    assert len({item["path"] for item in documented}) == len(documented)

