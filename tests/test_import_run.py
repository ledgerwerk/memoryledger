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
    assert "use memoryledger" in shown["content"].lower()
    assert "AGENTS.md directly" in shown["content"]
    assert "Never import" not in shown["content"]


def test_structured_run_prevalidates_all_candidates(runner, work) -> None:
    invoke_ok(runner, ["init"])
    payload = {
        "schema": "memoryledger.session.v1",
        "entries": [
            {
                "id": "one",
                "type": "memory_correction",
                "text": "Use memoryledger to update AGENTS.md.",
            },
            {
                "id": "two",
                "type": "memory_correction",
                "text": "Use memoryledger to update AGENTS.md. password = abcdefghijklmnop",
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


def test_import_real_run_html_extracts_visible_candidates_and_run_evidence(runner, work) -> None:
    invoke_ok(runner, ["init"])
    payload = {
        "header": {"type": "session", "version": 3, "id": "fixture-session"},
        "entries": [
            {"type": "message", "id": "u1", "message": {"role": "user", "content": [{"type": "text", "text": "please use the memoryledger skill to store all the gained knowledge"}]}},
            {"type": "message", "id": "x1", "message": {"role": "assistant", "content": [{"type": "thinking", "text": "hidden thinking memoryledger"}]}},
            {"type": "message", "id": "t1", "message": {"role": "toolResult", "toolName": "bash", "isError": True, "content": [{"type": "text", "text": "error: MANUAL_FILE: Refusing to overwrite manual file: AGENTS.md"}]}},
            {"type": "message", "id": "a1", "message": {"role": "assistant", "content": [{"type": "text", "text": "Created and accepted memories. Backup created by adoption: AGENTS.md.memoryledger-adopt-1.bak"}]}},
            {"type": "message", "id": "raw", "message": {"role": "assistant", "content": [{"type": "text", "text": "Total entries: 173 Assistant messages: 81 Tool result messages: 74"}]}},
        ],
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    path = work / "real.html"
    path.write_text(f'<script id="session-data">{encoded}</script>')
    data = json.loads(invoke_ok(runner, ["import", "run-html", "--file", str(path), "--json"]).output)
    assert data["candidates"] == ["memory-0001", "memory-0002", "memory-0003"]
    shown = json.loads(invoke_ok(runner, ["memory", "show", "memory-0001", "--content", "--json"]).output)
    assert "hidden thinking" not in shown["content"]
    evidence = json.loads(invoke_ok(runner, ["memory", "evidence", "list", "memory-0001", "--json"]).output)
    assert evidence["evidence"][0]["uri"] == "run:fixture-session#u1"
