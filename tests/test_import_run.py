from __future__ import annotations

import base64
import json
from pathlib import Path

from .conftest import invoke_ok


def test_import_run_html_and_current_run(runner, work: Path) -> None:
    html = work / "run.html"
    html.write_text("<html><body>Durable lesson</body></html>")
    invoke_ok(runner, ["init"])
    assert (
        "memory-0001"
        in invoke_ok(runner, ["import", "run-html", "--file", str(html)]).output
    )
    current = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app, ["import", "current-run"]
    )
    assert current.exit_code == 2
    assert "not supported" in current.output


def test_structured_run_import_is_allowlisted_and_idempotent(runner, work) -> None:
    invoke_ok(runner, ["init"])
    fixture = Path(__file__).parent / "fixtures/run_session.html"
    first = json.loads(
        invoke_ok(
            runner,
            ["import", "run-html", "--file", str(fixture), "--json"],
        ).output
    )
    assert first["candidates"] == ["memory-0001"]
    second = json.loads(
        invoke_ok(
            runner,
            ["import", "run-html", "--file", str(fixture), "--json"],
        ).output
    )
    assert second["candidates"] == ["memory-0001"]
    shown = json.loads(
        invoke_ok(
            runner, ["memory", "show", "memory-0001", "--content", "--json"]
        ).output
    )
    assert "Remember to run" in shown["content"]
    assert "Never import" not in shown["content"]


def test_structured_run_prevalidates_all_candidates(runner, work) -> None:
    invoke_ok(runner, ["init"])
    payload = {
        "schema": "memoryledger.session.v1",
        "entries": [
            {"id": "one", "type": "user_message", "text": "Safe lesson."},
            {
                "id": "two",
                "type": "user_message",
                "text": "password = abcdefghijklmnop",
            },
        ],
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    path = work / "structured.html"
    path.write_text(f'<script id="session-data">{encoded}</script>')
    result = runner.invoke(
        __import__("memoryledger.cli", fromlist=["app"]).app,
        ["import", "run-html", "--file", str(path)],
    )
    assert result.exit_code == 1
    assert not list((work / ".memoryledger/memories").iterdir())
