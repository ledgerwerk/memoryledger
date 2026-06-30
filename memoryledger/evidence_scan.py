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
    observed: str
    suggested: str
    line: int
    source_hash: str

    @property
    def origin(self) -> str:
        return f"scan:{self.scanner}:{self.path}:{self.fact_key}"

    def to_dict(self) -> dict[str, object]:
        return {
            "origin": self.origin,
            "path": self.path,
            "fact_key": self.fact_key,
            "observed": self.observed,
            "suggested": self.suggested,
            "line": self.line,
            "source_hash": self.source_hash,
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
                        observed,
                        f"Project Python requirement is `{observed.split('=', 1)[-1].strip()}`.",
                        number,
                    )
                )
                break
    return sorted(proposals, key=lambda item: item.origin)


def _proposal(
    scanner: str,
    path: str,
    key: str,
    observed: str,
    suggested: str,
    line: int,
) -> ScanProposal:
    digest = hashlib.sha256(observed.encode()).hexdigest()
    return ScanProposal(scanner, path, key, observed, suggested, line, digest)


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
                status="candidate",
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
                "learning",
                proposal.fact_key.replace("-", " ").title(),
                proposal.suggested,
                "Detected from repository configuration.",
                "repo",
                proposal.path,
                "root_agents",
                "scan",
                origin=proposal.origin,
                origin_hash=proposal.source_hash,
                evidence_refs=[evidence],
            )
            results.append({"action": "created", "memory_id": memory.id})
    return results
