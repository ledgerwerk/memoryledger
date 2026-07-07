from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

import typer

from . import __version__
from .adopt import adopt, adoption_plan, verify_adoption
from .errors import MemoryledgerError
from .evidence_scan import apply as apply_scan
from .evidence_scan import scan as scan_evidence
from .guardrails import validate_memory, validate_scope_path
from .intake import import_run_html as intake_run_html
from .intake import import_text as intake_text
from .models import (
    EVIDENCE_KINDS,
    KINDS,
    RENDER_TARGETS,
    SCOPES,
    STATUSES,
    Config,
    EvidenceRef,
)
from .render import export as export_rendered
from .render import render_all, write_rendered
from .review import transition
from .storage import (
    Store,
    find_config,
    init_workspace,
    linked_docs_dir_migration,
    load_config,
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
scan_app = typer.Typer(no_args_is_help=True)
schema_app = typer.Typer(no_args_is_help=True)
migrate_app = typer.Typer(no_args_is_help=True)
app.add_typer(memory_app, name="memory")
memory_app.add_typer(evidence_app, name="evidence")
app.add_typer(review_app, name="review")
app.add_typer(import_app, name="import")
app.add_typer(agents_app, name="agents")
app.add_typer(templates_app, name="templates")
app.add_typer(scan_app, name="evidence")
app.add_typer(schema_app, name="schema")
app.add_typer(migrate_app, name="migrate")


def _json(data: object) -> None:
    typer.echo(json.dumps(data, indent=2, sort_keys=True))


def _load() -> tuple[Config, Store]:
    config = load_config()
    return config, Store(config)


def _read_input(text: str | None, file: Path | None, stdin: bool) -> str:
    choices = sum([text is not None, file is not None, stdin])
    if choices != 1:
        raise MemoryledgerError(
            "INPUT_REQUIRED", "Provide exactly one of --text, --file, or --stdin"
        )
    if text is not None:
        return text
    if file is not None:
        return file.read_text()
    return sys.stdin.read()


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, MemoryledgerError):
        typer.echo(f"error: {exc.code}: {exc.message}", err=True)
        raise typer.Exit(1) from exc
    raise exc


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


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def init(
    project_name: str | None = None,
    memoryledger_dir: str = ".memoryledger",
    hidden_config: bool = False,
) -> None:
    try:
        config = init_workspace(project_name, memoryledger_dir, hidden_config)
        typer.echo(f"initialized {config.config_path}")
    except Exception as exc:
        _handle_error(exc)


@app.command()
def status(
    check: bool = False, json_output: bool = typer.Option(False, "--json")
) -> None:
    try:
        config_path = find_config()
        if config_path is None:
            data = {"ok": False, "configured": False}
            if json_output:
                _json(data)
            else:
                typer.echo("No memoryledger config found.")
            if check:
                raise typer.Exit(1)
            return
        config, store = _load()
        memories = store.all_memories()
        status_data: dict[str, object] = {
            "ok": True,
            "configured": True,
            "config": str(config.config_path),
            "storage": str(config.storage_dir),
            "memories": len(memories),
        }
        if json_output:
            _json(status_data)
        else:
            typer.echo(f"config: {config.config_path}")
            typer.echo(f"storage: {config.storage_dir}")
            typer.echo(f"memories: {len(memories)}")
    except Exception as exc:
        _handle_error(exc)


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json")) -> None:
    try:
        config, _store = _load()
        issues: list[str] = []
        if not config.storage_dir.exists():
            issues.append("storage directory missing")
        data = {"ok": not issues, "issues": issues}
        if json_output:
            _json(data)
        else:
            typer.echo("ok" if not issues else "issues: " + ", ".join(issues))
    except Exception as exc:
        _handle_error(exc)


@app.command()
def info(
    json_output: bool = typer.Option(False, "--json"),
    paths_only: bool = False,
    no_content: bool = False,
) -> None:
    try:
        config, _store = _load()
        data = {
            "config": str(config.config_path),
            "root": str(config.root),
            "storage": str(config.storage_dir),
        }
        if json_output:
            _json(data)
        else:
            for value in data.values() if paths_only else data.items():
                typer.echo(value if paths_only else f"{value[0]}: {value[1]}")
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
        config = load_config()
        result = render_all(config)
        written = write_rendered(config, result, out)
        if print_output:
            typer.echo(result.root_text, nl=False)
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
        config = load_config()
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
        config = load_config()
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
    data = {"commands": ["memoryledger render", "memoryledger export"]}
    _json(data) if json_output else typer.echo(
        "memoryledger render\nmemoryledger export"
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
