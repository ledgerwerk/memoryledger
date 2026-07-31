# Models API

This page documents the supported data-model boundary used by integrations.
The CLI remains more stable than direct model construction. Model operations are
side-effect free unless a caller passes them to storage or workflow functions.

```{automodule} memoryledger.models
:members:
:member-order: bysource
:show-inheritance:
```

Import example:

```python
from memoryledger.models import Memory, RenderConfig
```

Validation errors are raised by guardrails and storage layers; model dataclasses
do not perform workspace writes or path resolution.
