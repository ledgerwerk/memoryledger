from __future__ import annotations

import re
from pathlib import Path

from .errors import MemoryledgerError
from .models import GENERATED_MARKER, KINDS, RENDER_TARGETS, SCOPES, STATUSES, Memory

SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*['\"]?[A-Za-z0-9_./+-]{12,}"
)
PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO:|<fill>)\b")


def validate_scope_path(root: Path, scope_path: str) -> None:
    if not scope_path:
        return
    target = (root / scope_path).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise MemoryledgerError(
            "INVALID_SCOPE_PATH", "scope_path must not escape the workspace"
        ) from exc
    if Path(scope_path).is_absolute() or ".." in Path(scope_path).parts:
        raise MemoryledgerError(
            "INVALID_SCOPE_PATH", "scope_path must be repo-relative"
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


def validate_memory(memory: Memory, content: str, evidence: str = "") -> None:
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
    validate_content(content)
    if memory.status == "accepted" and not evidence.strip():
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
