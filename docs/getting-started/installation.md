# Installation

Memoryledger supports Python 3.10 and newer and requires Ledgercore
`>=0.6.0,<0.7.0`.

## Standard installation

```bash
python -m pip install memoryledger
memoryledger --version
```

The `memoryledger` executable is the canonical entry point. `memledger` remains
available as a deprecated alias and emits a deprecation warning.

## Development and documentation installations

From a checkout:

```bash
python -m pip install -e .
python -m pip install -r docs/requirements.txt
```

Alternatively install the project development group:

```bash
python -m pip install -e ".[dev]"
```

The documentation requirements file installs documentation tooling; it does
not install Memoryledger itself.
