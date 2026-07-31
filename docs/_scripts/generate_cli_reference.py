#!/usr/bin/env python3
"""Generate the deterministic MyST CLI reference from Typer and the catalog."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from typer.main import get_command

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memoryledger.cli import app  # noqa: E402
from memoryledger.command_catalog import CATALOG  # noqa: E402

OUTPUT = ROOT / "docs" / "reference" / "cli.md"
MARKER = (
    "<!-- Generated from memoryledger.command_catalog and the Typer command tree. -->"
)
DO_NOT_EDIT = "<!-- Do not edit directly. -->"
GROUPS = {
    "Project": {"init", "status", "info", "doctor", "next-action", "commands", "help"},
    "Rendering": {"preview", "build", "export", "finalize"},
    "Configuration": {"config"},
    "Schema": {"schema"},
    "Memory": {"memory"},
    "Review": {"review"},
    "Evidence": {"evidence"},
    "Import": {"import"},
    "Agents": {"agents"},
    "Templates": {"template"},
    "Storage": {"storage"},
    "Migrations": {"migrate"},
}


def _walk(command: Any, prefix: tuple[str, ...] = (), hidden_parent: bool = False):
    hidden = hidden_parent or bool(getattr(command, "hidden", False))
    children = getattr(command, "commands", None)
    if children is not None:
        for name in sorted(children):
            yield from _walk(children[name], prefix + (name,), hidden)
        return
    yield " ".join(prefix), command, hidden


def command_tree() -> dict[str, Any]:
    return {path: command for path, command, _hidden in _walk(get_command(app))}


def _options(command: Any) -> list[Any]:
    return [parameter for parameter in command.params if getattr(parameter, "opts", [])]


def validate() -> tuple[dict[str, Any], list[str]]:
    commands = command_tree()
    visible = {
        path: command for path, command, hidden in _walk(get_command(app)) if not hidden
    }
    entries = list(CATALOG.entries)
    paths = [entry.path for entry in entries]
    errors: list[str] = []
    if len(paths) != len(set(paths)):
        errors.append("catalog contains duplicate command paths")
    for path, command in visible.items():
        entry = next((item for item in entries if item.path == path), None)
        if entry is None:
            errors.append(f"visible command lacks catalog metadata: {path}")
        elif not (command.help or "").strip():
            errors.append(f"visible command has empty help: {path}")
    for entry in entries:
        if entry.path not in commands:
            errors.append(f"catalog path is not registered: {entry.path}")
        if entry.deprecated and not entry.replacement:
            errors.append(f"deprecated command has no replacement: {entry.path}")
        aliases = set(entry.aliases)
        if aliases & set(paths):
            errors.append(f"alias shadows a catalog path: {entry.path}")
        if entry.path in aliases:
            errors.append(f"command aliases itself: {entry.path}")
    return commands, errors


def _group(path: str) -> str:
    root = path.split()[0]
    for name, roots in GROUPS.items():
        if root in roots:
            return name
    return "Automation"


def _format_parameter(parameter: Any) -> str:
    opts = ", ".join(parameter.opts + getattr(parameter, "secondary_opts", []))
    required = "required" if parameter.required else "optional"
    kind = "argument" if parameter.param_type_name == "argument" else "option"
    type_name = getattr(parameter.type, "name", None) or parameter.param_type_name
    details = f"{kind}; {required}; type `{type_name}`"
    if getattr(parameter, "is_flag", False):
        details += "; flag"
    if parameter.default is not None and parameter.default is not False:
        details += f"; default `{parameter.default}`"
    if parameter.help:
        details += f" — {parameter.help.strip()}"
    return f"- `{opts or parameter.name}` — {details}"


def render() -> str:
    commands, errors = validate()
    if errors:
        raise ValueError("\n".join(errors))
    entries = {entry.path: entry for entry in CATALOG.entries if not entry.deprecated}
    lines = [
        MARKER,
        DO_NOT_EDIT,
        "",
        "# CLI reference",
        "",
        "The canonical command reference is generated from the Typer command tree and `memoryledger.command_catalog.CATALOG`.",
        "",
    ]
    lines += [
        "```{note}",
        "Deprecated compatibility aliases are listed in [Deprecations](deprecations).",
        "```",
        "",
    ]
    for group in sorted(GROUPS):
        paths = sorted(path for path in entries if _group(path) == group)
        if not paths:
            continue
        lines += [f"## {group}", ""]
        for path in paths:
            entry = entries[path]
            command = commands[path]
            lines += [
                f"### `{path}`",
                "",
                entry.summary,
                "",
                f"- **Audience:** `{entry.audience}`",
                f"- **Stability:** `{entry.stability}`",
                f"- **Effect:** `{entry.effect}`",
                f"- **Workspace:** `{entry.requires_workspace}`",
                f"- **Target:** `{entry.targeting}`",
                f"- **JSON:** `{entry.supports_json}`",
                "",
            ]
            lines += [
                "**Usage**",
                "",
                f"`memoryledger {path}`",
                "",
                "**Arguments and options**",
                "",
            ]
            parameters = _options(command)
            lines += [_format_parameter(parameter) for parameter in parameters] or [
                "- None."
            ]
            lines += [
                "",
                "**Example**",
                "",
                f"```bash\nmemoryledger {path}\n```",
                "",
                "**Related commands**",
                "",
                "See the adjacent command group and the [workflow guide](../guides/memory-workflow).",
                "",
            ]
    lines += [
        "## Automation",
        "",
        "Use `memoryledger --json commands` for the machine-readable catalog. JSON output follows `ledgerwerk.cli.v1`.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="fail when the generated file is stale"
    )
    args = parser.parse_args(argv)
    try:
        content = render()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != content:
            print(f"generated CLI reference is stale: {OUTPUT}", file=sys.stderr)
            return 1
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
