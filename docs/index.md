# Memoryledger

Memoryledger is an auditable long-term project-memory ledger and deterministic
`AGENTS.md` renderer. Durable canonical memory lives in Ledgercore-managed
schema-3 storage; `AGENTS.md` and owned linked documents are derived output.

```{warning}
Do not edit generated `AGENTS.md` files or marker-owned linked documents
directly. Update memory records, review them, build, and export instead.
```

## Five-command quick start

```bash
memoryledger init
memoryledger memory create --kind rule --title "Use plans" --stdin <<'EOF'
Always create and review a plan before implementation.
EOF
memoryledger review accept memory-0001 --reason "User approved the project rule."
memoryledger build
memoryledger export
```

Install from Python 3.10+ with `python -m pip install memoryledger` or use an
editable checkout as described in [Installation](getting-started/installation).
The CLI is the primary supported interface. The Python API is useful for
integrations, but its supported boundary is explicitly marked in the API
reference. The project is active and its compatibility target is Ledgercore
`>=0.6.0,<0.7.0`.

```{toctree}
:caption: Getting started
:maxdepth: 2

getting-started/index
```

```{toctree}
:caption: Concepts
:maxdepth: 2

concepts/index
```

```{toctree}
:caption: Guides
:maxdepth: 2

guides/index
```

```{toctree}
:caption: Reference
:maxdepth: 2

reference/index
```

```{toctree}
:caption: Python API
:maxdepth: 2

api/index
```

```{toctree}
:caption: Development
:maxdepth: 2

development/index
```

```{toctree}
:hidden:

changelog
```
