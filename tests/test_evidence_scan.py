from __future__ import annotations

import json

from .conftest import invoke_ok


def test_scan_preview_and_candidate_deduplication(runner, work) -> None:
    invoke_ok(runner, ["init"])
    (work / "pyproject.toml").write_text(
        '[project]\nname = "example"\nrequires-python = ">=3.10"\n'
    )
    preview = json.loads(
        invoke_ok(runner, ["evidence", "scan", "--json"]).output
    )
    assert preview["proposals"][0]["fact_key"] == "requires-python"
    assert preview["applied"] == []
    first = json.loads(
        invoke_ok(
            runner, ["evidence", "scan", "--apply-candidates", "--json"]
        ).output
    )
    assert first["applied"][0]["action"] == "created"
    second = json.loads(
        invoke_ok(
            runner, ["evidence", "scan", "--apply-candidates", "--json"]
        ).output
    )
    assert second["applied"][0]["action"] == "unchanged"
