from __future__ import annotations

from .conftest import invoke_ok


def test_import_text_creates_candidate(runner, work) -> None:
    invoke_ok(runner, ["init"])
    out = invoke_ok(
        runner, ["import", "text", "--text", "A stable project fact."]
    ).output
    assert "memory-0001" in out
    assert "candidate" in invoke_ok(runner, ["memory", "list"]).output
