from __future__ import annotations

from pathlib import Path


def test_skill_files_exist() -> None:
    skill = Path("skills/memoryledger/SKILL.md").read_text()
    readme = Path("skills/memoryledger/README.md").read_text()
    assert "memoryledger" in skill
    assert "When implementation work is requested" in skill
    assert "memoryledger memory create" in readme
    assert "Never edit a configured generated target" in skill
    assert "not automatically generated" in skill
    assert "memoryledger agents adopt" in skill
    assert "--apply --backup" in skill
