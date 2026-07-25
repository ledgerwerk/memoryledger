from pathlib import Path

import ledgercore

from memoryledger.config import load_tool_config


def test_schema3_ledgercore_facade_exposes_required_apis() -> None:
    for name in (
        "load_ledger_project",
        "resolve_ledger_layout",
        "initialize_config_binding",
        "initialize_storage_binding",
        "validate_ledger_layout_storage",
        "read_front_matter_document",
        "write_front_matter_document",
        "load_yaml_object",
        "write_yaml",
        "next_prefixed_id",
        "sha256_bytes",
    ):
        assert hasattr(ledgercore, name), name


def test_tool_config_v2_excludes_identity_and_storage(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """config_version = 2

[ledger]
code = "ml"
version = 3

[render]
root_agents_path = "AGENTS.md"
linked_docs_dir = "agent_docs"
""",
        encoding="utf-8",
    )
    config = load_tool_config(path, global_defaults=False)
    assert config.config_version == 2
    assert config.ledger_version == 3
    assert config.render.root_agents_path == "AGENTS.md"
