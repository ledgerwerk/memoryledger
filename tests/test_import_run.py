from __future__ import annotations

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
