from __future__ import annotations

import json

from .conftest import invoke_ok


def test_json_envelopes(runner, work) -> None:
    invoke_ok(runner, ["init"])
    data = json.loads(invoke_ok(runner, ["--json", "status"]).output)
    assert data["ok"] is True
    assert data["result"]["memories"] == 0
    invoke_ok(
        runner,
        ["memory", "create", "--kind", "rule", "--title", "R", "--text", "Do it."],
    )
    data = json.loads(invoke_ok(runner, ["memory", "list", "--json"]).output)
    assert data["memories"][0]["id"] == "memory-0001"
