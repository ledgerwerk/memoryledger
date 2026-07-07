from __future__ import annotations

import json
from pathlib import Path

import yaml

from .conftest import invoke_ok


def test_evidence_add_list_and_version_snapshot(runner, work: Path) -> None:
    invoke_ok(runner, ["init"])
    invoke_ok(
        runner,
        ["memory", "create", "--kind", "rule", "--title", "R", "--text", "Rule."],
    )
    result = invoke_ok(
        runner,
        [
            "memory",
            "evidence",
            "add",
            "memory-0001",
            "--kind",
            "file",
            "--title",
            "Source",
            "--uri",
            "README.md",
            "--line-start",
            "1",
            "--line-end",
            "2",
            "--reason",
            "Attach source.",
            "--json",
        ],
    )
    assert json.loads(result.output) == {"memory_id": "memory-0001", "version": 2}
    listed = json.loads(
        invoke_ok(
            runner, ["memory", "evidence", "list", "memory-0001", "--json"]
        ).output
    )
    assert listed["evidence"][0]["uri"] == "README.md"
    stored = yaml.safe_load(
        (work / ".memoryledger/memories/memory-0001.md").read_text().split("---", 2)[1]
    )
    assert stored["evidence"][0]["kind"] == "file"
    assert stored["modified_version"] == 2
    assert not (work / ".memoryledger/memories/memory-0001/versions").exists()


def test_acceptance_adds_structured_approval(runner, work: Path) -> None:
    invoke_ok(runner, ["init"])
    invoke_ok(
        runner,
        ["memory", "create", "--kind", "rule", "--title", "R", "--text", "Rule."],
    )
    invoke_ok(runner, ["review", "accept", "memory-0001", "--reason", "Approved."])
    data = json.loads(
        invoke_ok(
            runner, ["memory", "evidence", "list", "memory-0001", "--json"]
        ).output
    )
    assert data["evidence"][0]["kind"] == "user_approval"


def test_rendered_evidence_is_markdown_escaped(runner, work: Path) -> None:
    invoke_ok(runner, ["init"])
    config = work / "memoryledger.toml"
    config.write_text(
        config.read_text().replace(
            "include_rejected = false",
            "include_rejected = false\ninclude_evidence = true\n"
            'evidence_index_path = "agent_docs/evidence.md"',
        )
    )
    invoke_ok(
        runner,
        [
            "memory",
            "create",
            "--kind",
            "procedure",
            "--title",
            "P",
            "--text",
            "Procedure.",
            "--render-target",
            "linked_doc",
        ],
    )
    invoke_ok(
        runner,
        [
            "memory",
            "evidence",
            "add",
            "memory-0001",
            "--kind",
            "external",
            "--title",
            "Source [unsafe]",
            "--uri",
            "https://example.test/a_(b)",
            "--reason",
            "Attach.",
        ],
    )
    invoke_ok(runner, ["review", "accept", "memory-0001", "--reason", "Approved."])
    invoke_ok(runner, ["render"])
    text = (work / ".memoryledger/rendered/agent_docs/procedures.md").read_text()
    assert r"Source \[unsafe\]" in text
    assert r"a\_\(b\)" in text


def test_root_render_points_to_evidence_index(runner, work: Path) -> None:
    invoke_ok(runner, ["init"])
    config = work / "memoryledger.toml"
    config.write_text(
        config.read_text().replace(
            "include_rejected = false",
            "include_rejected = false\ninclude_evidence = true\n"
            'evidence_index_path = "agent_docs/evidence.md"',
        )
    )
    invoke_ok(
        runner,
        ["memory", "create", "--kind", "rule", "--title", "R", "--text", "Rule."],
    )
    invoke_ok(
        runner,
        [
            "memory",
            "evidence",
            "add",
            "memory-0001",
            "--kind",
            "file",
            "--title",
            "Source",
            "--uri",
            "README.md",
            "--reason",
            "Attach source.",
        ],
    )
    invoke_ok(runner, ["review", "accept", "memory-0001", "--reason", "Approved."])
    invoke_ok(runner, ["render"])
    root = (work / ".memoryledger/rendered/AGENTS.md").read_text()
    index = (work / ".memoryledger/rendered/agent_docs/evidence.md").read_text()
    assert (
        "<!-- memoryledger:evidence memory-0001 agent_docs/evidence.md#memory-0001 -->"
        in root
    )
    assert '<a id="memory-0001"></a>' in index
