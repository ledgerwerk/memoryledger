from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass

from .errors import MemoryledgerError

MAX_HTML_BYTES = 2_000_000
MAX_PAYLOAD_BYTES = 1_000_000
MAX_ENTRY_CHARS = 4000
MAX_EXCERPT_CHARS = 1200
SESSION_RE = re.compile(
    r'<script[^>]+id=["\']session-data["\'][^>]*>([^<]+)</script>',
    re.IGNORECASE,
)
ALLOWED_TYPES = {"user_message", "memory_correction", "command_outcome"}
USER_PATTERNS = (
    "remember this",
    "store this",
    "store all the gained knowledge",
    "durable memory",
    "add this to agents.md",
    "build an agents.md",
    "update agents.md",
    "memoryledger",
    "run.html",
)
WORKFLOW_KEYWORDS = (
    "memoryledger",
    "agents.md",
    "render",
    "export",
    "review accept",
    "memory create",
    "manual_file",
    "manual.bak",
    "invalid_argument",
    "bad substitution",
    "modulenotfounderror",
    "fetchpypi",
    "pythonruntimedepscheck",
    "agents adopt",
)
ASSISTANT_SUMMARY_KEYWORDS = (
    "created memories",
    "created and accepted memories",
    "accepted memories",
    "rendered",
    "exported",
    "backup",
    "validation",
    "adoption",
)
RAW_TRANSCRIPT_MARKERS = (
    "total entries:",
    "assistant messages:",
    "tool result messages:",
    "<html",
    "session-data",
)


@dataclass(frozen=True)
class RunProposal:
    entry_id: str
    entry_type: str
    text: str
    kind: str
    title: str
    render_target: str = "linked_doc"
    timestamp: str = ""
    session_id: str = ""


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


def _safe_excerpt(text: str) -> str:
    cleaned = text.strip()
    if len(cleaned) > MAX_EXCERPT_CHARS:
        cleaned = cleaned[:MAX_EXCERPT_CHARS].rstrip() + "…"
    return cleaned


def _raw_transcript_like(text: str) -> bool:
    normalized = _normalized(text)
    return any(marker in normalized for marker in RAW_TRANSCRIPT_MARKERS)


def _classify(entry_type: str, text: str) -> RunProposal | None:
    if _raw_transcript_like(text):
        return None
    text = _safe_excerpt(text)
    normalized = _normalized(text)
    if entry_type == "memory_correction":
        if any(keyword in normalized for keyword in WORKFLOW_KEYWORDS):
            return RunProposal("", entry_type, text, "episode", "Run memoryledger correction")
        return None
    if entry_type == "user_message":
        if any(pattern in normalized for pattern in USER_PATTERNS) or (
            "memoryledger" in normalized and "agents.md" in normalized
        ):
            return RunProposal("", entry_type, text, "episode", "Run durable memory request")
        return None
    if entry_type == "command_outcome" and any(keyword in normalized for keyword in WORKFLOW_KEYWORDS):
        return RunProposal("", entry_type, text, "episode", "Run memoryledger command outcome")
    if entry_type == "assistant_summary" and any(keyword in normalized for keyword in ASSISTANT_SUMMARY_KEYWORDS):
        return RunProposal("", entry_type, text, "episode", "Run memoryledger summary")
    return None


def decode_session(html: str) -> list[RunProposal] | None:
    if len(html.encode()) > MAX_HTML_BYTES:
        raise MemoryledgerError("RUN_TOO_LARGE", "run HTML exceeds size limit")
    match = SESSION_RE.search(html)
    if not match:
        return None
    try:
        decoded = base64.b64decode(match.group(1).strip(), validate=True)
        if len(decoded) > MAX_PAYLOAD_BYTES:
            raise MemoryledgerError("RUN_TOO_LARGE", "session payload exceeds size limit")
        data = json.loads(decoded)
    except MemoryledgerError:
        raise
    except (ValueError, json.JSONDecodeError) as exc:
        raise MemoryledgerError("INVALID_RUN_PAYLOAD", "invalid session-data") from exc
    if not isinstance(data, dict):
        raise MemoryledgerError("UNSUPPORTED_RUN_SCHEMA", "unsupported session schema")
    if data.get("schema") == "memoryledger.session.v1":
        return _decode_memoryledger_session(data)
    if data.get("header", {}).get("type") == "session" and isinstance(data.get("entries"), list):
        return _decode_real_session_export(data)
    raise MemoryledgerError("UNSUPPORTED_RUN_SCHEMA", "unsupported session schema")


def _decode_memoryledger_session(data: dict) -> list[RunProposal]:
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise MemoryledgerError("INVALID_RUN_PAYLOAD", "entries must be a list")
    proposals: list[RunProposal] = []
    for raw in entries:
        if not isinstance(raw, dict) or raw.get("type") not in ALLOWED_TYPES:
            continue
        entry_id = str(raw.get("id", ""))
        text = str(raw.get("text", "")).strip()
        if not entry_id or not text or len(text) > MAX_ENTRY_CHARS:
            continue
        proposal = _classify(str(raw["type"]), text)
        if proposal is None:
            continue
        proposals.append(RunProposal(entry_id, proposal.entry_type, proposal.text, proposal.kind, proposal.title, proposal.render_target, str(raw.get("timestamp", ""))))
    return proposals


def _decode_real_session_export(data: dict) -> list[RunProposal]:
    session_id = str(data.get("header", {}).get("id", ""))
    proposals: list[RunProposal] = []
    for raw in data.get("entries", []):
        if not isinstance(raw, dict) or raw.get("type") != "message":
            continue
        entry_id = str(raw.get("id", ""))
        if not entry_id:
            continue
        msg = raw.get("message") if isinstance(raw.get("message"), dict) else {}
        role = str(msg.get("role", ""))
        text = _visible_text_from_message(msg)
        if not text or len(text) > MAX_ENTRY_CHARS:
            continue
        entry_type = _entry_type_for_role(role, msg)
        if entry_type is None:
            continue
        proposal = _classify(entry_type, text)
        if proposal is None:
            continue
        proposals.append(RunProposal(entry_id, proposal.entry_type, proposal.text, proposal.kind, proposal.title, proposal.render_target, str(raw.get("timestamp", "")), session_id))
    return proposals


def _entry_type_for_role(role: str, msg: dict) -> str | None:
    normalized = role.lower()
    if normalized == "user":
        return "user_message"
    if normalized == "assistant":
        return "assistant_summary"
    if normalized in {"toolresult", "tool_result", "tool"}:
        return "command_outcome"
    return None


def _visible_text_from_message(msg: dict) -> str:
    parts: list[str] = []
    for item in msg.get("content") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            parts.append(str(item.get("text") or ""))
    if msg.get("role", "").lower() in {"toolresult", "tool_result", "tool"} and msg.get("toolName"):
        prefix = f"tool {msg.get('toolName')}"
        if msg.get("isError"):
            prefix += " error"
        if parts:
            parts[0] = prefix + ": " + parts[0]
    return "\n".join(parts).strip()
