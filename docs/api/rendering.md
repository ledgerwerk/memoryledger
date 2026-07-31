# Rendering API

Rendering converts canonical records into owned derived documents. Rendering is
deterministic; export and artifact initialization are the side-effecting steps.

```{automodule} memoryledger.render
:members:
:member-order: bysource
:show-inheritance:
```

```{automodule} memoryledger.adopt
:members:
:member-order: bysource
:show-inheritance:
```

```python
from memoryledger.render import render_all
```

Adoption APIs are preview-first and preserve source hashes and backups.
