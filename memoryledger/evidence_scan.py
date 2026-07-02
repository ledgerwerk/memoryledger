from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .models import EvidenceRef
from .storage import Store


@dataclass(frozen=True)
class ScanProposal:
    scanner: str
    path: str
    fact_key: str
    title: str
    kind: str
    observed: str
    suggested: str
    line: int
    source_hash: str
    render_target: str = "root_agents"

    @property
    def origin(self) -> str:
        return f"scan:{self.scanner}:{self.path}:{self.fact_key}"

    def to_dict(self) -> dict[str, object]:
        return {
            "origin": self.origin,
            "path": self.path,
            "fact_key": self.fact_key,
            "title": self.title,
            "kind": self.kind,
            "observed": self.observed,
            "suggested": self.suggested,
            "line": self.line,
            "source_hash": self.source_hash,
            "render_target": self.render_target,
        }


def scan(root: Path) -> list[ScanProposal]:
    proposals: list[ScanProposal] = []
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        lines = pyproject.read_text().splitlines()
        for number, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("requires-python"):
                observed = stripped
                proposals.append(
                    _proposal(
                        "pyproject",
                        "pyproject.toml",
                        "requires-python",
                        "Python requirement",
                        "learning",
                        observed,
                        f"Project Python requirement is `{observed.split('=', 1)[-1].strip()}`.",
                        number,
                    )
                )
                break
        section_headers = {
            "[tool.mypy]": (
                "tool.mypy",
                "Python type checking",
                "procedure",
                "Run `mypy memoryledger` when changing typed public APIs or core logic.",
                "linked_doc",
            ),
            "[tool.ruff]": (
                "tool.ruff",
                "Ruff validation",
                "procedure",
                "Run `ruff check .` when Python code or lint configuration changes.",
                "linked_doc",
            ),
            "[tool.ruff.lint]": (
                "tool.ruff.lint",
                "Ruff validation",
                "procedure",
                "Run `ruff check .` when Python code or lint configuration changes.",
                "linked_doc",
            ),
            "[tool.pytest.ini_options]": (
                "tool.pytest.ini_options",
                "Pytest validation",
                "procedure",
                "Run `pytest -q` and any focused pytest selection that covers the changed behavior.",
                "linked_doc",
            ),
        }
        for number, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped not in section_headers:
                continue
            key, title, kind, suggested, render_target = section_headers[stripped]
            proposals.append(
                _proposal(
                    "pyproject",
                    "pyproject.toml",
                    key,
                    title,
                    kind,
                    stripped,
                    suggested,
                    number,
                    render_target=render_target,
                )
            )
    for name in (".pre-commit-config.yaml", ".pre-commit-config.yml"):
        pre_commit = root / name
        if not pre_commit.exists():
            continue
        line = 1
        for number, raw in enumerate(pre_commit.read_text().splitlines(), 1):
            if raw.strip():
                line = number
                break
        proposals.append(
            _proposal(
                "pre-commit",
                name,
                "pre-commit-hooks",
                "Pre-commit validation",
                "procedure",
                "configured hooks",
                "Run `pre-commit run --all-files` when changes affect repository-wide formatting, linting, or configured hooks.",
                line,
                render_target="linked_doc",
            )
        )
        break
    return sorted(proposals, key=lambda item: item.origin)


def _proposal(
    scanner: str,
    path: str,
    key: str,
    title: str,
    kind: str,
    observed: str,
    suggested: str,
    line: int,
    *,
    render_target: str = "root_agents",
) -> ScanProposal:
    digest = hashlib.sha256(observed.encode()).hexdigest()
    return ScanProposal(
        scanner,
        path,
        key,
        title,
        kind,
        observed,
        suggested,
        line,
        digest,
        render_target,
    )


def apply(store: Store, proposals: list[ScanProposal]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    by_origin = {memory.origin: memory for memory in store.all_memories()}
    for proposal in proposals:
        old = by_origin.get(proposal.origin)
        if old and old.origin_hash == proposal.source_hash:
            results.append({"action": "unchanged", "memory_id": old.id})
            continue
        evidence = EvidenceRef(
            kind="file",
            title="Observed configuration",
            uri=proposal.path,
            excerpt=proposal.observed,
            line_start=proposal.line,
            line_end=proposal.line,
        )
        if old:
            from dataclasses import replace

            from ledgercore.time import utc_now_iso

            updated = replace(
                old,
                kind=proposal.kind,
                title=proposal.title,
                status="candidate",
                scope_path=proposal.path,
                render_target=proposal.render_target,
                origin_hash=proposal.source_hash,
                evidence_refs=[evidence],
                updated_at=utc_now_iso(),
                version=old.version + 1,
            )
            store.write(
                updated, proposal.suggested, "Scanner fact changed.", "scan update"
            )
            results.append({"action": "updated", "memory_id": old.id})
        else:
            memory = store.create(
                proposal.kind,
                proposal.title,
                proposal.suggested,
                "Detected from repository configuration.",
                "repo",
                proposal.path,
                proposal.render_target,
                "scan",
                origin=proposal.origin,
                origin_hash=proposal.source_hash,
                evidence_refs=[evidence],
            )
            results.append({"action": "created", "memory_id": memory.id})
    return results
