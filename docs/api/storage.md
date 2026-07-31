# Storage API

The storage API owns canonical memory records, serialization, versions, and
evidence metadata. It writes only inside resolved workspace data paths.

```{automodule} memoryledger.storage
:members:
:member-order: bysource
:show-inheritance:
```

```{automodule} memoryledger.guardrails
:members:
:member-order: bysource
:show-inheritance:
```

```python
from memoryledger.storage import Store
```

Storage methods can mutate durable records and require a validated workspace.
Guardrail exceptions should be surfaced to callers rather than bypassed.
