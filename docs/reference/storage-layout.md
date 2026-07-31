# Storage layout

## Canonical layout

```text
.ledger/
├── ledger.toml
├── ledger.local.toml                 # optional local override
└── memoryledger/
    ├── .ledger-project.toml
    ├── config.toml
    └── data/
        ├── .ledger-project.toml
        ├── storage.yaml
        ├── memories/
        │   └── memory-NNNN.md
        └── imports/
```

The resolved artifacts mount is in the Ledgercore cache, under the project UUID
and checkout identity, rather than necessarily in the repository. Use
`memoryledger storage where` for the active paths. The registration uses
`data=project` and `artifacts=cache`.

## Legacy layout

Legacy `.memoryledger/` or equivalent data directories are migration sources,
not recommended setup. They may contain a config, `storage.yaml`, memories, and
imports directly. Read-only discovery can identify them; migration must copy,
validate, activate, journal, and only then permit cleanup. Do not use manual
copying to move between layouts.
