from __future__ import annotations

from pathlib import Path


def test_skill_files_exist() -> None:
    skill = Path("skills/memoryledger/SKILL.md").read_text()
    readme = Path("skills/memoryledger/README.md").read_text()
    assert "memoryledger" in skill
    assert "When implementation work is requested" in skill
    assert "memoryledger memory create" in readme
