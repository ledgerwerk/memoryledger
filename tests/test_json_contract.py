from __future__ import annotations

import json

from .conftest import invoke_ok


def test_json_envelopes(runner, work) -> None:
    invoke_ok(runner, ["init"])
    assert json.loads(invoke_ok(runner, ["status", "--json"]).output)["ok"] is True
    invoke_ok(
        runner,
        ["memory", "create", "--kind", "rule", "--title", "R", "--text", "Do it."],
    )
    data = json.loads(invoke_ok(runner, ["memory", "list", "--json"]).output)
    assert data["memories"][0]["id"] == "memory-0001"
