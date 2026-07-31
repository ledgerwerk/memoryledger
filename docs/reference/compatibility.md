# Compatibility

- Python: 3.10 or newer.
- Ledgercore: `>=0.6.0,<0.7.0`.
- Storage: canonical schema 3, with read and migration support for recognized
  legacy layouts.
- Paths: repository-relative paths are confined to the project root; platform
  path separators are resolved by `pathlib`.
- Source-tree installs: if package metadata is unavailable, the version falls
  back safely for documentation, but runtime compatibility still depends on an
  installed Ledgercore package.
- Windows: use `python -m sphinx` and `docs\make.bat html`; replace POSIX
  heredocs with a file or PowerShell equivalent when following CLI examples.

The shared Ledgercore manifest and binding markers are authoritative. A local
mount override changes resolution for one machine and does not rewrite the
project's canonical registration.
