"""Storage layer for memoryledger.

Responsibilities:
- Initialize the on-disk layout (config, state dir, memory folders, exports,
  ``ledger.jsonl`` audit log, ``state.json``).
- Allocate deterministic date-based IDs (``mem-YYYYMMDD-NNNN`` /
  ``evt-YYYYMMDD-NNNN``).
- Read/write memory Markdown files via ledgercore front matter helpers.
- Append-only event log writes.
- Status mutators and memory iteration.

The append-only event log is written one compact JSON object per line using
``json.dumps(..., sort_keys=True, separators=(",",":"), ensure_ascii=False)``
plus a trailing newline. ``ledger.jsonl`` is never rewritten during normal
commands.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from ledgercore.frontmatter import (
    read_front_matter_document,
    write_front_matter_document,
)
from ledgercore.io import ensure_dir
from ledgercore.jsonio import load_json_object, write_json
from ledgercore.jsonl import load_jsonl_object_rows
from ledgercore.time import utc_now_iso

from memoryledger.config import (
    CONFIG_FILENAME,
    MemoryLedgerConfig,
    MemoryLedgerProject,
    default_config_text,
    find_project,
)
from memoryledger.errors import (
    AlreadyExistsError,
    NotFoundError,
    StateError,
    ValidationError,
)
from memoryledger.model import (
    EVENT_TYPES,
    MEMORY_FRONTMATTER_KEY_ORDER,
    Confidence,
    LedgerEvent,
    Memory,
    MemoryStatus,
    MemoryType,
)

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

STATE_DIR_NAME = ".memoryledger"
LEDGER_FILENAME = "ledger.jsonl"
STATE_FILENAME = "state.json"
MEMORIES_DIRNAME = "memories"
EXPORTS_DIRNAME = "exports"
DEFAULT_EXPORT_FILENAME = "AGENTS.memory.md"

# Memory type -> folder under memories/
MEMORY_TYPE_FOLDERS: dict[MemoryType, str] = {
    MemoryType.rule: "rules",
    MemoryType.learning: "learnings",
    MemoryType.episodic: "episodes",
    MemoryType.procedural: "procedures",
    MemoryType.semantic: "semantic",
    MemoryType.local: "local",
}

REQUIRED_MEMORY_SUBDIRS = tuple(MEMORY_TYPE_FOLDERS.values())

DEFAULT_ACTOR = "memoryledger"
AGENT_ACTOR = "agent"
USER_ACTOR = "user"


# ---------------------------------------------------------------------------
# Now-provider type
# ---------------------------------------------------------------------------


NowProvider = "datetime | None | callable[[], datetime | None]"


def _resolve_now(now: datetime | None) -> datetime | None:
    return now


def _now_iso(now: datetime | None = None) -> str:
    return utc_now_iso(now=now)


def _today_stamp(now: datetime | None = None) -> str:
    """Return YYYYMMDD using the provided (UTC) ``now`` or real current time."""
    ts = _now_iso(now)
    # ts is like 2026-06-13T10:00:00Z
    return ts.split("T", 1)[0].replace("-", "")


# ---------------------------------------------------------------------------
# ID allocation
# ---------------------------------------------------------------------------


def _scan_used_numbers_for_date(
    prefix_with_date: str, candidates: Iterator[str]
) -> int:
    """Return the highest used NNNN for ids starting with ``prefix_with_date``."""
    highest = 0
    prefix = prefix_with_date + "-"
    for cand in candidates:
        s = cand.strip()
        if not s.startswith(prefix):
            continue
        tail = s[len(prefix) :]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return highest


class MemoryStore:
    """Filesystem-backed store for memoryledger.

    All paths are derived from a discovered :class:`MemoryLedgerProject`.
    Tests inject ``now`` for deterministic timestamps and IDs.
    """

    def __init__(
        self,
        project: MemoryLedgerProject,
        *,
        actor: str = DEFAULT_ACTOR,
        now: datetime | None = None,
    ) -> None:
        self.project = project
        self.config: MemoryLedgerConfig = project.config
        self.state_dir: Path = project.state_dir
        self.memories_dir: Path = project.memories_dir
        self.exports_dir: Path = self.state_dir / EXPORTS_DIRNAME
        self.ledger_path: Path = project.ledger_path
        self.state_file: Path = project.state_file
        self.export_path: Path = project.export_path
        self.actor: str = actor
        self._now: datetime | None = now

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def init_project(self, *, force: bool = False) -> MemoryLedgerProject:
        """Create the on-disk layout for the project.

        Writes the config file if absent, creates the state directory tree,
        and ensures ``ledger.jsonl`` and ``state.json`` exist. With
        ``force=False`` (the MVP default) an existing ``.memoryledger.toml``
        is NOT overwritten and no error is raised — init is idempotent for
        the directory layout but protective of the config file.

        Returns the freshly discovered project (so callers always operate on
        the on-disk state).
        """
        config_path = self.project.workspace_root / CONFIG_FILENAME
        if config_path.exists():
            if force:
                raise AlreadyExistsError(
                    "Refusing to overwrite existing config without explicit "
                    "force support in MVP.",
                    context={"path": str(config_path)},
                )
            # Idempotent: keep existing config.
        else:
            config_path.write_text(default_config_text(), encoding="utf-8")

        self._ensure_layout()
        return self.project

    def _ensure_layout(self) -> None:
        ensure_dir(self.state_dir)
        ensure_dir(self.memories_dir)
        for sub in REQUIRED_MEMORY_SUBDIRS:
            ensure_dir(self.memories_dir / sub)
        ensure_dir(self.exports_dir)
        if not self.ledger_path.exists():
            self.ledger_path.write_text("", encoding="utf-8")
        if not self.state_file.exists():
            write_json(self.state_file, {}, atomic=True)

    # ------------------------------------------------------------------
    # State file
    # ------------------------------------------------------------------

    def load_state(self) -> dict[str, object]:
        return load_json_object(self.state_file, missing="empty")

    def save_state(self, data: dict[str, object]) -> None:
        ensure_dir(self.state_dir)
        write_json(self.state_file, data, atomic=True)

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------

    def append_event(
        self,
        *,
        event_type: str,
        memory_id: str,
        payload: dict[str, object] | None = None,
        actor: str | None = None,
        now: datetime | None = None,
    ) -> LedgerEvent:
        """Append one compact JSONL event line and return it."""
        if event_type not in EVENT_TYPES:
            raise ValidationError(f"Unknown event type {event_type!r}")
        ts = _now_iso(now if now is not None else self._now)
        event_id = self._allocate_event_id(ts)
        event = LedgerEvent(
            event_id=event_id,
            ts=ts,
            type=event_type,
            memory_id=memory_id,
            actor=actor or self.actor,
            payload=payload or {},
        )
        self._write_event_line(event.to_json_line())
        return event

    def _write_event_line(self, line: str) -> None:
        ensure_dir(self.state_dir)
        if not line.endswith("\n"):
            line = line + "\n"
        # Append-only: open in append-binary to avoid accidental truncation.
        with self.ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def read_events(self) -> list[dict[str, object]]:
        """Read all JSONL rows, raising on unrecoverable issues."""
        result = load_jsonl_object_rows(self.ledger_path, missing="empty")
        if result.issues:
            raise StateError(
                "Malformed event log rows detected",
                context={"issues": [str(i) for i in result.issues]},
            )
        return [row.value for row in result.rows]

    def read_events_lenient(self) -> tuple[list[dict[str, object]], list[str]]:
        """Read events without raising; return (rows, issue_descriptions).

        Used by ``doctor`` for recoverable issue reporting.
        """
        result = load_jsonl_object_rows(self.ledger_path, missing="empty")
        rows = [row.value for row in result.rows]
        issues = [str(i) for i in result.issues]
        return rows, issues

    def _allocate_event_id(self, ts: str) -> str:
        date_stamp = ts.split("T", 1)[0].replace("-", "")
        prefix = f"evt-{date_stamp}"
        existing_event_ids = (
            str(r.get("event_id", "")) for r in self.read_events_lenient()[0]
        )
        # Also scan memory ids is not relevant here; events are independent.
        highest = _scan_used_numbers_for_date(prefix, existing_event_ids)
        return f"{prefix}-{highest + 1:04d}"

    # ------------------------------------------------------------------
    # Memory ID allocation
    # ------------------------------------------------------------------

    def _allocate_memory_id(self, now: datetime | None = None) -> str:
        date_stamp = _today_stamp(now if now is not None else self._now)
        prefix = f"mem-{date_stamp}"
        existing_ids = (m.id for m in self.iter_memories())
        highest = _scan_used_numbers_for_date(prefix, existing_ids)
        return f"{prefix}-{highest + 1:04d}"

    # ------------------------------------------------------------------
    # Memory read/write
    # ------------------------------------------------------------------

    def memory_path(self, memory: Memory) -> Path:
        folder = MEMORY_TYPE_FOLDERS[memory.type]
        return self.memories_dir / folder / f"{_safe_filename(memory.id)}.md"

    def memory_path_for_id_type(self, memory_id: str, memory_type: MemoryType) -> Path:
        folder = MEMORY_TYPE_FOLDERS[memory_type]
        return self.memories_dir / folder / f"{_safe_filename(memory_id)}.md"

    def write_memory(self, memory: Memory) -> Path:
        path = self.memory_path(memory)
        ensure_dir(path.parent)
        front = memory.to_front_matter()
        body = memory.body
        if memory.title:
            # Persist the title as an H1 at the top of the body so list/search
            # can recover it deterministically without extra state.
            body = self._render_body_with_title(memory.title, memory.body)
        write_front_matter_document(
            path,
            front,
            body,
            key_order=MEMORY_FRONTMATTER_KEY_ORDER,
            atomic=True,
        )
        return path

    @staticmethod
    def _render_body_with_title(title: str, body: str) -> str:
        title = title.strip()
        if not title:
            return body
        header = f"# {title}\n"
        if not body:
            return header.rstrip("\n")
        return header + body

    def read_memory(self, path: Path) -> Memory:
        front, body = read_front_matter_document(path)
        title, stripped_body = _split_title_and_body(body)
        mem = Memory.from_front_matter(front, stripped_body)
        if title and not mem.title:
            mem.title = title
        return mem

    def find_memory_path(self, memory_id: str) -> Path:
        """Locate a memory file by id across all type folders."""
        for sub in REQUIRED_MEMORY_SUBDIRS:
            candidate = self.memories_dir / sub / f"{_safe_filename(memory_id)}.md"
            if candidate.exists():
                return candidate
        raise NotFoundError(
            f"Memory {memory_id} not found", context={"memory_id": memory_id}
        )

    def load_memory(self, memory_id: str) -> Memory:
        return self.read_memory(self.find_memory_path(memory_id))

    # ------------------------------------------------------------------
    # Status mutators
    # ------------------------------------------------------------------

    def set_status(
        self,
        memory_id: str,
        status: MemoryStatus,
        *,
        event_type: str,
        actor: str | None = None,
        now: datetime | None = None,
    ) -> Memory:
        """Set a memory's status, rewrite its Markdown, and append an event."""
        mem = self.load_memory(memory_id)
        mem.status = status
        ts = _now_iso(now if now is not None else self._now)
        mem.updated_at = ts
        self.write_memory(mem)
        self.append_event(
            event_type=event_type,
            memory_id=memory_id,
            payload={"status": status.value, "title": mem.title}
            if mem.title
            else {"status": status.value},
            actor=actor,
            now=now if now is not None else self._now,
        )
        return mem

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    def capture_memory(
        self,
        *,
        memory_type: MemoryType,
        title: str,
        body: str,
        tags: list[str] | None = None,
        applies_to: list[str] | None = None,
        scope: str = "project",
        source: str = "session",
        confidence: Confidence = Confidence.observed,
        links: list[dict[str, str]] | None = None,
        actor: str = AGENT_ACTOR,
        now: datetime | None = None,
    ) -> Memory:
        """Create a candidate memory and append a ``memory.proposed`` event.

        Status is always ``candidate`` here — capture never produces accepted
        memory. Approval gating is enforced by this invariant regardless of
        policy settings.
        """
        ts = _now_iso(now if now is not None else self._now)
        memory_id = self._allocate_memory_id(now if now is not None else self._now)
        from memoryledger.model import MemoryLink

        mem = Memory(
            id=memory_id,
            type=memory_type,
            scope=scope,
            status=MemoryStatus.candidate,
            confidence=confidence,
            tags=list(tags or []),
            applies_to=list(applies_to or []),
            source=source,
            created_at=ts,
            updated_at=ts,
            links=[MemoryLink(**lk) for lk in (links or [])],
            title=title,
            body=body,
        )
        self.write_memory(mem)
        self.append_event(
            event_type="memory.proposed",
            memory_id=memory_id,
            payload={
                "title": title,
                "memory_type": memory_type.value,
                "scope": scope,
            },
            actor=actor,
            now=now if now is not None else self._now,
        )
        return mem

    # ------------------------------------------------------------------
    # Iteration
    # ------------------------------------------------------------------

    def iter_memories(self) -> Iterator[Memory]:
        """Yield all memory records across type folders (best-effort order)."""
        if not self.memories_dir.exists():
            return
        for sub in REQUIRED_MEMORY_SUBDIRS:
            folder = self.memories_dir / sub
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*.md")):
                try:
                    yield self.read_memory(path)
                except Exception:  # malformed file; skip in iteration
                    continue

    def iter_memory_files(self) -> Iterator[tuple[Path, MemoryType]]:
        """Yield (path, type) for every ``*.md`` memory file by folder."""
        if not self.memories_dir.exists():
            return
        for mem_type, sub in MEMORY_TYPE_FOLDERS.items():
            folder = self.memories_dir / sub
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*.md")):
                yield path, mem_type

    # ------------------------------------------------------------------
    # Diagnostics (doctor)
    # ------------------------------------------------------------------

    def diagnose(self, *, create_export_dir: bool = True) -> DoctorReport:
        """Run read-only health checks for ``memoryledger doctor``.

        Returns a :class:`DoctorReport`. Optionally creates a missing
        export directory (the only mutation doctor performs in the MVP).
        """
        report = DoctorReport()
        # Config discoverability is implicit: this store was built from a
        # discovered project. Record the config path for completeness.
        report.config_path = self.project.config_path
        report.config_ok = self.project.config_path.exists()

        report.state_dir = self.state_dir
        report.state_dir_ok = self.state_dir.exists()

        missing_subs: list[str] = []
        for sub in REQUIRED_MEMORY_SUBDIRS:
            if not (self.memories_dir / sub).exists():
                missing_subs.append(sub)
        report.memory_subdirs_ok = not missing_subs
        report.missing_subdirs = missing_subs

        # JSONL parse with recoverable issue reporting.
        rows, issues = self.read_events_lenient()
        report.ledger_path = self.ledger_path
        report.ledger_ok = not issues
        report.ledger_issues = issues
        report.event_count = len(rows)

        # Memory Markdown front matter validation.
        required = REQUIRED_FRONTMATTER_FIELDS
        fm_problems: list[DoctorFrontMatterIssue] = []
        for path, _mem_type in self.iter_memory_files():
            try:
                front, _body = read_front_matter_document(path)
            except Exception as exc:  # malformed front matter
                fm_problems.append(
                    DoctorFrontMatterIssue(
                        path=str(path), error=str(exc), missing_fields=[]
                    )
                )
                continue
            missing = [f for f in required if f not in front]
            if missing:
                fm_problems.append(
                    DoctorFrontMatterIssue(
                        path=str(path), error="missing fields", missing_fields=missing
                    )
                )
        report.memory_files_ok = not fm_problems
        report.front_matter_issues = fm_problems

        # Export directory.
        report.export_dir = self.exports_dir
        if not self.exports_dir.exists() and create_export_dir:
            try:
                ensure_dir(self.exports_dir)
                report.export_dir_created = True
                report.export_dir_ok = True
            except Exception as exc:
                report.export_dir_ok = False
                report.export_dir_error = str(exc)
        else:
            report.export_dir_ok = self.exports_dir.exists()

        # Status agreement (best effort): latest status event vs front matter.
        report.status_agreement = _check_status_agreement(
            rows, list(self.iter_memories())
        )

        report.compute_ok()
        return report


# ---------------------------------------------------------------------------
# Module-level helpers / factories
# ---------------------------------------------------------------------------


def open_store(
    start: Path | None = None,
    *,
    actor: str = DEFAULT_ACTOR,
    now: datetime | None = None,
) -> MemoryStore:
    """Discover the project from ``start`` and return an open store."""
    project = find_project(start)
    return MemoryStore(project, actor=actor, now=now)


def init_store(
    root: Path,
    *,
    actor: str = DEFAULT_ACTOR,
    now: datetime | None = None,
    force: bool = False,
) -> MemoryStore:
    """Initialize a fresh project under ``root`` and return its store.

    Writes ``.memoryledger.toml`` (if absent), creates the layout, then
    re-discovers so the store uses validated paths.
    """
    project = find_project_or_init(root)
    store = MemoryStore(project, actor=actor, now=now)
    store.init_project(force=force)
    # Re-discover to pick up on-disk config defaults (e.g. state_dir).
    rediscovered = find_project(root)
    return MemoryStore(rediscovered, actor=actor, now=now)


def find_project_or_init(root: Path) -> MemoryLedgerProject:
    """Return an existing project under ``root``, else a config-less shell.

    The shell is only used transiently to write the default config; callers
    must run :meth:`MemoryStore.init_project` afterwards.
    """
    from pydantic import BaseModel  # local import to avoid cycle in type hints

    # Try to discover; if missing, build a minimal project pointing at root.
    config_path = root / CONFIG_FILENAME
    if config_path.exists():
        return find_project(root)

    # Build a default config in memory so init_project writes defaults.
    from memoryledger.config import MemoryLedgerConfig, MemoryLedgerProject

    cfg = MemoryLedgerConfig.model_validate({})
    cfg.config_path = config_path
    state_dir = (root / cfg.ledger.state_dir).resolve()
    export_path = (root / cfg.exports.default_path).resolve()
    project = MemoryLedgerProject(
        workspace_root=root.resolve(),
        config_path=config_path,
        config=cfg,
        state_dir=state_dir,
        export_path=export_path,
    )
    # Suppress unused-import lint for BaseModel (kept for clarity).
    _ = BaseModel
    return project


# ---------------------------------------------------------------------------
# Filename + title helpers
# ---------------------------------------------------------------------------


def _safe_filename(memory_id: str) -> str:
    """Return a filesystem-safe base name for a memory id.

    Memory ids are already restricted (``mem-YYYYMMDD-NNNN``), so we only
    guard against any stray path separators.
    """
    safe = memory_id.replace("/", "_").replace("\\", "_").strip()
    if not safe:
        raise ValidationError("Empty memory id")
    return safe


def _extract_title_from_body(body: str) -> str:
    """If ``body`` starts with an H1 line, return its text; else ''."""
    return _split_title_and_body(body)[0]


def _split_title_and_body(body: str) -> tuple[str, str]:
    """Split a leading ``# Title`` line from the body.

    Returns ``(title, remaining_body)``. If no H1 leads the body, returns
    ``('', body)`` unchanged so the original body survives round-trips.
    """
    if not body:
        return "", ""
    stripped = body.lstrip("\n")
    if not stripped.startswith("# "):
        return "", body
    lines = stripped.splitlines()
    title = lines[0][2:].strip()
    rest = "\n".join(lines[1:])
    # Drop exactly one leading blank line that conventionally follows H1.
    if rest.startswith("\n"):
        rest = rest[1:]
    return title, rest


# ---------------------------------------------------------------------------
# Doctor report types
# ---------------------------------------------------------------------------


REQUIRED_FRONTMATTER_FIELDS: tuple[str, ...] = (
    "id",
    "type",
    "scope",
    "status",
    "created_at",
    "updated_at",
)


class DoctorFrontMatterIssue:
    """A single memory file front-matter problem reported by ``doctor``."""

    def __init__(self, *, path: str, error: str, missing_fields: list[str]) -> None:
        self.path = path
        self.error = error
        self.missing_fields = list(missing_fields)

    def __str__(self) -> str:
        if self.missing_fields:
            return f"{self.path}: missing {', '.join(self.missing_fields)}"
        return f"{self.path}: {self.error}"


class DoctorStatusMismatch:
    """A materialized status that disagrees with the latest status event."""

    def __init__(self, *, memory_id: str, materialized: str, event: str) -> None:
        self.memory_id = memory_id
        self.materialized = materialized
        self.event = event

    def __str__(self) -> str:
        return (
            f"{self.memory_id}: front matter status '{self.materialized}' "
            f"disagrees with latest event status '{self.event}'"
        )


class DoctorReport:
    """Aggregate result of :meth:`MemoryStore.diagnose`."""

    def __init__(self) -> None:
        self.config_path: Path | None = None
        self.config_ok: bool = False
        self.state_dir: Path | None = None
        self.state_dir_ok: bool = False
        self.memory_subdirs_ok: bool = False
        self.missing_subdirs: list[str] = []
        self.ledger_path: Path | None = None
        self.ledger_ok: bool = False
        self.ledger_issues: list[str] = []
        self.event_count: int = 0
        self.memory_files_ok: bool = False
        self.front_matter_issues: list[DoctorFrontMatterIssue] = []
        self.export_dir: Path | None = None
        self.export_dir_ok: bool = False
        self.export_dir_created: bool = False
        self.export_dir_error: str | None = None
        self.status_agreement: list[DoctorStatusMismatch] = []
        self.ok: bool = False

    def compute_ok(self) -> None:
        """Compute the overall ``ok`` flag from sub-checks."""
        self.ok = (
            self.config_ok
            and self.state_dir_ok
            and self.memory_subdirs_ok
            and self.ledger_ok
            and self.memory_files_ok
            and self.export_dir_ok
            and not self.status_agreement
        )

    @property
    def all_issues(self) -> list[str]:
        """Return a flat list of human-readable issue strings."""
        issues: list[str] = []
        if not self.config_ok and self.config_path is not None:
            issues.append(f"config not found: {self.config_path}")
        if not self.state_dir_ok:
            issues.append(f"state directory missing: {self.state_dir}")
        if not self.memory_subdirs_ok:
            issues.append("missing memory subdirs: " + ", ".join(self.missing_subdirs))
        if not self.ledger_ok:
            issues.append(f"ledger.jsonl has {len(self.ledger_issues)} parse issue(s)")
            issues.extend(f"  - {i}" for i in self.ledger_issues)
        if not self.memory_files_ok:
            issues.append(f"{len(self.front_matter_issues)} memory file issue(s)")
            issues.extend(f"  - {i}" for i in self.front_matter_issues)
        if not self.export_dir_ok:
            err = self.export_dir_error or "missing"
            issues.append(f"export directory not ok: {err}")
        for mismatch in self.status_agreement:
            issues.append(str(mismatch))
        return issues


def _check_status_agreement(
    events: list[dict[str, object]], memories: list[Memory]
) -> list[DoctorStatusMismatch]:
    """Compare each memory's materialized status with the latest status event."""
    # Build latest status per memory_id from status-bearing events.
    status_map: dict[str, str] = {}
    for ev in events:
        ev_type = str(ev.get("type", ""))
        mid = str(ev.get("memory_id", ""))
        if not mid or not ev_type.startswith("memory."):
            continue
        if ev_type in ("memory.accepted", "memory.rejected", "memory.deprecated"):
            status_map[mid] = ev_type.split(".", 1)[1]
        elif ev_type == "memory.proposed":
            status_map.setdefault(mid, "candidate")
    mismatches: list[DoctorStatusMismatch] = []
    for mem in memories:
        expected = status_map.get(mem.id)
        if expected is not None and expected != mem.status.value:
            mismatches.append(
                DoctorStatusMismatch(
                    memory_id=mem.id,
                    materialized=mem.status.value,
                    event=expected,
                )
            )
    return mismatches


__all__ = [
    "AGENT_ACTOR",
    "DEFAULT_ACTOR",
    "DEFAULT_EXPORT_FILENAME",
    "EXPORTS_DIRNAME",
    "LEDGER_FILENAME",
    "MEMORIES_DIRNAME",
    "MEMORY_TYPE_FOLDERS",
    "MemoryStore",
    "REQUIRED_FRONTMATTER_FIELDS",
    "REQUIRED_MEMORY_SUBDIRS",
    "STATE_DIR_NAME",
    "STATE_FILENAME",
    "USER_ACTOR",
    "DoctorReport",
    "find_project_or_init",
    "init_store",
    "open_store",
]
