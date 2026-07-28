from __future__ import annotations

from .cli import app


def main() -> None:
    """Canonical memoryledger entry point."""
    app()


def deprecated_memledger_main() -> None:
    """Deprecated memledger entry point with warning."""
    import typer

    typer.echo(
        "warning: `memledger` is deprecated; use `memoryledger` instead.",
        err=True,
    )
    app()
