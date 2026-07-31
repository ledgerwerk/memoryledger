# Evidence scanning

`evidence scan` inspects repository files and proposes candidate memories. It
can recognize project evidence such as `pyproject.toml` and mypy settings,
Ruff configuration, pre-commit hooks, test commands, and project-specific
configuration. Scan output is proposal-only until candidates are applied and
then reviewed; a scan never silently creates accepted policy.

```bash
memoryledger evidence scan
memoryledger evidence scan --apply-candidates
memoryledger review list
```
