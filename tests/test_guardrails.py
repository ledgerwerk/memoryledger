from __future__ import annotations

from .conftest import invoke_ok


def test_reject_secret_and_bad_scope(runner, work) -> None:
    invoke_ok(runner, ["init"])
    secret = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app,
        [
            "memory",
            "create",
            "--kind",
            "rule",
            "--title",
            "S",
            "--text",
            "password = abcdefghijklmnop",
        ],
    )
    assert secret.exit_code == 1
    scope = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app,
        [
            "memory",
            "create",
            "--kind",
            "rule",
            "--title",
            "S",
            "--scope-path",
            "../x",
            "--text",
            "Safe text.",
        ],
    )
    assert scope.exit_code == 1


def test_manual_root_protected(runner, work) -> None:
    invoke_ok(runner, ["init"])
    (work / "AGENTS.md").write_text("manual")
    invoke_ok(
        runner,
        ["memory", "create", "--kind", "rule", "--title", "R", "--text", "Do it."],
    )
    invoke_ok(runner, ["review", "accept", "memory-0001", "--reason", "Approved."])
    result = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app, ["export"]
    )
    assert result.exit_code == 1
    assert "MANUAL_FILE" in result.output
