from __future__ import annotations

from pathlib import Path

from memoryledger.storage import load_config

from .conftest import invoke_ok


def test_config_discovery_from_child(runner, work: Path, monkeypatch) -> None:
    invoke_ok(runner, ["init"])
    child = work / "a" / "b"
    child.mkdir(parents=True)
    monkeypatch.chdir(child)
    assert "config:" in invoke_ok(runner, ["status"]).output


def test_global_config_merges_before_project(runner, work: Path, monkeypatch) -> None:
    xdg = work / "xdg"
    global_path = xdg / "ledger" / "memoryledger.toml"
    global_path.parent.mkdir(parents=True)
    global_path.write_text(
        '[render]\ninclude_evidence = true\nlinked_docs_dir = "docs/global"\n'
        'evidence_index_path = "agent_docs/evidence.md"\n'
        '[template_policy]\nenabled = ["base"]\nauto_accept = false\n'
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    invoke_ok(runner, ["init"])
    config = work / ".ledger/memoryledger/config.toml"
    config.write_text(
        config.read_text().replace(
            'linked_docs_dir = "agent_docs"',
            'linked_docs_dir = "docs/project"',
        )
    )
    data = load_config(work)
    assert data.render.include_evidence is False
    assert data.render.evidence_index_path == ""
    assert data.render.linked_docs_dir == "docs/project"
    assert data.template_policy.enabled is False
    assert data.template_policy.ids == []
