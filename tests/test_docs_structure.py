from __future__ import annotations

import re
from pathlib import Path

import tomllib

ROOT = Path(__file__).parents[1]
DOCS = ROOT / "docs"


def test_markdown_first_structure() -> None:
    assert (DOCS / "index.md").is_file()
    assert not (DOCS / "index.rst").exists()
    assert not list((DOCS / "api").glob("*.rst"))
    assert (DOCS / "Makefile").is_file()
    assert (DOCS / "make.bat").is_file()
    assert not (ROOT / ".readthedocs.yaml").exists() or "Read the Docs" in (DOCS / "README.md").read_text()


def test_requested_pages_and_build_paths_exist() -> None:
    expected = [
        "getting-started/installation.md", "getting-started/quickstart.md", "getting-started/first-project.md",
        "concepts/memory-model.md", "concepts/lifecycle.md", "concepts/evidence.md", "concepts/rendering.md", "concepts/storage-model.md",
        "guides/memory-workflow.md", "guides/agents-md.md", "guides/adopt-existing-agents.md", "guides/nested-agents.md", "guides/linked-documents.md", "guides/templates.md", "guides/evidence-scan.md", "guides/importing-memory.md", "guides/migrations.md", "guides/json-automation.md", "guides/troubleshooting.md",
        "reference/cli.md", "reference/configuration.md", "reference/schemas.md", "reference/file-formats.md", "reference/storage-layout.md", "reference/errors-and-exit-codes.md", "reference/deprecations.md", "reference/compatibility.md",
        "api/models.md", "api/configuration.md", "api/project.md", "api/storage.md", "api/rendering.md", "api/workflows.md", "api/migrations.md", "api/cli-contracts.md", "api/internals.md",
        "development/contributing.md", "development/testing.md", "development/documentation.md", "development/release.md",
    ]
    assert all((DOCS / path).is_file() for path in expected)
    assert "html_static_path" in (DOCS / "conf.py").read_text()
    assert "templates_path" in (DOCS / "conf.py").read_text()


def test_docs_requirements_match_development_dependencies() -> None:
    requirements = {
        line.strip().split("<", 1)[0].split(">", 1)[0].split("=", 1)[0]
        for line in (DOCS / "requirements.txt").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dev = set(project["project"]["optional-dependencies"]["dev"])
    normalized = {item.split("<", 1)[0].split(">", 1)[0].split("=", 1)[0] for item in dev}
    assert requirements <= normalized


def test_internal_markdown_links_have_local_targets() -> None:
    for page in DOCS.rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", text):
            if "://" in target or target.startswith("mailto:"):
                continue
            target_path = (page.parent / target).with_suffix(".md")
            assert target_path.exists(), f"{page}: missing {target}"
