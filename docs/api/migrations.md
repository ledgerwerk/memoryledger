# Migration APIs

Migration orchestration is semi-public and intentionally stricter than ordinary
file operations. Plans, fingerprints, journals, activation ordering, and
cleanup are part of the safety contract.

```{automodule} memoryledger.migration
:members:
:member-order: bysource
:show-inheritance:
```

```{automodule} memoryledger.migrations
:members:
:member-order: bysource
:show-inheritance:
```

```{automodule} memoryledger.migrations.plan_io
:members:
:member-order: bysource
:show-inheritance:
```

```{automodule} memoryledger.migrations.registry
:members:
:member-order: bysource
:show-inheritance:
```

Use the CLI migration workflow for normal operations; exceptions identify
conflict, incomplete, or invalid-plan conditions.
