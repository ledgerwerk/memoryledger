# Templates

Global templates live at the user configuration path and define an id, version,
kind, title, scope, render target, and either inline `content` or a
`content_file`. Inspect and manage them with:

```bash
memoryledger template list
memoryledger template show project-rule
memoryledger template apply project-rule
memoryledger template sync project-rule
memoryledger template remove project-rule --reason "Retired template."
```

Template policy controls whether templates are enabled, which ids are allowed,
and whether auto-accept is permitted. Project policy overrides global policy;
auto-accept should be used only when an explicit review policy authorizes it.
Canonical content hashes and versions make sync updates deterministic.
