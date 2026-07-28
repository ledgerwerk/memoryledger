from __future__ import annotations

import json

from .conftest import invoke_ok


def test_status_json(runner, work) -> None:
    invoke_ok(runner, ["init"])
    result = invoke_ok(runner, ["--json", "status"])
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["result"]["memories"] == 0


def test_doctor(runner, work) -> None:
    invoke_ok(runner, ["init"])
    assert "ok" in invoke_ok(runner, ["doctor"]).output
