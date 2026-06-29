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
