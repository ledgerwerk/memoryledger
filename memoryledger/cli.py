from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

import typer

from . import __version__
from .errors import MemoryledgerError
from .guardrails import validate_memory, validate_scope_path
from .intake import import_run_html as intake_run_html
from .intake import import_text as intake_text
from .models import KINDS, RENDER_TARGETS, SCOPES, Config
from .render import export as export_rendered
from .render import render_all, write_rendered
from .review import transition
from .storage import Store, find_config, init_workspace, load_config

app = typer.Typer(no_args_is_help=True)
memory_app = typer.Typer(no_args_is_help=True)
review_app = typer.Typer(no_args_is_help=True)
import_app = typer.Typer(no_args_is_help=True)
agents_app = typer.Typer(no_args_is_help=True)
app.add_typer(memory_app, name="memory")
app.add_typer(review_app, name="review")
app.add_typer(import_app, name="import")
app.add_typer(agents_app, name="agents")


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
) -> None:
    try:
        if (
            kind not in KINDS
            or scope not in SCOPES
            or render_target not in RENDER_TARGETS
        ):
            raise MemoryledgerError(
                "INVALID_ARGUMENT", "invalid kind, scope, or render target"
            )
        config, store = _load()
        validate_scope_path(config.root, scope_path)
        content = _read_input(text, file, stdin)
        memory = store.create(
            kind, title, content, evidence, scope, scope_path, render_target
        )
        validate_memory(memory, content, evidence)
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
) -> None:
    try:
        _config, store = _load()
        memory = store.update_content(memory_id, _read_input(text, file, stdin), reason)
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
            memory, store.read_content(memory_id), store.read_evidence(memory_id)
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


@review_app.command("list")
def review_list(json_output: bool = typer.Option(False, "--json")) -> None:
    return memory_list(status="candidate", json_output=json_output)


@review_app.command("accept")
def review_accept(memory_id: str, reason: str = typer.Option(..., "--reason")) -> None:
    memory_status(memory_id, "accepted", reason)


@review_app.command("reject")
def review_reject(memory_id: str, reason: str = typer.Option(..., "--reason")) -> None:
    memory_status(memory_id, "rejected", reason)


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
