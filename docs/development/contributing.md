# Contributing

Use an editable install and keep changes in the owning layer:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m mypy memoryledger
python -m sphinx -W --keep-going -b html docs docs/_build/html
```

Do not edit generated CLI or agent artifacts directly. The command catalog and
Typer tree are the source of truth for CLI documentation. Changelog ownership
belongs to releaseledger.
