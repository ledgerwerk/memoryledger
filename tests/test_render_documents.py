from __future__ import annotations

from pathlib import Path

from .conftest import invoke_ok


def test_linked_document_export(runner, work: Path) -> None:
    invoke_ok(runner, ["init"])
    text = "\n".join(["Step one."] * 120)
    invoke_ok(
        runner,
        [
            "memory",
            "create",
            "--kind",
            "procedure",
            "--title",
            "Workflow",
            "--render-target",
            "linked_doc",
            "--text",
            text,
        ],
    )
    invoke_ok(runner, ["review", "accept", "memory-0001", "--reason", "Approved."])
    invoke_ok(runner, ["export"])
    assert (work / "AGENTS.md").exists()
    doc = work / "agent_docs" / "procedures.md"
    assert doc.exists()
    assert "Workflow" in doc.read_text()
