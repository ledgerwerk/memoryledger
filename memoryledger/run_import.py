from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass

from .errors import MemoryledgerError

MAX_HTML_BYTES = 2_000_000
MAX_PAYLOAD_BYTES = 1_000_000
MAX_ENTRY_CHARS = 4000
SESSION_RE = re.compile(
    r'<script[^>]+id=["\']session-data["\'][^>]*>([^<]+)</script>',
    re.IGNORECASE,
)
ALLOWED_TYPES = {"user_message", "memory_correction", "command_outcome"}


@dataclass(frozen=True)
class RunProposal:
    entry_id: str
    entry_type: str
    text: str
    timestamp: str = ""


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
    if not isinstance(data, dict) or data.get("schema") != "memoryledger.session.v1":
        raise MemoryledgerError("UNSUPPORTED_RUN_SCHEMA", "unsupported session schema")
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
        proposals.append(
            RunProposal(entry_id, str(raw["type"]), text, str(raw.get("timestamp", "")))
        )
    return proposals
