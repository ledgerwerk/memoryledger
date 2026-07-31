# Lifecycle

```text
candidate ──accept──> accepted
candidate ──reject──> rejected
accepted ────────────> archived
rejected ────────────> archived
```

Intake defaults to `candidate`, which prevents unreviewed material from
appearing in generated output. Accept and reject transitions require a reason;
the reason becomes review evidence. Archive removes a record from active
rendering without pretending that it never existed.

Rendering includes accepted records by default. `include_rejected` can opt
rejected records into a configured render, while `include_local` controls local
scope records. Candidates remain excluded by default. The CLI and service layer
validate the target status and reason before updating storage, so direct
acceptance without review context is rejected.
