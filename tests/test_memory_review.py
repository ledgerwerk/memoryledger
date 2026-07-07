from __future__ import annotations

import json

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


def test_review_accept_all_accepts_only_candidates_and_reports_json(
    runner, work
) -> None:
    invoke_ok(runner, ["init"])
    for title in ["One", "Two", "Three"]:
        invoke_ok(
            runner,
            [
                "memory",
                "create",
                "--kind",
                "rule",
                "--title",
                title,
                "--text",
                "Always test.",
            ],
        )
    invoke_ok(runner, ["review", "reject", "memory-0002", "--reason", "No."])
    data = json.loads(
        invoke_ok(
            runner, ["review", "accept", "--all", "--reason", "Yes.", "--json"]
        ).output
    )
    assert data == {"accepted": ["memory-0001", "memory-0003"]}
    listing = invoke_ok(runner, ["memory", "list"]).output
    assert "memory-0001 accepted" in listing
    assert "memory-0002 rejected" in listing
    assert "memory-0003 accepted" in listing


def test_review_reject_all_requires_reason(runner, work) -> None:
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
    result = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app,
        ["review", "reject", "--all"],
    )
    assert result.exit_code != 0
