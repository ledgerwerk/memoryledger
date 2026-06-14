"""Typer CLI for memoryledger.

Commands (MVP): init, capture, list, accept, reject, search, context,
export, doctor. The ``memledger`` console script points at the same ``app``.

CLI boundary rules:
- Catch ``ledgercore.errors.LedgerCoreError`` and ``memoryledger.errors.*``
  and convert them into clean Typer errors (exit code 1, plain message).
- Print IDs and paths predictably for tests.
- No rich terminal formatting in the MVP.
"""

from __future__ import annotations

import functools
import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated, NoReturn, ParamSpec, TypeVar

import typer
from ledgercore.errors import LedgerCoreError

from memoryledger.config import (
    ExportTarget,
    find_project,
)
from memoryledger.errors import MemoryLedgerError
from memoryledger.export import write_export
from memoryledger.model import Confidence, MemoryStatus, MemoryType
from memoryledger.retrieval import (
    ScoredMemory,
    eligible_memories,
    render_context_from_query,
    score_memory,
    tokenize,
)
from memoryledger.store import (
    AGENT_ACTOR,
    DEFAULT_ACTOR,
    MemoryStore,
    find_project_or_init,
    init_store,
    open_store,
)

app = typer.Typer(
    name="memoryledger",
    help="Auditable long-term project memory ledger for coding agents.",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _actor_from_env() -> str:
    return os.environ.get("MEMORYLEDGER_ACTOR") or DEFAULT_ACTOR


def _now_from_env() -> datetime | None:
    raw = os.environ.get("MEMORYLEDGER_NOW")
    if not raw:
        return None
    # Accept a simple ISO timestamp for test determinism.
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _fail(message: str, *, code: int = 1) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=code)


P = ParamSpec("P")
R = TypeVar("R")


def _handle_domain_errors(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator: convert domain/ledgercore errors into clean Typer exits."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except MemoryLedgerError as exc:
            _fail(exc.message)
        except LedgerCoreError as exc:
            _fail(f"ledgercore error: {exc}")
        except OSError as exc:
            # Filesystem permission/space errors -> clean message, no traceback.
            _fail(f"filesystem error: {exc}")

    return wrapper


def _open_store_or_fail(start: Path | None = None) -> MemoryStore:
    return open_store(start, actor=_actor_from_env(), now=_now_from_env())


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@app.command()
@_handle_domain_errors
def init(
    project_dir: Annotated[
        Path | None,
        typer.Option("--project-dir", help="Project root to initialize."),
    ] = None,
) -> None:
    """Create .memoryledger.toml and the .memoryledger/ layout.

    Idempotent for the directory layout. Does not overwrite an existing
    .memoryledger.toml.
    """
    root = (project_dir or Path.cwd()).resolve()
    store = init_store(root, actor=_actor_from_env(), now=_now_from_env(), force=False)
    typer.echo(f"Initialized memoryledger at {store.project.config_path}")
    typer.echo(f"State directory: {store.state_dir}")


# ---------------------------------------------------------------------------
# capture
# ---------------------------------------------------------------------------


@app.command()
@_handle_domain_errors
def capture(
    type_: Annotated[str, typer.Option("--type", help="Memory type.")],
    title: Annotated[str, typer.Option("--title", help="Memory title.")],
    body: Annotated[
        Path,
        typer.Option("--body", help="Path to a UTF-8 text file with the memory body."),
    ],
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Tag (repeatable)."),
    ] = None,
    scope: Annotated[str, typer.Option("--scope", help="Memory scope.")] = "project",
    source: Annotated[str, typer.Option("--source", help="Memory source.")] = "session",
    confidence: Annotated[
        str, typer.Option("--confidence", help="Confidence value.")
    ] = Confidence.observed.value,
    applies_to: Annotated[
        list[str] | None,
        typer.Option("--applies-to", help="Glob pattern this applies to (repeatable)."),
    ] = None,
) -> None:
    """Capture a new memory as a candidate from a body file.

    Project/rule memories always start as ``candidate`` regardless of policy.
    """
    try:
        mem_type = MemoryType(type_)
    except ValueError:
        _fail(f"Unknown memory type: {type_}")
        return
    try:
        conf = Confidence(confidence)
    except ValueError:
        _fail(f"Unknown confidence: {confidence}")
        return

    if not body.exists() or not body.is_file():
        _fail(f"Body file not found: {body}")
        return
    text = body.read_text(encoding="utf-8")

    store = _open_store_or_fail()
    mem = store.capture_memory(
        memory_type=mem_type,
        title=title,
        body=text,
        tags=list(tags) if tags else None,
        applies_to=list(applies_to) if applies_to else None,
        scope=scope,
        source=source,
        confidence=conf,
        actor=AGENT_ACTOR,
        now=_now_from_env(),
    )
    typer.echo(mem.id)


# ---------------------------------------------------------------------------
# accept / reject
# ---------------------------------------------------------------------------


@app.command()
@_handle_domain_errors
def accept(
    memory_id: Annotated[
        str, typer.Argument(help="Memory id, e.g. mem-YYYYMMDD-0001.")
    ],
) -> None:
    """Accept a candidate memory (promote to accepted project memory)."""
    store = _open_store_or_fail()
    store.set_status(
        memory_id,
        MemoryStatus.accepted,
        event_type="memory.accepted",
        actor="user",
        now=_now_from_env(),
    )
    typer.echo(f"Accepted {memory_id}")


@app.command()
@_handle_domain_errors
def reject(
    memory_id: Annotated[
        str, typer.Argument(help="Memory id, e.g. mem-YYYYMMDD-0001.")
    ],
) -> None:
    """Reject a memory (excluded from materialized memory)."""
    store = _open_store_or_fail()
    store.set_status(
        memory_id,
        MemoryStatus.rejected,
        event_type="memory.rejected",
        actor="user",
        now=_now_from_env(),
    )
    typer.echo(f"Rejected {memory_id}")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@app.command(name="list")
@_handle_domain_errors
def list_memories(
    status: Annotated[
        str | None,
        typer.Option("--status", help="Filter by status (candidate/accepted/...)."),
    ] = None,
    include_local: Annotated[
        bool, typer.Option("--include-local", help="Include local memories.")
    ] = False,
    include_deprecated: Annotated[
        bool, typer.Option("--include-deprecated", help="Include deprecated memories.")
    ] = False,
    include_rejected: Annotated[
        bool, typer.Option("--include-rejected", help="Include rejected memories.")
    ] = False,
) -> None:
    """List memories from materialized Markdown files.

    Defaults exclude rejected and deprecated memories.
    """
    store = _open_store_or_fail()
    all_memories = list(store.iter_memories())

    if status:
        try:
            status_filter = MemoryStatus(status)
        except ValueError:
            _fail(f"Unknown status: {status}")
            return
        filtered = [m for m in all_memories if m.status == status_filter]
    else:
        filtered = eligible_memories(
            all_memories,
            include_candidates=True,
            include_local=include_local,
            include_deprecated=include_deprecated,
            include_rejected=include_rejected,
        )

    # Deterministic order: newest first, then id.
    filtered.sort(key=lambda m: m.id)
    filtered.sort(key=lambda m: m.updated_at, reverse=True)

    if not filtered:
        typer.echo("(no memories)")
        return
    for mem in filtered:
        typer.echo(f"{mem.id}\t{mem.type.value}\t{mem.status.value}\t{mem.title}")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@app.command()
@_handle_domain_errors
def search(
    query: Annotated[str, typer.Argument(help="Lexical query.")],
    include_candidates: Annotated[
        bool, typer.Option("--include-candidates", help="Include candidate memories.")
    ] = False,
    include_local: Annotated[
        bool, typer.Option("--include-local", help="Include local memories.")
    ] = False,
    limit: Annotated[int | None, typer.Option("--limit", help="Max results.")] = None,
) -> None:
    """Deterministic lexical search over memories."""
    store = _open_store_or_fail()
    memories = list(store.iter_memories())
    tokens = tokenize(query)
    eligible = eligible_memories(
        memories,
        include_candidates=include_candidates,
        include_local=include_local,
    )
    scored = [score_memory(mem, tokens) for mem in eligible]
    if tokens:

        def neutral(s: ScoredMemory) -> int:
            return s.status_boost + s.type_boost

        scored = [s for s in scored if s.score != neutral(s)]
    scored.sort(key=lambda s: s.memory.id)
    scored.sort(key=lambda s: s.memory.updated_at, reverse=True)
    from memoryledger.retrieval import TYPE_BOOST

    scored.sort(key=lambda s: TYPE_BOOST.get(s.memory.type.value, 0), reverse=True)
    scored.sort(key=lambda s: s.score, reverse=True)
    if limit is not None and limit >= 0:
        scored = scored[:limit]
    for item in scored:
        mem = item.memory
        typer.echo(f"{mem.id}\t{mem.status.value}\t{item.score}\t{mem.title}")


# ---------------------------------------------------------------------------
# context
# ---------------------------------------------------------------------------


@app.command()
@_handle_domain_errors
def context(
    query: Annotated[str, typer.Argument(help="Context query.")],
    include_local: Annotated[
        bool, typer.Option("--include-local", help="Include local memories.")
    ] = False,
) -> None:
    """Render a bounded Markdown context bundle of relevant memories."""
    store = _open_store_or_fail()
    retrieval = store.config.retrieval
    text = render_context_from_query(
        list(store.iter_memories()),
        query,
        retrieval=retrieval,
        include_local=include_local or retrieval.include_local_by_default,
    )
    typer.echo(text, nl=False)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@app.command()
@_handle_domain_errors
def export(
    target: Annotated[
        str, typer.Option("--target", help="Export target (agents-md).")
    ] = ExportTarget.agents_md.value,
    output: Annotated[
        Path | None, typer.Option("--output", help="Override export path.")
    ] = None,
) -> None:
    """Write the memory export (agents-md by default)."""
    try:
        target_enum = ExportTarget(target)
    except ValueError:
        _fail(f"Unknown export target: {target}")
        return
    store = _open_store_or_fail()
    out_path = output or store.export_path
    memories = list(store.iter_memories())
    text = write_export(
        memories,
        target=target_enum,
        output_path=out_path,
        state_dir=store.state_dir,
    )
    # Append a memory.exported event (memory_id '*' for a full export).
    store.append_event(
        event_type="memory.exported",
        memory_id="*",
        payload={
            "target": target_enum.value,
            "path": str(out_path),
            "bytes": len(text),
        },
        actor=DEFAULT_ACTOR,
        now=_now_from_env(),
    )
    typer.echo(str(out_path))


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


@app.command()
@_handle_domain_errors
def doctor(
    create_export_dir: Annotated[
        bool,
        typer.Option(
            "--create-export-dir/--no-create-export-dir",
            help="Allow creating a missing export directory.",
        ),
    ] = True,
) -> None:
    """Run read-only health checks (optionally creates the export dir)."""
    store = _open_store_or_fail()
    report = store.diagnose(create_export_dir=create_export_dir)
    typer.echo(f"Config path: {report.config_path}")
    typer.echo(f"State dir:   {report.state_dir}")
    typer.echo(f"Events:      {report.event_count}")
    typer.echo(
        f"Export dir:  {report.export_dir}"
        + (" (created)" if report.export_dir_created else "")
    )
    if report.ok:
        typer.echo("OK: memoryledger is healthy.")
        return
    typer.echo("Issues:")
    for issue in report.all_issues:
        typer.echo(f"  - {issue}")
    raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    app()


if __name__ == "__main__":
    main()


# Keep find_project referenced for downstream tooling/imports.
_ = (find_project, find_project_or_init, sys)
