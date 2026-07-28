from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

import typer
from ledgercore.cli import (
    CommonCLIState,
)

from . import __version__
from .adopt import adopt, adoption_plan, verify_adoption
from .cli_common import (
    _read_input,
    emit_error,
    emit_success,
    resolve_global_state,
    translate_error,
)
from .command_results import NextActionResult
from .errors import MemoryledgerError
from .evidence_scan import apply as apply_scan
from .evidence_scan import scan as scan_evidence
from .guardrails import validate_memory, validate_scope_path
from .intake import import_run_html as intake_run_html
from .intake import import_text as intake_text
from .migration import apply_plan, build_plan, cleanup_legacy, recover_plan, write_plan
from .models import (
    EVIDENCE_KINDS,
    KINDS,
    RENDER_TARGETS,
    SCOPES,
    STATUSES,
    EvidenceRef,
)
from .project import (
    discover_storage,
    ensure_artifacts,
    resolve_workspace,
    workspace_as_compat_config,
)
from .render import export as export_rendered
from .render import render_all, write_rendered
from .review import transition
from .storage import (
    Store,
    init_workspace,
    linked_docs_dir_migration,
)
from .templates import (
    apply_template,
    find_template,
    load_global_config,
    remove_template,
    template_content,
)

app = typer.Typer(no_args_is_help=True)
memory_app = typer.Typer(no_args_is_help=True)
evidence_app = typer.Typer(no_args_is_help=True)
review_app = typer.Typer(no_args_is_help=True)
import_app = typer.Typer(no_args_is_help=True)
agents_app = typer.Typer(no_args_is_help=True)
templates_app = typer.Typer(no_args_is_help=True)
template_app = typer.Typer(no_args_is_help=True)
scan_app = typer.Typer(no_args_is_help=True)
schema_app = typer.Typer(no_args_is_help=True)
migrate_app = typer.Typer(no_args_is_help=True)
storage_app = typer.Typer(no_args_is_help=True)
config_app = typer.Typer(no_args_is_help=True)
app.add_typer(config_app, name="config")
app.add_typer(memory_app, name="memory")
memory_app.add_typer(evidence_app, name="evidence")
app.add_typer(review_app, name="review")
app.add_typer(import_app, name="import")
app.add_typer(agents_app, name="agents")
app.add_typer(templates_app, name="templates", hidden=True)  # deprecated alias
app.add_typer(template_app, name="template")
app.add_typer(scan_app, name="evidence")
app.add_typer(schema_app, name="schema")
app.add_typer(migrate_app, name="migrate")
app.add_typer(storage_app, name="storage")


def _json(data: object) -> None:
    """Legacy JSON helper - use emit_success in new code."""
    typer.echo(json.dumps(data, indent=2, sort_keys=True))


def _load() -> tuple[Any, Any]:
    from .project import resolve_workspace, workspace_as_compat_config

    workspace = resolve_workspace()
    config = workspace_as_compat_config(workspace)
    return config, Store(config)


_GLOBAL_STATE: CommonCLIState | None = None


def get_state(ctx: typer.Context | None = None) -> CommonCLIState:
    """Get CLI state from Typer context or fall back to legacy global state."""
    if ctx is not None and ctx.obj and "state" in ctx.obj:
        return ctx.obj["state"]
    if _GLOBAL_STATE is not None:
        return _GLOBAL_STATE
    return CommonCLIState(tool="memoryledger", root=Path.cwd().resolve())


# Backward-compatible alias
_get_state = get_state


def _load_from_root(root: Path | None = None) -> tuple[Any, Any]:
    from .project import resolve_workspace, workspace_as_compat_config

    workspace = resolve_workspace(root)
    config = workspace_as_compat_config(workspace)
    return config, Store(config)


def _handle_error(exc: Exception, state: CommonCLIState | None = None) -> None:
    if isinstance(exc, typer.Exit):
        raise
    cli_error = translate_error(exc)
    emit_error(state or get_state(), "", cli_error)


KIND_ALIASES = {"package-workflow": "procedure", "package_workflow": "procedure"}
SCOPE_ALIASES = {"project": "repo"}
RENDER_TARGET_ALIASES: dict[str, str] = {}


def _normalize_choice(name: str, value: str) -> str:
    aliases = {
        "kind": KIND_ALIASES,
        "scope": SCOPE_ALIASES,
        "render_target": RENDER_TARGET_ALIASES,
    }[name]
    return aliases.get(value, value)


def _validate_choice(name: str, value: str, choices: tuple[str, ...]) -> str:
    normalized = _normalize_choice(name, value)
    if normalized not in choices:
        valid = ", ".join(choices)
        raise MemoryledgerError(
            f"INVALID_{name.upper()}",
            f"invalid {name} '{value}'. Valid: {valid}",
        )
    return normalized


def _schema_values() -> dict[str, list[str]]:
    return {
        "kinds": list(KINDS),
        "scopes": list(SCOPES),
        "render_targets": list(RENDER_TARGETS),
        "statuses": list(STATUSES),
        "evidence_kinds": list(EVIDENCE_KINDS),
    }


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
    root: Path | None = typer.Option(None, "--root", help="Project root directory."),
    json_output: bool = typer.Option(
        False, "--json", help="JSON output (ledgerwerk.cli.v1 envelope)."
    ),
) -> None:
    if version:
        if json_output:
            from ledgercore.cli import SuccessEnvelope

            env = SuccessEnvelope(
                tool="memoryledger", command="version", result={"version": __version__}
            )
            typer.echo(env.to_json())
        else:
            typer.echo(f"memoryledger {__version__}")
        raise typer.Exit()
    state = resolve_global_state(root=root, json_output=json_output)
    ctx.ensure_object(dict)
    ctx.obj["state"] = state


@app.command()
def init(
    ctx: typer.Context,
    project_name: str | None = None,
    memoryledger_dir: str = ".memoryledger",
    hidden_config: bool = False,
) -> None:
    """Initialize a new Memoryledger project."""
    state = get_state(ctx)
    try:
        config = init_workspace(project_name, memoryledger_dir, hidden_config)
        emit_success(state, "init", result={"config_path": str(config.config_path)})
    except Exception as exc:
        _handle_error(exc, state)


@app.command()
def status(
    ctx: typer.Context,
    check: bool = False,
    json_output: bool = typer.Option(False, "--json", hidden=True),
) -> None:
    state = get_state(ctx)
    if json_output:
        state = CommonCLIState(
            tool=state.tool, root=state.root, json_output=True, warnings=state.warnings
        )
    try:
        discovery = discover_storage(state.root)
        if discovery.status == "uninitialized":
            emit_success(state, "status", result={"ok": False, "configured": False})
            if check:
                raise typer.Exit(1)
            return
        config, store = _load_from_root(state.root)
        memories = store.all_memories()
        status_data: dict[str, object] = {
            "ok": True,
            "configured": True,
            "config": str(config.config_path),
            "storage": str(config.storage_dir),
            "memories": len(memories),
            "layout": discovery.status,
            "canonical": discovery.canonical_registered,
        }
        human = "\n".join(f"{k}: {v}" for k, v in status_data.items())
        emit_success(state, "status", result=status_data, human_output=human)
    except Exception as exc:
        _handle_error(exc, state)


@app.command()
def doctor(
    ctx: typer.Context, json_output: bool = typer.Option(False, "--json", hidden=True)
) -> None:
    state = get_state(ctx)
    if json_output:
        state = CommonCLIState(
            tool=state.tool, root=state.root, json_output=True, warnings=state.warnings
        )
    try:
        config, _store = _load_from_root(state.root)
        discovery = discover_storage(state.root)
        issues: list[str] = []
        if not config.storage_dir.exists():
            issues.append("storage directory missing")
        result = {"ok": not issues, "issues": issues, "layout": discovery.status}
        human = "ok" if not issues else "issues: " + ", ".join(issues)
        emit_success(state, "doctor", result=result, human_output=human)
    except Exception as exc:
        _handle_error(exc, state)


@app.command()
def info(
    ctx: typer.Context,
    paths_only: bool = False,
    no_content: bool = False,
    json_output: bool = typer.Option(False, "--json", hidden=True),
) -> None:
    state = get_state(ctx)
    if json_output:
        state = CommonCLIState(
            tool=state.tool, root=state.root, json_output=True, warnings=state.warnings
        )
    try:
        config, _store = _load_from_root(state.root)
        discovery = discover_storage(state.root)
        result = {
            "config": str(config.config_path),
            "root": str(config.root),
            "storage": str(config.storage_dir),
            "layout": discovery.status,
            "project_uuid": config.project_uuid,
            "project_name": config.project_name,
        }
        human = "\n".join(f"{k}: {v}" for k, v in result.items())
        emit_success(state, "info", result=result, human_output=human)
    except Exception as exc:
        _handle_error(exc, state)


@storage_app.command("where")
def storage_where(ctx: typer.Context) -> None:
    state = get_state(ctx)
    try:
        discovery = discover_storage(state.root)
        result = {
            "status": discovery.status,
            "project_root": str(discovery.project_root),
            "manifest": str(discovery.canonical_manifest)
            if discovery.canonical_manifest
            else None,
            "config": str(discovery.canonical_config)
            if discovery.canonical_config
            else None,
            "data": str(discovery.canonical_data)
            if discovery.canonical_data
            else str(discovery.legacy_data)
            if discovery.legacy_data
            else None,
            "legacy_config": str(discovery.legacy_config)
            if discovery.legacy_config
            else None,
        }
        human = "\n".join(f"{k}: {v}" for k, v in result.items())
        emit_success(state, "storage where", result=result, human_output=human)
    except Exception as exc:
        _handle_error(exc, state)


@storage_app.command("verify")
@storage_app.command("validate", hidden=True)
def storage_verify(
    ctx: typer.Context,
    strict: bool = typer.Option(False, "--strict"),
) -> None:
    """Validate storage layout and bindings (read-only)."""
    state = get_state(ctx)
    try:
        discovery = discover_storage(state.root)
        ok = discovery.status in {"canonical", "legacy", "uninitialized"}
        validation_details = {}
        if discovery.status == "canonical" and strict:
            try:
                from ledgercore.config import locate_ledger_project
                from ledgercore.layout import (
                    parse_ledger_project_manifest,
                    resolve_ledger_layout,
                )
                from ledgercore.storage_binding import validate_ledger_layout_storage

                locator = locate_ledger_project(state.root)
                if locator and locator.manifest_path.exists():
                    manifest = parse_ledger_project_manifest(locator.manifest_path)
                    layout = resolve_ledger_layout(locator, manifest, "memoryledger")
                    report = validate_ledger_layout_storage(layout)
                    validation_details = {
                        "mounts_checked": len(report.results)
                        if hasattr(report, "results")
                        else 0,
                        "valid": report.ok if hasattr(report, "ok") else True,
                    }
                    if hasattr(report, "ok") and not report.ok:
                        ok = False
            except Exception as e:
                validation_details["error"] = str(e)
                ok = False
        result = {
            "ok": ok,
            "status": discovery.status,
            "strict": strict,
            **validation_details,
        }
        human = "ok" if ok else f"invalid: {discovery.status}"
        emit_success(state, "storage validate", result=result, human_output=human)
        if not ok:
            raise typer.Exit(1)
    except Exception as exc:
        _handle_error(exc, state)


@storage_app.command("migrate")
def storage_migrate(
    dry_run: bool = typer.Option(False, "--dry-run"),
    plan_file: Path | None = typer.Option(None, "--plan-file"),
    adopt_project_uuid: bool = typer.Option(False, "--adopt-project-uuid"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        plan = build_plan(adopt_project_uuid=adopt_project_uuid)
        saved = write_plan(plan, plan_file)
        data = plan.to_dict()
        data["plan_file"] = str(saved)
        if not dry_run:
            data.update(apply_plan(plan, adopt_project_uuid=adopt_project_uuid))
        if json_output:
            _json(data)
        else:
            typer.echo(f"Migration: {plan.migration_id}")
            typer.echo("Source layout: legacy")
            typer.echo(f"Legacy data: {plan.source_data}")
            typer.echo(f"Target data: {plan.target_data}")
            typer.echo(f"Version: {plan.target_version}")
            typer.echo(f"Next memory: {plan.next_memory_number:04d}")
            typer.echo("Activation: manifest update last")
            if not dry_run:
                typer.echo("Phase: complete")
    except Exception as exc:
        _handle_error(exc)


@storage_app.command("recover")
def storage_recover(
    journal: Path = typer.Option(..., "--journal"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        plan = build_plan()
        if (
            journal
            != plan.root / ".ledger" / "migrations" / f"{plan.migration_id}.toml"
        ):
            raise MemoryledgerError(
                "STORAGE_MIGRATION_CONFLICT",
                "journal does not match the deterministic migration plan",
            )
        data = recover_plan(plan)
        _json(data) if json_output else typer.echo(
            f"{data['migration_id']}: {data['phase']}"
        )
    except Exception as exc:
        _handle_error(exc)


@storage_app.command("cleanup-legacy")
def storage_cleanup_legacy(
    yes: bool = typer.Option(False, "--yes"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    discard_rendered: bool = typer.Option(False, "--discard-rendered"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        plan = build_plan()
        data = cleanup_legacy(
            plan, confirm=yes and not dry_run, discard_rendered=discard_rendered
        )
        removals = data.get("remove", [])
        _json(data) if json_output else typer.echo(
            "\n".join(str(item) for item in removals)
            if isinstance(removals, list)
            else ""
        )
    except Exception as exc:
        _handle_error(exc)


@memory_app.command("create")
def memory_create(
    kind: str = typer.Option(..., "--kind"),
    title: str = typer.Option(..., "--title"),
    text: str | None = typer.Option(None, "--text"),
    file: Path | None = typer.Option(None, "--file"),
    stdin: bool = typer.Option(False, "--stdin"),
    evidence: str = typer.Option("", "--evidence"),
    scope: str = typer.Option("global", "--scope"),
    scope_path: str = typer.Option("", "--scope-path"),
    render_target: str = typer.Option("root_agents", "--render-target"),
    section: str = typer.Option("", "--section"),
) -> None:
    try:
        kind = _validate_choice("kind", kind, KINDS)
        scope = _validate_choice("scope", scope, SCOPES)
        render_target = _validate_choice("render_target", render_target, RENDER_TARGETS)
        config, store = _load()
        validate_scope_path(config.root, scope_path)
        content = _read_input(text, file, stdin)
        memory = store.create(
            kind,
            title,
            content,
            evidence,
            scope,
            scope_path,
            render_target,
            section=section,
        )
        typer.echo(memory.id)
    except Exception as exc:
        _handle_error(exc)


@memory_app.command("list")
def memory_list(
    kind: str | None = typer.Option(None, "--kind"),
    status: str | None = typer.Option(None, "--status"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        _config, store = _load()
        items = [
            m
            for m in store.all_memories()
            if (kind is None or m.kind == kind)
            and (status is None or m.status == status)
        ]
        if json_output:
            _json({"memories": [m.to_dict() for m in items]})
        else:
            for m in items:
                typer.echo(f"{m.id} {m.status} {m.kind} {m.title}")
    except Exception as exc:
        _handle_error(exc)


@memory_app.command("show")
def memory_show(
    memory_id: str,
    content: bool = False,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        _config, store = _load()
        memory = store.get(memory_id)
        body = store.read_content(memory_id)
        if json_output:
            data = memory.to_dict()
            if content:
                data["content"] = body
            _json(data)
        else:
            typer.echo(f"{memory.id} {memory.status} {memory.kind} {memory.title}")
            if content:
                typer.echo(body.rstrip())
    except Exception as exc:
        _handle_error(exc)


@memory_app.command("status")
def memory_status(
    memory_id: str, status: str, reason: str = typer.Option(..., "--reason")
) -> None:
    try:
        _config, store = _load()
        memory = transition(store, memory_id, status, reason)
        typer.echo(f"{memory.id} {memory.status}")
    except Exception as exc:
        _handle_error(exc)


@memory_app.command("edit")
def memory_edit(
    memory_id: str,
    reason: str = typer.Option(..., "--reason"),
    text: str | None = typer.Option(None, "--text"),
    file: Path | None = typer.Option(None, "--file"),
    stdin: bool = typer.Option(False, "--stdin"),
    section: str | None = typer.Option(None, "--section"),
) -> None:
    try:
        _config, store = _load()
        memory = store.update_content(
            memory_id, _read_input(text, file, stdin), reason, section=section
        )
        typer.echo(f"{memory.id} v{memory.version:04d}")
    except Exception as exc:
        _handle_error(exc)


@memory_app.command("append")
def memory_append(
    memory_id: str,
    reason: str = typer.Option(..., "--reason"),
    text: str | None = typer.Option(None, "--text"),
    file: Path | None = typer.Option(None, "--file"),
    stdin: bool = typer.Option(False, "--stdin"),
) -> None:
    try:
        _config, store = _load()
        memory = store.update_content(
            memory_id, _read_input(text, file, stdin), reason, append=True
        )
        typer.echo(f"{memory.id} v{memory.version:04d}")
    except Exception as exc:
        _handle_error(exc)


@memory_app.command("validate")
def memory_validate(
    memory_id: str, json_output: bool = typer.Option(False, "--json")
) -> None:
    try:
        _config, store = _load()
        memory = store.get(memory_id)
        validate_memory(
            memory,
            store.read_content(memory_id),
            store.read_evidence(memory_id),
            store.config.root,
        )
        if json_output:
            _json({"ok": True, "memory_id": memory_id})
        else:
            typer.echo("ok")
    except Exception as exc:
        _handle_error(exc)


@memory_app.command("versions")
def memory_versions(
    memory_id: str, json_output: bool = typer.Option(False, "--json")
) -> None:
    try:
        _config, store = _load()
        versions = sorted(
            p.stem for p in (store.memory_dir(memory_id) / "versions").glob("v*.yaml")
        )
        if json_output:
            _json({"versions": versions})
        else:
            typer.echo("\n".join(versions))
    except Exception as exc:
        _handle_error(exc)


@memory_app.command("diff")
def memory_diff(
    memory_id: str,
    from_version: str = typer.Option(..., "--from"),
    to: str = typer.Option(..., "--to"),
) -> None:
    try:
        _config, store = _load()
        base = store.memory_dir(memory_id) / "versions"
        a = (base / f"{from_version}.md").read_text().splitlines()
        b = (base / f"{to}.md").read_text().splitlines()
        typer.echo("\n".join(difflib.unified_diff(a, b, from_version, to)))
    except Exception as exc:
        _handle_error(exc)


@evidence_app.command("list")
def evidence_list(
    memory_id: str, json_output: bool = typer.Option(False, "--json")
) -> None:
    try:
        _config, store = _load()
        refs = [ref.to_dict() for ref in store.get(memory_id).evidence_refs]
        if json_output:
            _json({"memory_id": memory_id, "evidence": refs})
        else:
            for ref in refs:
                typer.echo(f"{ref['kind']} {ref['title']} {ref['uri']}")
    except Exception as exc:
        _handle_error(exc)


@evidence_app.command("add")
def evidence_add(
    memory_id: str,
    kind: str = typer.Option(..., "--kind"),
    title: str = typer.Option(..., "--title"),
    uri: str = typer.Option(..., "--uri"),
    reason: str = typer.Option(..., "--reason"),
    excerpt: str = typer.Option("", "--excerpt"),
    line_start: int | None = typer.Option(None, "--line-start"),
    line_end: int | None = typer.Option(None, "--line-end"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        if kind not in EVIDENCE_KINDS:
            raise MemoryledgerError("INVALID_EVIDENCE_KIND", kind)
        _config, store = _load()
        memory = store.add_evidence(
            memory_id,
            EvidenceRef(
                kind=kind,
                title=title,
                uri=uri,
                excerpt=excerpt,
                line_start=line_start,
                line_end=line_end,
            ),
            reason,
        )
        data = {"memory_id": memory.id, "version": memory.version}
        _json(data) if json_output else typer.echo(f"{memory.id} v{memory.version:04d}")
    except Exception as exc:
        _handle_error(exc)


@review_app.command("list")
def review_list(json_output: bool = typer.Option(False, "--json")) -> None:
    return memory_list(status="candidate", json_output=json_output)


def _review_bulk(status: str, reason: str, json_output: bool) -> None:
    if not reason.strip():
        raise MemoryledgerError("MISSING_REASON", "bulk review requires --reason")
    _config, store = _load()
    changed: list[str] = []
    for memory in store.all_memories():
        if memory.status != "candidate":
            continue
        transition(store, memory.id, status, reason)
        changed.append(memory.id)
    key = "accepted" if status == "accepted" else "rejected"
    if json_output:
        _json({key: changed})
    else:
        typer.echo("\n".join(changed))


@review_app.command("accept")
def review_accept(
    memory_id: str | None = typer.Argument(None),
    all_candidates: bool = typer.Option(False, "--all"),
    reason: str = typer.Option(..., "--reason"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        if all_candidates:
            _review_bulk("accepted", reason, json_output)
            return
        if memory_id is None:
            raise MemoryledgerError(
                "MISSING_MEMORY_ID", "memory id is required unless --all is used"
            )
        memory_status(memory_id, "accepted", reason)
    except Exception as exc:
        _handle_error(exc)


@review_app.command("reject")
def review_reject(
    memory_id: str | None = typer.Argument(None),
    all_candidates: bool = typer.Option(False, "--all"),
    reason: str = typer.Option(..., "--reason"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        if all_candidates:
            _review_bulk("rejected", reason, json_output)
            return
        if memory_id is None:
            raise MemoryledgerError(
                "MISSING_MEMORY_ID", "memory id is required unless --all is used"
            )
        memory_status(memory_id, "rejected", reason)
    except Exception as exc:
        _handle_error(exc)


@review_app.command("archive")
def review_archive(memory_id: str, reason: str = typer.Option(..., "--reason")) -> None:
    memory_status(memory_id, "archived", reason)


@app.command()
def render(
    out: Path | None = None,
    print_output: bool = typer.Option(False, "--print"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        workspace = resolve_workspace()
        config = workspace_as_compat_config(workspace)
        result = render_all(config)
        if print_output:
            typer.echo(result.root_text, nl=False)
            written: list[Path] = []
        else:
            ensure_artifacts(workspace)
            written = write_rendered(config, result, out)
        if json_output:
            _json(
                {
                    "root": str(written[0]),
                    "linked_docs": sorted(result.linked_docs),
                    "nested_docs": sorted(result.nested_docs),
                }
            )
    except Exception as exc:
        _handle_error(exc)


@app.command()
def export(
    out: Path | None = None,
    json_output: bool = typer.Option(False, "--json"),
    backup: bool = False,
    include_nested: bool = False,
) -> None:
    try:
        config, _store = _load()
        result = render_all(config)
        written = export_rendered(config, result, out, backup, include_nested)
        if json_output:
            _json({"written": [str(p) for p in written]})
        else:
            for path in written:
                typer.echo(path)
    except Exception as exc:
        _handle_error(exc)


@app.command()
def finalize(
    accept_all: bool = typer.Option(False, "--accept-all", "--accept-candidates"),
    reason: str = typer.Option("", "--reason"),
    render_step: bool = typer.Option(True, "--render/--no-render"),
    export_step: bool = typer.Option(False, "--export/--no-export"),
    json_output: bool = typer.Option(False, "--json"),
    backup: bool = False,
    include_nested: bool = False,
    out: Path | None = None,
) -> None:
    try:
        config, store = _load()
        accepted: list[str] = []
        steps: list[str] = []
        if accept_all:
            if not reason.strip():
                raise MemoryledgerError(
                    "MISSING_REASON", "finalize acceptance requires --reason"
                )
            for memory in store.all_memories():
                if memory.status == "candidate":
                    transition(store, memory.id, "accepted", reason)
                    accepted.append(memory.id)
            steps.append("accept")
        rendered: list[str] = []
        exported: list[str] = []
        if render_step or export_step:
            result = render_all(config)
        if render_step:
            ensure_artifacts(resolve_workspace())
            rendered = [str(path) for path in write_rendered(config, result, out)]
            steps.append("render")
        if export_step:
            exported = [
                str(path)
                for path in export_rendered(config, result, out, backup, include_nested)
            ]
            steps.append("export")
        data = {
            "accepted": accepted,
            "rendered": rendered,
            "exported": exported,
            "steps": steps,
        }
        if json_output:
            _json(data)
        else:
            for key in ("accepted", "rendered", "exported"):
                for value in data[key]:
                    typer.echo(value)
    except Exception as exc:
        _handle_error(exc)


@migrate_app.command("storage-v2")
def migrate_storage_v2(
    plan: bool = typer.Option(False, "--plan"),
    apply: bool = typer.Option(False, "--apply"),
    backup: bool = False,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        if plan == apply:
            raise MemoryledgerError(
                "INVALID_ARGUMENT", "choose exactly one of --plan or --apply"
            )
        _config, store = _load()
        data = (
            store.storage_v2_plan() if plan else store.migrate_storage_v2(backup=backup)
        )
        if json_output:
            _json(data)
        else:
            paths = data.get("changed" if apply else "create", [])
            for path in paths if isinstance(paths, list) else []:
                typer.echo(str(path))
    except Exception as exc:
        _handle_error(exc)


@migrate_app.command("linked-docs-dir")
def migrate_linked_docs_dir(
    from_dir: str = typer.Option("docs/agents", "--from"),
    to_dir: str = typer.Option("agent_docs", "--to"),
    plan: bool = typer.Option(False, "--plan"),
    apply: bool = typer.Option(False, "--apply"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        if plan == apply:
            raise MemoryledgerError(
                "INVALID_ARGUMENT", "choose exactly one of --plan or --apply"
            )
        config, _store = _load()
        data = linked_docs_dir_migration(config, from_dir, to_dir, apply=apply)
        if json_output:
            _json(data)
        else:
            moved = data["move"]
            for path in moved if isinstance(moved, list) else []:
                typer.echo(str(path))
    except Exception as exc:
        _handle_error(exc)


@agents_app.command("plan")
def agents_plan(json_output: bool = typer.Option(False, "--json")) -> None:
    data = {
        "commands": [
            "memoryledger preview --output -",
            "memoryledger build",
            "memoryledger export --output AGENTS.md",
        ]
    }
    _json(data) if json_output else typer.echo(
        "memoryledger preview --output -\nmemoryledger build\nmemoryledger export --output AGENTS.md"
    )


@agents_app.command("render")
def agents_render(json_output: bool = typer.Option(False, "--json")) -> None:
    render(json_output=json_output)


@agents_app.command("export")
def agents_export(json_output: bool = typer.Option(False, "--json")) -> None:
    export(json_output=json_output)


@agents_app.command("adopt")
def agents_adopt(
    target: Path = typer.Argument(Path("AGENTS.md")),
    apply: bool = typer.Option(False, "--apply"),
    backup: bool = typer.Option(False, "--backup"),
    accept: bool = typer.Option(False, "--accept"),
    reason: str = typer.Option("", "--reason"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        config, store = _load()
        path = target if target.is_absolute() else config.root / target
        try:
            path.resolve().relative_to(config.root.resolve())
        except ValueError as exc:
            raise MemoryledgerError(
                "INVALID_ADOPTION_PATH", "adoption target must be in the workspace"
            ) from exc
        if accept and not reason.strip():
            raise MemoryledgerError(
                "MISSING_REASON", "--accept requires a review reason"
            )
        if not apply:
            data = adoption_plan(path, config.root)
        else:
            ids, backup_path = adopt(
                store, path, backup=backup, accept=accept, reason=reason
            )
            data = {
                "target": str(path),
                "candidates": ids,
                "backup": str(backup_path),
                "mutated": True,
            }
        if json_output:
            _json(data)
        elif apply:
            typer.echo("\n".join(ids))
        else:
            proposals = data.get("proposals", [])
            for proposal in proposals if isinstance(proposals, list) else []:
                if isinstance(proposal, dict):
                    typer.echo(f"{proposal['kind']} {proposal['title']}")
    except Exception as exc:
        _handle_error(exc)


@schema_app.command("values")
def schema_values(json_output: bool = typer.Option(False, "--json")) -> None:
    data = _schema_values()
    if json_output:
        _json(data)
    else:
        for key, values in data.items():
            typer.echo(f"{key}: {', '.join(values)}")


@agents_app.command("verify-adoption")
def agents_verify_adoption(
    source: Path = typer.Option(..., "--source"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        config, store = _load()
        path = source if source.is_absolute() else config.root / source
        data = verify_adoption(store, path)
        if json_output:
            _json(data)
        else:
            typer.echo("ok" if data["ok"] else "failed")
            missing = data["missing_headings"]
            if isinstance(missing, list) and missing:
                typer.echo(
                    "missing headings: " + ", ".join(str(item) for item in missing)
                )
        if not data["ok"]:
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as exc:
        _handle_error(exc)


@templates_app.command("list")
def templates_list(json_output: bool = typer.Option(False, "--json")) -> None:
    try:
        templates = load_global_config().templates
        data = [
            {"id": item.id, "version": item.version, "title": item.title}
            for item in templates
        ]
        if json_output:
            _json({"templates": data})
        else:
            for item in data:
                typer.echo(f"{item['id']} {item['version']} {item['title']}")
    except Exception as exc:
        _handle_error(exc)


@templates_app.command("show")
def templates_show(
    template_id: str, json_output: bool = typer.Option(False, "--json")
) -> None:
    try:
        template = find_template(load_global_config(), template_id)
        data = {
            "id": template.id,
            "version": template.version,
            "title": template.title,
            "kind": template.kind,
            "content": template_content(template),
        }
        _json(data) if json_output else typer.echo(data["content"], nl=False)
    except Exception as exc:
        _handle_error(exc)


def _template_apply(
    template_id: str,
    json_output: bool,
    *,
    accept: bool = False,
    reason: str = "",
) -> None:
    config, store = _load()
    if config.template_policy.ids and template_id not in config.template_policy.ids:
        raise MemoryledgerError("TEMPLATE_NOT_ENABLED", template_id)
    if accept and not reason.strip():
        raise MemoryledgerError("MISSING_REASON", "--accept requires a review reason")
    template = find_template(load_global_config(), template_id)
    action, memory = apply_template(store, template)
    if accept and memory.status != "accepted":
        memory = transition(store, memory.id, "accepted", reason)
    data = {"action": action, "memory_id": memory.id, "status": memory.status}
    _json(data) if json_output else typer.echo(f"{action} {memory.id}")


@templates_app.command("apply")
def templates_apply(
    template_id: str,
    accept: bool = typer.Option(False, "--accept"),
    reason: str = typer.Option("", "--reason"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        _template_apply(template_id, json_output, accept=accept, reason=reason)
    except Exception as exc:
        _handle_error(exc)


@templates_app.command("sync")
def templates_sync(
    template_id: str,
    accept: bool = typer.Option(False, "--accept"),
    reason: str = typer.Option("", "--reason"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        _template_apply(template_id, json_output, accept=accept, reason=reason)
    except Exception as exc:
        _handle_error(exc)


@templates_app.command("remove")
def templates_remove(
    template_id: str,
    reason: str = typer.Option(..., "--reason"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        _config, store = _load()
        memory = remove_template(store, template_id, reason)
        data = {"memory_id": memory.id, "status": memory.status}
        _json(data) if json_output else typer.echo(f"{memory.id} archived")
    except Exception as exc:
        _handle_error(exc)


@scan_app.command("scan")
def evidence_scan(
    apply_candidates: bool = typer.Option(False, "--apply-candidates"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        config, store = _load()
        proposals = scan_evidence(config.root)
        results = apply_scan(store, proposals) if apply_candidates else []
        data = {
            "proposals": [proposal.to_dict() for proposal in proposals],
            "applied": results,
        }
        if json_output:
            _json(data)
        elif apply_candidates:
            for result in results:
                typer.echo(f"{result['action']} {result['memory_id']}")
        else:
            for proposal in proposals:
                typer.echo(f"{proposal.path}:{proposal.line} {proposal.observed}")
    except Exception as exc:
        _handle_error(exc)


@import_app.command("text")
def import_text_cmd(
    text: str | None = typer.Option(None, "--text"),
    file: Path | None = typer.Option(None, "--file"),
    stdin: bool = typer.Option(False, "--stdin"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        _config, store = _load()
        ids = intake_text(store, _read_input(text, file, stdin))
        _json({"candidates": ids}) if json_output else typer.echo("\n".join(ids))
    except Exception as exc:
        _handle_error(exc)


@import_app.command("run-html")
def import_run_html_cmd(
    file: Path = typer.Option(..., "--file"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        _config, store = _load()
        ids = intake_run_html(store, file)
        _json({"candidates": ids}) if json_output else typer.echo("\n".join(ids))
    except Exception as exc:
        _handle_error(exc)


@import_app.command("current-run")
def import_current_run(json_output: bool = typer.Option(False, "--json")) -> None:
    data = {
        "ok": False,
        "unsupported": True,
        "message": "current-run import is not supported in this runtime",
    }
    _json(data) if json_output else typer.echo(data["message"])
    raise typer.Exit(2)


# ── Canonical commands (Phase 4) ──────────────────────────────────────────


# ── Canonical commands (Phase 4) ──────────────────────────────────────────


# -- memory set-status (canonical; memory status is deprecated alias) --
@memory_app.command("set-status")
def memory_set_status(
    memory_id: str,
    status: str,
    reason: str = typer.Option(..., "--reason"),
) -> None:
    """Change the lifecycle status of one memory."""
    state = _get_state()
    try:
        _config, store = _load()
        from .review import transition

        memory = transition(store, memory_id, status, reason)
        emit_success(
            state,
            "memory set-status",
            result={
                "memory_id": memory.id,
                "status": memory.status,
                "version": memory.version,
            },
            events=(
                {
                    "type": "memory.status_changed",
                    "memory_id": memory.id,
                    "status": status,
                },
            ),
        )
    except Exception as exc:
        _handle_error(exc)


# -- memory update (canonical; memory edit is deprecated alias) --
@memory_app.command("update")
def memory_update(
    memory_id: str,
    reason: str = typer.Option(..., "--reason"),
    text: str | None = typer.Option(None, "--text"),
    file: Path | None = typer.Option(None, "--file"),
    stdin: bool = typer.Option(False, "--stdin"),
    section: str | None = typer.Option(None, "--section"),
) -> None:
    """Replace the body of a memory record."""
    state = _get_state()
    try:
        _config, store = _load()
        memory = store.update_content(
            memory_id, _read_input(text, file, stdin), reason, section=section
        )
        emit_success(
            state,
            "memory update",
            result={"memory_id": memory.id, "version": memory.version},
        )
    except Exception as exc:
        _handle_error(exc)


# -- memory archive --
@memory_app.command("archive")
def memory_archive(
    memory_id: str,
    reason: str = typer.Option(..., "--reason"),
) -> None:
    """Archive a memory record."""
    state = _get_state()
    try:
        _config, store = _load()
        from .review import transition

        memory = transition(store, memory_id, "archived", reason)
        emit_success(
            state,
            "memory archive",
            result={
                "memory_id": memory.id,
                "status": "archived",
                "version": memory.version,
            },
            events=(
                {
                    "type": "memory.status_changed",
                    "memory_id": memory.id,
                    "to": "archived",
                },
            ),
        )
    except Exception as exc:
        _handle_error(exc)


# -- preview (render without side effects) --
@app.command()
def preview(
    output: str = typer.Option("-", "--output", "-o"),
) -> None:
    """Render without modifying authoritative or derived state."""
    state = _get_state()
    try:
        from .project import resolve_workspace, workspace_as_compat_config
        from .render import render_all

        workspace = resolve_workspace()
        config = workspace_as_compat_config(workspace)
        result = render_all(config)
        if output == "-":
            typer.echo(result.root_text, nl=False)
        else:
            out_path = Path(output)
            out_path.write_text(result.root_text)
            typer.echo(str(out_path))
        # In JSON mode, return rendered structure info
        if state.json_output:
            emit_success(
                state,
                "preview",
                result={
                    "linked_docs": sorted(result.linked_docs),
                    "nested_docs": sorted(result.nested_docs),
                },
            )
    except Exception as exc:
        _handle_error(exc)


# -- build (materialize derived artifacts) --
@app.command()
def build(
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Materialize deterministic derived artifacts in the artifacts mount."""
    state = _get_state()
    try:
        from .project import (
            ensure_artifacts,
            resolve_workspace,
            workspace_as_compat_config,
        )
        from .render import render_all, write_rendered

        workspace = resolve_workspace()
        config = workspace_as_compat_config(workspace)
        result = render_all(config)
        ensure_artifacts(workspace)
        written = write_rendered(config, result, output)
        emit_success(
            state,
            "build",
            result={
                "root": str(written[0]) if written else "",
                "linked_docs": sorted(result.linked_docs),
                "nested_docs": sorted(result.nested_docs),
            },
        )
    except Exception as exc:
        _handle_error(exc)


# -- commands --
@app.command()
def commands(ctx: typer.Context) -> None:
    """List all registered commands with metadata."""
    state = get_state(ctx)
    from .command_catalog import CATALOG

    emit_success(
        state,
        "commands",
        result={"commands": CATALOG.to_dict()},
        human_output=CATALOG.human_table(),
    )


# -- help --
@app.command()
def help(ctx: typer.Context, command: list[str] = typer.Argument(None)) -> None:
    """Show help for a command path."""
    state = get_state(ctx)
    if not command:
        # Show general help

        app.info.help = "Memoryledger: auditable long-term project memory ledger."
        # Just show the app help
        typer.echo(app.info.help)
        return
    # Show help for specific command
    cmd_path = " ".join(command)
    from .command_catalog import CATALOG

    resolved = CATALOG.resolve(cmd_path)
    if resolved:
        human = f"{resolved.path}: {resolved.summary}"
        emit_success(
            state,
            "help",
            result={"path": resolved.path, "summary": resolved.summary},
            human_output=human,
        )
    else:
        raise MemoryledgerError("NOT_FOUND", f"Command '{cmd_path}' not found.")


# -- next-action --
@app.command()
def next_action(ctx: typer.Context) -> None:
    """Return the recommended next workflow action."""
    state = get_state(ctx)
    try:
        from .project import discover_storage

        discovery = discover_storage(state.root)
        if discovery.status == "uninitialized":
            result = NextActionResult(
                command="memoryledger init", reason="Project is not initialized."
            )
            emit_success(
                state,
                "next-action",
                result=result.to_dict(),
                human_output=f"{result.command}\n{result.reason}",
            )
            return
        _config, store = _load_from_root(state.root)
        candidates = [m for m in store.all_memories() if m.status == "candidate"]
        if candidates:
            result = NextActionResult(
                command="memoryledger review list",
                reason=f"{len(candidates)} candidate memories require review.",
                context={"candidate_count": len(candidates)},
            )
            emit_success(
                state,
                "next-action",
                result=result.to_dict(),
                human_output=f"{result.command}\n{result.reason}",
            )
            return
        result = NextActionResult(
            command="no action",
            reason="Project is healthy with no pending actions.",
        )
        emit_success(
            state,
            "next-action",
            result=result.to_dict(),
            human_output=f"{result.command}\n{result.reason}",
        )
    except Exception as exc:
        _handle_error(exc, state)


# -- schema list --
@schema_app.command("list")
def schema_list() -> None:
    """List available schema names."""
    state = _get_state()
    names = ["memory", "evidence", "tool-config", "migration-bundle"]
    if state.json_output:
        from ledgercore.cli import SuccessEnvelope

        typer.echo(
            SuccessEnvelope(
                tool="memoryledger", command="schema list", result={"schemas": names}
            ).to_json()
        )
    else:
        typer.echo("\n".join(names))


# -- schema show --
@schema_app.command("show")
def schema_show(
    name: str = typer.Argument(...),
) -> None:
    """Show field definitions for a schema."""
    state = _get_state()
    data = _schema_values()
    if name in data:
        if state.json_output:
            from ledgercore.cli import SuccessEnvelope

            typer.echo(
                SuccessEnvelope(
                    tool="memoryledger",
                    command="schema show",
                    result={"name": name, "values": data[name]},
                ).to_json()
            )
        else:
            typer.echo(f"{name}: {', '.join(data[name])}")
    else:
        raise MemoryledgerError(
            "NOT_FOUND",
            f"Schema '{name}' not found. Available: {', '.join(data.keys())}",
        )


# -- config show --
@config_app.command("show")
def config_show(ctx: typer.Context) -> None:
    """Show effective configuration with source tracking."""
    state = get_state(ctx)
    try:
        from .project import (
            discover_storage,
            resolve_workspace,
            workspace_as_compat_config,
        )

        discovery = discover_storage(state.root)
        if discovery.status == "uninitialized":
            raise MemoryledgerError("NO_CONFIG", "Run `memoryledger init` first.")
        workspace = resolve_workspace(state.root)
        config = workspace_as_compat_config(workspace)
        result = {
            "project_root": str(config.root),
            "config_path": str(config.config_path),
            "storage_dir": str(config.storage_dir),
            "artifacts_dir": str(config.artifacts_dir)
            if config.artifacts_dir
            else None,
            "project_name": config.project_name,
            "project_uuid": config.project_uuid,
            "ledger_code": config.ledger_code,
            "render": {
                "root_section": config.render.root_section,
            },
        }
        human = "\n".join(f"{k}: {v}" for k, v in result.items())
        emit_success(state, "config show", result=result, human_output=human)
    except Exception as exc:
        _handle_error(exc)


# -- config validate --
@config_app.command("validate")
def config_validate(ctx: typer.Context) -> None:
    """Validate configuration without writing."""
    state = get_state(ctx)
    try:
        from .project import discover_storage, resolve_workspace

        discovery = discover_storage(state.root)
        if discovery.status == "uninitialized":
            raise MemoryledgerError("NO_CONFIG", "Run `memoryledger init` first.")
        resolve_workspace(state.root)
        emit_success(
            state,
            "config validate",
            result={"valid": True, "status": "ok"},
            human_output="ok",
        )
    except Exception as exc:
        _handle_error(exc)


# -- storage set --
@storage_app.command("set")
def storage_set(
    ctx: typer.Context,
    mount: str = typer.Argument(...),
    storage: str = typer.Option(..., "--storage"),
    storage_root: Path | None = typer.Option(None, "--storage-root"),
    scope: str = typer.Option("project", "--scope"),
) -> None:
    """Set a mount's storage kind and scope."""
    state = get_state(ctx)
    try:
        if mount not in ("data", "artifacts"):
            raise MemoryledgerError(
                "INVALID_ARGUMENT", f"Unknown mount: {mount}. Valid: data, artifacts"
            )
        if storage not in ("project", "external", "user-data", "cache"):
            raise MemoryledgerError(
                "INVALID_ARGUMENT", f"Unknown storage kind: {storage}"
            )
        if mount == "data" and storage == "cache":
            raise MemoryledgerError(
                "INVALID_ARGUMENT", "data mount cannot use cache storage"
            )
        raise MemoryledgerError(
            "FEATURE_UNAVAILABLE",
            "storage set is not yet implemented. Use `migrate plan storage-layout` for topology changes.",
        )
    except Exception as exc:
        _handle_error(exc, state)


# -- storage clear-override --
@storage_app.command("clear-override")
def storage_clear_override(
    ctx: typer.Context,
    mount: str = typer.Argument(...),
) -> None:
    """Remove a local mount override."""
    state = get_state(ctx)
    try:
        if mount not in ("data", "artifacts"):
            raise MemoryledgerError("INVALID_ARGUMENT", f"Unknown mount: {mount}")
        raise MemoryledgerError(
            "FEATURE_UNAVAILABLE",
            "storage clear-override is not yet implemented.",
        )
    except Exception as exc:
        _handle_error(exc, state)


# -- migrate status, plan, apply, recover, cleanup --
@migrate_app.command("status")
def migrate_status(ctx: typer.Context) -> None:
    """Show migration status for all registered migrations."""
    state = get_state(ctx)
    try:
        from .migrations.registry import REGISTRY

        migrations = REGISTRY.status(state.root)
        result = {"migrations": migrations}
        human = "\n".join(
            f"{m['name']}: {'applied' if m.get('applied') else 'pending'}"
            for m in migrations
        )
        emit_success(state, "migrate status", result=result, human_output=human)
    except Exception as exc:
        _handle_error(exc, state)


@migrate_app.command("plan")
def migrate_plan(
    ctx: typer.Context,
    migration: str | None = typer.Argument(None),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Generate a read-only migration plan."""
    state = get_state(ctx)
    try:
        if migration is None:
            raise MemoryledgerError(
                "MISSING_MIGRATION",
                "Provide a migration name: storage-layout, storage-v2, linked-docs-dir",
            )
        from .migrations.registry import REGISTRY

        handler = REGISTRY.get(migration)
        result = handler.plan(state.root, output=output)
        emit_success(state, "migrate plan", result=result)
    except Exception as exc:
        _handle_error(exc, state)


@migrate_app.command("apply")
def migrate_apply(
    ctx: typer.Context,
    migration: str | None = typer.Argument(None),
    plan_file: Path | None = typer.Option(None, "--plan-file"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Apply a migration plan."""
    state = get_state(ctx)
    try:
        if migration is None:
            raise MemoryledgerError("MISSING_MIGRATION", "Provide a migration name")
        from .migrations.registry import REGISTRY

        handler = REGISTRY.get(migration)
        result = handler.apply(state.root, plan_file=plan_file, dry_run=dry_run)
        emit_success(state, "migrate apply", result=result)
    except Exception as exc:
        _handle_error(exc, state)


@migrate_app.command("recover")
def migrate_recover(
    ctx: typer.Context,
    journal: Path = typer.Option(..., "--journal"),
    policy: str = typer.Option("auto", "--policy"),
    migration: str | None = typer.Argument(None),
) -> None:
    """Recover from a migration journal."""
    state = get_state(ctx)
    try:
        if migration is None:
            # Default to storage-layout for backward compat
            migration = "storage-layout"
        from .migrations.registry import REGISTRY

        handler = REGISTRY.get(migration)
        result = handler.recover(state.root, journal=journal, policy=policy)
        emit_success(state, "migrate recover", result=result)
    except Exception as exc:
        _handle_error(exc, state)


@migrate_app.command("cleanup")
def migrate_cleanup(
    ctx: typer.Context,
    migration: str | None = typer.Argument(None),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes"),
) -> None:
    """Clean up legacy paths after successful migration."""
    state = get_state(ctx)
    try:
        if migration is None:
            raise MemoryledgerError("MISSING_MIGRATION", "Provide a migration name")
        from .migrations.registry import REGISTRY

        handler = REGISTRY.get(migration)
        result = handler.cleanup(state.root, dry_run=dry_run, confirm=yes)
        emit_success(state, "migrate cleanup", result=result)
    except Exception as exc:
        _handle_error(exc, state)


# ── Canonical template commands (registered on template_app) ──────────────
template_app.command("list")(templates_list)
template_app.command("show")(templates_show)
template_app.command("apply")(templates_apply)
template_app.command("sync")(templates_sync)
template_app.command("remove")(templates_remove)
