# Adopt existing `AGENTS.md`

Adoption is a preview-first migration that preserves the source and extracts
candidate memories:

```bash
memoryledger agents adopt AGENTS.md --json
memoryledger agents adopt AGENTS.md \
  --apply --backup --accept \
  --reason "User approved migration."
memoryledger agents verify-adoption \
  --source AGENTS.md.memoryledger-adopt-1.bak
memoryledger finalize --accept-all \
  --reason "User approved migration." --export
```

Preview is read-only. The plan records a source hash, heading inventory, and
full-source preservation. Apply prevalidates before changing the ledger,
deduplicates retry attempts, and uses deterministic backup names. A root source
is expected to shrink to a concise generated file while detailed content moves
to linked documents. Verification compares the adopted records and headings to
the preserved source; source-changed and backup failures stop the operation.
