# Configuration API

Configuration loading is supported for integrations that need effective
settings. It validates version 2 fields, merges global defaults, and rejects
unknown fields without writing files. See the [configuration reference](../reference/configuration)
for the TOML contract.

```{automodule} memoryledger.config
:members:
:member-order: bysource
:show-inheritance:
```

```python
from memoryledger.config import load_tool_config
```

Writing requires an explicit caller action through `write_tool_config`; loading
alone is read-only.
