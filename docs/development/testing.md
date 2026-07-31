# Testing

The repository quality gates are:

```bash
python -m pytest -q
python -m ruff check .
python -m mypy memoryledger
python -m sphinx -W --keep-going -b html docs docs/_build/html
python docs/_scripts/generate_cli_reference.py --check
```

Tests use temporary canonical workspaces rather than repository-local legacy
state. Documentation tests cover command/catalog synchronization, generated
reference freshness, MyST structure, links, and important CLI examples.
