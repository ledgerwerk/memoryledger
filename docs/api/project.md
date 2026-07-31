# Project API

Project discovery and Ledgercore compatibility helpers are semi-public
integration APIs. Discovery is read-only and must not initialize storage. Path
resolution is confined by the project and Ledgercore bindings.

```{automodule} memoryledger.project
:members:
:member-order: bysource
:show-inheritance:
```

```{automodule} memoryledger.ledgercore_compat
:members:
:member-order: bysource
:show-inheritance:
```

```python
from memoryledger.project import discover_storage, resolve_workspace
```

Workspace creation and artifact initialization are explicit write operations;
callers should prefer the CLI for those workflows.
