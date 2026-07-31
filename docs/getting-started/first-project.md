# First project

`memoryledger init` discovers or creates the canonical Ledgercore project and
registers Memoryledger. The relevant project-local files are:

```text
.ledger/
├── ledger.toml
└── memoryledger/
    ├── .ledger-project.toml
    ├── config.toml
    └── data/
        ├── .ledger-project.toml
        ├── storage.yaml
        ├── memories/
        └── imports/
```

The generated registration uses project data and cache artifacts:

```toml
[ledgers.memoryledger.mounts.data]
storage = "project"

[ledgers.memoryledger.mounts.artifacts]
storage = "cache"
```

The project manifest carries the project UUID. Rendered artifacts are placed in
the resolved Ledgercore cache under a project- and checkout-specific path; the
exact platform-dependent path is shown by `memoryledger storage where`.
`.ledger/ledger.local.toml` may provide machine-local mount overrides and is not
the shared project configuration.
