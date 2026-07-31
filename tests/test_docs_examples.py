from __future__ import annotations

import json
from pathlib import Path

from memoryledger.storage import default_config_text


def test_quickstart_and_storage_examples(runner, work: Path) -> None:
    assert runner.invoke(__import__("memoryledger.cli", fromlist=["app"]).app, ["init"]).exit_code == 0
    created = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app,
        ["memory", "create", "--kind", "rule", "--title", "Use plans", "--stdin"],
        input="Always plan.\n",
    )
    assert created.exit_code == 0, created.output
    accepted = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app,
        ["review", "accept", "memory-0001", "--reason", "User approved."],
    )
    assert accepted.exit_code == 0, accepted.output
    for command in (["preview"], ["build"], ["export"], ["storage", "where"], ["storage", "validate"]):
        result = runner.invoke(__import__("memoryledger.cli", fromlist=["app"]).app, command)
        assert result.exit_code == 0, f"{command}: {result.output}"
    status = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app,
        ["--json", "status"],
    )
    assert status.exit_code == 0, status.output
    assert json.loads(status.output)["result"]["memories"] == 1


def test_adoption_preview_and_migration_plan(runner, work: Path, monkeypatch) -> None:
    source = work / "AGENTS.md"
    source.write_text("# Local rules\n\nKeep tests focused.\n", encoding="utf-8")
    app = __import__("memoryledger.cli", fromlist=["app"]).app
    assert runner.invoke(app, ["init"]).exit_code == 0
    adoption = runner.invoke(app, ["agents", "adopt", "AGENTS.md", "--json"])
    assert adoption.exit_code == 0, adoption.output
    assert json.loads(adoption.output)["proposals"]
    legacy = work / "legacy"
    legacy.mkdir()
    monkeypatch.chdir(legacy)
    (legacy / "memoryledger.toml").write_text(
        default_config_text("legacy", ".memoryledger"),
        encoding="utf-8",
    )
    migration = runner.invoke(app, ["migrate", "plan", "storage-layout", "--output", "plan.toml"])
    assert migration.exit_code == 0, migration.output
    assert (legacy / "plan.toml").exists()
