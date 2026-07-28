"""Central CLI execution, error handling, and output emission.

Resolve ``CommonCLIState``, centralize command execution, catch and translate
exceptions, emit human or JSON output, add deprecation warnings, provide
common input-source validation, and provide helpers for legacy command-local
``--json``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer
from ledgercore.cli import (
    CLIError,
    CLIWarning,
    CommonCLIState,
    ErrorEnvelope,
    ExitCode,
    SuccessEnvelope,
)

from .errors import MemoryledgerError


def resolve_global_state(
    root: Path | None = None,
    json_output: bool = False,
) -> CommonCLIState:
    """Resolve global CLI state once at startup."""
    resolved_root = Path(root).resolve(strict=False) if root else Path.cwd().resolve()
    return CommonCLIState(
        tool="memoryledger",
        root=resolved_root,
        json_output=json_output,
    )


def emit_success(
    state: CommonCLIState,
    command: str,
    result: dict[str, object] | None = None,
    events: tuple[dict[str, object], ...] = (),
    human_output: str | None = None,
) -> None:
    """Emit a successful command result in JSON or human mode."""
    if state.json_output:
        envelope = SuccessEnvelope(
            tool=state.tool,
            command=command,
            result=result or {},
            events=events,
            warnings=state.warnings,
        )
        typer.echo(envelope.to_json())
        return

    # Human mode
    for w in state.warnings:
        msg = f"warning: {w.message}"
        if w.replacement:
            msg += f" Use `{w.replacement}` instead."
        typer.echo(msg, err=True)
    if human_output is not None:
        typer.echo(human_output, nl=False if human_output.endswith("\n") else True)


def emit_error(
    state: CommonCLIState,
    command: str,
    error: CLIError,
    events: tuple[dict[str, object], ...] = (),
) -> None:
    """Emit a CLI error in JSON or human mode."""
    if state.json_output:
        envelope = ErrorEnvelope(
            tool=state.tool,
            command=command,
            error={
                "code": error.code,
                "message": error.message,
                "details": dict(error.details),
                "remediation": list(error.remediation),
            },
            events=events,
            warnings=state.warnings,
        )
        typer.echo(envelope.to_json())
    else:
        for w in state.warnings:
            msg = f"warning: {w.message}"
            if w.replacement:
                msg += f" Use `{w.replacement}` instead."
            typer.echo(msg, err=True)
        typer.echo(f"error: {error.code}: {error.message}", err=True)
        for hint in error.remediation:
            typer.echo(f"  hint: {hint}", err=True)
    raise typer.Exit(int(error.exit_code))


def translate_error(exc: Exception) -> CLIError:
    """Translate Memoryledger domain errors into framework-neutral CLIError."""
    if isinstance(exc, CLIError):
        return exc
    if isinstance(exc, typer.Exit):
        raise exc
    if isinstance(exc, MemoryledgerError):
        return _map_memoryledger_error(exc)
    # Unexpected exception
    return CLIError(
        code="internal_error",
        message=str(exc),
        exit_code=ExitCode.DOMAIN_FAILURE,
    )


def _map_memoryledger_error(exc: MemoryledgerError) -> CLIError:
    """Map a MemoryledgerError code to exit code and remediation."""
    code = exc.code

    # Exit code 3: unavailable or missing
    unavailable_codes = {
        "NO_CONFIG",
        "NOT_FOUND",
        "TEMPLATE_NOT_FOUND",
        "MIGRATION_REQUIRED",
        "STORAGE_MIGRATION_REQUIRED",
        "FEATURE_UNAVAILABLE",
        "LEDGERCORE_VERSION_UNSUPPORTED",
    }
    # Exit code 4: conflict or failed precondition
    conflict_codes = {
        "ADOPTION_BACKUP_REQUIRED",
        "ADOPTION_SOURCE_CHANGED",
        "ALREADY_GENERATED",
        "MANUAL_FILE",
        "PROJECT_UUID_MISMATCH",
        "STORAGE_LAYOUT_AMBIGUOUS",
        "STORAGE_MIGRATION_CONFLICT",
        "STORAGE_MIGRATION_INCOMPLETE",
        "STORAGE_REGISTRATION_CONFLICT",
        "TEMPLATE_CONFLICT",
        "STORAGE_MIGRATION_LOCKED",
        "STORAGE_MIGRATION_PLAN_INVALID",
        "STORAGE_MIGRATION_SOURCE_CHANGED",
        "STORAGE_MIGRATION_DESTINATION_CHANGED",
        "STORAGE_MIGRATION_RECOVERY_AMBIGUOUS",
    }
    # Exit code 2: usage or malformed input
    usage_codes = {
        "INPUT_REQUIRED",
        "INVALID_ARGUMENT",
        "INVALID_KIND",
        "INVALID_SCOPE",
        "INVALID_RENDER_TARGET",
        "INVALID_STATUS",
        "INVALID_EVIDENCE_KIND",
        "INVALID_LINE_RANGE",
        "MISSING_MEMORY_ID",
        "MISSING_REASON",
        "MISSING_MIGRATION",
        "INVALID_CONFIG",
        "INVALID_CONFIG_VERSION",
        "INVALID_PLAN_FILE",
    }

    if code in usage_codes:
        exit_code = ExitCode.USAGE
    elif code in unavailable_codes:
        exit_code = ExitCode.UNAVAILABLE
    elif code in conflict_codes:
        exit_code = ExitCode.CONFLICT
    else:
        exit_code = ExitCode.DOMAIN_FAILURE

    return CLIError(
        code=code.lower(),
        message=exc.message,
        exit_code=exit_code,
        details={"domain_code": code, **(exc.details or {})},
    )


def run_command(
    state: CommonCLIState,
    command: str,
    fn: Callable[..., dict[str, object]],
    *args: Any,
    **kwargs: Any,
) -> None:
    """Centralized command execution boundary.

    Handlers return values and never emit directly.
    This boundary catches exceptions and emits output.
    """
    try:
        result = fn(*args, **kwargs)
        emit_success(state, command, result=result)
    except typer.Exit:
        raise
    except Exception as exc:
        cli_error = translate_error(exc)
        emit_error(state, command, cli_error)


def _read_input(text: str | None, file: Path | None, stdin: bool) -> str:
    """Validate and read exactly one input source."""
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


def deprecated_json_option() -> CLIWarning:
    """Warning for command-local --json option."""
    return CLIWarning(
        code="deprecated_option",
        message="--json should be used as a global option: `memoryledger --json ...`",
        replacement="memoryledger --json",
    )
