# CLI contract APIs

These modules define result envelopes and command metadata used by automation
and generated documentation. The command catalog, not raw Typer implementation
details, is the source of truth for the generated reference.

```{automodule} memoryledger.cli_common
:members:
:member-order: bysource
:show-inheritance:
```

```{automodule} memoryledger.command_catalog
:members:
:member-order: bysource
:show-inheritance:
```

```{automodule} memoryledger.command_results
:members:
:member-order: bysource
:show-inheritance:
```

The CLI contract emits `ledgerwerk.cli.v1`; callers should use its schema and
exit codes rather than human output.
