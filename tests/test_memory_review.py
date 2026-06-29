from __future__ import annotations

from .conftest import invoke_ok


def test_accept_and_reject(runner, work) -> None:
    invoke_ok(runner, ["init"])
    invoke_ok(
        runner,
        [
            "memory",
            "create",
            "--kind",
            "rule",
            "--title",
            "Rule",
            "--text",
            "Always test.",
        ],
    )
    invoke_ok(runner, ["review", "accept", "memory-0001", "--reason", "User approved."])
    assert "accepted" in invoke_ok(runner, ["memory", "list"]).output
    invoke_ok(
        runner, ["review", "reject", "memory-0001", "--reason", "No longer wanted."]
    )
    assert "rejected" in invoke_ok(runner, ["memory", "list"]).output
