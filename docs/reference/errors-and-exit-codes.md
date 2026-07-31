# Errors and exit codes

Domain errors are mapped to stable lowercase JSON codes and the Ledgercore CLI
exit-code contract. Normal expected failures use the envelope, not tracebacks.

| Domain family | Typical JSON code                                                        | Cause and remediation                                          |
| ------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------- |
| configuration | `no-config`, `invalid-config`, `invalid-config-version`                  | Initialize or correct the versioned TOML config.               |
| storage       | `invalid-ledger-layout`, `invalid-storage-binding`, `migration-required` | Validate the schema-3 manifest and use the migration workflow. |
| records       | `not-found`, `invalid-status`, `invalid-kind`, `invalid-scope`           | Use a known id and canonical enum value.                       |
| guardrails    | `secret-like-content`, `invalid-evidence-path`, `manual-file`            | Redact content, confine paths, or adopt a manual target.       |
| migration     | `migration-conflict`, `migration-incomplete`                             | Stop, inspect the plan/journal, and recover before cleanup.    |

Exit codes are 0 success, 1 domain failure, 2 usage or invalid input, 3
unavailable/missing resource, 4 conflict or failed precondition, and 5
external-process failure. The exact `domain_code` remains available in JSON
error details for automation.
