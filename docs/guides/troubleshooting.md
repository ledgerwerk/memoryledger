# Troubleshooting

| Symptom/code                          | Remediation                                                                           |
| ------------------------------------- | ------------------------------------------------------------------------------------- |
| `NO_CONFIG`                           | Run `memoryledger init` or select the correct `--root`.                               |
| `MIGRATION_REQUIRED`                  | Inspect `migrate status`, then plan and apply the named migration.                    |
| `INVALID_LEDGER_LAYOUT`               | Run `storage validate`; repair through migration, not manual copying.                 |
| `INVALID_STORAGE_BINDING`             | Check the schema-3 manifest, binding markers, and local overrides.                    |
| `manual_file`                         | Adopt the manual file or choose a different export target; do not force overwrite.    |
| Adoption backup/source changed        | Restore the source, rerun preview, and apply only after the hash matches.             |
| Secret-like content                   | Remove the secret and store a safe reference or redacted excerpt.                     |
| Invalid scope/evidence path           | Use a repo-relative confined path and a supported enum value.                         |
| Migration conflict/incomplete journal | Stop cleanup; inspect the journal and use `migrate recover`.                          |
| Unsupported Ledgercore version        | Install a Ledgercore version in `>=0.6.0,<0.7.0`.                                     |
| Stale generated CLI docs              | Run `python docs/_scripts/generate_cli_reference.py`.                                 |
| Sphinx warning-as-error               | Fix the reported link, toctree, import, or type reference; do not disable `nitpicky`. |
