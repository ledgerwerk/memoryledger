# Migrations

Use the migration framework for all layout changes. It validates source and
destination, writes a deterministic plan and fingerprints, copies first,
activates last, and records a journal:

```bash
memoryledger migrate status
memoryledger migrate plan storage-layout
memoryledger migrate apply storage-layout --dry-run
memoryledger migrate apply storage-layout --plan-file <path>
memoryledger migrate recover storage-layout --journal <path>
memoryledger migrate cleanup storage-layout --dry-run
memoryledger migrate cleanup storage-layout --yes
```

Supported migration names include `storage-layout`, `storage-v2`, and
`linked-docs-dir`. Plans are read-only until apply. Ownership, source/destination
fingerprints, and activation ordering protect against ambiguous or conflicting
layouts. Recovery uses the journal after an incomplete operation; cleanup
requires confirmation after successful activation. Manual copying is forbidden
because it bypasses these checks and can create split-brain storage.
