# Storage model

Memoryledger uses Ledgercore's shared schema-3 manifest. The manifest identifies
the project UUID and registers a Memoryledger tool with:

```toml
[ledgers.memoryledger.mounts.data]
storage = "project"

[ledgers.memoryledger.mounts.artifacts]
storage = "cache"
```

Project data contains the config binding, storage metadata, memories, and
imports. Derived artifacts use a cache checkout identity so separate checkouts
do not overwrite one another. Binding markers and the config binding connect
the registration to those paths.

Discovery and read-only layout validation do not write. Local mount overrides
are machine-local and can change resolved locations without changing shared
manifest intent. The artifacts mount is initialized only when a build or other
rendering operation actually writes output. See [Storage layout](../reference/storage-layout)
for exact canonical and legacy paths.
