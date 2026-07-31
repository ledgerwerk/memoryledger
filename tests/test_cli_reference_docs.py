from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from memoryledger.command_catalog import CATALOG

ROOT = Path(__file__).parents[1]
REFERENCE = ROOT / "docs" / "reference" / "cli.md"


def test_cli_reference_is_current() -> None:
    result = subprocess.run(
        [sys.executable, "docs/_scripts/generate_cli_reference.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_cli_reference_marker_and_canonical_paths() -> None:
    text = REFERENCE.read_text(encoding="utf-8")
    assert "<!-- Generated from memoryledger.command_catalog and the Typer command tree. -->" in text
    for entry in CATALOG.entries:
        if not entry.deprecated:
            assert text.count(f"### `{entry.path}`") == 1
    assert "### `memory edit`" not in text
    assert "### `storage verify`" not in text
    assert "2026-" not in text

