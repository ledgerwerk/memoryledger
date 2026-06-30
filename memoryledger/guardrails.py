from __future__ import annotations

import re
from pathlib import Path

from .errors import MemoryledgerError
from .models import (
    EVIDENCE_KINDS,
    GENERATED_MARKER,
    KINDS,
    RENDER_TARGETS,
    SCOPES,
    STATUSES,
    EvidenceRef,
    Memory,
)

SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*['\"]?[A-Za-z0-9_./+-]{12,}"
)
PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO:|<fill>)\b")


def confined_path(
    root: Path,
    value: str | Path,
    *,
    code: str = "INVALID_PATH",
    label: str = "path",
    must_exist: bool = False,
) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        raise MemoryledgerError(code, f"{label} must be relative to its owning root")
    target = (root.resolve() / raw).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise MemoryledgerError(code, f"{label} must not escape its owning root") from exc
    if must_exist and not target.exists():
        raise MemoryledgerError(code, f"{label} does not exist: {value}")
    return target


def validate_scope_path(root: Path, scope_path: str) -> None:
    if scope_path:
        confined_path(
            root, scope_path, code="INVALID_SCOPE_PATH", label="scope_path"
        )


def validate_content(content: str) -> None:
    if not content.strip():
        raise MemoryledgerError("EMPTY_CONTENT", "content.md must be non-empty")
    if SECRET_RE.search(content):
        raise MemoryledgerError(
            "SECRET_LIKE_CONTENT", "content contains secret-like text"
        )
    if PLACEHOLDER_RE.search(content):
        raise MemoryledgerError(
            "PLACEHOLDER_CONTENT", "content contains unresolved placeholders"
        )
    if len(content) > 200_000 or content.lower().count("assistant") > 100:
        raise MemoryledgerError(
            "TRANSCRIPT_LIKE_CONTENT", "content looks like a huge pasted transcript"
        )


def validate_evidence_ref(root: Path, evidence: EvidenceRef) -> None:
    if evidence.kind not in EVIDENCE_KINDS:
        raise MemoryledgerError("INVALID_EVIDENCE_KIND", evidence.kind)
    if not evidence.title.strip() or not evidence.uri.strip():
        raise MemoryledgerError(
            "INVALID_EVIDENCE", "evidence title and URI are required"
        )
    if len(evidence.excerpt) > 2000:
        raise MemoryledgerError("EVIDENCE_TOO_LARGE", "evidence excerpt is too large")
    if SECRET_RE.search(evidence.excerpt):
        raise MemoryledgerError(
            "SECRET_LIKE_EVIDENCE", "evidence contains secret-like text"
        )
    if evidence.line_start is not None and evidence.line_start < 1:
        raise MemoryledgerError("INVALID_LINE_RANGE", "line_start must be positive")
    if evidence.line_end is not None and (
        evidence.line_start is None or evidence.line_end < evidence.line_start
    ):
        raise MemoryledgerError("INVALID_LINE_RANGE", "invalid evidence line range")
    if evidence.kind in {"file", "config"}:
        confined_path(
            root, evidence.uri, code="INVALID_EVIDENCE_URI", label="evidence URI"
        )
    if evidence.kind == "run" and not re.fullmatch(
        r"run:[A-Za-z0-9._-]+#[A-Za-z0-9._-]+", evidence.uri
    ):
        raise MemoryledgerError("INVALID_EVIDENCE_URI", "invalid internal run URI")


def validate_memory(
    memory: Memory, content: str, evidence: str = "", root: Path | None = None
) -> None:
    if memory.kind not in KINDS:
        raise MemoryledgerError("INVALID_KIND", f"Invalid kind: {memory.kind}")
    if memory.status not in STATUSES:
        raise MemoryledgerError("INVALID_STATUS", f"Invalid status: {memory.status}")
    if memory.scope not in SCOPES:
        raise MemoryledgerError("INVALID_SCOPE", f"Invalid scope: {memory.scope}")
    if memory.render_target not in RENDER_TARGETS:
        raise MemoryledgerError(
            "INVALID_RENDER_TARGET", f"Invalid render target: {memory.render_target}"
        )
    if not memory.title.strip():
        raise MemoryledgerError("EMPTY_TITLE", "title must be non-empty")
    if memory.section and (
        len(memory.section) > 80
        or "\n" in memory.section
        or not re.fullmatch(r"[\w .&/+()-]+", memory.section)
    ):
        raise MemoryledgerError("INVALID_SECTION", "section name is invalid")
    validate_content(content)
    if evidence and SECRET_RE.search(evidence):
        raise MemoryledgerError(
            "SECRET_LIKE_EVIDENCE", "evidence contains secret-like text"
        )
    for ref in memory.evidence_refs:
        validate_evidence_ref(root or Path.cwd(), ref)
    if memory.status == "accepted" and not (evidence.strip() or memory.evidence_refs):
        raise MemoryledgerError(
            "MISSING_EVIDENCE", "accepted memory must have evidence or approval reason"
        )


def validate_generated_text(
    text: str, max_chars: int, require_marker: bool = True
) -> None:
    if require_marker and GENERATED_MARKER not in text:
        raise MemoryledgerError(
            "MISSING_MARKER", "generated output must contain marker"
        )
    if len(text) > max_chars:
        raise MemoryledgerError(
            "OUTPUT_TOO_LARGE", "generated output exceeds configured limit"
        )
    if "run.html" in text.lower():
        raise MemoryledgerError(
            "RAW_RUN_HTML", "generated output must not contain raw run.html"
        )
    if SECRET_RE.search(text):
        raise MemoryledgerError(
            "SECRET_LIKE_OUTPUT", "generated output contains secret-like text"
        )


def safe_to_replace(path: Path) -> None:
    if path.exists() and GENERATED_MARKER not in path.read_text():
        raise MemoryledgerError(
            "MANUAL_FILE", f"Refusing to overwrite manual file: {path}"
        )
