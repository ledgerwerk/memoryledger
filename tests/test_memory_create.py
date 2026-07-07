from __future__ import annotations

import json

from .conftest import invoke_ok


def test_memory_create_candidate(runner, work) -> None:
    invoke_ok(runner, ["init"])
    result = invoke_ok(
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
    assert "memory-0001" in result.output
    show = invoke_ok(runner, ["memory", "show", "memory-0001", "--content", "--json"])
    data = json.loads(show.output)
    assert data["status"] == "candidate"
    assert data["content"] == "Always test.\n"


def test_invalid_create_does_not_consume_id(runner, work) -> None:
    invoke_ok(runner, ["init"])
    bad = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app,
        [
            "memory",
            "create",
            "--kind",
            "rule",
            "--title",
            "Bad",
            "--text",
            "password = abcdefghijklmnop",
        ],
    )
    assert bad.exit_code == 1
    result = invoke_ok(
        runner,
        [
            "memory",
            "create",
            "--kind",
            "rule",
            "--title",
            "Good",
            "--text",
            "Safe content.",
        ],
    )
    assert "memory-0001" in result.output


def test_schema_values_json_and_precise_invalid_kind(runner, work) -> None:
    invoke_ok(runner, ["init"])
    data = json.loads(invoke_ok(runner, ["schema", "values", "--json"]).output)
    assert "procedure" in data["kinds"]
    assert "repo" in data["scopes"]
    assert "run" in data["evidence_kinds"]
    result = invoke_ok(
        runner,
        [
            "memory",
            "create",
            "--kind",
            "package-workflow",
            "--scope",
            "project",
            "--title",
            "Alias",
            "--text",
            "Alias works.",
        ],
    )
    assert "memory-0001" in result.output
    data = json.loads(
        invoke_ok(runner, ["memory", "show", "memory-0001", "--json"]).output
    )
    assert data["kind"] == "procedure"
    assert data["scope"] == "repo"
