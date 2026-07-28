from __future__ import annotations

from pathlib import Path

from .conftest import invoke_ok


def test_nested_export(runner, work: Path) -> None:
    invoke_ok(runner, ["init"])
    (work / "packages" / "foo").mkdir(parents=True)
    invoke_ok(
        runner,
        [
            "memory",
            "create",
            "--kind",
            "rule",
            "--title",
            "Pkg",
            "--scope",
            "directory",
            "--scope-path",
            "packages/foo",
            "--render-target",
            "nested_agents",
            "--text",
            "Run package tests.",
        ],
    )
    invoke_ok(runner, ["review", "accept", "memory-0001", "--reason", "Approved."])
    invoke_ok(runner, ["export", "--include-nested"])
    nested = work / "packages" / "foo" / "AGENTS.md"
    assert nested.exists()
    assert "Run package tests" in nested.read_text()


def test_manual_nested_protected(runner, work: Path) -> None:
    invoke_ok(runner, ["init"])
    (work / "packages" / "foo").mkdir(parents=True)
    (work / "packages" / "foo" / "AGENTS.md").write_text("manual")
    invoke_ok(
        runner,
        [
            "memory",
            "create",
            "--kind",
            "rule",
            "--title",
            "Pkg",
            "--scope",
            "directory",
            "--scope-path",
            "packages/foo",
            "--render-target",
            "nested_agents",
            "--text",
            "Run package tests.",
        ],
    )
    invoke_ok(runner, ["review", "accept", "memory-0001", "--reason", "Approved."])
    result = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app,
        ["export", "--include-nested"],
    )
    assert result.exit_code == 4
    assert "manual_file" in result.output
