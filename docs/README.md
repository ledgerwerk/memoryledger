# MemoryLedger Documentation

This directory contains the Sphinx documentation for MemoryLedger.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
uv pip install -e ".[dev]"
```

### Building HTML Documentation

To build the HTML documentation:

```bash
cd docs
make html
```

The built documentation will be available in `docs/_build/html/`.

### Building PDF Documentation

To build PDF documentation (requires LaTeX):

```bash
cd docs
make latexpdf
```

## Documentation Structure

- `conf.py` - Sphinx configuration file
- `index.rst` - Main documentation index
- `changelog.md` - Project changelog (included from project root)
- `api/` - API documentation
- `_build/` - Built documentation output (not version controlled)

## Read the Docs

This project is configured to build documentation on Read the Docs. The configuration is in `.readthedocs.yaml` at the project root.