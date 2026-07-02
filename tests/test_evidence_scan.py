from __future__ import annotations

import json

from .conftest import invoke_ok


def test_scan_preview_and_candidate_deduplication(runner, work) -> None:
    invoke_ok(runner, ["init"])
    (work / "pyproject.toml").write_text(
        '[project]\nname = "example"\nrequires-python = ">=3.10"\n'
    )
    preview = json.loads(invoke_ok(runner, ["evidence", "scan", "--json"]).output)
    assert preview["proposals"][0]["fact_key"] == "requires-python"
    assert preview["applied"] == []
    first = json.loads(
        invoke_ok(runner, ["evidence", "scan", "--apply-candidates", "--json"]).output
    )
    assert first["applied"][0]["action"] == "created"
    second = json.loads(
        invoke_ok(runner, ["evidence", "scan", "--apply-candidates", "--json"]).output
    )
    assert second["applied"][0]["action"] == "unchanged"


def test_scan_detects_quality_signals(runner, work) -> None:
    invoke_ok(runner, ["init"])
    (work / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "example"',
                'requires-python = ">=3.10"',
                "",
                "[tool.mypy]",
                "check_untyped_defs = true",
                "",
                "[tool.ruff.lint]",
                'select = ["E", "F"]',
                "",
                "[tool.pytest.ini_options]",
                'testpaths = ["tests"]',
            ]
        )
        + "\n"
    )
    (work / ".pre-commit-config.yaml").write_text("repos: []\n")
    preview = json.loads(invoke_ok(runner, ["evidence", "scan", "--json"]).output)
    keys = {item["fact_key"] for item in preview["proposals"]}
    assert {
        "requires-python",
        "tool.mypy",
        "tool.ruff.lint",
        "tool.pytest.ini_options",
        "pre-commit-hooks",
    } <= keys
    mypy = next(
        item for item in preview["proposals"] if item["fact_key"] == "tool.mypy"
    )
    assert mypy["path"] == "pyproject.toml"
    assert mypy["line"] == 5
    assert "mypy memoryledger" in mypy["suggested"]
    applied = json.loads(
        invoke_ok(runner, ["evidence", "scan", "--apply-candidates", "--json"]).output
    )
    assert len(applied["applied"]) == 5
    memories = json.loads(invoke_ok(runner, ["memory", "list", "--json"]).output)[
        "memories"
    ]
    titles = {item["title"] for item in memories}
    assert "Python type checking" in titles
    assert "Pre-commit validation" in titles
