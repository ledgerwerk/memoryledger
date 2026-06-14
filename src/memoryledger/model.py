"""Pydantic domain models for memoryledger.

These models serialize cleanly to plain ``dict[str, object]`` values for the
ledgercore front matter and JSONL helpers. Enum members are stored as their
string values so YAML/JSON stay human-readable.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums / literals
# ---------------------------------------------------------------------------


class MemoryType(str, Enum):
    """Memory category. Each type lives in its own folder under ``memories/``."""

    rule = "rule"
    learning = "learning"
    episodic = "episodic"
    procedural = "procedural"
    semantic = "semantic"
    local = "local"

    @property
    def folder(self) -> str:
        """Folder name under ``memories/`` for this type."""
        # Every enum value currently matches its folder name. Keep an explicit
        # map so a future rename does not silently break storage layout.
        return {
            MemoryType.rule: "rules",
            MemoryType.learning: "learnings",
            MemoryType.episodic: "episodes",
            MemoryType.procedural: "procedures",
            MemoryType.semantic: "semantic",
            MemoryType.local: "local",
        }[self]


class MemoryStatus(str, Enum):
    """Lifecycle status of a memory."""

    candidate = "candidate"
    accepted = "accepted"
    rejected = "rejected"
    deprecated = "deprecated"


class Confidence(str, Enum):
    """MVP confidence values (strings)."""

    observed = "observed"
    confirmed = "confirmed"
    inferred = "inferred"
    stale = "stale"


VALID_SCOPES = ("project", "local", "role", "organization")
DEFAULT_SCOPE = "project"
DEFAULT_SOURCE = "session"
DEFAULT_CONFIDENCE = Confidence.observed

# Deterministic YAML key order for memory Markdown front matter.
MEMORY_FRONTMATTER_KEY_ORDER: tuple[str, ...] = (
    "id",
    "type",
    "scope",
    "status",
    "confidence",
    "tags",
    "applies_to",
    "source",
    "created_at",
    "updated_at",
    "links",
)

# MVP event types appended to ``ledger.jsonl``.
EVENT_TYPES: tuple[str, ...] = (
    "memory.proposed",
    "memory.accepted",
    "memory.rejected",
    "memory.deprecated",
    "memory.updated",
    "memory.exported",
)


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class MemoryLink(BaseModel):
    """An opaque cross-ledger reference attached to a memory."""

    model_config = ConfigDict(extra="allow")

    ledger: str
    ref: str

    def to_dict(self) -> dict[str, object]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


# ---------------------------------------------------------------------------
# Primary models
# ---------------------------------------------------------------------------


class Memory(BaseModel):
    """A single durable memory record (front matter + body)."""

    model_config = ConfigDict(extra="ignore", use_enum_values=False)

    id: str
    type: MemoryType
    scope: str = DEFAULT_SCOPE
    status: MemoryStatus = MemoryStatus.candidate
    confidence: Confidence = DEFAULT_CONFIDENCE
    tags: list[str] = Field(default_factory=list)
    applies_to: list[str] = Field(default_factory=list)
    source: str = DEFAULT_SOURCE
    created_at: str
    updated_at: str
    links: list[MemoryLink] = Field(default_factory=list)
    title: str = ""
    body: str = ""

    def to_front_matter(self) -> dict[str, object]:
        """Return front matter as a plain dict with deterministic key set."""
        data: dict[str, object] = {
            "id": self.id,
            "type": self.type.value,
            "scope": self.scope,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "tags": list(self.tags),
            "applies_to": list(self.applies_to),
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "links": [link.to_dict() for link in self.links],
        }
        return data

    @classmethod
    def from_front_matter(cls, front_matter: Mapping[str, object], body: str) -> Memory:
        """Construct a Memory from parsed front matter and body text.

        Unknown keys are ignored. Missing optional fields take defaults.
        ``title`` is intentionally not part of stored front matter by default;
        callers may pass it through ``body`` or via the ``title`` key when
        capture persists it.
        """
        kwargs: dict[str, Any] = {}
        for key in (
            "id",
            "type",
            "scope",
            "status",
            "confidence",
            "source",
            "created_at",
            "updated_at",
        ):
            if key in front_matter and front_matter[key] is not None:
                kwargs[key] = front_matter[key]
        if "tags" in front_matter and front_matter["tags"] is not None:
            kwargs["tags"] = list(front_matter["tags"])  # type: ignore[call-overload]
        if "applies_to" in front_matter and front_matter["applies_to"] is not None:
            kwargs["applies_to"] = list(front_matter["applies_to"])  # type: ignore[call-overload]
        if "links" in front_matter and front_matter["links"] is not None:
            raw_links: list[object] = list(front_matter["links"])  # type: ignore[call-overload]
            links: list[MemoryLink] = []
            for entry in raw_links:
                if isinstance(entry, Mapping):
                    links.append(MemoryLink(**dict(entry)))
                elif isinstance(entry, str):
                    links.append(MemoryLink(ledger=entry, ref=""))
            kwargs["links"] = links
        kwargs["body"] = body
        return cls.model_validate(kwargs)


class LedgerEvent(BaseModel):
    """One compact JSONL event appended to ``ledger.jsonl``."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    ts: str
    type: str
    memory_id: str
    actor: str
    payload: dict[str, object] = Field(default_factory=dict)

    def to_json_line(self) -> str:
        """Serialize as one compact JSON object line (append-friendly)."""
        import json

        obj: dict[str, object] = {
            "event_id": self.event_id,
            "ts": self.ts,
            "type": self.type,
            "memory_id": self.memory_id,
            "actor": self.actor,
            "payload": dict(self.payload),
        }
        return json.dumps(
            obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )


class MemoryRecordSummary(BaseModel):
    """Compact summary used by ``list`` output and retrieval scoring."""

    model_config = ConfigDict(extra="ignore")

    id: str
    type: str
    scope: str
    status: str
    title: str = ""
    tags: list[str] = Field(default_factory=list)
    updated_at: str = ""


def utc_now_iso_value(now: datetime | None = None) -> str:
    """Thin wrapper so model layer does not import ledgercore directly in tests.

    Uses ledgercore's tz-aware ISO helper (seconds precision, trailing ``Z``).
    """
    from ledgercore.time import utc_now_iso

    return utc_now_iso(now=now)


__all__ = [
    "Confidence",
    "DEFAULT_CONFIDENCE",
    "DEFAULT_SCOPE",
    "DEFAULT_SOURCE",
    "EVENT_TYPES",
    "LedgerEvent",
    "MEMORY_FRONTMATTER_KEY_ORDER",
    "Memory",
    "MemoryLink",
    "MemoryRecordSummary",
    "MemoryStatus",
    "MemoryType",
    "VALID_SCOPES",
    "utc_now_iso_value",
]
